# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Focused #183 control-plane, ov.conf fork compat, memory templates, and group/GLOBAL tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from openviking.config.binding import manager_over_source
from openviking.config.source import MemoryConfigSource
from openviking.server.api_keys.new import NewAPIKeyManager
from openviking.server.app import create_app
from openviking.server.auth.plugins import ApiKeyAuthPlugin
from openviking.server.config import ServerConfig
from openviking.server.dependencies import set_service
from openviking.server.identity import RequestContext, Role
from openviking.service.session_service import SessionService
from openviking_cli.utils.config.open_viking_config import (
    OpenVikingConfig,
    OpenVikingConfigSingleton,
)


class _MemAGFS:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def read(self, path: str, ctx=None):
        del ctx
        if path not in self.files:
            from openviking.pyagfs import AGFSNotFoundError

            raise AGFSNotFoundError(path)
        return self.files[path]

    def write(self, path: str, data: bytes, ctx=None):
        del ctx
        self.files[path] = bytes(data)
        return path

    def ensure_parent_dirs(self, path: str, ctx=None):
        del path, ctx
        return {}

    def rm(self, path: str, recursive: bool = False, force: bool = True, ctx=None):
        del recursive, force, ctx
        self.files.pop(path, None)
        return {}

    def ls(self, path: str, ctx=None):
        del path, ctx
        return []

    def pathlock_acquire_exact(self, ctx=None, path: str = "", *_args, **_kwargs):
        del ctx
        return {"lease_ref": f"exact:{path}"}

    def pathlock_release(self, *_args, **_kwargs):
        pass


@pytest.fixture
def isolated_ov_singleton():
    OpenVikingConfigSingleton.reset_instance()
    yield
    OpenVikingConfigSingleton.reset_instance()


def test_fork_custom_ov_conf_fields_preserved(tmp_path, isolated_ov_singleton):
    """Preserve fork ov.conf fields (skills, output_language_override, vlm.stream, rerank)."""
    conf_file = tmp_path / "ov.conf"
    conf_file.write_text(
        json.dumps(
            {
                "skills": {"enabled": True},
                "output_language_override": "zh-CN",
                "allow_private_networks": True,
                "vlm": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "api_key": "k-vlm",
                    "stream": True,
                },
                "embedding": {
                    "dense": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "api_key": "k-emb",
                        "dimension": 1536,
                    },
                    "max_input_tokens": 4096,
                    "allow_metadata_override": False,
                },
                "rerank": {
                    "provider": "cohere",
                    "model": "rerank-english-v3.0",
                    "api_key": "k-rerank",
                    "timeout": 15.0,
                    "max_input_tokens": 2048,
                },
            }
        ),
        encoding="utf-8",
    )
    cfg = OpenVikingConfig.from_dict(json.loads(conf_file.read_text(encoding="utf-8")))
    assert cfg.output_language_override == "zh-CN"
    assert cfg.allow_private_networks is True
    assert cfg.vlm.stream is True
    assert cfg.embedding.max_input_tokens == 4096
    assert cfg.rerank.timeout == 15.0


