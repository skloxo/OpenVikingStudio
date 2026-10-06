# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Agent Principal Storage Engine (Card-111 / Card-117 SSOT).

First Principles:
1. "Immutable Identity vs Mutable Display Name":
   - `agent_id`: Permanent, immutable, system-generated identity (e.g. ag_a7b9c1d3e5f2).
   - `agent_name`: Human-friendly customizable name, modifiable at any time.
2. "Soft Deletion SSOT":
   - Never physically destroy audit logs. Deletions mark `is_deleted = 1`.
   - Incoming traffic with a deleted agent_id fails fast with 404/401 credential invalid.
3. "Dynamic Tool ACL":
   - Explicit `allowed_tools` JSON list per principal, powering dynamic tools/list and tools/call.
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

logger = logging.getLogger("openviking.storage.agent_principal_store")

DEFAULT_ALLOWED_TOOLS = [
    "find",
    "search",
    "read",
    "record_evolution_lesson",
]


def generate_agent_id() -> str:
    """Generate permanent immutable agent identity (e.g. ag_a7b9c1d3e5f2)."""
    return f"ag_{uuid.uuid4().hex[:12]}"


class AgentPrincipal(BaseModel):
    """Strongly typed DTO representing an authorized agent principal under a user."""
    agent_id: str = Field(..., description="Permanent immutable agent identity e.g. ag_a7b9c1d3e5f2")
    agent_name: str = Field("", description="Customizable display name e.g. 前端结对助手")
    user_id: str = Field("default", description="Owner tenant user ID e.g. default")
    role_desc: str = Field(..., description="Human-readable role description")
    icon: str = Field("terminal", description="Lucide icon name")
    connection_mode: str = Field("realtimeApi", description="realtimeApi | apiClient")
    status: str = Field("active", description="active | suspended | revoked")
    total_messages: int = Field(0, description="Cumulative message count")
    last_seen: float = Field(0.0, description="Unix timestamp of last heartbeat/traffic")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    allowed_tools: List[str] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS),
        description="Granted tool names or ['*']",
    )
    is_deleted: int = Field(0, description="1 if soft deleted, 0 otherwise")
    deleted_at: float = Field(0.0, description="Timestamp of soft deletion")


