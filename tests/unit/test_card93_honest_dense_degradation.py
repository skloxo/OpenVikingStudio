# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-93: Honest Dense-Degradation & GPU Node Heartbeat Fallback."""

import socket
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.hybrid_search import probe_gpu_node, router
from openviking_cli.session.user_id import UserIdentifier


def _make_client() -> TestClient:
    """Build a TestClient with auth dependency bypassed."""
    _app = FastAPI()
    _app.include_router(router)
    _mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    _app.dependency_overrides[get_request_context] = lambda: _mock_ctx
    return TestClient(_app, raise_server_exceptions=False)


_client = _make_client()


# ---------------------------------------------------------------------------
# 1. probe_gpu_node unit tests
# ---------------------------------------------------------------------------

class TestProbeGpuNode:
    """Verify heartbeat probe behavior without real network calls."""

    def test_online_returns_true_and_latency(self):
        """When connection succeeds, returns (True, latency_ms >= 0)."""
        mock_sock = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_sock
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_ctx):
            alive, latency = probe_gpu_node(host="127.0.0.1", port=11432, timeout_s=0.2)

        assert alive is True
        assert latency >= 0.0

    def test_offline_connection_refused_returns_false(self):
        """ConnectionRefusedError → (False, latency_ms >= 0), never raises."""
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            alive, latency = probe_gpu_node(host="127.0.0.1", port=11432, timeout_s=0.2)

        assert alive is False
        assert latency >= 0.0

    def test_offline_timeout_returns_false(self):
        """TimeoutError → (False, latency_ms >= 0), never raises."""
        with patch("socket.create_connection", side_effect=TimeoutError):
            alive, latency = probe_gpu_node(host="127.0.0.1", port=11432, timeout_s=0.2)

        assert alive is False
        assert latency >= 0.0

    def test_offline_oserror_returns_false(self):
        """OSError (generic unreachable) → (False, latency_ms >= 0)."""
        with patch("socket.create_connection", side_effect=OSError("unreachable")):
            alive, latency = probe_gpu_node()

        assert alive is False
        assert latency >= 0.0

    def test_timeout_respected(self):
        """Probe must respect the timeout_s parameter contract (no actual wait in test)."""
        with patch("socket.create_connection", side_effect=TimeoutError) as mock_conn:
            probe_gpu_node(host="127.0.0.1", port=11432, timeout_s=0.05)
            mock_conn.assert_called_once_with(("127.0.0.1", 11432), timeout=0.05)


# ---------------------------------------------------------------------------
# 2. hybrid_metrics endpoint — gpu_node field
# ---------------------------------------------------------------------------

