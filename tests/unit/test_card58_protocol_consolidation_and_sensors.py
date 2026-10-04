# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Unit tests for Card-58 (v1.7.12): Unified Communications SSOT, Agent 3D Sensors & Context Router Parity."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.routers.agent_sensors import router as agent_sensors_router
from openviking.server.routers.evolution_cicd import router as evolution_cicd_router
from openviking.server.mcp_endpoint import openviking_agent_sensors, openviking_context_route
from openviking.core.agent_sensors import AgentSensorsAggregator


@pytest.fixture(scope="module")
def test_client():
    app = FastAPI()
    app.include_router(agent_sensors_router)
    app.include_router(evolution_cicd_router)
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_mcp_openviking_context_route_execution():
    """Verify openviking_context_route FastMCP tool dispatches hybrid input and reports reduction."""
    hybrid_content = (
        "# System Directives\n"
        "Always follow First Principles and zero-tolerance for fake features.\n\n"
        "## Python Implementation\n"
        "```python\n"
        "def compute_aggregate(values: list[int]) -> int:\n"
        "    # Calculate sum\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        total += v\n"
        "    return total\n"
        "```\n"
    )

    report = await openviking_context_route(
        content=hybrid_content,
        default_code_mode="skeleton",
        target_dehydration_rate=0.50,
        enable_skillzip=True,
        preserve_static_header=True,
    )

    assert "=== Context Router Compression Report ===" in report
    assert "Original Tokens:" in report
    assert "Compressed Tokens:" in report
    assert "Tokens Saved:" in report
    assert "Segment Routing Breakdown:" in report
    assert "=== Compressed Content Output ===" in report


@pytest.mark.asyncio
async def test_mcp_openviking_agent_sensors_execution(tmp_path, monkeypatch):
    """Verify openviking_agent_sensors FastMCP tool returns 3D physical sensor metrics."""
    agg = AgentSensorsAggregator.get_instance()
    monkeypatch.setattr(agg, "metrics_file", str(tmp_path / "test_agent_metrics.jsonl"))
    # Inject a known sample
    agg.record_telemetry(
        session_id="test_mcp_sess_01",
        effective_tokens=850,
        total_tokens=1000,
        top5_hits=5,
        interventions_count=0,
    )

    output = await openviking_agent_sensors()
    assert "=== Agent 3D Performance Sensors Telemetry ===" in output
    assert "Token SNR (Effective Payload Ratio):" in output
    assert "P@5 Retrieval Adoption Precision:" in output
    assert "Human Intervention Rate:" in output
    assert "Sample Count:" in output


def test_agent_sensors_rest_endpoints(test_client, tmp_path, monkeypatch):
    """Verify REST endpoints for Agent 3D Performance Sensors."""
    agg = AgentSensorsAggregator.get_instance()
    monkeypatch.setattr(agg, "metrics_file", str(tmp_path / "test_rest_metrics.jsonl"))
    # 1. Post a sample
    post_res = test_client.post(
        "/api/v1/metrics/agent-sensors/sample",
        json={
            "session_id": "test_rest_sess_02",
            "effective_tokens": 780,
            "total_tokens": 1000,
            "top5_hits": 4,
            "interventions_count": 1,
        },
    )
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["status"] == "success"
    assert "point" in post_data
    assert post_data["point"]["session_id"] == "test_rest_sess_02"

    # 2. Get summary
    get_res = test_client.get("/api/v1/metrics/agent-sensors")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["status"] == "success"
    assert "data" in get_data
    assert get_data["data"]["sample_count"] > 0
    assert "avg_token_snr" in get_data["data"]
    assert "avg_p5_precision" in get_data["data"]
    assert "human_intervention_rate" in get_data["data"]


def test_evolution_cicd_rest_endpoints(test_client):
    """Verify REST endpoints for Evolution CI/CD governance and status."""
    gov_res = test_client.get("/api/v1/evolution/governance")
    assert gov_res.status_code == 200
    gov_data = gov_res.json()
    assert "autonomous_level" in gov_data
    assert "emergency_kill_switch_tripped" in gov_data
    assert "second_order_metrics" in gov_data

    pkg_res = test_client.get("/api/v1/evolution/pipeline/packages")
    assert pkg_res.status_code == 200
    pkg_data = pkg_res.json()
    assert "packages" in pkg_data

    dream_res = test_client.get("/api/v1/evolution/dreaming/status")
    assert dream_res.status_code == 200
    dream_data = dream_res.json()
    assert "status" in dream_data
    assert "defects_mined" in dream_data
