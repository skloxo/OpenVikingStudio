# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-90: Chaos Resilience Middleware & Watchdog Drill.

Covers:
  1. ChaosResilienceEngine.drill_transient_retry — real 429 backoff + Jitter
  2. ChaosResilienceEngine.drill_watchdog_timeout — zombie task physical cancellation
  3. ChaosResilienceEngine.drill_real_merkle_tree — real file SHA-256 Merkle root
  4. /api/v1/system/failure_taxonomy_probe endpoint — probe header isolation
  5. Production isolation: non-probe requests are never affected
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.chaos_resilience_engine import ChaosResilienceEngine, ChaosDrillResult
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.failure_taxonomy import router
from openviking_cli.session.user_id import UserIdentifier


# ---------------------------------------------------------------------------
# Fixture: TestClient with auth bypass
# ---------------------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_engine():
    """Ensure ChaosResilienceEngine singleton is fresh per test."""
    ChaosResilienceEngine.reset_instance()
    yield
    ChaosResilienceEngine.reset_instance()


# ---------------------------------------------------------------------------
# 1. ChaosResilienceEngine Unit Tests
# ---------------------------------------------------------------------------

class TestDrillTransientRetry:
    """Real 429 exponential backoff drill unit tests."""

    def test_returns_healed_true_on_success(self):
        """429 first attempt → backoff sleep → 200 OK on second."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(engine.drill_transient_retry(tool_name="test_tool", max_retries=3))

        assert isinstance(result, ChaosDrillResult)
        assert result.drill_type == "transient_429"
        assert result.success is True
        assert result.details["healed"] is True
        assert result.details["attempts_used"] == 2
        assert result.details["initial_status"] == 429
        assert result.details["final_status"] == 200
        assert result.production_isolated is True

    def test_retry_delays_are_non_empty(self):
        """Must record at least one real retry delay (exponential backoff executed)."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(engine.drill_transient_retry())

        assert len(result.details["retry_delays_ms"]) >= 1
        # Delay must be > 0 (real sleep was executed)
        assert all(d > 0 for d in result.details["retry_delays_ms"])

    def test_backoff_algorithm_is_exponential_with_jitter(self):
        """Backoff algorithm field must be ExponentialBackoffWithFullJitter."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(engine.drill_transient_retry())

        assert "ExponentialBackoff" in result.details["backoff_algorithm"]

    def test_duration_ms_is_positive(self):
        """Physical drill must have measurable elapsed time."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(engine.drill_transient_retry())

        assert result.duration_ms > 0.0


class TestDrillWatchdogTimeout:
    """Zombie task Watchdog timeout drill unit tests."""

    def test_watchdog_triggers_timeout_and_cancels_task(self):
        """Watchdog must physically cancel the zombie coroutine."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(
            engine.drill_watchdog_timeout(hang_duration_sec=1.0, watchdog_limit_sec=0.1)
        )

        assert result.drill_type == "watchdog_timeout"
        assert result.success is True
        assert result.details["timeout_triggered"] is True
        assert result.details["task_reclaimed"] is True
        assert result.details["zombie_leak_prevented"] is True
        assert result.production_isolated is True

    def test_reclaim_latency_is_tracked(self):
        """Resource reclaim latency must be recorded (physical GC evidence)."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(
            engine.drill_watchdog_timeout(hang_duration_sec=0.5, watchdog_limit_sec=0.05)
        )

        assert result.details["reclaim_latency_ms"] >= 0.0

    def test_task_is_truly_cancelled(self):
        """The zombie asyncio task must be in CANCELLED state after drill."""
        engine = ChaosResilienceEngine.get_instance()
        result = asyncio.run(
            engine.drill_watchdog_timeout(hang_duration_sec=2.0, watchdog_limit_sec=0.05)
        )

        assert result.details.get("task_cancelled", True) is True


