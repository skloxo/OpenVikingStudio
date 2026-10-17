# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Server API endpoint tests for Memory Dream Consolidation and Temporal Decay Simulation.
(Card-37 / v1.6.1)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.memory_lifecycle import router
from openviking.service.memory_lifecycle_fsm import MemoryLifecycleStore
from openviking.service.offline_dreamer import OfflineDreamer
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client(tmp_path):
    """Setup test client with mock admin context and clean stores."""
    db_file = tmp_path / "memory_lifecycle.db"
    store = MemoryLifecycleStore(db_path=str(db_file))
    MemoryLifecycleStore._instance = store
    OfflineDreamer.reset_for_testing()

    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="default", user_id="test_admin"),
        role=Role.ADMIN,
    )
    app.include_router(router)
    yield TestClient(app)
    OfflineDreamer.reset_for_testing()
    MemoryLifecycleStore._instance = None


def test_api_decay_simulation(client):
    """Verify /api/v1/memory/decay/simulate accurately calculates decay multiplier, hit boost, and effective score."""
    resp = client.post(
        "/api/v1/memory/decay/simulate",
        json={
            "uri": "viking://resources/experience/auth_token.md",
            "raw_score": 0.80,
            "delta_days": 30.0,
            "active_count": 10,
            "memory_type": "experience",
            "status": "active",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    res = data["result"]
    assert res["memory_type"] == "experience"
    assert res["lambda_val"] == 0.007
    assert res["hit_boost"] > 1.40
    assert res["decay_factor"] > 1.0  # Hit boost outweighs 30-day experience decay
    assert res["adjusted_score"] > 0.80


def test_api_dream_stats_and_run(client):
    """Verify /api/v1/memory/dream/stats and /dream/run endpoints."""
    # 1. Check initial dream stats
    resp_stats = client.get("/api/v1/memory/dream/stats")
    assert resp_stats.status_code == 200
    assert resp_stats.json()["status"] == "ok"
    assert "total_dreams" in resp_stats.json()["result"]

    # 2. Trigger dream run (dry_run=True when empty)
    resp_run = client.post(
        "/api/v1/memory/dream/run",
        json={"theme": "network_diagnostics", "dry_run": True, "min_cluster_size": 2},
    )
    assert resp_run.status_code == 200
    run_data = resp_run.json()
    assert run_data["status"] == "ok"
    assert "dream_id" in run_data["result"]
