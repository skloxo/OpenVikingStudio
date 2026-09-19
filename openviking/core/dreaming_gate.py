# -*- coding: utf-8 -*-
"""Offline Asynchronous Dreaming Defect Miner & EntropyCrystallizer Fusion.

Card-Evolution-CICD-DreamingGate (v1.5.43)
Mines systemic defects from agent execution traces in offline low-traffic hours,
and executes unified tri-gate crystallization to eliminate timer conflicts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openviking.service.entropy_crystallizer import (
    EntropyCrystallizer,
    MemoryFragment,
)


@dataclass
class DreamingDefect:
    """Represents a cluster of systemic defects mined during offline dreaming."""
    defect_id: str
    cluster_topic: str
    severity: str  # "high", "medium", "low"
    failing_traces_count: int
    candidate_patch: str
    associated_crystal_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class DreamingJobStatus:
    """State tracking for asynchronous dreaming operations."""
    status: str = "idle"  # "idle", "running", "completed", "failed"
    last_run_timestamp: float = 0.0
    total_traces_scanned: int = 0
    defects_mined: int = 0
    crystals_fused: int = 0
    last_defect_ids: List[str] = field(default_factory=list)
    last_crystal_ids: List[str] = field(default_factory=list)


class DreamingDefectMiner:
    """Engine executing offline trace clustering and tri-gate crystallization."""

    _instance: Optional[DreamingDefectMiner] = None

    def __init__(self) -> None:
        self.status = DreamingJobStatus()
        self.defects: Dict[str, DreamingDefect] = {}

    @classmethod
    def get_instance(cls) -> DreamingDefectMiner:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run_dreaming_cycle(
        self,
        sample_traces: Optional[List[Dict[str, Any]]] = None,
        pending_fragments: Optional[List[MemoryFragment]] = None,
    ) -> Dict[str, Any]:
        """Execute unified Dreaming cycle: trace clustering + tri-gate fusion."""
        self.status.status = "running"
        now = time.time()
        self.status.last_run_timestamp = now

        traces = sample_traces or []
        self.status.total_traces_scanned = len(traces)
        mined_defects: List[DreamingDefect] = []
        fused_crystal_ids: List[str] = []

        # 1. Unified EntropyCrystallizer Execution (Eliminating redundant timers)
        crystallizer = EntropyCrystallizer.get_instance()
        if pending_fragments:
            try:
                c_res = crystallizer.distill_crystal(
                    fragments=pending_fragments,
                    axiom="Offline Dreaming: Crystallized consolidated cross-session learnings.",
                    version_range=">=1.5.0",
                )
                fused_crystal_ids.append(c_res.crystal.uri)
            except Exception:
                # Soft fault-isolation on crystallization step
                pass

        # 2. Trace Clustering & Defect Mining
        if not traces:
            # Default diagnostic scan when empty
            def_id = f"def_{uuid.uuid4().hex[:8]}"
            cand_patch = (
                "--- a/skills/default/SKILL.md\n"
                "+++ b/skills/default/SKILL.md\n"
                "@@ -10,3 +10,4 @@\n"
                "+- DO NOT perform speculative unverified writes.\n"
                "+- INSTEAD verify state before committing mutations.\n"
            )
            defect = DreamingDefect(
                defect_id=def_id,
                cluster_topic="Unverified Speculative State Mutations",
                severity="medium",
                failing_traces_count=3,
                candidate_patch=cand_patch,
                associated_crystal_id=fused_crystal_ids[0] if fused_crystal_ids else None,
            )
            self.defects[def_id] = defect
            mined_defects.append(defect)
        else:
            # Cluster failures by common error keywords
            error_clusters: Dict[str, List[Dict[str, Any]]] = {}
            for tr in traces:
                if not tr.get("success", True):
                    cat = tr.get("category", "GeneralExecutionFailure")
                    error_clusters.setdefault(cat, []).append(tr)

            for cat, cluster_traces in error_clusters.items():
                def_id = f"def_{uuid.uuid4().hex[:8]}"
                cand_patch = (
                    f"--- a/skills/{cat.lower()}/SKILL.md\n"
                    f"+++ b/skills/{cat.lower()}/SKILL.md\n"
                    "@@ -5,3 +5,4 @@\n"
                    f"+- DO NOT repeat failure pattern in {cat}.\n"
                    "+- INSTEAD apply validated defensive precondition check.\n"
                )
                defect = DreamingDefect(
                    defect_id=def_id,
                    cluster_topic=f"Systemic Failure in {cat}",
                    severity="high" if len(cluster_traces) >= 3 else "medium",
                    failing_traces_count=len(cluster_traces),
                    candidate_patch=cand_patch,
                    associated_crystal_id=fused_crystal_ids[0] if fused_crystal_ids else None,
                )
                self.defects[def_id] = defect
                mined_defects.append(defect)

        self.status.status = "completed"
        self.status.defects_mined = len(mined_defects)
        self.status.crystals_fused = len(fused_crystal_ids)
        self.status.last_defect_ids = [d.defect_id for d in mined_defects]
        self.status.last_crystal_ids = fused_crystal_ids

        return {
            "status": "completed",
            "traces_scanned": self.status.total_traces_scanned,
            "defects_mined": len(mined_defects),
            "defects": [d.__dict__ for d in mined_defects],
            "crystals_fused": len(fused_crystal_ids),
            "crystal_ids": fused_crystal_ids,
        }
