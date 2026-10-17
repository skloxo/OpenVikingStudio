# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Tests for Memory Lifecycle DAG and Conflict Resolution Endpoints.
Card-36: Memory-Anti-Entropy-Lineage-DAG-And-Conflict-Resolution (v1.6.0)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.memory_lifecycle import router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    MemoryConflictResolver.reset_for_testing()
    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="default", user_id="test_user"),
        role=Role.ADMIN,
    )
    app.include_router(router)
    yield TestClient(app)
    MemoryConflictResolver.reset_for_testing()


def test_conflict_stats_endpoint(client):
    response = client.get("/api/v1/memory/conflicts/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert "active_nodes" in result
    assert "superseded_nodes" in result
    assert "purity_ratio" in result


def test_conflict_resolve_and_history_endpoint(client):
    old_uri = "viking://resources/master_memory/algo_v1.md"
    new_uri = "viking://resources/master_memory/algo_v2.md"

    # Resolve conflict via API
    res = client.post(
        "/api/v1/memory/conflicts/resolve",
        json={
            "old_uri": old_uri,
            "new_uri": new_uri,
            "reason": "Upgraded sorting algorithm to O(N log N)",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["result"]["old_uri"] == old_uri
    assert body["result"]["new_uri"] == new_uri
    assert body["result"]["old_status"] == "superseded"
    assert body["result"]["new_status"] == "active"

    # Check history
    h_res = client.get("/api/v1/memory/conflicts/history?limit=10")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "ok"
    items = h_data["result"]
    assert any(i["old_uri"] == old_uri and i["new_uri"] == new_uri for i in items)

    # Check DAG lineage
    dag_res = client.get(f"/api/v1/memory/lineage/dag?uri={old_uri}")
    assert dag_res.status_code == 200
    dag_data = dag_res.json()
    assert dag_data["status"] == "ok"
    chain = dag_data["result"]
    assert chain["root_uri"] == old_uri
    assert chain["current_active_ssot"] == new_uri
    assert chain["is_superseded"] is True
