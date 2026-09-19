# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
RARG Evidence Grounding Verifier & Zero-Hallucination Abstention Gate.
(Card-RAG-Abstention-ZeroHallucination-Pipeline / v1.5.18)
"""

import collections
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AbstentionDecision(BaseModel):
    """Decision produced by AbstentionGate on whether to answer or refuse."""
    should_abstain: bool = Field(description="True if model must refuse/abstain to avoid hallucination")
    confidence: float = Field(ge=0.0, le=1.0, description="Calibrated evidence grounding score")
    abstain_reason: Optional[str] = None
    matched_evidence_count: int = 0
    grounded_tokens: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class AbstentionTelemetrySnapshot(BaseModel):
    """Cumulative telemetry metrics for abstention gate."""
    total_verifications: int = 0
    total_abstained: int = 0
    abstention_rate: float = 0.0
    avg_confidence: float = 0.0
    avg_latency_ms: float = 0.0
    confidence_distribution: Dict[str, int] = Field(default_factory=dict)
    recent_verifications: List[Dict[str, Any]] = Field(default_factory=list)


class AbstentionGate:
    """
    Abstention Gate with RARG Grounding Verification.
    Calculates empirical token-level precision and query-claim overlap.
    Triggers Abstention when evidence confidence drops below calibrated threshold.
    """

    _instance: Optional["AbstentionGate"] = None

    def __init__(self, confidence_threshold: float = 0.40, min_evidence_length: int = 15):
        self.threshold = confidence_threshold
        self.min_evidence_len = min_evidence_length
        # Telemetry counters
        self._total_verifications = 0
        self._total_abstained = 0
        self._sum_confidence = 0.0
        self._sum_latency_ms = 0.0
        self._confidence_brackets: Dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        self._recent_events: collections.deque = collections.deque(maxlen=20)

    @classmethod
    def get_instance(cls, threshold: float = 0.40) -> "AbstentionGate":
        if cls._instance is None:
            cls._instance = cls(confidence_threshold=threshold)
        return cls._instance

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """Extract alphanumeric and snake_case tokens >= 2 chars."""
        tokens = re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]{2,}", text.lower())
        stops = {
            "the", "and", "is", "in", "to", "for", "with", "that", "this", "how",
            "what", "where", "of", "or", "by", "at", "on", "from", "be", "as", "an",
            "的", "了", "在", "是", "和", "或", "与", "从", "到"
        }
        return {t for t in tokens if t not in stops}

    def verify_and_decide(
        self,
        query: str,
        evidence_chunks: List[str],
        custom_threshold: Optional[float] = None,
    ) -> AbstentionDecision:
        """
        Verify query grounding against candidate evidence chunks.
        Determines whether RAG system should answer or abstain.
        """
        start_t = time.perf_counter()
        active_thresh = custom_threshold if custom_threshold is not None else self.threshold

        q_keywords = self._extract_keywords(query)
        if not q_keywords:
            # Query is empty or too vague
            decision = AbstentionDecision(
                should_abstain=True,
                confidence=0.0,
                abstain_reason="EMPTY_OR_VAGUE_QUERY: Query lacks substantive semantic keywords",
                matched_evidence_count=0,
                latency_ms=round((time.perf_counter() - start_t) * 1000, 2),
            )
            self._record_telemetry(decision, query)
            return decision

        if not evidence_chunks:
            # Zero evidence retrieved
            decision = AbstentionDecision(
                should_abstain=True,
                confidence=0.0,
                abstain_reason="NO_EVIDENCE_RETRIEVED: Corpus returned zero relevant candidates",
                matched_evidence_count=0,
                latency_ms=round((time.perf_counter() - start_t) * 1000, 2),
            )
            self._record_telemetry(decision, query)
            return decision

        combined_evidence = " ".join(evidence_chunks)
        e_keywords = self._extract_keywords(combined_evidence)

        # 1. Query token coverage in evidence
        covered = q_keywords.intersection(e_keywords)
        coverage_ratio = len(covered) / len(q_keywords)

        # 2. Evidence density bonus: penalize if evidence is ultra short
        length_penalty = 1.0
        if len(combined_evidence.strip()) < self.min_evidence_len:
            length_penalty = 0.5

        # 3. Compute final grounding confidence score
        confidence = round(min(1.0, coverage_ratio * length_penalty), 3)

        # 4. Abstention decision
        should_abstain = confidence < active_thresh
        reason = None
        if should_abstain:
            if coverage_ratio == 0.0:
                reason = "OUT_OF_DOMAIN: Zero semantic overlap between query and evidence"
            elif coverage_ratio < active_thresh:
                reason = f"LOW_CONFIDENCE: Evidence coverage ({int(coverage_ratio*100)}%) below threshold ({int(active_thresh*100)}%)"
            else:
                reason = "INSUFFICIENT_EVIDENCE_LENGTH: Evidence is too brief to ground a reliable answer"

        matched_count = sum(1 for c in evidence_chunks if any(k in c.lower() for k in q_keywords))
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

        decision = AbstentionDecision(
            should_abstain=should_abstain,
            confidence=confidence,
            abstain_reason=reason,
            matched_evidence_count=matched_count,
            grounded_tokens=sorted(list(covered)),
            latency_ms=elapsed_ms,
        )

        self._record_telemetry(decision, query)
        return decision

    def _record_telemetry(self, decision: AbstentionDecision, query: str = "") -> None:
        """Record decision into cumulative telemetry metrics."""
        self._total_verifications += 1
        if decision.should_abstain:
            self._total_abstained += 1
        self._sum_confidence += decision.confidence
        self._sum_latency_ms += decision.latency_ms

        if decision.confidence < 0.30:
            self._confidence_brackets["low"] += 1
        elif decision.confidence < 0.70:
            self._confidence_brackets["medium"] += 1
        else:
            self._confidence_brackets["high"] += 1

        self._recent_events.append({
            "query": query[:60] if query else "synthetic_query",
            "confidence": decision.confidence,
            "should_abstain": decision.should_abstain,
            "latency_ms": decision.latency_ms,
            "timestamp": time.time(),
        })

    def get_telemetry(self) -> AbstentionTelemetrySnapshot:
        """Get snapshot of cumulative telemetry."""
        total = self._total_verifications
        if total == 0:
            return AbstentionTelemetrySnapshot(
                confidence_distribution={"low": 0, "medium": 0, "high": 0},
                recent_verifications=[],
            )

        return AbstentionTelemetrySnapshot(
            total_verifications=total,
            total_abstained=self._total_abstained,
            abstention_rate=round(self._total_abstained / total, 3),
            avg_confidence=round(self._sum_confidence / total, 3),
            avg_latency_ms=round(self._sum_latency_ms / total, 2),
            confidence_distribution=dict(self._confidence_brackets),
            recent_verifications=list(self._recent_events),
        )
