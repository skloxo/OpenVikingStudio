# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Regression tests for Card #281: system/wait dual-input & non-silent router logging."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers import relations as relations_router
from openviking.server.routers import search as search_router
from openviking.server.routers import system as system_router
from openviking_cli.exceptions import NotFoundError
from openviking_cli.session.user_id import UserIdentifier


def _make_system_app(wait_mock: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.router)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier("default", "default"),
        role=Role.ADMIN,
    )
    app.state._wait_mock = wait_mock
    return app


@pytest.mark.asyncio
async def test_system_wait_accepts_empty_query_and_json_body():
    """POST /api/v1/system/wait must accept no body, ?timeout query param, and JSON body."""
    wait_mock = AsyncMock(return_value={"processed": 0, "errors": 0, "queries": {}})
    fake_service = SimpleNamespace(resources=SimpleNamespace(wait_processed=wait_mock))
    app = _make_system_app(wait_mock)

    with patch("openviking.server.routers.system.get_service", return_value=fake_service):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r_empty = await client.post("/api/v1/system/wait")
            assert r_empty.status_code == 200
            assert r_empty.json()["status"] == "ok"

            r_query = await client.post("/api/v1/system/wait?timeout=5.5")
            assert r_query.status_code == 200
            assert r_query.json()["status"] == "ok"

            r_json = await client.post("/api/v1/system/wait", json={"timeout": 12.25})
            assert r_json.status_code == 200
            assert r_json.json()["status"] == "ok"

            r_both = await client.post("/api/v1/system/wait?timeout=3.0", json={"timeout": 99.0})
            assert r_both.status_code == 200

    assert wait_mock.await_args_list[0].kwargs == {"timeout": None}
    assert wait_mock.await_args_list[1].kwargs == {"timeout": 5.5}
    assert wait_mock.await_args_list[2].kwargs == {"timeout": 12.25}
    assert wait_mock.await_args_list[3].kwargs == {"timeout": 3.0}


@pytest.mark.asyncio
async def test_relations_get_topology_logs_and_reports_degraded_sections():
    """Failing topology sub-loaders must emit warning logs and populate degraded_sections."""
    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.ADMIN)
    fake_store = MagicMock()
    fake_store.list_all_links.return_value = []
    fake_service = SimpleNamespace(
        skills=MagicMock(),
        sessions=SimpleNamespace(sessions=AsyncMock(side_effect=RuntimeError("sessions backend offline"))),
        viking_fs=SimpleNamespace(ls=AsyncMock(side_effect=RuntimeError("vfs timeout"))),
    )

    with (
        patch("openviking.server.routers.relations.RelationStore.get_instance", return_value=fake_store),
        patch(
            "openviking.server.routers.skills._list_skills_from_root",
            new=AsyncMock(side_effect=RuntimeError("skills store unavailable")),
        ),
        patch.object(relations_router.logger, "warning", wraps=relations_router.logger.warning) as mock_warn,
    ):
        resp = await relations_router.get_topology(limit=100, service=fake_service, _ctx=ctx)

    assert resp.status == "ok"
    assert resp.result["degraded_sections"] == ["skills", "sessions", "resources"]
    assert resp.result["stats"]["degraded_count"] == 3
    assert mock_warn.call_count == 3
    logged_templates = [call.args[0] for call in mock_warn.call_args_list]
    assert any("skills" in msg for msg in logged_templates)
    assert any("sessions" in msg for msg in logged_templates)
    assert any("resources" in msg for msg in logged_templates)


@pytest.mark.asyncio
async def test_search_inline_read_logs_unexpected_error_without_suppressing_not_found():
    """_inline_read_content skips NotFoundError quietly but warns on unexpected FS errors."""
    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.USER)

    async def _fake_read(uri: str, *, ctx: RequestContext) -> str:
        if "missing" in uri:
            raise NotFoundError(uri, "resource")
        if "broken" in uri:
            raise RuntimeError("agfs socket reset")
        return "ok content"

    fake_service = SimpleNamespace(fs=SimpleNamespace(read_visible=AsyncMock(side_effect=_fake_read)))
    payload = {
        "memories": [
            {"uri": "viking://user/default/memories/ok.md"},
            {"uri": "viking://user/default/memories/missing.md"},
            {"uri": "viking://user/default/memories/broken.md"},
        ]
    }

    with (
        patch.object(search_router.logger, "warning", wraps=search_router.logger.warning) as mock_warn,
        patch.object(search_router.logger, "debug", wraps=search_router.logger.debug) as mock_debug,
    ):
        out = await search_router._inline_read_content(payload, service=fake_service, ctx=ctx)

    assert out["memories"][0]["content"] == "ok content"
    assert "content" not in out["memories"][1]
    assert "content" not in out["memories"][2]
    mock_debug.assert_called_once()
    mock_warn.assert_called_once()
    assert "broken.md" in str(mock_warn.call_args.args[1])
