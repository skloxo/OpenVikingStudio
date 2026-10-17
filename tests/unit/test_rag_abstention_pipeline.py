# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for MinHash LSH Deduplication & Zero-Hallucination Abstention Gate.
(Card-RAG-Abstention-ZeroHallucination-Pipeline / v1.5.18)
"""

import pytest
from fastapi.testclient import TestClient

from openviking.retrieve.minhash_dedup import MinHashDedup
from openviking.retrieve.abstention_gate import AbstentionGate
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


def test_minhash_near_duplicate_detection():
    """Verify MinHash LSH detects near-duplicate texts while preserving distinct ones."""
    deduper = MinHashDedup(num_perm=64, num_bands=16, threshold=0.75)

    base_doc = "OpenViking provides decentralized memory orchestration with SQLite FTS5 and FastMCP protocol."
    # Near duplicate with minor word tweak
    near_dup = "OpenViking provides decentralized memory orchestration with SQLite FTS5 and FastMCP protocols!"
    # Completely distinct doc
    distinct_doc = "Quantum computing relies on qubits and entanglement to solve discrete optimization problems."

    items = [
        ("doc_1", base_doc),
        ("doc_2", near_dup),
        ("doc_3", distinct_doc),
    ]

    results = deduper.deduplicate(items)
    assert len(results) == 3

    # doc_1 is the initial entry (not duplicate)
    assert results[0].chunk_id == "doc_1"
    assert not results[0].is_duplicate

    # doc_2 is recognized as duplicate of doc_1
    assert results[1].chunk_id == "doc_2"
    assert results[1].is_duplicate
    assert results[1].duplicate_of == "doc_1"
    assert results[1].similarity_score >= 0.75

    # doc_3 is distinct
    assert results[2].chunk_id == "doc_3"
    assert not results[2].is_duplicate
    assert results[2].duplicate_of is None


def test_abstention_gate_grounding_and_decisions():
    """Verify AbstentionGate makes grounded decisions and triggers abstention when evidence is insufficient."""
    gate = AbstentionGate(confidence_threshold=0.40)

    evidence = [
        "The OpenViking service listens on standard port 1933 for HTTP and FastMCP connections.",
        "System telemetry records memory usage, CPU load, and active sessions in SQLite database.",
    ]

    # 1. High confidence groundable query
    q_grounded = "What is the standard port for OpenViking service?"
    decision_ok = gate.verify_and_decide(q_grounded, evidence)
    assert not decision_ok.should_abstain
    assert decision_ok.confidence >= 0.40
    assert "1933" in decision_ok.grounded_tokens or "openviking" in decision_ok.grounded_tokens
    assert decision_ok.abstain_reason is None

    # 2. Out of domain query (zero overlap)
    q_ood = "How to bake a chocolate sourdough bread at 220 degrees celsius?"
    decision_ood = gate.verify_and_decide(q_ood, evidence)
    assert decision_ood.should_abstain
    assert decision_ood.confidence < 0.20
    assert "OUT_OF_DOMAIN" in (decision_ood.abstain_reason or "")

    # 3. Empty or stop-word only query
    decision_empty = gate.verify_and_decide("the and of is", evidence)
    assert decision_empty.should_abstain
    assert "EMPTY_OR_VAGUE_QUERY" in (decision_empty.abstain_reason or "")

    # 4. Zero evidence
    decision_no_ev = gate.verify_and_decide("OpenViking port", [])
    assert decision_no_ev.should_abstain
    assert "NO_EVIDENCE_RETRIEVED" in (decision_no_ev.abstain_reason or "")


def test_rag_abstention_rest_api():
    """Verify RAG abstention and MinHash REST endpoints with authentication."""
    app = create_app()

    def mock_admin_ctx():
        return RequestContext(
            user=UserIdentifier(account_id="test-account", user_id="test-admin"),
            role=Role.ADMIN,
        )

    app.dependency_overrides[get_request_context] = mock_admin_ctx
    client = TestClient(app)

    # 1. GET /api/v1/rag/metrics
    res_m = client.get("/api/v1/rag/metrics")
    assert res_m.status_code == 200
    metrics = res_m.json()
    assert "total_verifications" in metrics
    assert "abstention_rate" in metrics

    # 2. POST /api/v1/rag/dedup
    res_d = client.post(
        "/api/v1/rag/dedup",
        json={
            "chunks": [
                {"id": "c1", "content": "FastMCP server runs on port 1933."},
                {"id": "c2", "content": "FastMCP server runs on port 1933!"},
                {"id": "c3", "content": "Different content entirely here."},
            ],
            "threshold": 0.80,
        },
    )
    assert res_d.status_code == 200
    dedup_results = res_d.json()["results"]
    assert len(dedup_results) == 3
    assert not dedup_results[0]["is_duplicate"]
    assert dedup_results[1]["is_duplicate"]
    assert dedup_results[1]["duplicate_of"] == "c1"

    # 3. POST /api/v1/rag/verify
    res_v = client.post(
        "/api/v1/rag/verify",
        json={
            "query": "What port does FastMCP run on?",
            "evidence_chunks": [
                "FastMCP server runs on port 1933.",
                "FastMCP server runs on port 1933.",
            ],
            "custom_threshold": 0.40,
            "enable_dedup": True,
        },
    )
    assert res_v.status_code == 200
    v_data = res_v.json()
    assert not v_data["decision"]["should_abstain"]
    assert v_data["effective_evidence_count"] == 1
    assert v_data["original_evidence_count"] == 2
