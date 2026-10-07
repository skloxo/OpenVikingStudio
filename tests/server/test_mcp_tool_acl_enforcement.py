# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test for MCP Tool ACL Gate enforcement in _IdentityASGIMiddleware."""

import json
from types import SimpleNamespace
import httpx
import pytest
from fastapi import FastAPI
from starlette.routing import Route

from openviking.server.auth.plugins import DevAuthPlugin
from openviking.server.identity import AuthMode
from openviking.server.mcp_endpoint import _IdentityASGIMiddleware
from openviking.storage.agent_principal_store import AgentPrincipalStore, generate_agent_id


@pytest.mark.asyncio
async def test_mcp_middleware_tool_acl_enforcement():
    store = AgentPrincipalStore.get_instance()
    test_agent_id = generate_agent_id()
    store.register_agent(
        agent_id=test_agent_id,
        agent_name="ACL Unit Agent",
        user_id="default",
        role_desc="Test ACL",
        allowed_tools=["find", "search", "read"],
    )

    called_tool = None

    async def downstream(scope, receive, send):
        nonlocal called_tool
        req_body = await receive()
        data = json.loads(req_body["body"])
        called_tool = data.get("params", {}).get("name")
        resp = httpx.Response(200, json={"result": f"called {called_tool}"})
        await send({"type": "http.response.start", "status": resp.status_code, "headers": []})
        await send({"type": "http.response.body", "body": resp.content})

    app = FastAPI()
    app.state.config = SimpleNamespace(get_effective_auth_mode=lambda: AuthMode.DEV)
    app.state.auth_plugin = DevAuthPlugin()
    app.routes.append(Route("/mcp", endpoint=_IdentityASGIMiddleware(downstream), methods=["POST"]))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://ov.test") as client:
        # 1. Authorized tool call: 'find' -> must succeed (200)
        res1 = await client.post(
            f"/mcp?agent_id={test_agent_id}",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "find", "arguments": {}},
            },
        )
        assert res1.status_code == 200
        assert called_tool == "find"

        # 2. Unauthorized tool call: 'write' -> must be physically intercepted (403)
        res2 = await client.post(
            f"/mcp?agent_id={test_agent_id}",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "write", "arguments": {}},
            },
        )
        assert res2.status_code == 403
        data2 = res2.json()
        assert data2["error"]["code"] == -32003
        assert "write" in data2["error"]["message"]

        # 3. Wildcard tool grant: update agent to allow ['*'] -> 'write' now succeeds
        store.update_agent(test_agent_id, allowed_tools=["*"])
        res3 = await client.post(
            f"/mcp?agent_id={test_agent_id}",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "write", "arguments": {}},
            },
        )
        assert res3.status_code == 200
        assert called_tool == "write"

    # Cleanup
    store.soft_delete_agent(test_agent_id)


@pytest.mark.asyncio
async def test_mcp_middleware_owner_cross_verification():
    """Verify that agent_id and user_id must match to prevent cross-tenant hijacking."""
    store = AgentPrincipalStore.get_instance()
    alice_agent_id = generate_agent_id()
    store.register_agent(
        agent_id=alice_agent_id,
        agent_name="Alice Agent",
        user_id="alice",
        role_desc="Alice only",
        allowed_tools=["find"],
    )

    async def downstream(scope, receive, send):
        resp = httpx.Response(200, json={"result": "ok"})
        await send({"type": "http.response.start", "status": resp.status_code, "headers": []})
        await send({"type": "http.response.body", "body": resp.content})

    app = FastAPI()
    app.state.config = SimpleNamespace(get_effective_auth_mode=lambda: AuthMode.DEV)
    app.state.auth_plugin = DevAuthPlugin()
    app.routes.append(Route("/mcp", endpoint=_IdentityASGIMiddleware(downstream), methods=["POST"]))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://ov.test") as client:
        # 1. Matching owner: user_id=alice accessing alice_agent_id -> 200 OK
        res1 = await client.post(
            f"/mcp?agent_id={alice_agent_id}&user_id=alice",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "find", "arguments": {}}},
        )
        assert res1.status_code == 200

        # 2. Mismatched owner: user_id=bob attempting to access alice_agent_id -> 403 Forbidden
        res2 = await client.post(
            f"/mcp?agent_id={alice_agent_id}&user_id=bob",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "find", "arguments": {}}},
        )
        assert res2.status_code == 403
        data2 = res2.json()
        assert data2["error"]["code"] == -32003
        assert "Cross-tenant access denied" in data2["error"]["message"]

        # 3. Header-based mismatched identity: x-openviking-user=bob attempting to access alice_agent_id -> 403 Forbidden
        res3 = await client.post(
            f"/mcp?agent_id={alice_agent_id}",
            headers={"x-openviking-user": "bob"},
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "find", "arguments": {}}},
        )
        assert res3.status_code == 403
        data3 = res3.json()
        assert data3["error"]["code"] == -32003
        assert "Cross-tenant access denied" in data3["error"]["message"] or "Owner mismatch" in data3["error"]["message"]

    store.soft_delete_agent(alice_agent_id)

