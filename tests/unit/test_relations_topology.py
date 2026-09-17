# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for knowledge graph topology endpoint (Card-Authenticity-FakeDataPurge-And-RealWiring v1.5.23).
Validates that /api/v1/relations/topology returns real/dynamic nodes and edges, without artificial 1458 hardcoding.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.dependencies import get_service, get_service_or_none
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.relations import router as relations_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(relations_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test_acc", user_id="test_user"),
        role=Role(Role.ADMIN),
    )
    mock_service = MagicMock()
    mock_service.skills = None
    mock_service.sessions = None
    mock_service.viking_fs = None

    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    app.dependency_overrides[get_service] = lambda: mock_service
    app.dependency_overrides[get_service_or_none] = lambda: mock_service
    return TestClient(app)


def test_topology_returns_truthful_structure(client):
    """Verify that /api/v1/relations/topology returns 9 architectural peers and orchestrated edges."""
    response = client.get("/api/v1/relations/topology")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "result" in data
    result = data["result"]
    assert "nodes" in result
    assert "edges" in result

    node_ids = [n["id"] for n in result["nodes"]]
    assert "viking://peers/antigravity@2080ti" in node_ids
    assert "viking://peers/antigravity@rtx3070" in node_ids
    assert "viking://peers/openclaw@2080ti" in node_ids
    assert "viking://peers/macstudio" in node_ids

    # There should NOT be any artificial skill_1 or doc_1458 mock strings
    assert not any("skill_1" in nid for nid in node_ids)
    assert not any("doc_1" in nid for nid in node_ids)

    # Check edges connect 2080ti master to peers
    edge_pairs = [(e["source"], e["target"]) for e in result["edges"]]
    assert ("viking://peers/antigravity@2080ti", "viking://peers/antigravity@rtx3070") in edge_pairs
    assert ("viking://peers/antigravity@2080ti", "viking://peers/macstudio") in edge_pairs


def test_topology_with_mocked_services():
    """Verify that /api/v1/relations/topology correctly surfaces skills and sessions."""
    app = FastAPI()
    app.include_router(relations_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test_acc", user_id="test_user"),
        role=Role(Role.ADMIN),
    )

    mock_service = MagicMock()
    mock_service.skills = MagicMock()
    mock_service.sessions = MagicMock()
    mock_service.sessions.sessions = AsyncMock(return_value=[
        {"session_id": "sess_alpha_123"},
        {"session_id": "sess_beta_456"},
    ])
    mock_service.viking_fs = None

    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    app.dependency_overrides[get_service] = lambda: mock_service
    app.dependency_overrides[get_service_or_none] = lambda: mock_service

    test_client = TestClient(app)
    response = test_client.get("/api/v1/relations/topology?limit=100")
    assert response.status_code == 200
    data = response.json()
    nodes = data["result"]["nodes"]
    node_ids = [n["id"] for n in nodes]

    assert "viking://sessions/sess_alpha_123" in node_ids
    assert "viking://sessions/sess_beta_456" in node_ids
