# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Advanced Operational Telemetry (Card-Retrieval-AdvancedCards / v1.5.45).
Verifies:
1. AbstentionGate confidence distribution & recent verifications stream.
2. KnowledgeHygieneEngine report generation with SQLite fts_documents.
3. HybridRetrievalTelemetry rank distribution and exact symbol boost metrics.
"""

import pytest
from openviking.retrieve.abstention_gate import AbstentionGate, AbstentionDecision
from openviking.retrieve.knowledge_hygiene import KnowledgeHygieneEngine, HygieneReport
from openviking.retrieve.hybrid_retriever import HybridRetrievalTelemetry, HybridTelemetrySnapshot
from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine


def test_abstention_gate_confidence_distribution_and_recent_events():
    """Verify confidence bracket bucketing and recent events deque."""
    gate = AbstentionGate(confidence_threshold=0.40)
    
    # 1. High confidence verification
    dec1 = gate.verify_and_decide(
        query="fastmcp tool execution and schema verification",
        evidence_chunks=["fastmcp provides tool execution and schema verification for VikingFS agents"],
    )
    assert not dec1.should_abstain
    assert dec1.confidence >= 0.70
    
    # 2. Low confidence / out-of-domain verification
    dec2 = gate.verify_and_decide(
        query="quantum mechanics superstrings and black holes",
        evidence_chunks=["fastmcp tool execution and schema verification"],
    )
    assert dec2.should_abstain
    assert dec2.confidence < 0.30
    
    # Check snapshot
    snapshot = gate.get_telemetry()
    assert snapshot.total_verifications >= 2
    assert snapshot.total_abstained >= 1
    assert "low" in snapshot.confidence_distribution
    assert "high" in snapshot.confidence_distribution
    assert snapshot.confidence_distribution["low"] >= 1
    assert snapshot.confidence_distribution["high"] >= 1
    assert len(snapshot.recent_verifications) >= 2
    assert snapshot.recent_verifications[-1]["query"].startswith("quantum mechanics")


def test_knowledge_hygiene_report_computation():
    """Verify hygiene engine produces accurate multi-dimensional metrics."""
    decay_engine = AsymmetricDecayEngine()
    hygiene = KnowledgeHygieneEngine(decay_engine)
    
    sample_items = [
        {"uri": "viking://resources/rules/AGENTS.md", "updated_ts": 1789800000, "call_count": 50, "status": "active"},
        {"uri": "viking://resources/old_draft.md", "updated_ts": 1000000000, "call_count": 0, "status": "dormant"},
        {"uri": "viking://resources/conflict_fact.md", "updated_ts": 1789800000, "call_count": 2, "status": "disputed"},
        {"uri": "viking://resources/active_note.md", "updated_ts": 1789800000, "call_count": 10, "status": "active"},
    ]
    
    report: HygieneReport = hygiene.inspect_items(sample_items, dormant_threshold_days=30.0)
    assert report.total_inspected == 4
    assert report.dormant_count == 1
    assert report.disputed_count == 1
    assert 0 <= report.health_score <= 100
    assert len(report.issues) >= 2


def test_hybrid_retriever_telemetry_rank_distribution():
    """Verify rank distribution and overlap metrics in HybridRetrievalTelemetry."""
    telemetry = HybridRetrievalTelemetry()
    
    telemetry.record(
        dense_count=10,
        sparse_count=8,
        fused_count=12,
        overlap_count=6,
        symbol_boost=True,
        latency_ms=14.5,
        dense_only=4,
        sparse_only=2,
    )
    
    snapshot: HybridTelemetrySnapshot = telemetry.get_snapshot(is_bm25_ready=True)
    assert snapshot.total_hybrid_queries == 1
    assert snapshot.exact_symbol_boost_count == 1
    assert snapshot.rank_distribution["hybrid_overlap"] == 6
    assert snapshot.rank_distribution["dense_only"] == 4
    assert snapshot.rank_distribution["sparse_only"] == 2
    assert snapshot.hybrid_overlap_rate == 0.5
