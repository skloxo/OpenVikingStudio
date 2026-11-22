# -*- coding: utf-8 -*-
"""Unit tests for Evolution CI/CD REST API router endpoints."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from openviking.core.evolution_cicd import (
    AutonomousLevel,
    EvolutionCICDPipeline,
)
from openviking.core.dreaming_gate import (
    DreamingDefectMiner,
)
from openviking.core.rsi_trajectory_store import RSITrajectoryStore
from openviking.server.routers.evolution_cicd import router


@pytest.fixture
def client(tmp_path):
    RSITrajectoryStore.reset_instance()
    store = RSITrajectoryStore.get_instance(tmp_path / "test_cicd_api.db")
    app = FastAPI()
    app.include_router(router)
    pipeline = EvolutionCICDPipeline.get_instance()
    pipeline.set_store(store)
    pipeline.packages.clear()
    pipeline.autonomous_level = AutonomousLevel.LEVEL_2_BOUNDED_AUTO
    pipeline.emergency_kill_switch_tripped = False
    pipeline.auto_downgrade_count = 0
    miner = DreamingDefectMiner.get_instance()
    miner.defects.clear()
    try:
        yield TestClient(app)
    finally:
        pipeline.packages.clear()
        pipeline.set_store(None)
        RSITrajectoryStore.reset_instance()


def test_api_package_lifecycle(client):
    # 1. Create package
    res = client.post("/api/v1/evolution/pipeline/package", json={
        "target_skill": "cockpit-ui",
        "diff_patch": "+- DO NOT introduce green\n+- INSTEAD use cyan-500",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    pkg_id = data["package"]["package_id"]

    # 2. Advance package
    adv_res = client.post("/api/v1/evolution/pipeline/advance", json={"package_id": pkg_id})
    assert adv_res.status_code == 200
    assert adv_res.json()["current_stage"] == "candidate_generation"

    # 3. List packages
    list_res = client.get("/api/v1/evolution/pipeline/packages")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


def test_api_governance_and_emergency_rollback(client):
    # Get governance state
    gov_res = client.get("/api/v1/evolution/governance")
    assert gov_res.status_code == 200
    assert "autonomous_level" in gov_res.json()
    assert "second_order_metrics" in gov_res.json()

    # Change autonomy level
    set_res = client.post("/api/v1/evolution/governance/level", json={
        "level": "level_3_full_evolve"
    })
    assert set_res.status_code == 200
    assert set_res.json()["new_level"] == "level_3_full_evolve"

    # Emergency rollback
    rb_res = client.post("/api/v1/evolution/governance/rollback", json={})
    assert rb_res.status_code == 200
    assert rb_res.json()["status"] == "emergency_rollback_success"
    assert rb_res.json()["new_level"] == "level_0_observe"


def test_api_dreaming_trigger_and_status(client):
    # Trigger dreaming
    trig_res = client.post("/api/v1/evolution/dreaming/trigger", json={
        "traces": [{"success": False, "category": "MemoryLeak"}]
    })
    assert trig_res.status_code == 200
    assert trig_res.json()["status"] == "success"

    # Check status
    stat_res = client.get("/api/v1/evolution/dreaming/status")
    assert stat_res.status_code == 200
    data = stat_res.json()
    assert data["status"] == "completed"
    assert len(data["defects"]) >= 1


def test_evolution_cicd_requires_auth_when_auth_plugin_configured():
    from unittest.mock import MagicMock
    from openviking.server.auth.plugins import ApiKeyAuthPlugin
    from openviking.server.routers.evolution_cicd import router as cicd_router

    app = FastAPI()
    app.state.auth_plugin = ApiKeyAuthPlugin()
    app.state.api_key_manager = MagicMock()
    app.include_router(cicd_router)
    secured_client = TestClient(app)

    resp = secured_client.get("/api/v1/evolution/governance")
    assert resp.status_code == 401
