# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Strongly-typed DTOs for the Unified Skill Evolution & Crystallization Pipeline (SSOT)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PipelineStage(str, Enum):
    """Execution stages of the skill evolution assembly line."""

    DETECT_COLLISIONS = "detect_collisions"
    HEALTH_AUDIT = "health_audit"
    REMEDIATION_DRAFT = "remediation_draft"
    ASSET_HERITAGE = "asset_heritage"
    ATTEMPT_JUDGE = "attempt_judge"
    VAULT_PUBLISH = "vault_publish"
    WEIGHT_TUNE = "weight_tune"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class SkillClusterCandidate:
    """A cluster of homogenous/conflicting skills targeted for crystallization."""

    cluster_id: str
    domain_name: str
    target_slug: str
    candidate_slugs: List[str]
    seed_slug: str = ""
    reasons: List[str] = field(default_factory=list)
    avg_health_score: float = 75.0

    @property
    def candidate_count(self) -> int:
        return len(self.candidate_slugs)

    @property
    def domain(self) -> str:
        return self.domain_name

    @property
    def cluster_name(self) -> str:
        return self.domain_name

    @property
    def target_crystallized_slug(self) -> str:
        return self.target_slug

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "domain_name": self.domain_name,
            "cluster_name": self.domain_name,
            "domain": self.domain_name,
            "target_slug": self.target_slug,
            "target_crystallized_slug": self.target_slug,
            "candidate_slugs": self.candidate_slugs,
            "candidate_count": self.candidate_count,
            "seed_slug": self.seed_slug,
            "reasons": self.reasons,
            "avg_health_score": round(self.avg_health_score, 1),
        }


@dataclass
class CrystallizeStageDetail:
    """Execution trace and diagnostics for an individual pipeline stage."""

    stage: PipelineStage
    passed: bool
    score: Optional[float] = None
    diagnostics: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "passed": self.passed,
            "score": round(self.score, 2) if self.score is not None else None,
            "diagnostics": self.diagnostics,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


@dataclass
class ClusterCrystallizeResult:
    """Outcome report for one crystallized skill cluster."""

    cluster_id: str
    domain_name: str
    target_slug: str
    success: bool
    stages: List[CrystallizeStageDetail] = field(default_factory=list)
    seed_slug: str = ""
    absorbed_slugs: List[str] = field(default_factory=list)
    inherited_files: List[str] = field(default_factory=list)
    version_hash: str = ""
    target_uri: str = ""
    final_judge_score: float = 0.0
    weight_boost: float = 1.0
    backup_dir: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "domain_name": self.domain_name,
            "target_slug": self.target_slug,
            "success": self.success,
            "stages": [s.to_dict() for s in self.stages],
            "seed_slug": self.seed_slug,
            "absorbed_slugs": self.absorbed_slugs,
            "inherited_files": self.inherited_files,
            "version_hash": self.version_hash,
            "target_uri": self.target_uri,
            "final_judge_score": round(self.final_judge_score, 2),
            "weight_boost": round(self.weight_boost, 2),
            "backup_dir": self.backup_dir,
            "error": self.error,
        }


@dataclass
class PipelineSummaryReport:
    """Holistic summary of the evolution pipeline run across all scanned clusters."""

    total_candidates: int
    clusters_identified: int
    clusters_crystallized: int
    clusters_blocked: int
    collisions_before: int
    collisions_after: int
    avg_health_before: float
    avg_health_after: float
    results: List[ClusterCrystallizeResult] = field(default_factory=list)

    @property
    def processed_clusters(self) -> int:
        return self.clusters_identified

    @property
    def total_crystallized(self) -> int:
        return self.clusters_crystallized

    @property
    def overall_attempt_pass_rate(self) -> float:
        if self.clusters_identified == 0:
            return 1.0
        return round(self.clusters_crystallized / self.clusters_identified, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_candidates": self.total_candidates,
            "clusters_identified": self.clusters_identified,
            "processed_clusters": self.processed_clusters,
            "clusters_crystallized": self.clusters_crystallized,
            "total_crystallized": self.total_crystallized,
            "clusters_blocked": self.clusters_blocked,
            "collisions_before": self.collisions_before,
            "collisions_after": self.collisions_after,
            "avg_health_before": round(self.avg_health_before, 2),
            "avg_health_after": round(self.avg_health_after, 2),
            "overall_attempt_pass_rate": self.overall_attempt_pass_rate,
            "results": [r.to_dict() for r in self.results],
        }