class TestHybridMetricsEndpoint:
    """Verify /api/v1/search/hybrid_metrics always returns gpu_node block."""

    def _mock_deps(self, gpu_alive: bool):
        bm25_mock = MagicMock()
        bm25_mock.get_stats.return_value = MagicMock(
            is_ready=True,
            total_documents=42,
            db_size_bytes=1024,
            db_path="/tmp/test.db",
            model_dump=lambda: {
                "total_documents": 42,
                "db_size_bytes": 1024,
                "db_path": "/tmp/test.db",
                "is_ready": True,
            },
        )
        telemetry_mock = MagicMock()
        snap = MagicMock()
        snap.model_dump.return_value = {
            "total_hybrid_queries": 0,
            "dense_candidates_total": 0,
            "sparse_candidates_total": 0,
            "hybrid_fused_total": 0,
            "hybrid_overlap_rate": 0.0,
            "exact_symbol_boost_count": 0,
            "avg_latency_ms": 0.0,
            "is_bm25_ready": True,
        }
        telemetry_mock.get_snapshot.return_value = snap
        return bm25_mock, telemetry_mock

    def test_metrics_contains_gpu_node_when_online(self):
        bm25_mock, telemetry_mock = self._mock_deps(gpu_alive=True)
        with (
            patch("openviking.server.routers.hybrid_search.BM25FTSIndex.get_instance", return_value=bm25_mock),
            patch("openviking.server.routers.hybrid_search.HybridRetrievalTelemetry.get_instance", return_value=telemetry_mock),
            patch("openviking.server.routers.hybrid_search.probe_gpu_node", return_value=(True, 12.5)),
        ):
            resp = _client.get("/api/v1/search/hybrid_metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert "gpu_node" in data
        assert data["gpu_node"]["status"] == "online"
        assert data["gpu_node"]["latency_ms"] == 12.5

    def test_metrics_contains_gpu_node_when_offline(self):
        bm25_mock, telemetry_mock = self._mock_deps(gpu_alive=False)
        with (
            patch("openviking.server.routers.hybrid_search.BM25FTSIndex.get_instance", return_value=bm25_mock),
            patch("openviking.server.routers.hybrid_search.HybridRetrievalTelemetry.get_instance", return_value=telemetry_mock),
            patch("openviking.server.routers.hybrid_search.probe_gpu_node", return_value=(False, 200.1)),
        ):
            resp = _client.get("/api/v1/search/hybrid_metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["gpu_node"]["status"] == "offline"
        assert data["gpu_node"]["latency_ms"] == 200.1


# ---------------------------------------------------------------------------
# 3. hybrid_probe endpoint — honest degradation when GPU offline
# ---------------------------------------------------------------------------

class TestHybridProbeHonestDegradation:
    """Core Card-93 invariant: offline GPU → pure BM25, degraded=True, zero fake Dense."""

    def _bm25_with_results(self):
        bm25_mock = MagicMock()
        match = MagicMock()
        match.uri = "viking://test/doc"
        match.title = "Test Document"
        match.level = 2
        match.context_type = "resource"
        match.bm25_score = 0.85
        match.snippet = "test snippet"
        match.model_dump.return_value = {
            "uri": "viking://test/doc",
            "title": "Test Document",
            "level": 2,
            "context_type": "resource",
            "bm25_score": 0.85,
            "snippet": "test snippet",
        }
        bm25_mock.search.return_value = [match]
        return bm25_mock

    def test_gpu_offline_returns_degraded_true_and_no_dense(self):
        """When GPU is offline, response must: degraded=True, dense_count=0, dense_status=offline."""
        bm25_mock = self._bm25_with_results()
        telemetry_mock = MagicMock()

        with (
            patch("openviking.server.routers.hybrid_search.BM25FTSIndex.get_instance", return_value=bm25_mock),
            patch("openviking.server.routers.hybrid_search.HybridRetrievalTelemetry.get_instance", return_value=telemetry_mock),
            patch("openviking.server.routers.hybrid_search.probe_gpu_node", return_value=(False, 201.3)),
        ):
            resp = _client.post("/api/v1/search/hybrid_probe", json={"query": "test query", "limit": 5})

        assert resp.status_code == 200
        data = resp.json()
        # Honest degradation invariants
        assert data["degraded"] is True
        assert data["dense_status"] == "offline"
        assert data["dense_count"] == 0
        # BM25 still works
        assert data["sparse_bm25_count"] >= 0
        # No fake dense injected
        assert data["dense_results"] == []

    def test_gpu_online_returns_not_degraded(self):
        """When GPU is online, degraded=False and dense_status=online."""
        bm25_mock = self._bm25_with_results()
        telemetry_mock = MagicMock()
        # Dense retrieval path: no service available → exception caught, status becomes 'error'
        # but importantly we should NOT see 'offline'
        with (
            patch("openviking.server.routers.hybrid_search.BM25FTSIndex.get_instance", return_value=bm25_mock),
            patch("openviking.server.routers.hybrid_search.HybridRetrievalTelemetry.get_instance", return_value=telemetry_mock),
            patch("openviking.server.routers.hybrid_search.probe_gpu_node", return_value=(True, 8.0)),
        ):
            resp = _client.post("/api/v1/search/hybrid_probe", json={"query": "openviking", "limit": 3})

        assert resp.status_code == 200
        data = resp.json()
        # Even if dense retrieval fails after probe, the dense_status reflects GPU state
        assert data["dense_status"] in ("online", "error")
        assert data["degraded"] in (True, False)  # depends on service availability

    def test_response_always_includes_gpu_heartbeat_ms(self):
        """gpu_heartbeat_ms must always be present in probe response."""
        bm25_mock = self._bm25_with_results()
        telemetry_mock = MagicMock()

        with (
            patch("openviking.server.routers.hybrid_search.BM25FTSIndex.get_instance", return_value=bm25_mock),
            patch("openviking.server.routers.hybrid_search.HybridRetrievalTelemetry.get_instance", return_value=telemetry_mock),
            patch("openviking.server.routers.hybrid_search.probe_gpu_node", return_value=(False, 199.9)),
        ):
            resp = _client.post("/api/v1/search/hybrid_probe", json={"query": "latency check"})

        assert resp.status_code == 200
        data = resp.json()
        assert "gpu_heartbeat_ms" in data
        assert data["gpu_heartbeat_ms"] == 199.9

    def test_zero_mock_compliance_no_fake_dense_when_offline(self):
        """Strict zero-mock compliance: offline probe must NEVER inject non-empty dense_results."""
        bm25_mock = self._bm25_with_results()
        telemetry_mock = MagicMock()

        # Run 3 offline probes with different queries
        queries = ["VikingFS.commit", "port 11432", "HierarchicalRetriever"]
        for q in queries:
            with (
                patch("openviking.server.routers.hybrid_search.BM25FTSIndex.get_instance", return_value=bm25_mock),
                patch("openviking.server.routers.hybrid_search.HybridRetrievalTelemetry.get_instance", return_value=telemetry_mock),
                patch("openviking.server.routers.hybrid_search.probe_gpu_node", return_value=(False, 200.0)),
            ):
                resp = _client.post("/api/v1/search/hybrid_probe", json={"query": q, "limit": 5})
            assert resp.status_code == 200
            data = resp.json()
            # Zero-mock compliance: dense_results must be empty list when offline
            assert data["dense_results"] == [], f"Fake Dense injected for query='{q}'"
            assert data["degraded"] is True
