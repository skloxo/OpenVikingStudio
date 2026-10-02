# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Memory Purity Benchmark & Unified Governance Stream Parser.
(Card-38 / v1.6.2)

First Principles:
1. "As time expands, memory must not simply accumulate; it must evolve, distill, and self-purify."
2. Layer 5 Anti-Entropy Benchmark: Quantifies knowledge signal-to-noise ratio (SNR),
   unresolved conflict rate, and 90-day operational freshness.
3. Unified Audit Stream: Unifies ingress admission (#dec_xxxx) and dream consolidation (#cry_xxxx)
   into a single, verifiable chronological stream from entropy_gatekeeper.jsonl.
4. Absolute Truthfulness: Computed directly from physical SQLite and filesystem stores without mocks.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.service.memory_conflict_resolver import MemoryConflictResolver
from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleStore,
    MemoryStatus,
    _LIFECYCLE_REGISTRY,
)

logger = logging.getLogger("openviking.service.memory_purity")


class MemoryPurityReport(BaseModel):
    """Holistic health assessment and benchmark telemetry of the external brain."""
    snr_ratio: float = Field(..., description="Signal-to-Noise Ratio (authoritative vs fragmented/superseded)")
    conflict_rate: float = Field(..., description="Proportion of unresolved cognitive conflicts (0.0 to 1.0)")
    freshness_retained: float = Field(..., description="90-day active/validated freshness coverage (0.0 to 1.0)")
    purity_score: int = Field(..., description="Overall health score normalized between 0 and 100")
    total_memories: int = 0
    canonical_count: int = 0
    active_count: int = 0
    superseded_count: int = 0
    disputed_count: int = 0
    unconsolidated_fragments: int = 0
    master_cards_count: int = 0
    evaluated_at: float = Field(default_factory=time.time)
    watchdog_status: Dict[str, Any] = Field(default_factory=dict)


class GovernanceStreamEvent(BaseModel):
    """Unified chronological audit event representing ingress admission or dream crystallization."""
    event_id: str
    type: str  # "INGRESS_ADMISSION" or "DREAM_CONSOLIDATION"
    action: str  # "add", "noop", "update", "consolidate"
    uri: str
    matched_uri: Optional[str] = None
    similarity: Optional[float] = None
    reason: str
    timestamp: float
    net_entropy_reduced: int = 0


