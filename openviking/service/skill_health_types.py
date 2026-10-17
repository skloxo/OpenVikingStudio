# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Strong-typed DTOs and Enums for Skill Health Scoring and Auto-Remediation (SSOT)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthStatus(str, Enum):
    """Overall health status tier of a skill specification."""
    HEALTHY = "HEALTHY"                     # 85 ~ 100: Ready for master deployment
    STABLE = "STABLE"                       # 70 ~ 84: Functional with minor notes
    NEEDS_REMEDIATION = "NEEDS_REMEDIATION" # 50 ~ 69: Substandard, remediation recommended
    CRITICAL = "CRITICAL"                   # < 50: Severe flaws or safety violations


class IssueSeverity(str, Enum):
    """Severity classification of identified skill defects."""
    CRITICAL = "CRITICAL"   # Broken YAML, unescaped secrets, destructive commands, >500 lines
    WARNING = "WARNING"     # Missing negative boundary, missing tool contract, 400-500 lines
    INFO = "INFO"           # Stylistic enhancements, suggested additional triggers


@dataclass
class HealthIssue:
    """Detailed defect description with actionable remediation hint."""
    category: str
    severity: IssueSeverity
    message: str
    remediation_hint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "remediation_hint": self.remediation_hint,
        }


@dataclass
class HealthCategoryScore:
    """Sub-dimension score breakdown."""
    category: str
    label: str
    score: float
    max_score: float = 25.0
    status: str = "good"
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "label": self.label,
            "score": round(self.score, 2),
            "max_score": self.max_score,
            "status": self.status,
            "details": self.details,
        }


@dataclass
class SkillHealthReport:
    """Holistic health assessment report of a skill."""
    skill_slug: str
    health_score: float
    status: HealthStatus
    categories: Dict[str, HealthCategoryScore]
    issues: List[HealthIssue]
    passed_gate: bool
    line_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_slug": self.skill_slug,
            "health_score": round(self.health_score, 2),
            "status": self.status.value,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "issues": [i.to_dict() for i in self.issues],
            "passed_gate": self.passed_gate,
            "line_count": self.line_count,
        }


@dataclass
class SkillRemediationResult:
    """Synthesis result of the auto-remediation patch generator."""
    original_report: SkillHealthReport
    remediated_content: str
    applied_remediations: List[str]
    projected_health_score: float
    projected_status: HealthStatus
    diff_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_report": self.original_report.to_dict(),
            "applied_remediations": self.applied_remediations,
            "projected_health_score": round(self.projected_health_score, 2),
            "projected_status": self.projected_status.value,
            "diff_summary": self.diff_summary,
            "remediated_content": self.remediated_content,
        }
