# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Universal Audit Ledger (Card-190 SSOT).

A thread-safe, high-concurrency SQLite SSOT for immutable audit events across OpenViking.
Unifies:
1. Skill Blackbox Provenance events.
2. Unified Lifecycle FSM transitions.
3. Guardrails & Circuit Breaker intervention events.
4. Memory & Entity snapshot references.

Features:
- SQLite WAL mode for non-blocking concurrent reads and serialized fast writes.
- Index-optimized timeline queries by (entity_type, entity_id, created_at).
- Automatic correlation with UnifiedLifecycleEngine events.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_AUDIT_DB_PATH = Path.home() / ".openviking" / "data" / "audit_ledger.db"


class AuditEvent(BaseModel):
    """Immutable audit event entry."""
    event_id: str
    entity_type: str
    entity_id: str
    action: str
    operator: str = "system"
    status: str = "SUCCESS"
    details: Dict[str, Any] = Field(default_factory=dict)
    snapshot_path: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class UniversalAuditLedger:
    """Thread-safe SQLite audit ledger SSOT."""

    _instance: Optional[UniversalAuditLedger] = None
    _singleton_lock = threading.Lock()

    def __init__(self, db_path: Optional[Path | str] = None):
        self._db_path = Path(db_path) if db_path else DEFAULT_AUDIT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path | str] = None) -> "UniversalAuditLedger":
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(db_path=db_path)
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS universal_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    snapshot_path TEXT,
                    created_at REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_entity
                ON universal_audit_events (entity_type, entity_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_action
                ON universal_audit_events (action);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_created
                ON universal_audit_events (created_at DESC);
            """)
            conn.commit()

    def record_event(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        operator: str = "system",
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        snapshot_path: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> AuditEvent:
        """Atomically append an immutable audit record."""
        eid = event_id or f"evt_{uuid.uuid4().hex[:12]}"
        now = time.time()
        d_map = details or {}
        details_json = json.dumps(d_map, ensure_ascii=False)

        event = AuditEvent(
            event_id=eid,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            operator=operator,
            status=status,
            details=d_map,
            snapshot_path=snapshot_path,
            created_at=now,
        )

        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO universal_audit_events (
                    event_id, entity_type, entity_id, action, operator, status,
                    details_json, snapshot_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    entity_type,
                    entity_id,
                    action,
                    operator,
                    status,
                    details_json,
                    snapshot_path,
                    now,
                ),
            )
            conn.commit()

        return event

    def get_timeline(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """Query timeline events with optional multi-axis filtering."""
        query = "SELECT * FROM universal_audit_events WHERE 1=1"
        params: List[Any] = []

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        if action:
            query += " AND action = ?"
            params.append(action)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        results: List[AuditEvent] = []
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                try:
                    d_parsed = json.loads(r["details_json"])
                except Exception:
                    d_parsed = {}

                results.append(
                    AuditEvent(
                        event_id=r["event_id"],
                        entity_type=r["entity_type"],
                        entity_id=r["entity_id"],
                        action=r["action"],
                        operator=r["operator"],
                        status=r["status"],
                        details=d_parsed,
                        snapshot_path=r["snapshot_path"],
                        created_at=r["created_at"],
                    )
                )

        return results

    def count_events(self, entity_type: Optional[str] = None, action: Optional[str] = None) -> int:
        """Count events matching criteria."""
        query = "SELECT COUNT(*) FROM universal_audit_events WHERE 1=1"
        params: List[Any] = []

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if action:
            query += " AND action = ?"
            params.append(action)

        with self._lock, self._get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return row[0] if row else 0

    def prune_older_than(self, days: int = 90) -> int:
        """Prune audit records older than specified retention horizon."""
        cutoff = time.time() - (days * 86400)
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM universal_audit_events WHERE created_at < ?", (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted
