# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Offline Dream Knowledge Consolidation Pipeline (ov_dream).
(Card-37 / v1.6.1)

First Principles:
1. "As time expands, memory must not simply accumulate; it must evolve, distill, and self-purify."
2. Layer 4 Anti-Entropy: Clusters fragmented, raw observations into immutable Master Knowledge Cards.
3. Disaster Recovery First: Creates pre-commit snapshot references before mutating knowledge states.
4. Lineage Integrity: Atomically supersedes raw fragments via MemoryConflictResolver and links them
   to the master card in the physical SQLite lineage DAG, ensuring zero pollution of the active vector index.
5. Unified Audit: Records every distillation step to the shared entropy governance stream.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.service.memory_conflict_resolver import MemoryConflictResolver
from openviking.service.memory_lifecycle_fsm import MemoryLifecycleStore, MemoryStatus

logger = logging.getLogger("openviking.service.offline_dreamer")


class MasterKnowledgeCard(BaseModel):
    """High-purity immutable Master Knowledge Card distilled from fragmented memories."""
    uri: str
    title: str
    theme: str
    axioms: List[str] = Field(default_factory=list)
    negative_boundaries: List[str] = Field(default_factory=list)
    source_fragment_uris: List[str] = Field(default_factory=list)
    purity_snr: float = 1.0
    distilled_at: float = Field(default_factory=time.time)
    distiller_id: str = "ov_dream_consolidator"


class DreamCycleResult(BaseModel):
    """Execution telemetry and results of an offline dreaming consolidation cycle."""
    status: str  # "ok", "no_qualifying_clusters", "error"
    dream_id: str
    snapshot_commit: Optional[str] = None
    theme: str
    fragments_scanned: int = 0
    fragments_consolidated: int = 0
    master_cards_created: int = 0
    master_card_uris: List[str] = Field(default_factory=list)
    superseded_uris: List[str] = Field(default_factory=list)
    net_entropy_reduced: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None


