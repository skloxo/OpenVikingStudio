# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Layer 5 Pre-Governance Snapshot, Rollback & Five-Layer Overview (Card-168 / Tududi #156).

Captures lifecycle FSM records and crystal files physically before offline dreaming
mutations execute, enabling deterministic, idempotent rollback and 5-layer reporting.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleRecord,
    MemoryLifecycleStore,
    MemoryStatus,
)

logger = logging.getLogger("openviking.service.memory_governance_snapshot")


class MemoryGovernanceSnapshotStore:
    """Persistent physical backup & rollback store for Layer 5 dream governance."""

    def __init__(self, snapshot_dir: Optional[Path] = None) -> None:
        self.snapshot_dir = snapshot_dir or (
            Path.home() / ".openviking" / "data" / "snapshots" / "dream"
        )
        self._lock = threading.Lock()

    def _snapshot_path(self, snapshot_id: str) -> Path:
        safe_id = "".join(c for c in snapshot_id if c.isalnum() or c in ("_", "-"))
        if not safe_id:
            raise ValueError(f"Invalid snapshot_id: {snapshot_id}")
        return self.snapshot_dir / f"{safe_id}.json"

    @staticmethod
    def _atomic_write_json(target: Path, payload: Dict[str, Any]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, target)

    def capture_dream_snapshot(
        self,
        *,
        snapshot_id: str,
        dream_id: str,
        theme: str,
        crystals_dir: Path,
        fragment_uris: List[str],
        target_filenames: List[str],
    ) -> Dict[str, Any]:
        """Persist pre-dream lifecycle records and crystal files before mutations occur."""
        store = MemoryLifecycleStore.get_instance()
        all_uris = sorted({u for u in fragment_uris if u})
        existing_records = store.get_records_batch(all_uris) if all_uris else {}
        lifecycle_before: Dict[str, Optional[Dict[str, Any]]] = {
            uri: existing_records[uri].to_dict() if uri in existing_records else None
            for uri in all_uris
        }

        file_backups: Dict[str, Optional[str]] = {}
        for fname in target_filenames:
            fpath = crystals_dir / fname
            if fpath.is_file():
                try:
                    file_backups[fname] = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    file_backups[fname] = None
            else:
                file_backups[fname] = None

        record = {
            "snapshot_id": snapshot_id,
            "dream_id": dream_id,
            "theme": theme,
            "crystals_dir": str(crystals_dir),
            "created_at": time.time(),
            "rolled_back": False,
            "rolled_back_at": None,
            "lifecycle_before": lifecycle_before,
            "file_backups": file_backups,
        }
        with self._lock:
            self._atomic_write_json(self._snapshot_path(snapshot_id), record)
        return record

    def list_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List stored dream governance snapshots sorted newest first."""
        if not self.snapshot_dir.is_dir():
            return []
        items: List[Dict[str, Any]] = []
        with self._lock:
            for path in self.snapshot_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                items.append(
                    {
                        "snapshot_id": data.get("snapshot_id"),
                        "dream_id": data.get("dream_id"),
                        "theme": data.get("theme"),
                        "created_at": data.get("created_at"),
                        "rolled_back": bool(data.get("rolled_back", False)),
                        "rolled_back_at": data.get("rolled_back_at"),
                        "tracked_fragments": len(data.get("lifecycle_before") or {}),
                        "tracked_crystals": len(data.get("file_backups") or {}),
                    }
                )
        items.sort(key=lambda x: float(x.get("created_at") or 0.0), reverse=True)
        return items[: max(1, int(limit))]

    def rollback_snapshot(
        self,
        snapshot_id: str,
        *,
        ledger_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Atomically restore lifecycle FSM state and crystal files captured before dreaming."""
        snap_path = self._snapshot_path(snapshot_id)
        if not snap_path.is_file():
            raise KeyError(f"Dream snapshot '{snapshot_id}' not found.")

        with self._lock:
            data = json.loads(snap_path.read_text(encoding="utf-8"))
            if data.get("rolled_back"):
                return {
                    "status": "already_rolled_back",
                    "snapshot_id": snapshot_id,
                    "restored_fragments": 0,
                    "removed_crystals": 0,
                    "restored_crystals": 0,
                }

            store = MemoryLifecycleStore.get_instance()
            restored_fragments = 0
            lifecycle_before: Dict[str, Optional[Dict[str, Any]]] = data.get("lifecycle_before") or {}
            for uri, prev in lifecycle_before.items():
                if isinstance(prev, dict):
                    rec = MemoryLifecycleRecord(
                        uri=uri,
                        status=MemoryStatus(prev.get("status", "active")),
                        superseded_by=prev.get("superseded_by"),
                        supersedes_uri=prev.get("supersedes_uri"),
                        disputed_reason=prev.get("disputed_reason"),
                        updated_at=float(prev.get("updated_at") or time.time()),
                    )
                else:
                    rec = MemoryLifecycleRecord(
                        uri=uri,
                        status=MemoryStatus.ACTIVE,
                        superseded_by=None,
                        supersedes_uri=None,
                        disputed_reason=None,
                    )
                store.save_record(rec)
                restored_fragments += 1

            crystals_dir = Path(str(data.get("crystals_dir") or ""))
            removed_crystals = 0
            restored_crystals = 0
            file_backups: Dict[str, Optional[str]] = data.get("file_backups") or {}
            for fname, prev_content in file_backups.items():
                target = crystals_dir / fname
                if prev_content is None:
                    if target.is_file():
                        target.unlink()
                        removed_crystals += 1
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(str(prev_content), encoding="utf-8")
                    restored_crystals += 1

            now_ts = time.time()
            data["rolled_back"] = True
            data["rolled_back_at"] = now_ts
            self._atomic_write_json(snap_path, data)

        if ledger_path is not None:
            try:
                ledger_path.parent.mkdir(parents=True, exist_ok=True)
                entry = {
                    "event_id": f"#rbk_{snapshot_id}",
                    "type": "DREAM_ROLLBACK",
                    "action": "rollback",
                    "snapshot_id": snapshot_id,
                    "restored_fragments": restored_fragments,
                    "removed_crystals": removed_crystals,
                    "timestamp": now_ts,
                }
                with open(ledger_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except OSError:
                pass

        return {
            "status": "rolled_back",
            "snapshot_id": snapshot_id,
            "dream_id": data.get("dream_id"),
            "restored_fragments": restored_fragments,
            "removed_crystals": removed_crystals,
            "restored_crystals": restored_crystals,
            "rolled_back_at": now_ts,
        }


def build_five_layer_governance_overview() -> Dict[str, Any]:
    """Collect unified live telemetry across all 5 Anti-Entropy Memory Evolution layers."""
    from openviking.retrieve.asymmetric_decay import DecayConfig
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper
    from openviking.service.memory_cold_archive_service import MemoryColdArchiveService
    from openviking.service.memory_conflict_resolver import MemoryConflictResolver
    from openviking.service.memory_purity import MemoryPurityBenchmark
    from openviking.service.offline_dreamer import OfflineDreamer

    gatekeeper_stats = EntropyGatekeeper.get_instance().get_stats().get("stats", {})
    conflict_stats = MemoryConflictResolver.get_instance().get_conflict_stats()
    cold_audit = MemoryColdArchiveService.get_instance().audit_storage_lifecycle(limit=50)
    decay_cfg = DecayConfig()
    dreamer = OfflineDreamer.get_instance()
    dream_stats = dreamer.get_stats()
    snapshots = dreamer.list_snapshots(limit=20)
    purity = MemoryPurityBenchmark.get_instance().compute_purity_report().model_dump()

    return {
        "layer1_ingestion_dedup": {
            "total_probes": gatekeeper_stats.get("total_probes", 0),
            "noop": gatekeeper_stats.get("noop", 0),
            "update": gatekeeper_stats.get("update", 0),
            "add": gatekeeper_stats.get("add", 0),
            "dlq": gatekeeper_stats.get("dlq", 0),
            "saved_bytes": gatekeeper_stats.get("saved_bytes", 0),
        },
        "layer2_conflict_dag": conflict_stats,
        "layer3_temporal_decay": {
            "axiom_immune": True,
            "experience_half_life_days": decay_cfg.default_half_life_days,
            "session_half_life_days": decay_cfg.session_half_life_days,
            "cold_audit_candidates": cold_audit.get("total_candidates", 0)
            if isinstance(cold_audit, dict)
            else 0,
        },
        "layer4_offline_dreaming": dream_stats,
        "layer5_snapshot_and_purity": {
            "total_snapshots": len(snapshots),
            "recoverable_snapshots": sum(1 for s in snapshots if not s.get("rolled_back")),
            "purity": purity,
        },
    }