class MemoryPurityBenchmark:
    """Singleton benchmark engine for memory purity computation and audit stream aggregation."""

    _instance: Optional["MemoryPurityBenchmark"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        ledger_path: Optional[Path] = None,
        crystals_dir: Optional[Path] = None,
    ) -> None:
        self.ledger_path = ledger_path or (
            Path.home() / ".openviking" / "data" / "entropy_gatekeeper.jsonl"
        )
        self.crystals_dir = crystals_dir or (
            Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "master_memory" / "crystals"
        )

    @classmethod
    def get_instance(
        cls,
        ledger_path: Optional[Path] = None,
        crystals_dir: Optional[Path] = None,
    ) -> "MemoryPurityBenchmark":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(ledger_path=ledger_path, crystals_dir=crystals_dir)
        return cls._instance

    def _count_master_cards(self) -> int:
        """Count physical Master Knowledge Cards persisted on disk."""
        if not self.crystals_dir.exists():
            return 0
        try:
            return sum(1 for p in self.crystals_dir.glob("*.md") if p.is_file())
        except Exception:
            return 0

    def compute_purity_report(self) -> MemoryPurityReport:
        """Compute true physical memory purity metrics directly from live SQLite and disk stores."""
        now_ts = time.time()
        freshness_cutoff = now_ts - (90.0 * 86400.0)

        # 1. Fetch lifecycle records
        records = list(_LIFECYCLE_REGISTRY.values())
        total_records = len(records)

        active_recs = [r for r in records if r.status == MemoryStatus.ACTIVE]
        disputed_recs = [r for r in records if r.status == MemoryStatus.DISPUTED]
        superseded_recs = [r for r in records if r.status == MemoryStatus.SUPERSEDED]

        active_count = len(active_recs)
        disputed_count = len(disputed_recs)
        superseded_count = len(superseded_recs)

        # 2. Count master cards and canonical definitions
        master_cards_count = self._count_master_cards()
        canonical_count = sum(1 for r in active_recs if "canonical" in r.uri.lower() or "crystals" in r.uri.lower())
        authoritative_total = master_cards_count + canonical_count

        # 3. Fragments not yet consolidated
        unconsolidated_fragments = max(0, active_count - canonical_count)

        # 4. Signal-to-Noise Ratio (SNR)
        # Authoritative knowledge vs noise (superseded + unconsolidated fragments)
        denominator = unconsolidated_fragments + (superseded_count * 0.5) + 1.0
        snr_ratio = round((authoritative_total + 1.0) / denominator, 3)

        # 5. Unresolved Conflict Rate
        conflict_rate = round(float(disputed_count) / max(1.0, float(total_records)), 4) if total_records > 0 else 0.0

        # 6. Freshness Retained (90 days)
        # An active record is fresh if updated recently or frequently hit (active_count >= 1)
        if active_count > 0:
            fresh_recs = sum(
                1 for r in active_recs
                if r.updated_at >= freshness_cutoff or getattr(r, "active_count", 0) >= 1
            )
            freshness_retained = round(float(fresh_recs) / float(active_count), 4)
        else:
            freshness_retained = 1.0

        # 7. Composite Purity Health Score (0 ~ 100)
        # Weights: SNR (40%), Low-Conflict (35%), Freshness (25%)
        snr_component = min(40.0, (snr_ratio / 1.5) * 40.0)
        conflict_component = max(0.0, (1.0 - (conflict_rate * 5.0)) * 35.0)
        freshness_component = freshness_retained * 25.0
        purity_score = round(snr_component + conflict_component + freshness_component)
        purity_score = max(0, min(100, purity_score))

        # 8. Watchdog telemetry preview
        watchdog_status = {
            "window": "active",
            "unconsolidated_threshold_met": unconsolidated_fragments >= 100,
            "unconsolidated_count": unconsolidated_fragments,
            "next_rem_window": "02:00 ~ 06:00 UTC",
        }

        return MemoryPurityReport(
            snr_ratio=snr_ratio,
            conflict_rate=conflict_rate,
            freshness_retained=freshness_retained,
            purity_score=purity_score,
            total_memories=total_records,
            canonical_count=canonical_count,
            active_count=active_count,
            superseded_count=superseded_count,
            disputed_count=disputed_count,
            unconsolidated_fragments=unconsolidated_fragments,
            master_cards_count=master_cards_count,
            evaluated_at=now_ts,
            watchdog_status=watchdog_status,
        )

    def get_governance_stream(
        self,
        limit: int = 50,
        event_type: Optional[str] = None,
    ) -> List[GovernanceStreamEvent]:
        """Read and normalize audit events from the shared entropy gatekeeper ledger."""
        events: List[GovernanceStreamEvent] = []
        if not self.ledger_path.exists():
            return events

        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for idx, line in enumerate(reversed(lines)):
                if len(events) >= limit:
                    break
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    raw = json.loads(line_str)
                    # Distinguish Dream Consolidation vs Ingress Admission
                    if raw.get("type") == "DREAM_CONSOLIDATION" or "master_card_uri" in raw:
                        e_type = "DREAM_CONSOLIDATION"
                        if event_type and event_type != e_type:
                            continue
                        events.append(
                            GovernanceStreamEvent(
                                event_id=raw.get("event_id") or f"#cry_{len(events):04d}",
                                type=e_type,
                                action="consolidate",
                                uri=raw.get("master_card_uri", ""),
                                matched_uri=None,
                                similarity=1.0,
                                reason=f"Distilled {raw.get('fragments_consolidated', 0)} fragments into Master Card on theme '{raw.get('theme', 'general')}'",
                                timestamp=float(raw.get("timestamp", time.time())),
                                net_entropy_reduced=int(raw.get("net_entropy_reduced", 0)),
                            )
                        )
                    else:
                        e_type = "INGRESS_ADMISSION"
                        if event_type and event_type != e_type:
                            continue
                        action = raw.get("action", "add")
                        sim = raw.get("similarity")
                        sim_val = float(sim) if sim is not None else None
                        events.append(
                            GovernanceStreamEvent(
                                event_id=f"#dec_{len(events):04d}",
                                type=e_type,
                                action=action,
                                uri=raw.get("uri", ""),
                                matched_uri=raw.get("matched_uri"),
                                similarity=sim_val,
                                reason=raw.get("reason", "Ingress admission check"),
                                timestamp=float(raw.get("timestamp", time.time())),
                                net_entropy_reduced=1 if action == "noop" else 0,
                            )
                        )
                except Exception as parse_e:
                    logger.debug(f"Failed to parse governance stream entry: {parse_e}")
                    continue
        except Exception as e:
            logger.warning(f"Error reading governance stream ledger {self.ledger_path}: {e}")

        return events