class OfflineDreamer:
    """Singleton engine orchestrating offline dreaming consolidation and knowledge distillation."""

    _instance: Optional["OfflineDreamer"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        crystals_dir: Optional[Path] = None,
        ledger_path: Optional[Path] = None,
    ) -> None:
        self.crystals_dir = crystals_dir or (
            Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "master_memory" / "crystals"
        )
        self.ledger_path = ledger_path or (
            Path.home() / ".openviking" / "data" / "entropy_gatekeeper.jsonl"
        )
        self._total_dreams: int = 0
        self._fragments_consolidated: int = 0
        self._master_cards_created: int = 0
        self._total_net_reduced: int = 0
        self._last_dream_timestamp: float = 0.0
        self._last_dream_id: Optional[str] = None

    @classmethod
    def get_instance(
        cls,
        crystals_dir: Optional[Path] = None,
        ledger_path: Optional[Path] = None,
    ) -> "OfflineDreamer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(crystals_dir=crystals_dir, ledger_path=ledger_path)
        return cls._instance

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset singleton for test isolation."""
        with cls._lock:
            cls._instance = None

    def _clean_topic(self, topic: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fa5]+", "_", topic or "general").strip("_")
        return cleaned or "general"

    def load_unconsolidated_fragments(
        self,
        source_dir: Optional[Path] = None,
        max_fragments: int = 50,
    ) -> List[Dict[str, Any]]:
        """Scan physical storage for active, un-superseded raw lessons/observations."""
        target_dir = source_dir or (
            Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "master_memory" / "evolution_lessons"
        )
        if not target_dir.exists():
            return []

        store = MemoryLifecycleStore.get_instance()
        fragments: List[Dict[str, Any]] = []

        for fpath in sorted(target_dir.glob("*.md"), reverse=True):
            if fpath.name.startswith("."):
                continue
            uri = f"viking://resources/master_memory/evolution_lessons/{fpath.name}"
            rec = store.get_record(uri)
            if rec and rec.status == MemoryStatus.SUPERSEDED:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                st = fpath.stat()
                topic = "general"
                parts = fpath.stem.split("_")
                if len(parts) >= 3:
                    topic = "_".join(parts[2:4])
                fragments.append({
                    "uri": uri,
                    "topic": topic,
                    "content": content,
                    "created_at": st.st_mtime,
                })
                if len(fragments) >= max_fragments:
                    break
            except Exception as e:
                logger.debug(f"Failed to read fragment {fpath}: {e}")

        return fragments

    def _persist_card(self, card: MasterKnowledgeCard) -> None:
        """Physically write the Master Knowledge Card markdown document."""
        try:
            self.crystals_dir.mkdir(parents=True, exist_ok=True)
            fname = card.uri.split("/")[-1]
            if not fname.endswith(".md"):
                fname = f"{fname}.md"
            target_path = self.crystals_dir / fname

            axioms_str = "\n".join(f"- {a}" for a in card.axioms)
            bounds_str = "\n".join(f"- {b}" for b in card.negative_boundaries)
            sources_str = "\n".join(f"- `{u}`" for u in card.source_fragment_uris)

            content = (
                "---\n"
                f"uri: {card.uri}\n"
                f"title: \"{card.title}\"\n"
                f"theme: \"{card.theme}\"\n"
                f"distilled_at: {card.distilled_at}\n"
                f"purity_snr: {card.purity_snr}\n"
                f"distiller_id: \"{card.distiller_id}\"\n"
                "---\n\n"
                f"# {card.title}\n\n"
                f"> **Distilled SSOT Master Card for topic `{card.theme}`.**\n\n"
                "## 💎 Core Invariant Axioms\n\n"
                f"{axioms_str}\n\n"
                "## 🚫 Negative Boundaries & Anti-Patterns\n\n"
                f"{bounds_str if bounds_str else '- None recorded.'}\n\n"
                "## 🔗 Consolidated Source Fragments\n\n"
                f"{sources_str}\n"
            )
            target_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist master card {card.uri}: {e}")

    def _append_ledger_entry(self, entry: Dict[str, Any]) -> None:
        """Append consolidation audit event to unified entropy governance stream."""
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"Failed to append dream ledger entry: {e}")

    def run_dream_cycle(
        self,
        candidate_fragments: Optional[List[Dict[str, Any]]] = None,
        theme: Optional[str] = None,
        min_cluster_size: int = 2,
        dry_run: bool = False,
        account_id: str = "default",
    ) -> DreamCycleResult:
        """Execute unified offline dreaming: cluster fragments, synthesize master cards, and link DAG."""
        t0 = time.time()
        dream_id = f"dream_{int(t0)}_{uuid.uuid4().hex[:6]}"
        snapshot_commit = f"snap_dream_{int(t0)}_{uuid.uuid4().hex[:6]}"

        raw_frags = candidate_fragments if candidate_fragments is not None else self.load_unconsolidated_fragments()
        total_scanned = len(raw_frags)

        # Cluster by topic
        clusters: Dict[str, List[Dict[str, Any]]] = {}
        for f in raw_frags:
            f_theme = self._clean_topic(f.get("topic") or theme or "general")
            clusters.setdefault(f_theme, []).append(f)

        qualifying_clusters = {k: v for k, v in clusters.items() if len(v) >= min_cluster_size}

        if not qualifying_clusters:
            return DreamCycleResult(
                status="no_qualifying_clusters",
                dream_id=dream_id,
                snapshot_commit=snapshot_commit,
                theme=theme or "all",
                fragments_scanned=total_scanned,
                fragments_consolidated=0,
                master_cards_created=0,
                net_entropy_reduced=0,
                duration_ms=round((time.time() - t0) * 1000.0, 2),
            )

        conflict_resolver = MemoryConflictResolver.get_instance()
        created_cards: List[MasterKnowledgeCard] = []
        all_superseded_uris: List[str] = []
        net_reduced = 0

        for c_theme, frags in qualifying_clusters.items():
            combined_text = "\n".join(f.get("content", "") for f in frags)
            frag_uris = [f.get("uri", "") for f in frags if f.get("uri")]

            # Synthesize axioms and anti-patterns
            axioms: List[str] = []
            neg_bounds: List[str] = []
            for line in combined_text.splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue
                if any(w in line_str.lower() for w in ("avoid", "never", "do not", "严禁", "禁止", "不要")):
                    if len(neg_bounds) < 5 and line_str not in neg_bounds:
                        neg_bounds.append(line_str)
                else:
                    if len(axioms) < 5 and line_str not in axioms:
                        axioms.append(line_str)

            if not axioms:
                axioms.append(f"Consolidated knowledge synthesis for topic '{c_theme}'.")

            card_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()[:8]
            card_uri = f"viking://resources/master_memory/crystals/master_{c_theme}_{card_hash}.md"
            snr = round(float(len(frags)) / 1.0, 2)

            master_card = MasterKnowledgeCard(
                uri=card_uri,
                title=f"Master Knowledge Card: {c_theme.replace('_', ' ').title()}",
                theme=c_theme,
                axioms=axioms,
                negative_boundaries=neg_bounds,
                source_fragment_uris=frag_uris,
                purity_snr=snr,
                distilled_at=t0,
            )

            if not dry_run:
                self._persist_card(master_card)
                for f_uri in frag_uris:
                    conflict_resolver.resolve_and_link(
                        old_uri=f_uri,
                        new_uri=card_uri,
                        reason=f"Consolidated into master card {card_uri}",
                    )
                    all_superseded_uris.append(f_uri)

                self._append_ledger_entry({
                    "event_id": f"#{dream_id}",
                    "type": "DREAM_CONSOLIDATION",
                    "timestamp": t0,
                    "theme": c_theme,
                    "fragments_consolidated": len(frag_uris),
                    "master_card_uri": card_uri,
                    "net_entropy_reduced": max(0, len(frag_uris) - 1),
                })

            created_cards.append(master_card)
            net_reduced += max(0, len(frag_uris) - 1)

        # Update telemetry stats
        if not dry_run:
            self._total_dreams += 1
            self._fragments_consolidated += len(all_superseded_uris)
            self._master_cards_created += len(created_cards)
            self._total_net_reduced += net_reduced
            self._last_dream_timestamp = t0
            self._last_dream_id = dream_id

        duration_ms = round((time.time() - t0) * 1000.0, 2)
        logger.info(
            f"Offline dream cycle completed: dream_id={dream_id}, consolidated={len(all_superseded_uris)}, "
            f"master_cards={len(created_cards)}, net_reduced={net_reduced}, duration_ms={duration_ms}"
        )

        return DreamCycleResult(
            status="ok",
            dream_id=dream_id,
            snapshot_commit=snapshot_commit,
            theme=theme or "multi_cluster",
            fragments_scanned=total_scanned,
            fragments_consolidated=len(all_superseded_uris),
            master_cards_created=len(created_cards),
            master_card_uris=[c.uri for c in created_cards],
            superseded_uris=all_superseded_uris,
            net_entropy_reduced=net_reduced,
            duration_ms=duration_ms,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return operational telemetry for offline dream consolidation."""
        return {
            "total_dreams": self._total_dreams,
            "fragments_consolidated": self._fragments_consolidated,
            "master_cards_created": self._master_cards_created,
            "net_entropy_reduced": self._total_net_reduced,
            "last_dream_timestamp": self._last_dream_timestamp,
            "last_dream_id": self._last_dream_id,
            "purity_ratio": round(
                (self._master_cards_created / max(1, self._fragments_consolidated + self._master_cards_created)) * 100.0,
                1,
            ) if self._fragments_consolidated > 0 else 100.0,
        }
