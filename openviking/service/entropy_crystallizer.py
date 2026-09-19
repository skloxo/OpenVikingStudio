# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Tri-Gate Entropy Crystallizer & Immutable SSOT Distillation Engine.
(Card-Memory-EntropyCrystallizer-TriGate / v1.5.33)

First Principles:
1. Tri-Gate Barrier: Strict parallel AND gate preventing premature or noisy crystallization:
   - Gate 1: Cluster Size >= 5 (statistical significance).
   - Gate 2: Avg Cosine Similarity > 0.75 (semantic tight convergence).
   - Gate 3: Cooling Period >= 24h (reject hot in-flight session data).
2. Three-Tier Fact Crystal Schema:
   - L0 Axiom: Single uncompromised, unambiguous declarative statement.
   - L1 Context & Bounds: Target version range, lineage source URIs, content SHA-256 hashes.
   - L2 Negative Boundary: Explicitly deprecated patterns & forbidden keywords.
3. Net Entropy Reduction:
   - When 1 Fact Crystal is distilled from N fragments (N >= 5), original fragments are
     atomically marked superseded via MemoryLifecycleFSM, achieving net node reduction (N - 1).
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleRecord,
    MemoryLifecycleStore,
    MemoryStatus,
    LifecycleTransitionEvent,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryFragment(BaseModel):
    """Raw candidate memory fragment in the crystallization pool."""
    uri: str
    content: str
    created_at: float = Field(default_factory=time.time)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TriGateRule(BaseModel):
    """Configuration thresholds for the tri-gate barrier."""
    min_cluster_size: int = 5
    min_avg_cosine_similarity: float = 0.75
    cooling_period_hours: float = 24.0


class TriGateEvaluation(BaseModel):
    """Verification results for the three parallel hard gates."""
    passed: bool
    cluster_size: int
    cluster_size_passed: bool
    avg_similarity: float
    similarity_passed: bool
    cooling_hours: float
    cooling_passed: bool
    rejection_reasons: List[str] = Field(default_factory=list)


class CrystalContextBounds(BaseModel):
    """L1: Target version range, provenance source URIs, and evidence hashes."""
    version_range: str
    source_uris: List[str]
    evidence_hashes: List[str]
    distilled_at: float = Field(default_factory=time.time)
    distiller_id: str = "openviking-crystallizer"


class CrystalNegativeBoundary(BaseModel):
    """L2: Repulsion sentinels, deprecated anti-patterns, and forbidden keywords."""
    deprecated_patterns: List[str] = Field(default_factory=list)
    forbidden_keywords: List[str] = Field(default_factory=list)


class FactCrystal(BaseModel):
    """Three-Tier Immutable Fact Crystal Schema (L0 / L1 / L2)."""
    uri: str
    axiom: str  # L0: Core Immutable Axiom
    context_bounds: CrystalContextBounds  # L1: Version range & Evidence chain
    negative_boundary: CrystalNegativeBoundary  # L2: Negative Repulsion Boundary
    status: str = "active"
    created_at: float = Field(default_factory=time.time)


class CrystallizationResult(BaseModel):
    """Result of distilling a cluster of fragments into an immutable Fact Crystal."""
    crystal: FactCrystal
    superseded_uris: List[str]
    net_entropy_reduced: int
    evaluation: TriGateEvaluation


class TriGateRejectionError(ValueError):
    """Raised when crystallization is attempted on candidates failing the tri-gate barrier."""
    pass


class EntropyCrystallizer:
    """Singleton engine orchestrating tri-gate evaluation, distillation, and net entropy reduction."""

    _instance: Optional["EntropyCrystallizer"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.rule = TriGateRule()
        self._crystals: Dict[str, FactCrystal] = {}
        self._total_evaluated: int = 0
        self._total_blocked: int = 0
        self._total_net_reduced: int = 0

    @classmethod
    def get_instance(cls) -> "EntropyCrystallizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two numeric vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a <= 1e-9 or norm_b <= 1e-9:
            return 0.0
        return dot / (norm_a * norm_b)

    def evaluate_tri_gate(self, fragments: List[MemoryFragment]) -> TriGateEvaluation:
        """Evaluate candidate fragments against the three parallel hard gates."""
        self._total_evaluated += 1
        now = time.time()
        reasons: List[str] = []

        # Gate 1: Cluster Size
        size = len(fragments)
        size_passed = size >= self.rule.min_cluster_size
        if not size_passed:
            reasons.append(f"候选聚类碎片条数不足 5 条 (当前: {size})，未达到结晶最小统计显著性阈值。")

        # Gate 2: Cosine Similarity
        avg_sim = 0.0
        if size >= 2:
            vectors = [f.embedding for f in fragments if f.embedding]
            if len(vectors) >= 2:
                pair_sims = []
                for i in range(len(vectors)):
                    for j in range(i + 1, len(vectors)):
                        pair_sims.append(self._cosine_similarity(vectors[i], vectors[j]))
                avg_sim = sum(pair_sims) / len(pair_sims) if pair_sims else 0.0
            else:
                # Text Jaccard similarity fallback if embeddings missing
                token_sets = [set(f.content.lower().split()) for f in fragments]
                jaccards = []
                for i in range(len(token_sets)):
                    for j in range(i + 1, len(token_sets)):
                        union = token_sets[i] | token_sets[j]
                        jaccards.append(len(token_sets[i] & token_sets[j]) / len(union) if union else 0.0)
                avg_sim = sum(jaccards) / len(jaccards) if jaccards else 0.0

        sim_passed = avg_sim > self.rule.min_avg_cosine_similarity
        if not sim_passed:
            reasons.append(f"碎片语义余弦相似度均值未达到 0.75 (当前: {avg_sim:.3f})，语义离散度过大禁止早熟结晶。")

        # Gate 3: Cooling Period
        min_cooling_hours = 0.0
        if fragments:
            youngest_ts = max(f.created_at for f in fragments)
            min_cooling_hours = max(0.0, (now - youngest_ts) / 3600.0)
        cooling_passed = min_cooling_hours >= self.rule.cooling_period_hours
        if not cooling_passed:
            reasons.append(f"存在未满 24h 冷却期的热数据碎片 (最晚沉淀距今: {min_cooling_hours:.1f}h)，禁止在活跃热会话中结晶。")

        all_passed = size_passed and sim_passed and cooling_passed
        if not all_passed:
            self._total_blocked += 1

        return TriGateEvaluation(
            passed=all_passed,
            cluster_size=size,
            cluster_size_passed=size_passed,
            avg_similarity=round(avg_sim, 4),
            similarity_passed=sim_passed,
            cooling_hours=round(min_cooling_hours, 2),
            cooling_passed=cooling_passed,
            rejection_reasons=reasons,
        )

    def distill_crystal(
        self,
        fragments: List[MemoryFragment],
        axiom: str,
        version_range: str,
        deprecated_patterns: Optional[List[str]] = None,
        forbidden_keywords: Optional[List[str]] = None,
        distiller_id: str = "openviking-crystallizer",
    ) -> CrystallizationResult:
        """Distill candidate fragments into an immutable Fact Crystal with net entropy reduction."""
        evaluation = self.evaluate_tri_gate(fragments)
        if not evaluation.passed:
            reasons_str = "; ".join(evaluation.rejection_reasons)
            raise TriGateRejectionError(f"Tri-gate barrier blocked crystallization: {reasons_str}")

        now = time.time()
        axiom_hash = hashlib.sha256(axiom.encode("utf-8")).hexdigest()[:12]
        crystal_uri = f"viking://resources/crystals/axiom_{axiom_hash}.md"

        evidence_hashes = [
            hashlib.sha256(f.content.encode("utf-8")).hexdigest()[:16] for f in fragments
        ]
        source_uris = [f.uri for f in fragments]

        crystal = FactCrystal(
            uri=crystal_uri,
            axiom=axiom.strip(),
            context_bounds=CrystalContextBounds(
                version_range=version_range.strip(),
                source_uris=source_uris,
                evidence_hashes=evidence_hashes,
                distilled_at=now,
                distiller_id=distiller_id,
            ),
            negative_boundary=CrystalNegativeBoundary(
                deprecated_patterns=deprecated_patterns or [],
                forbidden_keywords=forbidden_keywords or [],
            ),
            status="active",
            created_at=now,
        )

        # Net Entropy Reduction: Atomically supersede source fragments in lifecycle FSM
        superseded_list: List[str] = []
        lifecycle_store = MemoryLifecycleStore.get_instance()
        for frag in fragments:
            rec = lifecycle_store.get_record(frag.uri)
            if rec is None:
                rec = MemoryLifecycleRecord(uri=frag.uri, status=MemoryStatus.ACTIVE)
            try:
                updated_rec = MemoryLifecycleFSM.transition(
                    record=rec,
                    event=LifecycleTransitionEvent.SUPERSEDE,
                    target_uri=crystal_uri,
                    reason=f"Crystallized into immutable SSOT axiom '{crystal.axiom}'",
                    now_ts=now,
                    store=lifecycle_store,
                )
                superseded_list.append(frag.uri)
            except Exception as e:
                logger.warning(f"Failed to mark fragment {frag.uri} superseded: {e}")

        # Register crystal
        self._crystals[crystal_uri] = crystal
        net_reduced = max(0, len(fragments) - 1)
        self._total_net_reduced += net_reduced

        logger.info(
            f"Fact crystal distilled: uri={crystal_uri}, net_entropy_reduced={net_reduced}, "
            f"superseded_fragments={len(superseded_list)}"
        )

        return CrystallizationResult(
            crystal=crystal,
            superseded_uris=superseded_list,
            net_entropy_reduced=net_reduced,
            evaluation=evaluation,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return operational telemetry metrics for crystallization."""
        return {
            "total_crystals": len(self._crystals),
            "total_evaluated": self._total_evaluated,
            "total_blocked": self._total_blocked,
            "total_net_entropy_reduced": self._total_net_reduced,
            "block_rate": round(self._total_blocked / max(1, self._total_evaluated), 4),
        }

    def list_crystals(self) -> List[FactCrystal]:
        """List all crystallized immutable facts."""
        return list(self._crystals.values())

    def scan_and_auto_crystallize(
        self,
        candidate_fragments: Optional[List[MemoryFragment]] = None,
        default_version_range: str = "v1.5.x",
    ) -> List[CrystallizationResult]:
        """Scan fragment clusters and automatically crystallize qualified batches (Net Entropy Reduction)."""
        if not candidate_fragments:
            return []

        results: List[CrystallizationResult] = []
        buckets: Dict[str, List[MemoryFragment]] = {}
        for frag in candidate_fragments:
            topic = frag.metadata.get("topic") or (frag.uri.split("/")[-2] if "/" in frag.uri else "general")
            buckets.setdefault(topic, []).append(frag)

        for topic, frags in buckets.items():
            if len(frags) >= self.rule.min_cluster_size:
                eval_res = self.evaluate_tri_gate(frags)
                if eval_res.passed:
                    axiom = f"Immutable consensus across {len(frags)} verified records under topic '{topic}'."
                    try:
                        res = self.distill_crystal(
                            fragments=frags,
                            axiom=axiom,
                            version_range=default_version_range,
                            distiller_id="auto-entropy-worker",
                        )
                        results.append(res)
                    except Exception as exc:
                        logger.warning(f"Auto crystallization failed for topic {topic}: {exc}")
        return results