class AgentPrincipalStore:
    """Thread-safe SQLite persistent store for tenant-scoped Agent Principals."""

    _instance: Optional[AgentPrincipalStore] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is not None:
            self._db_path = db_path
        else:
            self._db_path = Path.home() / ".openviking" / "data" / "agent_principals.db"

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> AgentPrincipalStore:
        """Double-checked locking singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for test isolation)."""
        with cls._lock:
            cls._instance = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite table, migrate schema if needed."""
        with self._db_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_principals (
                        agent_id TEXT PRIMARY KEY,
                        agent_name TEXT NOT NULL DEFAULT '',
                        user_id TEXT NOT NULL,
                        role_desc TEXT NOT NULL,
                        icon TEXT NOT NULL DEFAULT 'terminal',
                        connection_mode TEXT NOT NULL DEFAULT 'apiClient',
                        status TEXT NOT NULL DEFAULT 'active',
                        total_messages INTEGER NOT NULL DEFAULT 0,
                        last_seen REAL NOT NULL DEFAULT 0.0,
                        created_at REAL NOT NULL,
                        allowed_tools TEXT NOT NULL DEFAULT '["find", "search", "read", "record_evolution_lesson"]',
                        is_deleted INTEGER NOT NULL DEFAULT 0,
                        deleted_at REAL NOT NULL DEFAULT 0.0
                    );
                    """
                )
                # Schema migration for existing databases
                columns = [r[1] for r in conn.execute("PRAGMA table_info(agent_principals);").fetchall()]
                if "agent_name" not in columns:
                    conn.execute("ALTER TABLE agent_principals ADD COLUMN agent_name TEXT NOT NULL DEFAULT '';")
                    conn.execute("UPDATE agent_principals SET agent_name = agent_id WHERE agent_name = '';")
                if "allowed_tools" not in columns:
                    conn.execute("ALTER TABLE agent_principals ADD COLUMN allowed_tools TEXT NOT NULL DEFAULT '[\"find\", \"search\", \"read\", \"record_evolution_lesson\"]';")
                if "is_deleted" not in columns:
                    conn.execute("ALTER TABLE agent_principals ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0;")
                if "deleted_at" not in columns:
                    conn.execute("ALTER TABLE agent_principals ADD COLUMN deleted_at REAL NOT NULL DEFAULT 0.0;")

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_agents_user_status
                    ON agent_principals (user_id, status, is_deleted);
                    """
                )
                conn.commit()

    def register_agent(
        self,
        agent_id: Optional[str] = None,
        agent_name: str = "",
        user_id: str = "default",
        role_desc: str = "",
        icon: str = "terminal",
        connection_mode: str = "apiClient",
        allowed_tools: Optional[List[str]] = None,
        total_messages: int = 0,
    ) -> AgentPrincipal:
        """Register a new agent principal or update an existing one."""
        clean_id = (agent_id.strip() if agent_id else generate_agent_id())
        clean_name = agent_name.strip() or clean_id
        tools = allowed_tools if allowed_tools is not None else list(DEFAULT_ALLOWED_TOOLS)
        tools_json = json.dumps(tools, ensure_ascii=False)
        now = time.time()

        with self._db_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_principals (
                        agent_id, agent_name, user_id, role_desc, icon, connection_mode,
                        status, total_messages, last_seen, created_at, allowed_tools,
                        is_deleted, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, 0, 0.0)
                    ON CONFLICT(agent_id) DO UPDATE SET
                        agent_name = excluded.agent_name,
                        user_id = excluded.user_id,
                        role_desc = CASE WHEN excluded.role_desc != '' THEN excluded.role_desc ELSE agent_principals.role_desc END,
                        icon = CASE WHEN excluded.icon != 'terminal' THEN excluded.icon ELSE agent_principals.icon END,
                        connection_mode = excluded.connection_mode,
                        allowed_tools = excluded.allowed_tools,
                        total_messages = CASE WHEN excluded.total_messages > 0 THEN excluded.total_messages ELSE agent_principals.total_messages END,
                        status = 'active',
                        is_deleted = 0,
                        deleted_at = 0.0;
                    """,
                    (clean_id, clean_name, user_id, role_desc, icon, connection_mode, total_messages, now, now, tools_json),
                )
                conn.commit()
        return self.get_agent(clean_id, include_deleted=True)  # type: ignore

    def update_agent(
        self,
        agent_id: str,
        agent_name: Optional[str] = None,
        role_desc: Optional[str] = None,
        connection_mode: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> Optional[AgentPrincipal]:
        """Update mutable fields of an agent (agent_id is strictly immutable)."""
        clean_id = agent_id.strip()
        existing = self.get_agent(clean_id, include_deleted=True)
        if not existing:
            return None

        fields: List[str] = []
        values: List[Any] = []

        if agent_name is not None:
            fields.append("agent_name = ?")
            values.append(agent_name.strip())
        if role_desc is not None:
            fields.append("role_desc = ?")
            values.append(role_desc.strip())
        if connection_mode is not None:
            fields.append("connection_mode = ?")
            values.append(connection_mode.strip())
        if allowed_tools is not None:
            fields.append("allowed_tools = ?")
            values.append(json.dumps(allowed_tools, ensure_ascii=False))
        if status is not None:
            fields.append("status = ?")
            values.append(status.strip())

        if not fields:
            return existing

        values.append(clean_id)
        with self._db_lock:
            with self._get_connection() as conn:
                conn.execute(
                    f"UPDATE agent_principals SET {', '.join(fields)} WHERE agent_id = ?;",
                    values,
                )
                conn.commit()
        return self.get_agent(clean_id, include_deleted=True)

    def get_agent(self, agent_id: str, include_deleted: bool = False) -> Optional[AgentPrincipal]:
        """Fetch an agent principal. Soft-deleted agents return None unless include_deleted=True."""
        with self._db_lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM agent_principals WHERE agent_id = ?;",
                    (agent_id.strip(),),
                ).fetchone()
                if not row:
                    return None
                data = dict(row)
                if not include_deleted and data.get("is_deleted", 0) == 1:
                    return None
                if isinstance(data.get("allowed_tools"), str):
                    try:
                        data["allowed_tools"] = json.loads(data["allowed_tools"])
                    except Exception:
                        data["allowed_tools"] = list(DEFAULT_ALLOWED_TOOLS)
                if not data.get("agent_name"):
                    data["agent_name"] = data["agent_id"]
                return AgentPrincipal(**data)

    def list_agents(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = "active",
        include_deleted: bool = False,
    ) -> List[AgentPrincipal]:
        """List agents filtered by user_id and status (excluding soft-deleted by default)."""
        query = "SELECT * FROM agent_principals WHERE 1=1"
        params: List[Any] = []
        if not include_deleted:
            query += " AND is_deleted = 0"
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY total_messages DESC, last_seen DESC;"

        with self._db_lock:
            with self._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                results: List[AgentPrincipal] = []
                for r in rows:
                    d = dict(r)
                    if isinstance(d.get("allowed_tools"), str):
                        try:
                            d["allowed_tools"] = json.loads(d["allowed_tools"])
                        except Exception:
                            d["allowed_tools"] = list(DEFAULT_ALLOWED_TOOLS)
                    if not d.get("agent_name"):
                        d["agent_name"] = d["agent_id"]
                    results.append(AgentPrincipal(**d))
                return results

    def soft_delete_agent(self, agent_id: str) -> bool:
        """Soft delete an agent principal. Preserves record, marks is_deleted=1, status='revoked'."""
        clean_id = agent_id.strip()
        now = time.time()
        with self._db_lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "UPDATE agent_principals SET is_deleted = 1, deleted_at = ?, status = 'revoked' WHERE agent_id = ?;",
                    (now, clean_id),
                )
                conn.commit()
                return cur.rowcount > 0

    def restore_agent(self, agent_id: str) -> bool:
        """Restore a soft-deleted agent."""
        clean_id = agent_id.strip()
        with self._db_lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "UPDATE agent_principals SET is_deleted = 0, deleted_at = 0.0, status = 'active' WHERE agent_id = ?;",
                    (clean_id),
                )
                conn.commit()
                return cur.rowcount > 0

    def count_active_agents_by_user(self) -> Dict[str, int]:
        """Return map of {user_id: active_agent_count} in O(1) indexed query."""
        with self._db_lock:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT user_id, COUNT(*) as cnt FROM agent_principals WHERE is_deleted = 0 GROUP BY user_id;"
                ).fetchall()
                return {r["user_id"]: int(r["cnt"]) for r in rows}

    def record_activity(
        self,
        agent_id: str,
        user_id: str = "default",
        increment: int = 1,
    ) -> None:
        """Increment message count and update last_seen timestamp in O(1)."""
        clean_id = agent_id.strip()
        now = time.time()
        with self._db_lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    UPDATE agent_principals
                    SET total_messages = total_messages + ?,
                        last_seen = ?,
                        status = 'active'
                    WHERE agent_id = ? AND is_deleted = 0;
                    """,
                    (increment, now, clean_id),
                )
                if cur.rowcount == 0:
                    existing = conn.execute("SELECT is_deleted FROM agent_principals WHERE agent_id = ?;", (clean_id,)).fetchone()
                    if existing and existing["is_deleted"] == 1:
                        # Do not resurrect soft deleted agents via activity
                        return
                    tools_json = json.dumps(DEFAULT_ALLOWED_TOOLS, ensure_ascii=False)
                    conn.execute(
                        """
                        INSERT INTO agent_principals (
                            agent_id, agent_name, user_id, role_desc, icon, connection_mode,
                            status, total_messages, last_seen, created_at, allowed_tools,
                            is_deleted, deleted_at
                        ) VALUES (?, ?, ?, ?, 'terminal', 'apiClient', 'active', ?, ?, ?, ?, 0, 0.0);
                        """,
                        (clean_id, clean_id, user_id, f"Agent {clean_id}", increment, now, now, tools_json),
                    )
                conn.commit()
