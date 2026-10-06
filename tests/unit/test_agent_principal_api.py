# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for User-Scoped Agent Management API (Card-112 / Card-117).
Validates:
1. Immutable agent_id auto-generation vs mutable agent_name;
2. Dynamic Tool ACL matrix;
3. Soft-deletion security semantics (deleted agents fail fast);
4. Multi-user agent counts aggregation.
"""

import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.storage.agent_principal_store import AgentPrincipalStore
from openviking.server.routers.agents import router as agents_router


@pytest.fixture
def client(tmp_path: Path):
    AgentPrincipalStore.reset_instance()
    db_file = tmp_path / "test_agents_api.db"
    AgentPrincipalStore.get_instance(db_path=db_file)

    app = FastAPI()
    app.include_router(agents_router)
    test_client = TestClient(app)
    yield test_client
    AgentPrincipalStore.reset_instance()


def test_create_and_auto_id_api(client: TestClient):
    # 1. Create agent with custom name and auto-generated immutable ID
    res = client.post(
        "/api/v1/users/default/agents",
        json={
            "agent_name": "前端结对开发助手",
            "role_desc": "TypeScript / React 开发专家",
            "connection_mode": "realtimeApi",
            "allowed_tools": ["find", "search", "read"],
        },
    )
    assert res.status_code == 200
    data = res.json()["result"]
    agent = data["agent"]
    assert agent["agent_name"] == "前端结对开发助手"
    assert agent["agent_id"].startswith("ag_")
    assert agent["allowed_tools"] == ["find", "search", "read"]
    assert agent["user_id"] == "default"

    # 2. Verify bootstrap payload
    bootstrap = data["bootstrap"]
    assert agent["agent_id"] in bootstrap["remote_mcp_url"]
    assert "前端结对开发助手" in bootstrap["system_prompt"]
    assert agent["agent_id"] in bootstrap["system_prompt"]


def test_update_agent_api(client: TestClient):
    # Create
    create_res = client.post(
        "/api/v1/users/default/agents",
        json={
            "agent_name": "初始名称",
            "role_desc": "测试角色",
        },
    )
    agent_id = create_res.json()["result"]["agent"]["agent_id"]

    # Update name and tool permissions
    patch_res = client.patch(
        f"/api/v1/users/default/agents/{agent_id}",
        json={
            "agent_name": "修改后的新名称",
            "allowed_tools": ["find", "record_evolution_lesson", "grep"],
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()["result"]
    assert updated["agent_name"] == "修改后的新名称"
    assert updated["agent_id"] == agent_id  # immutable
    assert updated["allowed_tools"] == ["find", "record_evolution_lesson", "grep"]


def test_soft_delete_and_reactivate_api(client: TestClient):
    # Create
    create_res = client.post(
        "/api/v1/users/default/agents",
        json={"agent_name": "临时测试 Agent"},
    )
    agent_id = create_res.json()["result"]["agent"]["agent_id"]

    # Soft delete
    del_res = client.delete(f"/api/v1/users/default/agents/{agent_id}")
    assert del_res.status_code == 200
    assert del_res.json()["result"]["soft_deleted"] is True

    # Active list must not show deleted agent
    list_res = client.get("/api/v1/users/default/agents")
    agents = list_res.json()["result"]
    assert not any(a["agent_id"] == agent_id for a in agents)

    # Reactivate
    act_res = client.post(f"/api/v1/users/default/agents/{agent_id}/activate")
    assert act_res.status_code == 200
    assert act_res.json()["result"]["activated"] is True

    # Now it is back in active list
    list_res2 = client.get("/api/v1/users/default/agents")
    agents2 = list_res2.json()["result"]
    assert any(a["agent_id"] == agent_id for a in agents2)


def test_agent_counts_api(client: TestClient):
    client.post("/api/v1/users/user_a/agents", json={"agent_name": "Agent A1"})
    client.post("/api/v1/users/user_a/agents", json={"agent_name": "Agent A2"})
    client.post("/api/v1/users/user_b/agents", json={"agent_name": "Agent B1"})

    counts_res = client.get("/api/v1/users/agent-counts")
    assert counts_res.status_code == 200
    counts = counts_res.json()["result"]
    assert counts.get("user_a") == 2
    assert counts.get("user_b") == 1


def test_mcp_middleware_soft_delete_interception(tmp_path: Path):
    from openviking.server.mcp_endpoint import _IdentityASGIMiddleware

    # Setup isolated store
    db_file = tmp_path / "test_mcp_mw.db"
    store = AgentPrincipalStore.get_instance(db_path=db_file)
    created = store.register_agent(
        user_id="default",
        agent_name="活跃测试智能体",
        role_desc="测试",
        connection_mode="realtimeApi",
    )
    agent_id = created.agent_id

    from openviking.server.auth.plugins import DevAuthPlugin

    app = FastAPI()
    app.state.auth_plugin = DevAuthPlugin()
    app.add_middleware(_IdentityASGIMiddleware)

    @app.get("/mcp")
    def dummy_endpoint():
        return {"status": "ok"}

    test_client = TestClient(app)

    # 1. Valid agent_id passes through
    res_valid = test_client.get(f"/mcp?agent_id={agent_id}")
    assert res_valid.status_code == 200
    assert res_valid.json() == {"status": "ok"}

    # 2. Soft delete the agent
    store.soft_delete_agent(agent_id)

    # 3. Soft deleted agent_id gets 401 with not found or credential invalid error
    res_deleted = test_client.get(f"/mcp?agent_id={agent_id}")
    assert res_deleted.status_code == 401
    err_json = res_deleted.json()
    assert "not found or credential invalid" in err_json["error"]["message"]

    # 4. Completely nonexistent agent_id gets 401
    res_nonexistent = test_client.get("/mcp?agent_id=ag_nonexistent_xyz")
    assert res_nonexistent.status_code == 401
    assert "not found or credential invalid" in res_nonexistent.json()["error"]["message"]


