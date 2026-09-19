# -*- coding: utf-8 -*-
"""Unit tests for Agent Sensors REST API router."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.agent_sensors import (
    AgentSensorsAggregator,
)
from openviking.server.routers.agent_sensors import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    aggregator = AgentSensorsAggregator.get_instance()
    aggregator._history.clear()
    return TestClient(app)


def test_api_agent_sensors_flow(client):
    # 1. Get initial metrics (empty or cold)
    get_res = client.get("/api/v1/metrics/agent-sensors")
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    assert "avg_token_snr" in data
    assert "avg_p5_precision" in data
    assert "human_intervention_rate" in data

    # 2. Ingest telemetry sample
    post_res = client.post("/api/v1/metrics/agent-sensors/sample", json={
        "session_id": "sess-test-01",
        "effective_tokens": 800,
        "total_tokens": 1000,
        "top5_hits": 5,
        "interventions_count": 0,
    })
    assert post_res.status_code == 200
    pt = post_res.json()["point"]
    assert pt["session_id"] == "sess-test-01"
    assert pt["token_snr"] == 0.80
    assert pt["p5_precision"] == 1.0
    assert pt["human_intervention_flag"] is False

    # 3. Verify aggregated update
    get_res2 = client.get("/api/v1/metrics/agent-sensors")
    assert get_res2.status_code == 200
    data2 = get_res2.json()["data"]
    assert data2["sample_count"] >= 1
    assert data2["avg_token_snr"] == 0.80
    assert data2["avg_p5_precision"] == 1.0
    assert data2["human_intervention_rate"] == 0.0
    assert data2["snr_status"] == "optimal"
    assert data2["p5_status"] == "optimal"
    assert data2["intervention_status"] == "optimal"
