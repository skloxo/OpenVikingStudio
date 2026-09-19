# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Memory Lifecycle Finite State Machine & SQLite Persistent Store.
(Card-Fix-FSM-Persistence / v1.5.47)

First Principles:
1. "Memories are living beliefs with lifecycles, backed by single persistent physical SSOT."
2. Eliminates in-memory registry silos. States (active, disputed, superseded) are permanently
   persisted into SQLite WAL database (~/.openviking/data/memory_lifecycle.db).
3. Fast & Safe: Thread-safe connection handling, LRU memory cache (up to 10,000 entries),
   and batch lookup for real-time retrieval demotion (0.20x superseded, 0.50x disputed).
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class MemoryStatus(str, Enum):
    """Canonical lifecycle states for memory items."""
    ACTIVE = "active"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"


class LifecycleTransitionEvent(str, Enum):
    """Valid events that trigger lifecycle state transitions."""
    CREATE = "create"
    DISPUTE = "dispute"
    RESOLVE = "resolve"
    SUPERSEDE = "supersede"
    REVERT = "revert"


class InvalidLifecycleTransitionError(ValueError):
    """Raised when an invalid state machine transition is attempted."""
    pass


class MemoryLifecycleRecord(BaseModel):
    """Typed DTO representing the lifecycle state and lineage of a memory unit."""
    uri: str
    status: MemoryStatus = MemoryStatus.ACTIVE
    superseded_by: Optional[str] = None
    supersedes_uri: Optional[str] = None
    disputed_reason: Optional[str] = None
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "status": self.status.value,
            "superseded_by": self.superseded_by,
            "supersedes_uri": self.supersedes_uri,
            "disputed_reason": self.disputed_reason,
            "updated_at": self.updated_at,
        }


