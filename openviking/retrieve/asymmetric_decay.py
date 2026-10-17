# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Asymmetric Temporal Decay Engine (非对称时效动力学与防通胀降权机制).
(Card-Hygiene-AsymmetricDecayAndBench / v1.5.31; Card-37 / v1.6.1)

First Principles & Physical Dynamics:
1. "Wrong memories cause more damage than correct memories provide benefit" (Asymmetric Rule).
2. Axiom Immunity: Fundamental system rules and master memories are 100% immune to decay (decay >= 1.0).
3. Type-Differentiated Decay:
   - Canonical: lambda = 0.0 (no decay)
   - Experience: lambda = 0.007 (slow decay, half-life ~99 days)
   - Event / Task / Session: lambda = 0.05 (fast decay, half-life ~14 days)
   - General: lambda = 0.01 (medium decay, half-life ~70 days)
4. Hit-Frequency Reinforcement Boost:
   Score_effective = Score_semantic * exp(-lambda * delta_t) * (1 + beta * log(1 + N_hits))
   High-value memories validated and retrieved frequently actively resist and overcome aging.
5. Status Penalties: 'disputed' items are penalized by 0.50x; 'superseded' items by 0.20x.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DecayConfig(BaseModel):
    """Configuration for asymmetric temporal decay, hit frequency boost, and category floors."""
    axiom_immune_prefixes: tuple[str, ...] = (
        "viking://resources/master_memory/",
        "master_memory/",
        "viking://rules/",
        "rules/",
        "skills/",
        "docs/adr/",
        "protocols/",
        "lessons/",
        "AGENTS.md",
        "BLUEPRINT.md",
        "REFACTORING_PLAN.md",
    )
    default_half_life_days: float = 90.0  # 3 months default half life for normal memories
    session_half_life_days: float = 14.0  # 2 weeks for transient session logs
    lambda_by_type: Dict[str, float] = Field(
        default_factory=lambda: {
            "canonical": 0.0,
            "axiom": 0.0,
            "invariant": 0.0,
            "rule": 0.0,
            "experience": 0.007,
            "event": 0.05,
            "task": 0.05,
            "session": 0.05,
            "general": 0.01,
        }
    )
    category_floors: Dict[str, float] = Field(
        default_factory=lambda: {
            "invariant": 1.0,
            "canonical": 1.0,
            "rule": 1.0,
            "axiom": 1.0,
            "lesson": 0.85,
            "adr": 0.85,
            "architecture": 0.85,
            "protocol": 0.85,
            "spec": 0.80,
            "experience": 0.60,
            "design": 0.60,
            "general": 0.25,
            "event": 0.05,
            "task": 0.05,
            "session": 0.05,
        }
    )
    beta_hit_boost: float = 0.20  # Logarithmic hit reinforcement coefficient
    disputed_penalty: float = 0.50
    superseded_penalty: float = 0.20
    min_decay_floor: float = 0.05
    max_decay_ceiling: float = 2.0


class DecayAssessment(BaseModel):
    """Detailed decay evaluation for a single memory/candidate item."""
    uri: str
    is_immune: bool
    status: str
    delta_days: float
    raw_score: float
    decay_factor: float
    adjusted_score: float
    penalty_reason: Optional[str] = None
    active_count: int = 0
    memory_type: str = "general"
    hit_boost: float = 1.0
    decay_multiplier: float = 1.0
    lambda_val: float = 0.01


