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
    assert probe_data["real_drill_executed"] is True
    assert probe_data["drill_success"] is True


def test_chaos_drill_transient_429_direct():
    """Card-90: 验证 ChaosResilienceEngine 真实 429 注入与指数退避自愈。"""
    import asyncio
    from openviking.core.chaos_resilience_engine import ChaosResilienceEngine

    engine = ChaosResilienceEngine.get_instance()
    res = asyncio.run(engine.drill_transient_retry(tool_name="test_api_probe", max_retries=3))
    assert res.success is True
    assert res.drill_type == "transient_429"
    assert res.duration_ms > 0.0
    assert res.details["attempts_used"] == 2
    assert res.details["healed"] is True
    assert len(res.details["retry_delays_ms"]) >= 1


def test_chaos_drill_watchdog_timeout_direct():
    """Card-90: 验证 Watchdog 僵尸任务超时熔断与物理回收。"""
    import asyncio
    from openviking.core.chaos_resilience_engine import ChaosResilienceEngine

    engine = ChaosResilienceEngine.get_instance()
    res = asyncio.run(engine.drill_watchdog_timeout(hang_duration_sec=0.5, watchdog_limit_sec=0.05))
    assert res.success is True
    assert res.drill_type == "watchdog_timeout"
    assert res.details["timeout_triggered"] is True
    assert res.details["task_reclaimed"] is True
    assert res.details["reclaim_latency_ms"] >= 0.0


def test_chaos_drill_real_merkle_tree():
    """Card-90: 验证真实 Merkle 状态树哈希计算，彻底消除 dummy [i*i] 假代码。"""
    from openviking.core.chaos_resilience_engine import ChaosResilienceEngine

    engine = ChaosResilienceEngine.get_instance()
    res = engine.drill_real_merkle_tree()
    assert res.success is True
    assert res.drill_type == "real_merkle"
    assert res.details["scanned_files"] > 0
    assert len(res.details["merkle_root"]) == 64
    assert res.duration_ms > 0.0


def test_agent_loop_probe_merkle_real():
    """Card-90: 验证 AgentLoopTelemetry 接入真实 Merkle 计算。"""
    from openviking.core.agent_loop_telemetry import get_agent_loop_telemetry_collector

    collector = get_agent_loop_telemetry_collector()
    res = collector.simulate_probe("probe_merkle")
    assert res["success"] is True
    assert res["file_count"] > 0
    assert len(res["merkle_root"]) == 64
    assert res["diff_ms"] > 0.0
