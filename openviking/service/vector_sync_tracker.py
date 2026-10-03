# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Vector Index Synchronization Tracker and Self-Healing Engine.

First Principles:
State Invariant: A document in VikingFS is in an incomplete state until its
vector representation exists in VikingDB. By recording the tripartite state
(PENDING, INDEXED, FAILED) as a persistent invariant in SQLite, the system
gains an active retina to detect and heal unindexed stragglers.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("openviking.service.vector_sync_tracker")


class SyncStatus(str, Enum):
    """Lifecycle states of vector indexing for files."""
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class VectorSyncRecord(BaseModel):
    """Strongly typed DTO representing the vector synchronization state of a file."""
    uri: str
    account_id: str = "default"
    status: SyncStatus = SyncStatus.PENDING
    content_hash: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "account_id": self.account_id,
            "status": self.status.value,
            "content_hash": self.content_hash,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class VectorSyncTracker:
    """Thread-safe persistent manager for tracking vector synchronization states."""

    _instance: Optional[VectorSyncTracker] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = os.path.expanduser("~/.openviking/data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "vector_sync_state.db")
        self.db_path = db_path
        self._rw_lock = threading.Lock()
        self._fast_path_count: int = 0
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> VectorSyncTracker:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset singleton instance for test isolation."""
        with cls._lock:
            cls._instance = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_sync_state (
                    uri TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content_hash TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    fast_path INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            try:
                conn.execute("ALTER TABLE vector_sync_state ADD COLUMN fast_path INTEGER DEFAULT 0;")
            except sqlite3.OperationalError:
                pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON vector_sync_state(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_account ON vector_sync_state(account_id);")

    def mark_fast_path(self, uri: str, account_id: str = "default") -> None:
        """Record a fast-path ingestion event (WAL committed immediately before vector indexing)."""
        with self._rw_lock:
            self._fast_path_count += 1
        now = time.time()
        with self._rw_lock, self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO vector_sync_state (uri, account_id, status, content_hash, retry_count, last_error, fast_path, created_at, updated_at)
                    VALUES (?, ?, 'PENDING', NULL, 0, NULL, 1, ?, ?)
                    ON CONFLICT(uri) DO UPDATE SET
                        fast_path = 1,
                        updated_at = excluded.updated_at
                    """,
                    (uri, account_id, now, now),
                )
            except Exception as e:
                logger.debug("Failed to record fast_path DB row for %s: %s", uri, e)

    def mark_pending(self, uri: str, account_id: str = "default", content_hash: Optional[str] = None) -> None:
        """Record or update a file's state to PENDING when queued for embedding."""
        now = time.time()
        with self._rw_lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO vector_sync_state (uri, account_id, status, content_hash, retry_count, last_error, created_at, updated_at)
                VALUES (?, ?, 'PENDING', ?, 0, NULL, ?, ?)
                ON CONFLICT(uri) DO UPDATE SET
                    status = 'PENDING',
                    content_hash = COALESCE(excluded.content_hash, vector_sync_state.content_hash),
                    updated_at = excluded.updated_at
                """,
                (uri, account_id, content_hash, now, now),
            )

    def record_write(self, uri: str, content_hash: Optional[str] = None, account_id: str = "default") -> None:
        """Convenience alias for mark_pending upon physical file write."""
        self.mark_pending(uri=uri, account_id=account_id, content_hash=content_hash)

    def mark_indexed(self, uri: str, account_id: str = "default", content_hash: Optional[str] = None) -> None:
        """Mark a file as successfully INDEXED in VikingDB."""
        now = time.time()
        with self._rw_lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO vector_sync_state (uri, account_id, status, content_hash, retry_count, last_error, created_at, updated_at)
                VALUES (?, ?, 'INDEXED', ?, 0, NULL, ?, ?)
                ON CONFLICT(uri) DO UPDATE SET
                    status = 'INDEXED',
                    content_hash = COALESCE(excluded.content_hash, vector_sync_state.content_hash),
                    last_error = NULL,
                    updated_at = excluded.updated_at
                """,
                (uri, account_id, content_hash, now, now),
            )

    def mark_failed(self, uri: str, account_id: str = "default", error: str = "") -> None:
        """Mark a file's indexing as FAILED with error diagnostic message."""
        now = time.time()
        with self._rw_lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO vector_sync_state (uri, account_id, status, content_hash, retry_count, last_error, created_at, updated_at)
                VALUES (?, ?, 'FAILED', NULL, 1, ?, ?, ?)
                ON CONFLICT(uri) DO UPDATE SET
                    status = 'FAILED',
                    retry_count = vector_sync_state.retry_count + 1,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (uri, account_id, error, now, now),
            )

    def remove(self, uri: str) -> bool:
        """Remove a file's tracking record upon file deletion."""
        with self._rw_lock, self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM vector_sync_state WHERE uri = ?", (uri,))
            return cursor.rowcount > 0

    def get_record(self, uri: str) -> Optional[VectorSyncRecord]:
        """Fetch the tracking record for a given URI."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM vector_sync_state WHERE uri = ?", (uri,)).fetchone()
            if not row:
                return None
            return VectorSyncRecord(
                uri=row["uri"],
                account_id=row["account_id"],
                status=SyncStatus(row["status"]),
                content_hash=row["content_hash"],
                retry_count=row["retry_count"],
                last_error=row["last_error"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def find_unindexed_or_failed(
        self,
        account_id: Optional[str] = None,
        max_age_seconds: float = 300.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Identify records that failed or have been stuck in PENDING beyond timeout threshold."""
        stale_threshold = time.time() - max_age_seconds
        query = """
            SELECT * FROM vector_sync_state
            WHERE (status = 'FAILED' OR (status = 'PENDING' AND updated_at <= ?))
        """
        params: List[Any] = [stale_threshold]
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        query += " ORDER BY updated_at ASC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_metrics(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute objective sync health metrics and percentage."""
        query = "SELECT status, COUNT(*) as cnt FROM vector_sync_state"
        params: List[Any] = []
        if account_id:
            query += " WHERE account_id = ?"
            params.append(account_id)
        query += " GROUP BY status"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            counts = {r["status"]: r["cnt"] for r in rows}
            indexed = counts.get("INDEXED", 0)
            pending = counts.get("PENDING", 0)
            failed = counts.get("FAILED", 0)
            total = indexed + pending + failed

            sync_rate = round((indexed / total * 100.0), 2) if total > 0 else 100.0
            
            fast_path_cnt = 0
            try:
                fp_row = conn.execute("SELECT COUNT(*) as cnt FROM vector_sync_state WHERE fast_path = 1").fetchone()
                if fp_row:
                    fast_path_cnt = int(fp_row["cnt"])
            except Exception:
                fast_path_cnt = self._fast_path_count
            fast_path_cnt = max(fast_path_cnt, self._fast_path_count)

            return {
                "total_files": total,
                "indexed_count": indexed,
                "pending_count": pending,
                "failed_count": failed,
                "fast_path_count": fast_path_cnt,
                "sync_rate_pct": sync_rate,
            }
