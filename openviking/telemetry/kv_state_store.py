# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Lightweight SQLite KV persistence helper for runtime telemetry & pipeline state."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
_KV_LOCK = threading.Lock()


def resolve_default_kv_db_path() -> Path:
    """Resolve the active TelemetryStore SQLite path (respecting OPENVIKING_TELEMETRY_DB)."""
    from openviking.telemetry.telemetry_store import TelemetryStore

    return TelemetryStore._resolve_db_path()


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_telemetry_kv (
            namespace TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        """
    )


def load_kv_state(namespace: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load persisted JSON dict for namespace from SQLite; returns {} if absent."""
    target = Path(db_path) if db_path is not None else resolve_default_kv_db_path()
    if not target.exists():
        return {}
    try:
        with _KV_LOCK:
            with sqlite3.connect(str(target), timeout=10.0) as conn:
                _ensure_table(conn)
                row = conn.execute(
                    "SELECT payload_json FROM runtime_telemetry_kv WHERE namespace = ?",
                    (namespace,),
                ).fetchone()
                if not row:
                    return {}
                parsed = json.loads(row[0])
                return parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        logger.warning("Failed loading telemetry KV state for %s: %s", namespace, exc)
        return {}


def save_kv_state(
    namespace: str,
    payload: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> None:
    """Persist JSON dict for namespace into SQLite."""
    target = Path(db_path) if db_path is not None else resolve_default_kv_db_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, ensure_ascii=False)
        with _KV_LOCK:
            with sqlite3.connect(str(target), timeout=10.0) as conn:
                _ensure_table(conn)
                conn.execute(
                    """
                    INSERT INTO runtime_telemetry_kv (namespace, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(namespace) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at;
                    """,
                    (namespace, encoded, time.time()),
                )
                conn.commit()
    except Exception as exc:
        logger.warning("Failed saving telemetry KV state for %s: %s", namespace, exc)


def clear_kv_state(namespace: str, db_path: Optional[Path] = None) -> None:
    """Delete persisted state for namespace (used by test resets)."""
    target = Path(db_path) if db_path is not None else resolve_default_kv_db_path()
    if not target.exists():
        return
    try:
        with _KV_LOCK:
            with sqlite3.connect(str(target), timeout=10.0) as conn:
                _ensure_table(conn)
                conn.execute(
                    "DELETE FROM runtime_telemetry_kv WHERE namespace = ?",
                    (namespace,),
                )
                conn.commit()
    except Exception as exc:
        logger.warning("Failed clearing telemetry KV state for %s: %s", namespace, exc)
