# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Knowledge Hygiene Async Inspection Engine (知识卫生异步巡检引擎).
(Card-Hygiene-AsymmetricDecayAndBench / v1.5.31)

Principles:
1. "Zero Blind Deletion": Never delete user data automatically. Only audit, detect, and report.
2. Dormant Detection: Identify dead-weight items with 0 recalls or stale timestamps.
3. Conflict Clustering: Detect disputed clusters and superseded trails.
4. Objective Hygiene Index: 0 to 100 health score with actionable recommendations.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine, DecayConfig


class HygieneIssueItem(BaseModel):
    """Specific hygiene issue detected during inspection."""
    uri: str
    issue_type: str  # "dormant" | "disputed" | "orphaned" | "excessive_fragmentation"
    severity: str    # "low" | "medium" | "high"
    detail: str
    recommendation: str


class HygieneReport(BaseModel):
    """Aggregate knowledge hygiene inspection report."""
    health_score: int  # 0 to 100
    total_inspected: int
    dormant_count: int
    disputed_count: int
    orphaned_count: int
    stale_percentage: float
    inspection_ts: float
    latency_ms: float
    issues: List[HygieneIssueItem] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    task_id: Optional[str] = None
    total_in_store: Optional[int] = None


class KnowledgeHygieneEngine:
    """Audits memory stores and generates hygiene health reports."""

    def __init__(self, decay_engine: Optional[AsymmetricDecayEngine] = None):
        self.decay_engine = decay_engine or AsymmetricDecayEngine()

    def inspect_items(
        self,
        items: List[Dict[str, Any]],
        dormant_threshold_days: float = 60.0,
    ) -> HygieneReport:
        """
        Inspect a list of knowledge/memory items for health metrics.
        Each item can have: uri, updated_ts, call_count, status, content_len, etc.
        """
        t0 = time.monotonic()
        now_ts = time.time()

        total = len(items)
        if total == 0:
            return HygieneReport(
                health_score=100,
                total_inspected=0,
                dormant_count=0,
                disputed_count=0,
                orphaned_count=0,
                stale_percentage=0.0,
                inspection_ts=now_ts,
                latency_ms=0.0,
                issues=[],
                recommendations=["Knowledge store is clean (no items found)."],
            )

        dormant_count = 0
        disputed_count = 0
        orphaned_count = 0
        issues: List[HygieneIssueItem] = []

        for item in items:
            uri = str(item.get("uri", ""))
            updated_ts = float(item.get("updated_ts", item.get("created_ts", now_ts)))
            call_count = int(item.get("call_count", item.get("recall_count", 0)))
            status = str(item.get("status", "active")).lower()

            delta_days = (now_ts - updated_ts) / 86400.0

            # 1. Axioms are always healthy
            if self.decay_engine.is_axiom_immune(uri):
                continue

            # 2. Check disputed / superseded
            if status in ("disputed", "superseded"):
                disputed_count += 1
                issues.append(
                    HygieneIssueItem(
                        uri=uri,
                        issue_type=status,
                        severity="high" if status == "disputed" else "medium",
                        detail=f"Memory marked {status} ({round(delta_days, 1)} days ago)",
                        recommendation="Review conflicting or superseded memories and merge into consensus axiom.",
                    )
                )

            # 3. Check dormant (0 recalls and stale)
            if call_count == 0 and delta_days > dormant_threshold_days:
                dormant_count += 1
                issues.append(
                    HygieneIssueItem(
                        uri=uri,
                        issue_type="dormant",
                        severity="low" if delta_days < 120 else "medium",
                        detail=f"Zero recalls for {round(delta_days, 1)} days (dormant)",
                        recommendation="Consider archival or compaction into L1 summary.",
                    )
                )

            # 4. Check orphaned (isolated fragments)
            if not item.get("has_relations", True) and not item.get("parent_uri"):
                if "staging" in uri or "tmp" in uri:
                    orphaned_count += 1
                    issues.append(
                        HygieneIssueItem(
                            uri=uri,
                            issue_type="orphaned",
                            severity="medium",
                            detail="Staging item with no parent hierarchy or relation links",
                            recommendation="Move to cold archive or attach to project taxonomy.",
                        )
                    )

        # Compute composite health score (deduct penalty from 100)
        disputed_penalty = (disputed_count / total) * 40.0
        dormant_penalty = (dormant_count / total) * 25.0
        orphaned_penalty = (orphaned_count / total) * 20.0

        health = max(10, min(100, round(100.0 - disputed_penalty - dormant_penalty - orphaned_penalty)))
        stale_pct = round((dormant_count / total) * 100.0, 1)

        recommendations = []
        if disputed_count > 0:
            recommendations.append(f"Resolve {disputed_count} disputed items to prevent retrieval confusion.")
        if dormant_count > 0:
            recommendations.append(f"Archive or consolidate {dormant_count} dormant memories ({stale_pct}% of total).")
        if orphaned_count > 0:
            recommendations.append(f"Bind {orphaned_count} isolated staging fragments to knowledge graph.")
        if not recommendations:
            recommendations.append("All inspected memories are fresh, verified, and well-linked.")

        latency = round((time.monotonic() - t0) * 1000.0, 2)

        return HygieneReport(
            health_score=health,
            total_inspected=total,
            dormant_count=dormant_count,
            disputed_count=disputed_count,
            orphaned_count=orphaned_count,
            stale_percentage=stale_pct,
            inspection_ts=now_ts,
            latency_ms=latency,
            issues=issues[:50],  # Cap output to avoid context overflow
            recommendations=recommendations,
        )