@pytest.mark.asyncio
async def test_183_admin_control_plane_memory_templates_and_global_users(
    tmp_path, isolated_ov_singleton, monkeypatch
):
    OpenVikingConfigSingleton.initialize(
        config_dict={
            "storage": {"workspace": str(tmp_path / "ws")},
            "embedding": {
                "dense": {
                    "provider": "openai",
                    "model": "test-emb",
                    "api_key": "test-key",
                    "dimension": 1024,
                }
            },
        }
    )
    mem_agfs = _MemAGFS()

    class _FakeFS:
        def __init__(self, agfs):
            self.agfs = agfs
            self._async_agfs = agfs

        async def mkdir(self, uri: str, exist_ok: bool = False, ctx=None):
            del uri, exist_ok, ctx

        async def read_file(self, uri: str, ctx=None):
            del ctx
            raw = mem_agfs.files.get(uri)
            if raw is None:
                from openviking_cli.exceptions import NotFoundError

                raise NotFoundError(uri, "file")
            return raw.decode("utf-8")

        async def write_file(self, uri: str, content: str, ctx=None, **_kwargs):
            del ctx
            mem_agfs.files[uri] = content.encode("utf-8")

        async def rm(self, uri: str, ctx=None, **_kwargs):
            del ctx
            if uri not in mem_agfs.files:
                from openviking_cli.exceptions import NotFoundError

                raise NotFoundError(uri, "file")
            mem_agfs.files.pop(uri, None)

        async def ls(self, uri: str, ctx=None, **_kwargs):
            del uri, ctx
            return []

    viking_fs = _FakeFS(mem_agfs)
    runtime_config = manager_over_source(MemoryConfigSource(), base_config=OpenVikingConfigSingleton.get_instance())
    await runtime_config.initialize()
    sessions = SessionService(viking_fs=viking_fs)
    sessions.set_runtime_config_manager(runtime_config)

    service = SimpleNamespace(
        sessions=sessions,
        viking_fs=viking_fs,
        runtime_config_manager=runtime_config,
        initialize_user_directories=AsyncMock(return_value=1),
        initialize_account_directories=AsyncMock(return_value=1),
    )

    cfg = ServerConfig(root_api_key="root-secret", auth_mode="api_key")
    app = create_app(config=cfg, service=service)
    set_service(service)

    mgr = NewAPIKeyManager("root-secret", viking_fs)
    await mgr.load()
    await mgr.register_user("default", "alice", "admin", seed="alice-seed")
    app.state.api_key_manager = mgr
    app.state.auth_plugin = ApiKeyAuthPlugin()

    root_hdr = {"X-API-Key": "root-secret"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Cluster runtime configuration GET & PATCH
        r_cfg = await client.get("/api/v1/admin/configuration", headers=root_hdr)
        assert r_cfg.status_code == 200
        assert r_cfg.json()["result"]["settings"] == {}

        # 2. Account configuration GET & PATCH + ADMIN root-only field guard
        r_acct_cfg = await client.get(
            "/api/v1/admin/accounts/default/configuration", headers=root_hdr
        )
        assert r_acct_cfg.status_code == 200
        assert "agent_evolution" in r_acct_cfg.json()["result"]["settings"]

        r_patch_acct = await client.patch(
            "/api/v1/admin/accounts/default/configuration",
            json={"settings": {"agent_evolution": {"enabled": True}}},
            headers=root_hdr,
        )
        assert r_patch_acct.status_code == 200
        assert r_patch_acct.json()["result"]["settings"]["agent_evolution"]["enabled"] is True

        # 3. Account memory-templates list & get
        r_tpl = await client.get(
            "/api/v1/admin/accounts/default/memory-templates", headers=root_hdr
        )
        assert r_tpl.status_code == 200
        tpl_names = [item["memory_type"] for item in r_tpl.json()["result"]["templates"]]
        assert set(tpl_names) == {"profile", "events", "preferences", "entities"}

        # 4. GLOBAL user creation, admin filtering/pagination, and batch + single group members
        r_global = await client.post(
            "/api/v1/admin/accounts/default/users",
            json={"user_id": "global-bot", "role": "global", "seed": "gseed"},
            headers=root_hdr,
        )
        assert r_global.status_code == 200, r_global.text
        g_key = r_global.json()["result"]["user_key"]
        assert g_key

        r_users = await client.get(
            "/api/v1/admin/accounts/default/users",
            params={"include_summary": "true", "query": "GLOBAL", "limit": 5, "page": 1},
            headers=root_hdr,
        )
        assert r_users.status_code == 200
        res_users = r_users.json()["result"]
        assert res_users["total"] == 1
        assert res_users["account_total"] == 2
        assert res_users["users"][0]["user_id"] == "global-bot"

        # 5. Groups: create, batch PUT/DELETE + single PUT compat
        assert (
            await client.post(
                "/api/v1/admin/accounts/default/groups",
                json={"group_id": "ops"},
                headers=root_hdr,
            )
        ).status_code == 200
        r_put_batch = await client.put(
            "/api/v1/admin/accounts/default/groups/ops/members",
            json={"user_ids": ["alice"]},
            headers=root_hdr,
        )
        assert r_put_batch.status_code == 200
        assert r_put_batch.json()["result"]["added"] == ["alice"]

        r_del_batch = await client.request(
            "DELETE",
            "/api/v1/admin/accounts/default/groups/ops/members",
            json={"user_ids": ["alice"]},
            headers=root_hdr,
        )
        assert r_del_batch.status_code == 200
        assert r_del_batch.json()["result"]["removed"] == ["alice"]

        # 6. Metric inventory NDJSON stream
        r_inv = await client.get("/api/v1/admin/metric-inventory", headers=root_hdr)
        assert r_inv.status_code == 200
        assert "application/x-ndjson" in r_inv.headers["content-type"]

        # 7. Bot capabilities endpoint
        r_bot = await client.get("/api/v1/admin/bot/capabilities", headers=root_hdr)
        assert r_bot.status_code == 200
        assert "enabled" in r_bot.json()["result"]
