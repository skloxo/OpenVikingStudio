# -*- coding: utf-8 -*-
"""Unit tests for Card-71 (v1.7.25): Whitebox Sensor Telemetry & Session Detail Inspection Drawer.

Validates:
1. Enriched recent_timeline with whitebox metrics in AgentSensorsAggregator.
2. get_session_detail returns exact token breakdown, formulas, and statuses.
3. REST endpoint GET /api/v1/metrics/agent-sensors/sessions/{session_id} returns 200 and 404.
4. FastMCP openviking_agent_sensors tool supports session_id inspection.
5. Strict environment isolation (zero writes to prod disk).
6. SemVer version 1.7.25 alignment across Python and package.json.
"""

import json
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking._version import __version__
from openviking.core.agent_sensors import AgentSensorsAggregator
from openviking.server.routers.agent_sensors import router as agent_sensors_router
from openviking.server.mcp_endpoint import openviking_agent_sensors


def test_card71_version_alignment():
    """Verify SemVer version alignment across Python and package.json and >= 1.7.25."""
    pkg_path = os.path.join(os.path.dirname(__file__), "..", "..", "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    assert pkg_data["version"] == __version__
    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7)
    assert parts[2] >= 25


def test_enriched_recent_timeline_and_session_detail(tmp_path, monkeypatch):
    """Verify recent_timeline includes all whitebox metrics and get_session_detail computes formulas."""
    agg = AgentSensorsAggregator.get_instance()
    monkeypatch.setattr(agg, "metrics_file", str(tmp_path / "test_sensors.jsonl"))

    # Record sample telemetry point
    point = agg.record_telemetry(
        session_id="test_sess_whitebox_01",
        effective_tokens=2500,
        total_tokens=10000,
        top5_hits=4,
        interventions_count=1,
    )
    assert point.session_id == "test_sess_whitebox_01"

    # 1. Verify get_aggregated_metrics enriched timeline
    metrics = agg.get_aggregated_metrics()
    assert metrics["sample_count"] >= 1
    recent = [pt for pt in metrics["recent_timeline"] if pt["session_id"] == "test_sess_whitebox_01"]
    assert len(recent) == 1
    target = recent[0]
    assert target["effective_tokens"] == 2500
    assert target["total_tokens"] == 10000
    assert target["top5_hits"] == 4
    assert target["interventions"] == 1
    assert target["human_intervention_flag"] is True

    # 2. Verify get_session_detail
    detail = agg.get_session_detail("test_sess_whitebox_01")
    assert detail is not None
    assert detail["session_id"] == "test_sess_whitebox_01"
    assert detail["overhead_tokens"] == 7500
    assert detail["token_snr"] == 0.25
    assert detail["p5_precision"] == 0.8
    assert "2,500 / 10,000" in detail["snr_formula"]
    assert "4 / 5" in detail["p5_formula"]
    assert detail["snr_status"] == "degraded"
    assert detail["p5_status"] == "optimal"
    assert detail["intervention_status"] == "elevated"

    # Non-existent session
    assert agg.get_session_detail("non_existent_session_id") is None


def test_rest_session_detail_endpoint(tmp_path, monkeypatch):
    """Verify REST endpoint /api/v1/metrics/agent-sensors/sessions/{session_id}."""
    agg = AgentSensorsAggregator.get_instance()
    monkeypatch.setattr(agg, "metrics_file", str(tmp_path / "test_rest.jsonl"))

    agg.record_telemetry(
        session_id="test_sess_rest_02",
        effective_tokens=8000,
        total_tokens=10000,
        top5_hits=5,
        interventions_count=0,
    )

    app = FastAPI()
    app.include_router(agent_sensors_router)
    client = TestClient(app)

    # Valid session detail
    res = client.get("/api/v1/metrics/agent-sensors/sessions/test_sess_rest_02")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"]["session_id"] == "test_sess_rest_02"
    assert data["data"]["token_snr"] == 0.8
    assert data["data"]["p5_precision"] == 1.0
    assert data["data"]["overhead_tokens"] == 2000
    assert data["data"]["intervention_status"] == "optimal"

    # 404 for missing session
    res404 = client.get("/api/v1/metrics/agent-sensors/sessions/unknown_session_xyz")
    assert res404.status_code == 404


@pytest.mark.asyncio
async def test_mcp_openviking_agent_sensors_session_inspection(tmp_path, monkeypatch):
    """Verify FastMCP openviking_agent_sensors tool returns breakdown when session_id provided."""
    agg = AgentSensorsAggregator.get_instance()
    monkeypatch.setattr(agg, "metrics_file", str(tmp_path / "test_mcp.jsonl"))

    agg.record_telemetry(
        session_id="test_sess_mcp_03",
        effective_tokens=7000,
        total_tokens=10000,
        top5_hits=5,
        interventions_count=0,
    )

    # 1. Summary call (default session_id="")
    summary = await openviking_agent_sensors()
    assert "=== Agent 3D Performance Sensors Telemetry ===" in summary

    # 2. Detailed call with session_id
    detail_str = await openviking_agent_sensors(session_id="test_sess_mcp_03")
    assert "=== Agent Sensor Session Detail: test_sess_mcp_03 ===" in detail_str
    assert "Total Tokens: 10,000" in detail_str
    assert "Effective: 7,000" in detail_str
    assert "Overhead: 3,000" in detail_str
    assert "Token SNR: 70.0%" in detail_str
    assert "P@5 Adoption: 100.0%" in detail_str

    # 3. Not found call
    missing_str = await openviking_agent_sensors(session_id="missing_session_abc")
    assert "not found in active window" in missing_str
