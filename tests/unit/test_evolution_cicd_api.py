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
from openviking.server.routers.evolution_cicd import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    pipeline = EvolutionCICDPipeline.get_instance()
    pipeline.packages.clear()
    pipeline.autonomous_level = AutonomousLevel.LEVEL_2_BOUNDED_AUTO
    pipeline.emergency_kill_switch_tripped = False
    pipeline.auto_downgrade_count = 0
    miner = DreamingDefectMiner.get_instance()
    miner.defects.clear()
    return TestClient(app)


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
