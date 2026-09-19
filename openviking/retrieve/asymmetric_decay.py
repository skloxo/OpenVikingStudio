# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Asymmetric Temporal Decay Engine (非对称时效动力学与防通胀降权机制).
(Card-Hygiene-AsymmetricDecayAndBench / v1.5.31)

Principles:
1. "Wrong memories cause more damage than correct memories provide benefit" (Asymmetric Rule).
2. Axiom Immunity: Fundamental system rules and master memories are 100% immune to decay (decay = 1.0).
3. Exponential Half-Life: Outdated or dormant items naturally decay.
4. Status Penalties: 'disputed' items are penalized by 0.5; 'superseded' items by 0.2.
"""

import math
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DecayConfig(BaseModel):
    """Configuration for asymmetric temporal decay."""
    axiom_immune_prefixes: tuple[str, ...] = (
        "viking://resources/master_memory/rules/",
        "viking://resources/master_memory/core/",
        "viking://rules/",
        "AGENTS.md",
    )
    default_half_life_days: float = 90.0  # 3 months default half life for normal memories
    session_half_life_days: float = 14.0  # 2 weeks for transient session logs
    disputed_penalty: float = 0.50
    superseded_penalty: float = 0.20
    min_decay_floor: float = 0.05


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


class AsymmetricDecayEngine:
    """Computes asymmetric decay factors and score adjustments."""

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()

    def is_axiom_immune(self, uri: str) -> bool:
        """Check if an item is a fundamental immutable axiom exempt from decay."""
        if not uri:
            return False
        for prefix in self.config.axiom_immune_prefixes:
            if prefix in uri:
                return True
        return False

    def compute_decay_factor(
        self,
        uri: str,
        updated_ts: Optional[float] = None,
        status: str = "active",
        now_ts: Optional[float] = None,
    ) -> tuple[float, Optional[str]]:
        """
        Calculate decay factor in range [min_floor, 1.0].
        Returns (decay_factor, penalty_reason).
        """
        # 1. Axioms are unconditionally immune
        if self.is_axiom_immune(uri):
            return 1.0, None

        current_time = now_ts or time.time()
        # Default to 30 days if timestamp not available
        delta_seconds = max(0.0, current_time - (updated_ts or (current_time - 30 * 86400)))
        delta_days = delta_seconds / 86400.0

        # Choose appropriate half life
        is_transient = "staging" in uri or "session" in uri or "tmp" in uri
        half_life = self.config.session_half_life_days if is_transient else self.config.default_half_life_days

        # Exponential decay: 2^(-delta / half_life)
        decay = math.pow(0.5, delta_days / max(1.0, half_life))

        # Status penalty
        penalty_reason = None
        status_lower = (status or "active").lower()
        if status_lower == "superseded":
            decay *= self.config.superseded_penalty
            penalty_reason = "superseded_by_newer_memory"
        elif status_lower == "disputed":
            decay *= self.config.disputed_penalty
            penalty_reason = "marked_disputed_or_unverified"

        final_factor = round(max(self.config.min_decay_floor, min(1.0, decay)), 4)
        return final_factor, penalty_reason

    def evaluate_candidate(
        self,
        uri: str,
        raw_score: float,
        updated_ts: Optional[float] = None,
        status: str = "active",
        now_ts: Optional[float] = None,
    ) -> DecayAssessment:
        """Produce a complete decay assessment for a search candidate."""
        immune = self.is_axiom_immune(uri)
        current_time = now_ts or time.time()
        delta_days = max(0.0, (current_time - (updated_ts or current_time)) / 86400.0)

        factor, reason = self.compute_decay_factor(
            uri=uri,
            updated_ts=updated_ts,
            status=status,
            now_ts=now_ts,
        )

        adjusted = round(raw_score * factor, 4)
        return DecayAssessment(
            uri=uri,
            is_immune=immune,
            status=status,
            delta_days=round(delta_days, 1),
            raw_score=raw_score,
            decay_factor=factor,
            adjusted_score=adjusted,
            penalty_reason=reason,
        )
