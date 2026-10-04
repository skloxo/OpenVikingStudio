# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Strong-typed DTOs and Enums for Skill Dynamic Weight Tuning and Ingestion (SSOT)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class AttemptVerdict(str, Enum):
    """Execution attempt verdict classification inspired by Microsoft SkillOpt."""
    PASS = "PASS"
    DEGRADED = "DEGRADED"
    FAIL = "FAIL"


@dataclass
class SkillWeightProfile:
    """Persistent execution performance and dynamic weight profile of a skill."""
    skill_slug: str
    weight: float = 1.0
    total_attempts: int = 0
    passed_attempts: int = 0
    failed_attempts: int = 0
    degraded_attempts: int = 0
    last_updated: float = field(default_factory=time.time)
    recent_history: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def success_rate(self) -> float:
        """Overall attempt success rate in [0.0, 1.0]."""
        if self.total_attempts == 0:
            return 1.0
        return round(self.passed_attempts / self.total_attempts, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_slug": self.skill_slug,
            "weight": round(self.weight, 4),
            "total_attempts": self.total_attempts,
            "passed_attempts": self.passed_attempts,
            "failed_attempts": self.failed_attempts,
            "degraded_attempts": self.degraded_attempts,
            "success_rate": self.success_rate,
            "last_updated": self.last_updated,
            "recent_history": self.recent_history[-10:],
            "notes": self.notes,
        }


@dataclass
class WeightTuneResult:
    """Verdict feedback and dynamic weight transition result."""
    skill_slug: str
    previous_weight: float
    new_weight: float
    weight_delta: float
    verdict: AttemptVerdict
    profile: SkillWeightProfile
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_slug": self.skill_slug,
            "previous_weight": round(self.previous_weight, 4),
            "new_weight": round(self.new_weight, 4),
            "weight_delta": round(self.weight_delta, 4),
            "verdict": self.verdict.value,
            "profile": self.profile.to_dict(),
            "message": self.message,
        }