class AsymmetricDecayEngine:
    """Computes asymmetric temporal decay factors, hit boosts, and score adjustments."""

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()

    def is_axiom_immune(self, uri: str, memory_type: Optional[str] = None) -> bool:
        """Check if an item is a fundamental immutable axiom exempt from decay."""
        if memory_type and memory_type.strip().lower() in ("canonical", "axiom", "invariant", "rule"):
            return True
        if not uri:
            return False
        for prefix in self.config.axiom_immune_prefixes:
            if prefix in uri:
                return True
        return False

    def resolve_category_floor(self, uri: str, memory_type: Optional[str] = None) -> float:
        """Resolve the minimum retention floor for a category/URI to prevent memory loss."""
        if self.is_axiom_immune(uri, memory_type):
            return 1.0

        type_clean = (memory_type or "").strip().lower()
        if type_clean in self.config.category_floors:
            return self.config.category_floors[type_clean]

        # URI heuristic pattern detection
        if uri:
            uri_lower = uri.lower()
            if "adr" in uri_lower or "architecture" in uri_lower or "protocol" in uri_lower:
                return self.config.category_floors.get("adr", 0.85)
            if "lesson" in uri_lower:
                return self.config.category_floors.get("lesson", 0.85)
            if "experience" in uri_lower:
                return self.config.category_floors.get("experience", 0.60)
            if "session" in uri_lower or "staging" in uri_lower or "tmp" in uri_lower:
                return self.config.category_floors.get("session", 0.05)

        return self.config.category_floors.get("general", 0.25)

    def resolve_lambda(self, uri: str, memory_type: Optional[str] = None) -> float:
        """Resolve the decay coefficient lambda based on type and URI patterns."""
        if self.is_axiom_immune(uri, memory_type):
            return 0.0
        if memory_type is not None:
            type_clean = memory_type.strip().lower()
            if type_clean in self.config.lambda_by_type:
                return self.config.lambda_by_type[type_clean]

        # Fallback to transient vs general half-life mapping
        is_transient = "staging" in uri or "session" in uri or "tmp" in uri
        if is_transient:
            return math.log(2.0) / max(1.0, self.config.session_half_life_days)
        return math.log(2.0) / max(1.0, self.config.default_half_life_days)

    def compute_decay_factor(
        self,
        uri: str,
        updated_ts: Optional[float] = None,
        status: str = "active",
        now_ts: Optional[float] = None,
        active_count: int = 0,
        memory_type: Optional[str] = None,
    ) -> tuple[float, Optional[str]]:
        """
        Calculate effective decay factor in range [min_floor, max_ceiling].
        Returns (decay_factor, penalty_reason).
        """
        assessment = self.evaluate_candidate(
            uri=uri,
            raw_score=1.0,
            updated_ts=updated_ts,
            status=status,
            now_ts=now_ts,
            active_count=active_count,
            memory_type=memory_type,
        )
        return assessment.decay_factor, assessment.penalty_reason

    def evaluate_candidate(
        self,
        uri: str,
        raw_score: float,
        updated_ts: Optional[float] = None,
        status: str = "active",
        now_ts: Optional[float] = None,
        active_count: int = 0,
        memory_type: Optional[str] = None,
    ) -> DecayAssessment:
        """Produce a complete physical decay assessment for a search candidate."""
        resolved_type = (memory_type or "general").lower()
        immune = self.is_axiom_immune(uri, resolved_type)
        current_time = now_ts or time.time()
        delta_seconds = max(0.0, current_time - (updated_ts or current_time))
        delta_days = delta_seconds / 86400.0

        if immune:
            lambda_val = 0.0
            decay_mult = 1.0
            hit_boost = 1.0
            factor = 1.0
            penalty_reason = None
        else:
            lambda_val = self.resolve_lambda(uri, memory_type)
            cat_floor = self.resolve_category_floor(uri, resolved_type)
            raw_decay = math.exp(-lambda_val * delta_days)
            decay_mult = max(cat_floor, raw_decay)
            hit_boost = 1.0 + self.config.beta_hit_boost * math.log1p(max(0, active_count))
            factor = decay_mult * hit_boost

            penalty_reason = None
            status_lower = (status or "active").lower()
            if status_lower == "superseded":
                factor *= self.config.superseded_penalty
                penalty_reason = "superseded_by_newer_memory"
            elif status_lower == "disputed":
                factor *= self.config.disputed_penalty
                penalty_reason = "marked_disputed_or_unverified"

            factor = round(max(self.config.min_decay_floor, min(self.config.max_decay_ceiling, factor)), 4)

        adjusted = round(raw_score * factor, 4)
        return DecayAssessment(
            uri=uri,
            is_immune=immune,
            status=status,
            delta_days=round(delta_days, 1),
            raw_score=raw_score,
            decay_factor=factor,
            adjusted_score=adjusted,
            penalty_reason=penalty_reason,
            active_count=active_count,
            memory_type=resolved_type,
            hit_boost=round(hit_boost, 4),
            decay_multiplier=round(decay_mult, 4),
            lambda_val=round(lambda_val, 6),
        )
