# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for User-Scoped Agent Management API (Card-112 / v1.7.66).
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


def test_create_and_list_agents_api(client: TestClient):
    # 1. Create a new agent under user default
    res = client.post(
        "/api/v1/users/default/agents",
        json={
            "agent_id": "cursor@macbook",
            "role_desc": "MacBook Cursor 编程助手",
            "icon": "code",
            "connection_mode": "apiClient",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["result"]["agent"]["agent_id"] == "cursor@macbook"
    assert data["result"]["agent"]["user_id"] == "default"
    
    # Verify bootstrap payload is present and safe
    bootstrap = data["result"]["bootstrap"]
    assert "mcp_config" in bootstrap
    assert "system_prompt" in bootstrap
    assert "${OPENVIKING_API_KEY}" in str(bootstrap["mcp_config"])
    assert "cursor@macbook" in bootstrap["system_prompt"]

    # 2. List agents
    list_res = client.get("/api/v1/users/default/agents")
    assert list_res.status_code == 200
    agents = list_res.json()["result"]
    assert len(agents) == 1
    assert agents[0]["agent_id"] == "cursor@macbook"


def test_revoke_agent_api(client: TestClient):
    # Create
    client.post(
        "/api/v1/users/default/agents",
        json={
            "agent_id": "test_agent@laptop",
            "role_desc": "Test Agent",
        },
    )
    # Revoke
    del_res = client.delete("/api/v1/users/default/agents/test_agent@laptop")
    assert del_res.status_code == 200
    assert del_res.json()["result"]["revoked"] is True

    # Check active list is empty
    active_res = client.get("/api/v1/users/default/agents?status=active")
    assert len(active_res.json()["result"]) == 0

    # Check all list has it as revoked
    all_res = client.get("/api/v1/users/default/agents?status=all")
    assert len(all_res.json()["result"]) == 1
    assert all_res.json()["result"][0]["status"] == "revoked"

    # Reactivate
    act_res = client.post("/api/v1/users/default/agents/test_agent@laptop/activate")
    assert act_res.status_code == 200
    assert act_res.json()["result"]["activated"] is True

    # Check active list has it back
    active_res = client.get("/api/v1/users/default/agents?status=active")
    assert len(active_res.json()["result"]) == 1

    # Revoke then purge permanently
    client.delete("/api/v1/users/default/agents/test_agent@laptop")
    purge_res = client.delete("/api/v1/users/default/agents/test_agent@laptop?purge=true")
    assert purge_res.status_code == 200
    assert purge_res.json()["result"]["deleted"] is True
    assert purge_res.json()["result"]["purged"] is True

    # Verify completely gone
    all_res_after = client.get("/api/v1/users/default/agents?status=all")
    assert len(all_res_after.json()["result"]) == 0


def test_local_direct_bootstrap_api(client: TestClient):
    """Verify local direct agent returns 127.0.0.1 bootstrap without public key."""
    res = client.post(
        "/api/v1/users/default/agents",
        json={
            "agent_id": "antigravity@2080ti",
            "role_desc": "本地反重力 IDE",
            "connection_mode": "realtimeApi",
        },
    )
    assert res.status_code == 200
    data = res.json()["result"]
    bootstrap = data["bootstrap"]
    assert bootstrap["topology"] == "local"
    assert "127.0.0.1:1933/mcp" in bootstrap["target_server"]
    # Local direct should not require public key in args
    args_str = str(bootstrap["mcp_config"]["mcpServers"]["openviking"]["args"])
    assert "127.0.0.1:1933/mcp" in args_str
    assert "--key" not in args_str
