# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Memory Conflict Resolver & Superseding Lineage DAG Pipeline.
(Card-36: Memory-Anti-Entropy-Lineage-DAG-And-Conflict-Resolution / v1.6.0)

First Principles:
1. "Zero silent coexistence": Conflicting or updated memories cannot peacefully coexist as duplicate truths.
2. Atomic Superseding DAG: Old knowledge is atomically demoted to `superseded` and injected with `superseded_by` pointer.
3. SSOT Lineage Traversal: Forward & backward link traversal guarantees the agent always resolves to the current active SSOT.
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.service.memory_lifecycle_fsm import (
    MemoryLifecycleFSM,
    MemoryLifecycleRecord,
    MemoryLifecycleStore,
    MemoryStatus,
    LifecycleTransitionEvent,
)

logger = logging.getLogger("openviking.memory_conflict_resolver")


class ConflictResolutionResult(BaseModel):
    """Result of an atomic conflict resolution & superseding link operation."""
    success: bool = True
    old_uri: str
    new_uri: str
    old_status: str
    new_status: str
    reason: str
    timestamp: float = Field(default_factory=time.time)
    lineage_depth: int = 1


class MemoryConflictResolver:
    """Orchestrates memory conflict resolution, superseding DAG updates, and lineage tracking."""

    _instance: Optional[MemoryConflictResolver] = None
    _lock = threading.Lock()

    def __init__(self, store: Optional[MemoryLifecycleStore] = None) -> None:
        self.store = store or MemoryLifecycleStore.get_instance()
        self._history: collections.deque[ConflictResolutionResult] = collections.deque(maxlen=300)
        self._history_lock = threading.Lock()

    @classmethod
    def get_instance(cls, store: Optional[MemoryLifecycleStore] = None) -> MemoryConflictResolver:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(store=store)
        elif store is not None and cls._instance.store != store:
            cls._instance.store = store
        return cls._instance

    @classmethod
    def reset_for_testing(cls) -> None:
        with cls._lock:
            cls._instance = None

    def resolve_and_link(
        self,
        old_uri: str,
        new_uri: str,
        reason: str = "Superseded by newer verified knowledge",
        ctx: Any = None,
    ) -> ConflictResolutionResult:
        """
        Atomically demote old_uri to superseded, link it to new_uri,
        and establish lineage DAG relations.
        """
        clean_old = old_uri.strip()
        clean_new = new_uri.strip()

        if clean_old == clean_new:
            # Self-reference noop
            rec = self.store.get_record(clean_old)
            status_val = rec.status.value if rec else MemoryStatus.ACTIVE.value
            return ConflictResolutionResult(
                success=True,
                old_uri=clean_old,
                new_uri=clean_new,
                old_status=status_val,
                new_status=status_val,
                reason="Self-referencing update, preserved status",
            )

        now = time.time()

        # 1. Fetch or create old and new records
        old_rec = self.store.get_record(clean_old)
        if old_rec is None:
            old_rec = MemoryLifecycleRecord(
                uri=clean_old,
                status=MemoryStatus.ACTIVE,
                updated_at=now,
            )

        new_rec = self.store.get_record(clean_new)
        if new_rec is None:
            new_rec = MemoryLifecycleRecord(
                uri=clean_new,
                status=MemoryStatus.ACTIVE,
                updated_at=now,
            )

        # 2. If already superseded by this exact URI, make it idempotent
        if old_rec.status == MemoryStatus.SUPERSEDED and old_rec.superseded_by == clean_new:
            res = ConflictResolutionResult(
                success=True,
                old_uri=clean_old,
                new_uri=clean_new,
                old_status=MemoryStatus.SUPERSEDED.value,
                new_status=new_rec.status.value,
                reason=reason,
                timestamp=now,
            )
            with self._history_lock:
                self._history.appendleft(res)
            return res

        # 3. Transition old record to SUPERSEDED
        if old_rec.status == MemoryStatus.SUPERSEDED:
            # Re-point to newer version
            updated_old = MemoryLifecycleRecord(
                uri=clean_old,
                status=MemoryStatus.SUPERSEDED,
                superseded_by=clean_new,
                supersedes_uri=old_rec.supersedes_uri,
                disputed_reason=reason,
                updated_at=now,
            )
            self.store.save_record(updated_old)
        else:
            updated_old = MemoryLifecycleFSM.transition(
                record=old_rec,
                event=LifecycleTransitionEvent.SUPERSEDE,
                target_uri=clean_new,
                reason=reason,
                now_ts=now,
                store=self.store,
            )

        # 4. Update new record as active SSOT superseding clean_old
        updated_new = MemoryLifecycleRecord(
            uri=clean_new,
            status=MemoryStatus.ACTIVE,
            superseded_by=None,
            supersedes_uri=clean_old,
            disputed_reason=None,
            updated_at=now,
        )
        self.store.save_record(updated_new)

        # 5. Persist explicit graph edge into relations.db (fail-safe)
        self._link_relations_store(clean_old, clean_new, reason=reason, ctx=ctx)

        # 6. Record result in rolling history
        res = ConflictResolutionResult(
            success=True,
            old_uri=clean_old,
            new_uri=clean_new,
            old_status=updated_old.status.value,
            new_status=updated_new.status.value,
            reason=reason,
            timestamp=now,
        )

        with self._history_lock:
            self._history.appendleft(res)

        logger.info(
            "[MemoryConflictResolver] Resolved conflict: %s (superseded) -> %s (active SSOT). Reason: %s",
            clean_old,
            clean_new,
            reason,
        )
        return res

    def _link_relations_store(
        self, old_uri: str, new_uri: str, reason: str, ctx: Any = None
    ) -> None:
        """Best-effort persistence to relations.db for graph visualization."""
        try:
            from openviking.storage.relations_store import RelationsStore
            rstore = RelationsStore.get_instance()
            rstore.add_link(
                from_uri=new_uri,
                to_uri=old_uri,
                link_type="supersedes",
                reason=reason,
                weight=1.0,
            )
            rstore.add_link(
                from_uri=old_uri,
                to_uri=new_uri,
                link_type="superseded_by",
                reason=reason,
                weight=1.0,
            )
        except Exception as e:
            logger.debug("[MemoryConflictResolver] Failed to write graph links: %s", e)

    def get_lineage_chain(self, uri: str, max_hops: int = 20) -> Dict[str, Any]:
        """
        Traverse forward through superseded_by links to find current active SSOT,
        and backward through supersedes_uri to find historical predecessors.
        """
        clean_uri = uri.strip()
        forward_path: List[str] = [clean_uri]
        curr = clean_uri
        hops = 0

        while hops < max_hops:
            rec = self.store.get_record(curr)
            if not rec or not rec.superseded_by or rec.superseded_by == curr:
                break
            curr = rec.superseded_by
            if curr in forward_path:
                break  # Cycle protection
            forward_path.append(curr)
            hops += 1

        active_ssot = forward_path[-1]

        # Backward predecessor
        rec_start = self.store.get_record(clean_uri)
        predecessor = rec_start.supersedes_uri if rec_start else None

        return {
            "root_uri": clean_uri,
            "current_active_ssot": active_ssot,
            "superseded_path": forward_path[:-1] if len(forward_path) > 1 else [],
            "full_chain": forward_path,
            "is_superseded": len(forward_path) > 1,
            "predecessor": predecessor,
        }

    def get_conflict_stats(self) -> Dict[str, Any]:
        """Aggregate real-time conflict and lifecycle statistics from physical store."""
        records, total_count, _ = self.store.list_records(limit=1000)
        active_cnt = sum(1 for r in records if r.status == MemoryStatus.ACTIVE)
        disputed_cnt = sum(1 for r in records if r.status == MemoryStatus.DISPUTED)
        superseded_cnt = sum(1 for r in records if r.status == MemoryStatus.SUPERSEDED)

        with self._history_lock:
            total_resolutions = len(self._history)

        return {
            "total_nodes": total_count,
            "active_nodes": active_cnt,
            "disputed_nodes": disputed_cnt,
            "superseded_nodes": superseded_cnt,
            "total_resolutions": max(total_resolutions, superseded_cnt),
            "purity_ratio": round(active_cnt / max(1, total_count), 4),
        }

    def get_resolution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent conflict resolution events, merging in-memory queue with persistent store."""
        with self._history_lock:
            items = list(self._history)

        seen_pairs = {(item.old_uri, item.new_uri) for item in items}
        results = [item.model_dump() for item in items]

        # Merge with persistent records from physical store
        if len(results) < limit:
            records, _, _ = self.store.list_records(limit=limit * 2)
            for r in records:
                if r.status == MemoryStatus.SUPERSEDED and r.superseded_by:
                    pair = (r.uri, r.superseded_by)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        results.append({
                            "success": True,
                            "old_uri": r.uri,
                            "new_uri": r.superseded_by,
                            "old_status": "superseded",
                            "new_status": "active",
                            "reason": r.disputed_reason or "Superseded by verified newer revision",
                            "timestamp": r.updated_at,
                            "lineage_depth": 1,
                        })
                        if len(results) >= limit:
                            break

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]
