# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for BM25 SQLite FTS5 Lexical Index, RRF Fusion, and Hybrid Search Diagnostics.
(Card-Retrieval-BM25Hybrid / v1.5.16)
"""

import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.storage.bm25_fts_index import BM25FTSIndex
from openviking.retrieve.rrf_fusion import rrf_fuse, FusedCandidate
from openviking.retrieve.hybrid_retriever import HybridRetriever, HybridRetrievalTelemetry
from openviking.server.app import create_app


@pytest.fixture
def temp_bm25_index(tmp_path):
    """Fixture providing an isolated BM25 FTS5 index in a temp directory."""
    db_file = tmp_path / "test_bm25.db"
    index = BM25FTSIndex(db_path=db_file)
    yield index
    if db_file.exists():
        db_file.unlink(missing_ok=True)


def test_bm25_index_and_exact_symbol_search(temp_bm25_index):
    """Verify that exact code symbols, snake_case, and methods are retrieved accurately."""
    # Index test documents
    docs = [
        {
            "uri": "viking://openviking/session_service.py",
            "title": "Session Service",
            "content": "def is_heartbeat_session(meta): return meta.get('is_heartbeat', False)",
            "level": 2,
            "context_type": "resource",
        },
        {
            "uri": "viking://openviking/viking_fs.py",
            "title": "VikingFS Core",
            "content": "class VikingFS: async def commit(self, message: str): pass",
            "level": 2,
            "context_type": "resource",
        },
        {
            "uri": "viking://openviking/server_config.py",
            "title": "Server Config",
            "content": "DEFAULT_PORT = 1933; HOST = '127.0.0.1'",
            "level": 2,
            "context_type": "resource",
        },
    ]
    indexed = temp_bm25_index.index_batch(docs)
    assert indexed == 3

    # 1. Exact snake_case symbol search
    matches = temp_bm25_index.search("is_heartbeat_session")
    assert len(matches) >= 1
    assert matches[0].uri == "viking://openviking/session_service.py"
    assert matches[0].bm25_score > 0.0
    assert "is_heartbeat_session" in matches[0].snippet or "is_heartbeat_session" in matches[0].title

    # 2. Dot-separated symbol search
    matches_commit = temp_bm25_index.search("VikingFS.commit")
    assert len(matches_commit) >= 1
    assert matches_commit[0].uri == "viking://openviking/viking_fs.py"

    # 3. Numeric port search
    matches_port = temp_bm25_index.search("1933")
    assert len(matches_port) >= 1
    assert matches_port[0].uri == "viking://openviking/server_config.py"

    # 4. Nonexistent term returns empty
    matches_empty = temp_bm25_index.search("nonexistent_random_symbol_998877")
    assert len(matches_empty) == 0

    # 5. Delete document
    deleted = temp_bm25_index.delete_document("viking://openviking/server_config.py")
    assert deleted is True
    assert len(temp_bm25_index.search("1933")) == 0

    stats = temp_bm25_index.get_stats()
    assert stats.total_documents == 2
    assert stats.is_ready is True


def test_rrf_rank_fusion_provenance():
    """Verify Reciprocal Rank Fusion k=60 math and origin labeling."""
    dense_results = [
        {"uri": "viking://doc/A", "title": "Doc A", "score": 0.95},
        {"uri": "viking://doc/B", "title": "Doc B", "score": 0.85},
        {"uri": "viking://doc/C", "title": "Doc C", "score": 0.75},
    ]
    sparse_results = [
        {"uri": "viking://doc/B", "title": "Doc B", "bm25_score": 0.99},
        {"uri": "viking://doc/D", "title": "Doc D (exact symbol)", "bm25_score": 0.90},
    ]

    fused = rrf_fuse(dense_results, sparse_results, k=60, top_k=5)

    assert len(fused) == 4
    # Doc B is in both dense (rank 2) and sparse (rank 1)
    # Score for B = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = ~0.03252
    # Score for A = 1/(60+1) = 1/61 = ~0.01639
    # Score for D = 1/(60+2) = 1/62 = ~0.016129
    # Therefore, Doc B should be rank 1 with origin 'hybrid'
    assert fused[0].uri == "viking://doc/B"
    assert fused[0].origin == "hybrid"
    assert fused[0].dense_rank == 2
    assert fused[0].sparse_rank == 1

    uris = [f.uri for f in fused]
    assert "viking://doc/D" in uris
    d_cand = next(f for f in fused if f.uri == "viking://doc/D")
    assert d_cand.origin == "sparse_only"
    assert d_cand.dense_rank is None
    assert d_cand.sparse_rank == 2

    a_cand = next(f for f in fused if f.uri == "viking://doc/A")
    assert a_cand.origin == "dense_only"
    assert a_cand.sparse_rank is None
    assert a_cand.dense_rank == 1


@pytest.mark.asyncio
async def test_hybrid_retriever_telemetry(temp_bm25_index):
    """Verify HybridRetriever orchestrator and telemetry metrics accumulation."""
    temp_bm25_index.index_document(
        uri="viking://test/code",
        title="Code File",
        content="def calculate_merkle_root(): pass",
    )
    retriever = HybridRetriever(bm25_index=temp_bm25_index)

    dense_sample = [
        {"uri": "viking://test/semantic", "title": "Semantic File", "score": 0.88}
    ]

    # Query matching exact code symbol
    results = await retriever.retrieve_hybrid(
        query="calculate_merkle_root",
        dense_candidates=dense_sample,
        limit=5,
    )
    assert len(results) >= 1
    snapshot = retriever.telemetry.get_snapshot()
    assert snapshot.total_hybrid_queries >= 1
    assert snapshot.exact_symbol_boost_count >= 1
    assert snapshot.is_bm25_ready is True


def test_hybrid_search_rest_api():
    """Verify hybrid REST metrics and diagnostic probe endpoints."""
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role
    from openviking_cli.session.user_id import UserIdentifier

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="test-user"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. GET /api/v1/search/hybrid_metrics
    res = client.get("/api/v1/search/hybrid_metrics")
    assert res.status_code == 200
    data = res.json()
    assert "telemetry" in data
    assert "index_stats" in data
    assert "total_hybrid_queries" in data["telemetry"]
    assert "is_ready" in data["index_stats"]

    # 2. POST /api/v1/search/hybrid_probe
    probe_res = client.post(
        "/api/v1/search/hybrid_probe",
        json={"query": "test_symbol_probe", "limit": 5},
    )
    assert probe_res.status_code == 200
    probe_data = probe_res.json()
    assert "sparse_results" in probe_data
    assert "dense_results" in probe_data
    assert "fused_results" in probe_data
    assert "latency_ms" in probe_data


def test_exact_code_symbol_and_payload_guard(temp_bm25_index):
    """Verify exact underscore symbols, ports, and payload guard against write amplification."""
    # 1. Payload guard: base64 image data should be rejected
    ok_base64 = temp_bm25_index.index_document(
        uri="viking://test/img.png",
        title="Image",
        content="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    )
    assert ok_base64 is False

    # 2. Large content should be clamped and indexed safely
    huge_content = "def _query_endpoint_frequency_sync(): return True\n" + ("padding " * 10000)
    ok_huge = temp_bm25_index.index_document(
        uri="viking://test/huge.py",
        title="Huge File",
        content=huge_content,
    )
    assert ok_huge is True

    # 3. Exact symbol search for _query_endpoint_frequency_sync
    matches = temp_bm25_index.search("_query_endpoint_frequency_sync")
    assert len(matches) >= 1
    assert matches[0].uri == "viking://test/huge.py"
    assert matches[0].bm25_score > 0.0

    # 4. RRF normalized score check
    dense = [{"uri": "viking://test/other", "score": 0.9}]
    sparse = [{"uri": "viking://test/huge.py", "bm25_score": 0.95}]
    fused = rrf_fuse(dense, sparse, k=60, top_k=2)
    assert len(fused) == 2
    assert fused[0].normalized_score == 1.0
    assert 0.0 <= fused[1].normalized_score <= 1.0