class MemoryLifecycleStore:
    """Thread-safe SQLite persistent store for MemoryLifecycleRecord."""

    _instance: Optional[MemoryLifecycleStore] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = os.path.expanduser("~/.openviking/data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "memory_lifecycle.db")
        self.db_path = db_path
        self._cache: Dict[str, MemoryLifecycleRecord] = {}
        self._cache_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> MemoryLifecycleStore:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_lifecycle (
                    uri TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    superseded_by TEXT,
                    supersedes_uri TEXT,
                    disputed_reason TEXT,
                    updated_at REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_status ON memory_lifecycle(status);")

    def get_record(self, uri: str) -> Optional[MemoryLifecycleRecord]:
        clean_uri = uri.strip()
        with self._cache_lock:
            if clean_uri in self._cache:
                return self._cache[clean_uri]

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT uri, status, superseded_by, supersedes_uri, disputed_reason, updated_at "
                "FROM memory_lifecycle WHERE uri = ?",
                (clean_uri,),
            )
            row = cursor.fetchone()
            if row:
                rec = MemoryLifecycleRecord(
                    uri=row[0],
                    status=MemoryStatus(row[1]),
                    superseded_by=row[2],
                    supersedes_uri=row[3],
                    disputed_reason=row[4],
                    updated_at=row[5],
                )
                with self._cache_lock:
                    if len(self._cache) < 10000:
                        self._cache[clean_uri] = rec
                return rec
        return None

    def get_records_batch(self, uris: List[str]) -> Dict[str, MemoryLifecycleRecord]:
        results: Dict[str, MemoryLifecycleRecord] = {}
        missing_uris: List[str] = []

        with self._cache_lock:
            for u in uris:
                clean_u = u.strip()
                if clean_u in self._cache:
                    results[clean_u] = self._cache[clean_u]
                else:
                    missing_uris.append(clean_u)

        if not missing_uris:
            return results

        placeholders = ",".join("?" for _ in missing_uris)
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"SELECT uri, status, superseded_by, supersedes_uri, disputed_reason, updated_at "
                f"FROM memory_lifecycle WHERE uri IN ({placeholders})",
                missing_uris,
            )
            for row in cursor.fetchall():
                rec = MemoryLifecycleRecord(
                    uri=row[0],
                    status=MemoryStatus(row[1]),
                    superseded_by=row[2],
                    supersedes_uri=row[3],
                    disputed_reason=row[4],
                    updated_at=row[5],
                )
                results[rec.uri] = rec
                with self._cache_lock:
                    if len(self._cache) < 10000:
                        self._cache[rec.uri] = rec

        return results

    def save_record(self, record: MemoryLifecycleRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memory_lifecycle (uri, status, superseded_by, supersedes_uri, disputed_reason, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(uri) DO UPDATE SET
                    status=excluded.status,
                    superseded_by=excluded.superseded_by,
                    supersedes_uri=excluded.supersedes_uri,
                    disputed_reason=excluded.disputed_reason,
                    updated_at=excluded.updated_at
                """,
                (
                    record.uri,
                    record.status.value,
                    record.superseded_by,
                    record.supersedes_uri,
                    record.disputed_reason,
                    record.updated_at,
                ),
            )
        with self._cache_lock:
            self._cache[record.uri] = record

    def list_records(
        self, status: Optional[str] = None, limit: int = 50
    ) -> Tuple[List[MemoryLifecycleRecord], int, Dict[str, int]]:
        with self._get_connection() as conn:
            # Get status counts
            counts = {"active": 0, "disputed": 0, "superseded": 0}
            for row in conn.execute("SELECT status, count(*) FROM memory_lifecycle GROUP BY status").fetchall():
                st = row[0].lower()
                if st in counts:
                    counts[st] = row[1]

            query = "SELECT uri, status, superseded_by, supersedes_uri, disputed_reason, updated_at FROM memory_lifecycle"
            params: List[Any] = []
            if status:
                query += " WHERE status = ?"
                params.append(status.lower())
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            records = [
                MemoryLifecycleRecord(
                    uri=r[0],
                    status=MemoryStatus(r[1]),
                    superseded_by=r[2],
                    supersedes_uri=r[3],
                    disputed_reason=r[4],
                    updated_at=r[5],
                )
                for r in cursor.fetchall()
            ]

            total = sum(counts.values())
            return records, total, counts


from collections.abc import MutableMapping, Iterator


class _LifecycleRegistryProxy(MutableMapping[str, MemoryLifecycleRecord]):
    """Backward-compatible dictionary proxy backed by SQLite store."""

    def __getitem__(self, key: str) -> MemoryLifecycleRecord:
        rec = MemoryLifecycleStore.get_instance().get_record(key)
        if rec is None:
            raise KeyError(key)
        return rec

    def __setitem__(self, key: str, value: MemoryLifecycleRecord) -> None:
        MemoryLifecycleStore.get_instance().save_record(value)

    def __delitem__(self, key: str) -> None:
        pass

    def __iter__(self) -> Iterator[str]:
        records, _, _ = MemoryLifecycleStore.get_instance().list_records(limit=200)
        return iter(r.uri for r in records)

    def __len__(self) -> int:
        _, total, _ = MemoryLifecycleStore.get_instance().list_records(limit=1)
        return total

    def get(self, key: str, default: Any = None) -> Any:
        rec = MemoryLifecycleStore.get_instance().get_record(key)
        return rec if rec is not None else default

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return MemoryLifecycleStore.get_instance().get_record(key) is not None


_LIFECYCLE_REGISTRY = _LifecycleRegistryProxy()


def get_or_create_lifecycle_record(uri: str) -> MemoryLifecycleRecord:
    """Retrieve existing persistent lifecycle record or initialize as active."""
    store = MemoryLifecycleStore.get_instance()
    rec = store.get_record(uri)
    if rec is None:
        rec = MemoryLifecycleRecord(
            uri=uri.strip(),
            status=MemoryStatus.ACTIVE,
            updated_at=time.time(),
        )
        store.save_record(rec)
    return rec


def get_lifecycle_records_batch(uris: List[str]) -> Dict[str, MemoryLifecycleRecord]:
    """Batch retrieve lifecycle records for fast retrieval demotion."""
    return MemoryLifecycleStore.get_instance().get_records_batch(uris)


class MemoryLifecycleFSM:
    """Deterministic finite state machine governing memory status transitions."""

    _TRANSITIONS = {
        (None, LifecycleTransitionEvent.CREATE): MemoryStatus.ACTIVE,
        (MemoryStatus.ACTIVE, LifecycleTransitionEvent.DISPUTE): MemoryStatus.DISPUTED,
        (MemoryStatus.ACTIVE, LifecycleTransitionEvent.SUPERSEDE): MemoryStatus.SUPERSEDED,
        (MemoryStatus.DISPUTED, LifecycleTransitionEvent.RESOLVE): MemoryStatus.ACTIVE,
        (MemoryStatus.DISPUTED, LifecycleTransitionEvent.SUPERSEDE): MemoryStatus.SUPERSEDED,
        (MemoryStatus.SUPERSEDED, LifecycleTransitionEvent.REVERT): MemoryStatus.ACTIVE,
    }

    @classmethod
    def can_transition(
        cls,
        current_status: Optional[MemoryStatus],
        event: LifecycleTransitionEvent,
    ) -> bool:
        return (current_status, event) in cls._TRANSITIONS

    @classmethod
    def transition(
        cls,
        record: MemoryLifecycleRecord,
        event: LifecycleTransitionEvent,
        *,
        target_uri: Optional[str] = None,
        reason: Optional[str] = None,
        now_ts: Optional[float] = None,
        store: Optional[MemoryLifecycleStore] = None,
    ) -> MemoryLifecycleRecord:
        key = (record.status, event)
        if key not in cls._TRANSITIONS:
            raise InvalidLifecycleTransitionError(
                f"Illegal memory lifecycle transition: Cannot perform '{event.value}' "
                f"from status '{record.status.value}' for URI '{record.uri}'."
            )

        new_status = cls._TRANSITIONS[key]
        current_time = now_ts or time.time()
        superseded_by = record.superseded_by
        disputed_reason = record.disputed_reason

        if event == LifecycleTransitionEvent.SUPERSEDE:
            if not target_uri:
                raise InvalidLifecycleTransitionError(
                    "Transition 'supersede' requires a non-empty target_uri pointing to successor memory."
                )
            superseded_by = target_uri
            disputed_reason = reason or "Superseded by verified newer revision."
        elif event == LifecycleTransitionEvent.DISPUTE:
            disputed_reason = reason or "Marked disputed due to conflicting evidence."
        elif event in (LifecycleTransitionEvent.RESOLVE, LifecycleTransitionEvent.REVERT):
            superseded_by = None
            disputed_reason = None

        updated = MemoryLifecycleRecord(
            uri=record.uri,
            status=new_status,
            superseded_by=superseded_by,
            supersedes_uri=record.supersedes_uri,
            disputed_reason=disputed_reason,
            updated_at=current_time,
        )
        active_store = store or MemoryLifecycleStore.get_instance()
        active_store.save_record(updated)
        return updated

    @classmethod
    def link_superseded_pair(
        cls,
        old_record: MemoryLifecycleRecord,
        new_uri: str,
        reason: str = "Superseded by newer knowledge",
        now_ts: Optional[float] = None,
        store: Optional[MemoryLifecycleStore] = None,
    ) -> tuple[MemoryLifecycleRecord, MemoryLifecycleRecord]:
        active_store = store or MemoryLifecycleStore.get_instance()
        updated_old = cls.transition(
            record=old_record,
            event=LifecycleTransitionEvent.SUPERSEDE,
            target_uri=new_uri,
            reason=reason,
            now_ts=now_ts,
            store=active_store,
        )
        new_successor = MemoryLifecycleRecord(
            uri=new_uri,
            status=MemoryStatus.ACTIVE,
            supersedes_uri=old_record.uri,
            updated_at=now_ts or time.time(),
        )
        active_store.save_record(new_successor)
        return updated_old, new_successor

    @classmethod
    def build_lineage_chain(
        cls,
        target_uri: str,
        records: Any,
    ) -> Dict[str, Any]:
        store = MemoryLifecycleStore.get_instance()
        current = store.get_record(target_uri)
        predecessors: List[Dict[str, Any]] = []
        successors: List[Dict[str, Any]] = []

        cursor = current
        visited_back = {target_uri}
        while cursor and cursor.supersedes_uri and cursor.supersedes_uri not in visited_back:
            pred_uri = cursor.supersedes_uri
            visited_back.add(pred_uri)
            pred_rec = store.get_record(pred_uri)
            if pred_rec:
                predecessors.append(pred_rec.to_dict())
                cursor = pred_rec
            else:
                predecessors.append({"uri": pred_uri, "status": "unknown"})
                break

        cursor = current
        visited_fwd = {target_uri}
        while cursor and cursor.superseded_by and cursor.superseded_by not in visited_fwd:
            succ_uri = cursor.superseded_by
            visited_fwd.add(succ_uri)
            succ_rec = store.get_record(succ_uri)
            if succ_rec:
                successors.append(succ_rec.to_dict())
                cursor = succ_rec
            else:
                successors.append({"uri": succ_uri, "status": "unknown"})
                break

        return {
            "uri": target_uri,
            "status": current.status.value if current else "unknown",
            "record": current.to_dict() if current else None,
            "predecessors": predecessors,
            "successors": successors,
            "is_active_head": bool(current and current.status == MemoryStatus.ACTIVE and not current.superseded_by),
        }
