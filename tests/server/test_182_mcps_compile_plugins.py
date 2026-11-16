# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Integration tests for #182 MCP mounts, Compile endpoints, and VK plugins."""

import ast
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from openviking.server.dependencies import get_service, set_service
from openviking.server.identity import RequestContext, Role
from openviking.server.mcp_endpoint import mcp
from openviking.server.routers.client_caps_constants import BATTLEFIELD_34_TOOLS
from openviking.server.routers.compile import router as compile_router
from openviking.server.routers.mcps import router as mcps_router
from openviking_cli.session.user_id import UserIdentifier

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mcp_endpoint_registers_ext_182_tools():
    tool_names = {t.name for t in mcp._tool_manager.list_tools()}
    assert {"find_mcp_tools", "invoke_mcp_tool", "rule_search"}.issubset(tool_names)
    cap_ids = {t["id"] for t in BATTLEFIELD_34_TOOLS}
    assert {
        "openviking_rule_search",
        "openviking_find_mcp_tools",
        "openviking_invoke_mcp_tool",
    }.issubset(cap_ids)


def test_openviking_memory_plugin_normalizes_182_tools():
    mem_server = REPO_ROOT / "packages" / "plugins" / "openviking-memory" / "server.py"
    dsh_server = (
        REPO_ROOT
        / "integrations"
        / "deepseek-harness"
        / "dsh-plugin-openviking-memory"
        / "server.py"
    )
    for path in (mem_server, dsh_server):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        mapping = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SERVER_TO_CLIENT_TOOLS":
                        mapping = ast.literal_eval(node.value)
        assert mapping is not None
        assert mapping["rule_search"] == "openviking_rule_search"
        assert mapping["find_mcp_tools"] == "openviking_find_mcp_tools"
        assert mapping["invoke_mcp_tool"] == "openviking_invoke_mcp_tool"


def test_openviking_ops_plugin_watch_routes_aligned():
    ops_path = REPO_ROOT / "integrations" / "antigravity" / "openviking-ops" / "server.py"
    spec = importlib.util.spec_from_file_location("ov_ops_server_test", ops_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    calls = []

    def fake_api_request(method, endpoint, params=None, body=None, timeout=None):
        calls.append((method, endpoint, params, body))
        return '{"status": "ok"}'

    mod._api_request = fake_api_request
    mod.openviking_list_watches(active_only=True)
    mod.openviking_cancel_watch(target_uri="viking://resources/demo/doc")
    mod.openviking_manage_watch(
        target_uri="viking://resources/demo/doc",
        interval_minutes=30,
        active=False,
        action="pause",
    )
    mod.openviking_manage_watch(
        target_uri="viking://resources/demo/doc",
        action="trigger",
    )

    assert calls[0] == ("GET", "/api/v1/watches", {"active_only": True}, None)
    assert calls[1][0] == "DELETE"
    assert calls[1][1] == "/api/v1/watches?to_uri=viking%3A%2F%2Fresources%2Fdemo%2Fdoc"
    assert calls[2] == (
        "PATCH",
        "/api/v1/watches?to_uri=viking%3A%2F%2Fresources%2Fdemo%2Fdoc",
        None,
        {"watch_interval": 30.0, "is_active": False},
    )
    assert calls[3] == (
        "POST",
        "/api/v1/watches/trigger?to_uri=viking%3A%2F%2Fresources%2Fdemo%2Fdoc",
        None,
        None,
    )


@pytest.mark.asyncio
async def test_mcps_and_compile_routes_dispatch():
    app = FastAPI()
    app.include_router(mcps_router)
    app.include_router(compile_router)

    class _FakeMCPs:
        list = AsyncMock(return_value={"servers": [], "total": 0})
        status = AsyncMock(return_value={"servers": [], "total": 0})
        find = AsyncMock(return_value={"tools": [], "total": 0})

    class _FakeCompile:
        capabilities = lambda self, ctx: {"configured": False, "can_create": False}  # noqa: E731
        list_configs = AsyncMock(return_value={"items": [], "next_cursor": None})

    class _FakeSvc:
        mcps = _FakeMCPs()
        compile = _FakeCompile()

    prev = None
    try:
        prev = get_service()
    except Exception:
        pass
    set_service(_FakeSvc())
    from openviking.server.auth import get_request_context

    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier("default", "default"),
        role=Role.ADMIN,
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            r1 = await client.get("/api/v1/mcps")
            r2 = await client.post("/api/v1/mcps/find", json={"query": "search"})
            r3 = await client.get("/api/v1/compile/capabilities")
            r4 = await client.get("/api/v1/compile/configs")
            assert r1.status_code == 200
            assert r2.status_code == 200
            assert r3.status_code == 200
            assert r4.status_code == 200
    finally:
        set_service(prev)