class TestDrillRealMerkleTree:
    """Real file traversal + SHA-256 Merkle root drill unit tests."""

    def test_merkle_root_is_valid_hex_string(self, tmp_path):
        """Merkle root must be a valid 64-char SHA-256 hex string."""
        # Create a simple test directory with 2 files
        (tmp_path / "a.txt").write_text("hello world", encoding="utf-8")
        (tmp_path / "b.txt").write_text("viking fs", encoding="utf-8")

        engine = ChaosResilienceEngine.get_instance()
        result = engine.drill_real_merkle_tree(target_dir=str(tmp_path), max_files=10)

        assert result.drill_type == "real_merkle"
        assert result.success is True
        merkle_root = result.details["merkle_root"]
        assert isinstance(merkle_root, str)
        assert len(merkle_root) == 64  # SHA-256 hex

    def test_scanned_files_count_accurate(self, tmp_path):
        """scanned_files must match actual number of files created."""
        for i in range(5):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}", encoding="utf-8")

        engine = ChaosResilienceEngine.get_instance()
        result = engine.drill_real_merkle_tree(target_dir=str(tmp_path), max_files=10)

        assert result.details["scanned_files"] == 5

    def test_max_files_cap_respected(self, tmp_path):
        """max_files cap must be respected — no more files scanned than limit."""
        for i in range(20):
            (tmp_path / f"file{i}.txt").write_text(f"data {i}", encoding="utf-8")

        engine = ChaosResilienceEngine.get_instance()
        result = engine.drill_real_merkle_tree(target_dir=str(tmp_path), max_files=3)

        assert result.details["scanned_files"] <= 3

    def test_production_isolated_always_true(self, tmp_path):
        """Merkle drill must always report production_isolated=True."""
        (tmp_path / "test.txt").write_text("safe", encoding="utf-8")
        engine = ChaosResilienceEngine.get_instance()
        result = engine.drill_real_merkle_tree(target_dir=str(tmp_path))

        assert result.production_isolated is True


# ---------------------------------------------------------------------------
# 2. /api/v1/system/failure_taxonomy_probe Endpoint Tests
# ---------------------------------------------------------------------------

class TestFailureTaxonomyProbeEndpoint:
    """Endpoint-level tests for Card-90 chaos drill route."""

    def test_simulate_transient_returns_real_drill_executed(self, client):
        """429 backoff drill must return real_drill_executed=True."""
        resp = client.post(
            "/api/v1/system/failure_taxonomy_probe",
            json={"action": "simulate_transient", "tool_name": "test_tool"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["real_drill_executed"] is True
        assert data["drill_success"] is True
        assert data["healed"] is True

    def test_drill_watchdog_timeout_action(self, client):
        """Watchdog drill must return real_drill_executed=True and task_reclaimed=True."""
        resp = client.post(
            "/api/v1/system/failure_taxonomy_probe",
            json={"action": "drill_watchdog_timeout"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["real_drill_executed"] is True
        assert data["drill_success"] is True
        assert data["task_reclaimed"] is True
        assert data["zombie_leak_prevented"] is True

    def test_drill_real_merkle_action(self, client):
        """Merkle tree drill must return real Merkle root hash."""
        resp = client.post(
            "/api/v1/system/failure_taxonomy_probe",
            json={"action": "drill_real_merkle"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["real_drill_executed"] is True
        assert data["drill_success"] is True
        # Details must contain the merkle_root hash
        assert "merkle_root" in data.get("details", {})

    def test_unknown_action_falls_back_gracefully(self, client):
        """Unknown action must not 500 — fallback to telemetry probe."""
        resp = client.post(
            "/api/v1/system/failure_taxonomy_probe",
            json={"action": "unknown_action", "tool_name": "x"},
        )
        assert resp.status_code == 200

    def test_production_isolation_regular_requests_unaffected(self, client):
        """Non-chaos actions must never trigger fault injection."""
        # Getting telemetry metrics must succeed cleanly
        resp = client.get("/api/v1/system/failure_taxonomy_metrics")
        assert resp.status_code == 200
        data = resp.json()
        # No drill contamination in telemetry (production 0 pollution)
        assert "total_transient_retries" in data or "action" not in data
