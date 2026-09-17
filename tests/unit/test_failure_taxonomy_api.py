# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-Observability-FailureTaxonomy-WhitelistSensor (v1.5.11).
Validates failure taxonomy telemetry, anti-loop barrier interceptions,
compression whitelist preservation, and interactive probe HTTP endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.failure_taxonomy_telemetry import (
    FailureTaxonomyTelemetry,
    get_failure_taxonomy_telemetry,
)
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.failure_taxonomy import router as failure_taxonomy_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(failure_taxonomy_router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app)


def test_failure_taxonomy_telemetry_initialization():
    """Verify singleton initialization, clean baseline state, and healthy status."""
    telemetry = get_failure_taxonomy_telemetry()
    telemetry.execute_probe("reset")
    snapshot = telemetry.get_snapshot()

    assert snapshot.status == "healthy"
    assert snapshot.whitelist_items_count == 0
    assert snapshot.estimated_tokens_saved == 0
    assert snapshot.whitelist_preservation_rate == 100.0
    assert snapshot.max_transient_retries == 3


def test_failure_taxonomy_probe_transient():
    """Verify transient error simulation triggers backoff retry and consumes budget."""
    telemetry = get_failure_taxonomy_telemetry()
    res = telemetry.execute_probe("simulate_transient", tool_name="fetch_web_content")

    assert res["category"] == "transient"
    assert res["can_retry"] is True
    assert res["backoff_sec"] > 0
    assert "attempt" in res["reason"] or "Transient" in res["reason"]

    snapshot = telemetry.get_snapshot()
    assert snapshot.transient_count >= 1
    assert snapshot.transient_retries_used >= 1


def test_failure_taxonomy_probe_deterministic_and_anti_loop():
    """Verify deterministic error triggers Anti-Loop Barrier and reflection prompt."""
    telemetry = get_failure_taxonomy_telemetry()
    res = telemetry.execute_probe("simulate_deterministic", tool_name="execute_sql_query")

    assert res["category"] == "deterministic"
    assert res["can_retry"] is False
    assert res["blocked_by_barrier"] is True
    assert res["reflection_prompt"] is not None
    assert "Anti-Loop Barrier" in res["reflection_prompt"]

    snapshot = telemetry.get_snapshot()
    assert snapshot.deterministic_count >= 1
    assert snapshot.anti_loop_interceptions >= 1


def test_failure_taxonomy_probe_fatal():
    """Verify fatal security/OOM error immediately halts execution."""
    telemetry = get_failure_taxonomy_telemetry()
    res = telemetry.execute_probe("simulate_fatal", tool_name="system_exec")

    assert res["category"] == "fatal"
    assert res["can_retry"] is False
    assert res["halt_execution"] is True
    assert "Fatal error" in res["reason"]


def test_failure_taxonomy_probe_whitelist_registration():
    """Verify whitelist registration exempts payload from compaction and updates metrics."""
    telemetry = get_failure_taxonomy_telemetry()
    prev_tokens = telemetry.get_snapshot().estimated_tokens_saved

    res = telemetry.execute_probe("register_whitelist", whitelist_type="TaskPlan")
    assert res["is_protected"] is True
    assert res["tokens_preserved"] == 520

    snapshot = telemetry.get_snapshot()
    assert snapshot.whitelist_by_type["TaskPlan"] >= 1
    assert snapshot.estimated_tokens_saved >= prev_tokens + 520


def test_failure_taxonomy_http_endpoints(client):
    """Verify HTTP GET metrics and POST probe endpoints."""
    # Test GET metrics
    res_get = client.get("/api/v1/system/failure_taxonomy_metrics")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "transient_count" in data
    assert "deterministic_count" in data
    assert "fatal_count" in data
    assert "whitelist_by_type" in data
    assert "recent_events" in data

    # Test POST probe
    res_post = client.post(
        "/api/v1/system/failure_taxonomy_probe",
        json={"action": "simulate_transient", "tool_name": "http_request_get"},
    )
    assert res_post.status_code == 200
    probe_data = res_post.json()
    assert probe_data["category"] == "transient"
    assert probe_data["can_retry"] is True
