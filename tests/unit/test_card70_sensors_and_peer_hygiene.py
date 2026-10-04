# -*- coding: utf-8 -*-
"""Unit tests for Card-70 (v1.7.24): Sensors & Peer Matrix Hygiene and Isolation.

Validates:
1. Pytest write prevention guard in AgentSensorsAggregator (no writes to prod disk).
2. Isolated telemetry recording in test sandbox (tmp_path).
3. Production metrics file is clean from test_ / sess_ fake pollution.
4. Console peers matrix hygiene: Mac Studio phantom agent removed, 0-message peers show ready & '--'.
5. Version alignment to 1.7.24 across _version.py and package.json.
"""

import json
import os
import sys
import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI

from openviking._version import __version__
from openviking.core.agent_sensors import AgentSensorsAggregator
from openviking.server.routers.console import router as console_router


def test_pytest_production_file_write_protection(tmp_path):
    """Verify record_telemetry refuses to write to production disk in pytest."""
    agg = AgentSensorsAggregator.get_instance()
    prod_path = os.path.abspath(os.path.expanduser("~/.openviking/data/agent_metrics.jsonl"))
    agg.metrics_file = prod_path

    initial_lines = 0
    if os.path.exists(prod_path):
        with open(prod_path, "r", encoding="utf-8") as f:
            initial_lines = len(f.readlines())

    point = agg.record_telemetry(
        session_id="test_probe_guard_01",
        effective_tokens=500,
        total_tokens=1000,
        top5_hits=3,
        interventions_count=0,
    )
    assert point.session_id == "test_probe_guard_01"

    after_lines = 0
    if os.path.exists(prod_path):
        with open(prod_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            after_lines = len(lines)
            assert not any("test_probe_guard_01" in l for l in lines)

    assert after_lines == initial_lines


def test_isolated_telemetry_recording(tmp_path):
    """Verify that isolated AgentSensorsAggregator writes normally to tmp_path."""
    sandbox_dir = tmp_path / "custom_data"
    agg = AgentSensorsAggregator(log_dir=str(sandbox_dir))

    point = agg.record_telemetry(
        session_id="sandbox_session_01",
        effective_tokens=800,
        total_tokens=1000,
        top5_hits=4,
        interventions_count=0,
    )
    assert point.token_snr == 0.8
    assert point.p5_precision == 0.8
    assert os.path.exists(sandbox_dir / "agent_metrics.jsonl")

    metrics = agg.get_aggregated_metrics()
    assert metrics["sample_count"] == 1
    assert metrics["avg_token_snr"] == 0.8


def test_production_metrics_file_is_clean():
    """Verify that production agent_metrics.jsonl has zero test_ or sess_ pollution."""
    prod_path = os.path.abspath(os.path.expanduser("~/.openviking/data/agent_metrics.jsonl"))
    if os.path.exists(prod_path):
        with open(prod_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    sid = data.get("session_id", "")
                    assert not sid.startswith("test_"), f"Pollution found: {sid}"
                    assert not sid.startswith("sess_"), f"Pollution found: {sid}"


def test_console_peers_matrix_hygiene():
    """Verify that console peers matrix has eliminated Mac Studio and handles 0-message peers cleanly."""
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = FastAPI()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="default", user_id="default"),
        role=Role.ROOT,
    )
    app.include_router(console_router)
    client = TestClient(app)

    res = client.get("/api/v1/console/peers")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    peers = body["result"]

    peer_ids = [p["id"] for p in peers]
    # 1. Mac Studio phantom agent must not exist in peer fleet
    assert "antigravity@macstudio" not in peer_ids

    # 2. Inactive/0-message peers must have status 'ready' and lastSync '--'
    for p in peers:
        if p["messagesCount"] == 0:
            assert p["status"] == "ready", f"Peer {p['id']} with 0 messages should be ready"
            assert p["lastSync"] == "--", f"Peer {p['id']} with 0 messages should have lastSync '--'"


def test_card70_version_alignment():
    """Verify SemVer version 1.7.24 across Python and package.json."""
    assert __version__ == "1.7.24"
    pkg_path = os.path.join(os.path.dirname(__file__), "..", "..", "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    assert pkg_data["version"] == "1.7.24"
