# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Dead Letter Queue (DLQ) Manager for QueueFS.

First Principles:
Zero Silent Loss: When queue handlers encounter permanent errors, dimensional
mismatches, or payload issues, the message MUST NOT vanish into thin air.
Instead, it is atomically preserved in the DLQ before ACK, making memory absorption
100% auditable, traceable, and recoverable.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("openviking.storage.queuefs.dlq_manager")


class DeadLetterRecord(BaseModel):
    """Strongly typed DTO representing an unprocessable queue message."""
    id: Optional[int] = None
    queue_name: str
    msg_id: Optional[str] = None
    uri: Optional[str] = None
    account_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    resolved: int = 0  # 0: pending, 1: resolved, 2: retried
    resolution_note: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DLQManager:
    """Thread-safe SQLite persistent manager for QueueFS Dead Letter Queue."""

    _instance: Optional[DLQManager] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            data_dir = os.path.expanduser("~/.openviking/data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "queue_dead_letters.db")
        self.db_path = db_path
        self._rw_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> DLQManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue_dead_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_name TEXT NOT NULL,
                    msg_id TEXT,
                    uri TEXT,
                    account_id TEXT,
                    payload TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    retry_count INTEGER DEFAULT 0,
                    resolved INTEGER DEFAULT 0,
                    resolution_note TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_status ON queue_dead_letters(resolved);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_queue ON queue_dead_letters(queue_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_uri ON queue_dead_letters(uri);")

    def record_dead_letter(
        self,
        queue_name: str,
        msg_id: Optional[str],
        payload: Dict[str, Any],
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        uri: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> int:
        """Atomically record an unprocessable queue message to DLQ."""
        now = time.time()
        payload_json = json.dumps(payload, ensure_ascii=False)
        with self._rw_lock, self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO queue_dead_letters (
                    queue_name, msg_id, uri, account_id, payload,
                    error_type, error_message, stack_trace,
                    retry_count, resolved, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
                """,
                (queue_name, msg_id, uri, account_id, payload_json, error_type, error_message, stack_trace, now, now),
            )
            dlq_id = cursor.lastrowid
            logger.warning(
                f"[DLQ] Recorded dead letter #{dlq_id} for queue '{queue_name}' "
                f"(uri={uri}, err={error_type}: {error_message[:120]})"
            )
            return int(dlq_id or 0)

    def list_dead_letters(
        self,
        queue_name: Optional[str] = None,
        resolved: Optional[int] = None,
        error_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List dead letter records matching the query criteria."""
        query = "SELECT * FROM queue_dead_letters WHERE 1=1"
        params: List[Any] = []
        if queue_name:
            query += " AND queue_name = ?"
            params.append(queue_name)
        if resolved is not None:
            query += " AND resolved = ?"
            params.append(resolved)
        if error_type:
            query += " AND error_type = ?"
            params.append(error_type)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                try:
                    item["payload"] = json.loads(item["payload"])
                except Exception:
                    pass
                results.append(item)
            return results

    def get_dead_letter(self, dlq_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single dead letter by its ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM queue_dead_letters WHERE id = ?", (dlq_id,)).fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["payload"] = json.loads(item["payload"])
            except Exception:
                pass
            return item

    def resolve_dead_letter(self, dlq_id: int, resolution_note: Optional[str] = None, resolved_status: int = 1) -> bool:
        """Mark a dead letter as resolved or retried."""
        now = time.time()
        with self._rw_lock, self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE queue_dead_letters
                SET resolved = ?, resolution_note = ?, updated_at = ?
                WHERE id = ?
                """,
                (resolved_status, resolution_note, now, dlq_id),
            )
            return cursor.rowcount > 0

    def increment_retry(self, dlq_id: int) -> bool:
        """Increment retry count on a dead letter."""
        now = time.time()
        with self._rw_lock, self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE queue_dead_letters
                SET retry_count = retry_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (now, dlq_id),
            )
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate DLQ statistics for health dashboards."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM queue_dead_letters").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM queue_dead_letters WHERE resolved = 0").fetchone()[0]
            resolved = conn.execute("SELECT COUNT(*) FROM queue_dead_letters WHERE resolved != 0").fetchone()[0]

            type_rows = conn.execute(
                "SELECT error_type, COUNT(*) as cnt FROM queue_dead_letters WHERE resolved = 0 GROUP BY error_type"
            ).fetchall()
            by_type = {row["error_type"]: row["cnt"] for row in type_rows}

            return {
                "total_count": total,
                "pending_count": pending,
                "resolved_count": resolved,
                "by_error_type": by_type,
            }
