# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Tri-Gate Entropy Crystallizer & Immutable SSOT Distillation.
(Card-Memory-EntropyCrystallizer-TriGate / v1.5.33)
"""

import time
import pytest
from fastapi.testclient import TestClient

from openviking.service.entropy_crystallizer import (
    MemoryFragment,
    TriGateRule,
    TriGateEvaluation,
    FactCrystal,
    CrystallizationResult,
    EntropyCrystallizer,
    TriGateRejectionError,
)
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryStatus,
    _LIFECYCLE_REGISTRY,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


def _build_mock_fragments(
    count: int = 5,
    similarity: float = 0.88,
    cooling_hours: float = 36.0,
) -> list[MemoryFragment]:
    """Helper to build synthetic memory fragments with controlled parameters."""
    now = time.time()
    created_at = now - (cooling_hours * 3600.0)
    fragments = []
    for i in range(count):
        # Create embeddings that produce approximate cosine similarity
        emb = [1.0 if j == 0 else similarity * 0.1 * (1 if i % 2 == 0 else -1) for j in range(8)]
        fragments.append(
            MemoryFragment(
                uri=f"viking://resources/memory/port_lesson_{i+1}.md",
                content=f"OpenViking service port physical binding: 1933 port note {i+1}.",
                created_at=created_at,
                embedding=emb,
                metadata={"author": "antigravity@2080ti", "revision": i + 1},
            )
        )
    return fragments


def test_gate1_cluster_size_rejection():
    """Gate 1: Cluster size < 5 must be rejected by TriGateBarrier."""
    crystallizer = EntropyCrystallizer.get_instance()
    fragments = _build_mock_fragments(count=4, similarity=0.90, cooling_hours=48.0)

    eval_result = crystallizer.evaluate_tri_gate(fragments)
    assert not eval_result.passed
    assert not eval_result.cluster_size_passed
    assert eval_result.cluster_size == 4
    assert any("条数不足 5 条" in r or "at least 5" in r for r in eval_result.rejection_reasons)


def test_gate2_cosine_similarity_rejection():
    """Gate 2: Average cosine similarity <= 0.75 must be rejected."""
    crystallizer = EntropyCrystallizer.get_instance()
    # Build 5 orthogonal / disparate fragments
    now = time.time()
    created_at = now - (30.0 * 3600.0)
    disparate_fragments = []
    for i in range(5):
        emb = [1.0 if j == i else 0.0 for j in range(8)]  # Orthogonal vectors -> sim = 0.0
        disparate_fragments.append(
            MemoryFragment(
                uri=f"viking://resources/memory/diff_{i}.md",
                content=f"Unrelated topic {i}",
                created_at=created_at,
                embedding=emb,
            )
        )

    eval_result = crystallizer.evaluate_tri_gate(disparate_fragments)
    assert not eval_result.passed
    assert not eval_result.similarity_passed
    assert eval_result.avg_similarity <= 0.75
    assert any("余弦相似度" in r or "similarity" in r for r in eval_result.rejection_reasons)


def test_gate3_cooling_period_rejection():
    """Gate 3: Any fragment younger than 24h must be rejected (prevent premature hot crystallization)."""
    crystallizer = EntropyCrystallizer.get_instance()
    # 5 fragments, but cooling is only 2 hours
    fragments = _build_mock_fragments(count=5, similarity=0.92, cooling_hours=2.0)

    eval_result = crystallizer.evaluate_tri_gate(fragments)
    assert not eval_result.passed
    assert not eval_result.cooling_passed
    assert eval_result.cooling_hours < 24.0
    assert any("冷却期" in r or "cooling" in r for r in eval_result.rejection_reasons)


def test_tri_gate_all_passed_and_ssot_distillation():
    """When all 3 gates pass, distillation yields a 3-tier FactCrystal and supersedes source fragments."""
    crystallizer = EntropyCrystallizer.get_instance()
    fragments = _build_mock_fragments(count=5, similarity=0.95, cooling_hours=48.0)

    eval_result = crystallizer.evaluate_tri_gate(fragments)
    assert eval_result.passed
    assert eval_result.cluster_size_passed
    assert eval_result.similarity_passed
    assert eval_result.cooling_passed
    assert len(eval_result.rejection_reasons) == 0

    # Execute distillation
    result = crystallizer.distill_crystal(
        fragments=fragments,
        axiom="对外唯一服务端口物理收口为 1933。",
        version_range=">= v1.5.00",
        deprecated_patterns=["独立 1936 端口常驻服务", "M3 算子硬件强绑定"],
        forbidden_keywords=["1936", "mlx-agent"],
        distiller_id="commander@antigravity",
    )

    # 1. FactCrystal L0/L1/L2 integrity check
    crystal = result.crystal
    assert crystal.axiom == "对外唯一服务端口物理收口为 1933。"  # L0
    assert crystal.context_bounds.version_range == ">= v1.5.00"  # L1
    assert len(crystal.context_bounds.source_uris) == 5  # L1
    assert len(crystal.context_bounds.evidence_hashes) == 5  # L1
    assert "独立 1936 端口常驻服务" in crystal.negative_boundary.deprecated_patterns  # L2
    assert "1936" in crystal.negative_boundary.forbidden_keywords  # L2
    assert crystal.status == "active"

    # 2. Net entropy reduction calculation
    assert result.net_entropy_reduced == 4  # 5 fragments -> 1 crystal (net -4 active nodes)
    assert len(result.superseded_uris) == 5

    # 3. MemoryLifecycleFSM state check: source fragments are now superseded
    for frag in fragments:
        rec = _LIFECYCLE_REGISTRY.get(frag.uri)
        assert rec is not None
        assert rec.status == MemoryStatus.SUPERSEDED
        assert rec.superseded_by == crystal.uri


def test_distill_crystal_rejection_raises_error():
    """Attempting to distill when gates fail must raise TriGateRejectionError."""
    crystallizer = EntropyCrystallizer.get_instance()
    fragments = _build_mock_fragments(count=3, similarity=0.95, cooling_hours=48.0)

    with pytest.raises(TriGateRejectionError, match="Tri-gate barrier blocked crystallization"):
        crystallizer.distill_crystal(
            fragments=fragments,
            axiom="Some test axiom",
            version_range=">= v1.5.00",
        )


def test_crystallizer_rest_api():
    """Verify REST API endpoints: evaluate, distill, stats, and crystals."""
    app = create_app()

    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    now = time.time()
    created_at = now - (36.0 * 3600.0)
    raw_fragments = [
        {
            "uri": f"viking://resources/memory/api_test_{i}.md",
            "content": f"Config port 1933 item {i}",
            "created_at": created_at,
            "embedding": [1.0, 0.8, 0.8, 0.8, 0.0, 0.0, 0.0, 0.0],
        }
        for i in range(5)
    ]

    # 1. POST /api/v1/memory/crystallize/evaluate
    eval_resp = client.post(
        "/api/v1/memory/crystallize/evaluate",
        json={"fragments": raw_fragments},
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()["result"]
    assert eval_data["passed"] is True
    assert eval_data["cluster_size"] == 5

    # 2. POST /api/v1/memory/crystallize/distill
    distill_resp = client.post(
        "/api/v1/memory/crystallize/distill",
        json={
            "fragments": raw_fragments,
            "axiom": "对外统一端口为 1933",
            "version_range": ">= v1.5.00",
            "deprecated_patterns": ["1936 legacy"],
            "forbidden_keywords": ["1936"],
        },
    )
    assert distill_resp.status_code == 200
    distill_data = distill_resp.json()["result"]
    assert distill_data["net_entropy_reduced"] == 4
    crystal_uri = distill_data["crystal"]["uri"]

    # 3. GET /api/v1/memory/crystallize/stats
    stats_resp = client.get("/api/v1/memory/crystallize/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()["result"]
    assert stats_data["total_crystals"] >= 1
    assert stats_data["total_net_entropy_reduced"] >= 4

    # 4. GET /api/v1/memory/crystallize/crystals
    list_resp = client.get("/api/v1/memory/crystallize/crystals")
    assert list_resp.status_code == 200
    crystals_data = list_resp.json()["result"]
    assert len(crystals_data) >= 1
    uris = [c["uri"] for c in crystals_data]
    assert crystal_uri in uris
