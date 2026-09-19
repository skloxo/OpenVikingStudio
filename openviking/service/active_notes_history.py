# -*- coding: utf-8 -*-
"""Codex-grade Active Notes and History Dual-Repository Context Governance.

Eliminates lossy global compaction summaries. Decouples active high-density
state (Active Notes) from lossless historical dialogue stream (History Repository).

Single File Size: strictly within 100~300 lines sweet spot.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActiveNotes:
    session_id: str
    active_goal: str = ""
    working_constraints: List[str] = field(default_factory=list)
    current_state: str = ""
    discovered_facts: List[str] = field(default_factory=list)
    version: int = 1
    updated_at: float = field(default_factory=time.time)

    def estimate_tokens(self) -> int:
        raw_text = f"{self.active_goal} {' '.join(self.working_constraints)} {self.current_state} {' '.join(self.discovered_facts)}"
        return max(10, len(raw_text) // 3)


@dataclass
class HistoryMessage:
    message_id: str
    session_id: str
    turn_index: int
    role: str
    content: str
    tool_calls: Optional[str] = None
    token_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class HistorySearchResult:
    message_id: str
    turn_index: int
    role: str
    content: str
    score: float
    created_at: float


class ActiveNotesHistoryManager:
    _instance: Optional[ActiveNotesHistoryManager] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = os.path.expanduser("~/.openviking/data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "active_notes_history.db")
        self.db_path = db_path
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> ActiveNotesHistoryManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_notes (
                    session_id TEXT PRIMARY KEY,
                    active_goal TEXT NOT NULL,
                    working_constraints TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    discovered_facts TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    token_count INTEGER NOT NULL,
                    created_at REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_sess ON history_messages(session_id, turn_index);")
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS history_messages_fts USING fts5(
                    message_id,
                    content,
                    tokenize='unicode61'
                );
            """)

    def get_or_create_notes(self, session_id: str) -> ActiveNotes:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT active_goal, working_constraints, current_state, discovered_facts, version, updated_at "
                "FROM active_notes WHERE session_id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if row:
                return ActiveNotes(
                    session_id=session_id,
                    active_goal=row[0],
                    working_constraints=json.loads(row[1]),
                    current_state=row[2],
                    discovered_facts=json.loads(row[3]),
                    version=row[4],
                    updated_at=row[5],
                )
            notes = ActiveNotes(session_id=session_id)
            conn.execute(
                "INSERT INTO active_notes (session_id, active_goal, working_constraints, current_state, discovered_facts, version, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    notes.active_goal,
                    json.dumps(notes.working_constraints, ensure_ascii=False),
                    notes.current_state,
                    json.dumps(notes.discovered_facts, ensure_ascii=False),
                    notes.version,
                    notes.updated_at,
                ),
            )
            return notes

    def update_notes(
        self,
        session_id: str,
        active_goal: str,
        working_constraints: List[str],
        current_state: str,
        discovered_facts: List[str],
    ) -> ActiveNotes:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT version FROM active_notes WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            current_ver = row[0] if row else 0
            new_version = current_ver + 1
            now = time.time()
            conn.execute(
                "INSERT INTO active_notes (session_id, active_goal, working_constraints, current_state, discovered_facts, version, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "active_goal = excluded.active_goal, "
                "working_constraints = excluded.working_constraints, "
                "current_state = excluded.current_state, "
                "discovered_facts = excluded.discovered_facts, "
                "version = excluded.version, "
                "updated_at = excluded.updated_at",
                (
                    session_id,
                    active_goal,
                    json.dumps(working_constraints, ensure_ascii=False),
                    current_state,
                    json.dumps(discovered_facts, ensure_ascii=False),
                    new_version,
                    now,
                ),
            )
            return ActiveNotes(
                session_id=session_id,
                active_goal=active_goal,
                working_constraints=working_constraints,
                current_state=current_state,
                discovered_facts=discovered_facts,
                version=new_version,
                updated_at=now,
            )

    def append_history(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[str] = None,
    ) -> HistoryMessage:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT COALESCE(MAX(turn_index), 0) FROM history_messages WHERE session_id = ?",
                (session_id,),
            )
            turn_index = cur.fetchone()[0] + 1
            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            token_count = max(1, len(content) // 3)
            now = time.time()

            conn.execute(
                "INSERT INTO history_messages (message_id, session_id, turn_index, role, content, tool_calls, token_count, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (msg_id, session_id, turn_index, role, content, tool_calls, token_count, now),
            )
            # Insert into FTS5
            conn.execute(
                "INSERT INTO history_messages_fts (message_id, content) VALUES (?, ?)",
                (msg_id, content),
            )

            return HistoryMessage(
                message_id=msg_id,
                session_id=session_id,
                turn_index=turn_index,
                role=role,
                content=content,
                tool_calls=tool_calls,
                token_count=token_count,
                created_at=now,
            )

    def list_history_windows(
        self,
        session_id: str,
        offset: int = 0,
        limit: int = 20,
        order: str = "asc",
    ) -> List[HistoryMessage]:
        direction = "DESC" if order.lower() == "desc" else "ASC"
        with self._get_connection() as conn:
            cur = conn.execute(
                f"SELECT message_id, session_id, turn_index, role, content, tool_calls, token_count, created_at "
                f"FROM history_messages WHERE session_id = ? ORDER BY turn_index {direction} LIMIT ? OFFSET ?",
                (session_id, limit, offset),
            )
            return [
                HistoryMessage(
                    message_id=r[0],
                    session_id=r[1],
                    turn_index=r[2],
                    role=r[3],
                    content=r[4],
                    tool_calls=r[5],
                    token_count=r[6],
                    created_at=r[7],
                )
                for r in cur.fetchall()
            ]

    def search_history(
        self,
        session_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[HistorySearchResult]:
        cleaned_query = "".join(c if c.isalnum() or c in ("_", "-") else " " for c in query).strip()
        with self._get_connection() as conn:
            # First try FTS5 match
            if cleaned_query:
                try:
                    fts_cur = conn.execute(
                        "SELECT fts.message_id, hm.turn_index, hm.role, hm.content, bm25(history_messages_fts) as rank, hm.created_at "
                        "FROM history_messages_fts fts "
                        "JOIN history_messages hm ON fts.message_id = hm.message_id "
                        "WHERE hm.session_id = ? AND history_messages_fts MATCH ? "
                        "ORDER BY rank ASC LIMIT ?",
                        (session_id, cleaned_query, top_k),
                    )
                    rows = fts_cur.fetchall()
                    if rows:
                        return [
                            HistorySearchResult(
                                message_id=r[0],
                                turn_index=r[1],
                                role=r[2],
                                content=r[3],
                                score=round(abs(r[4]), 4),
                                created_at=r[5],
                            )
                            for r in rows
                        ]
                except sqlite3.OperationalError:
                    pass

            # Fallback to precise LIKE substring match
            like_cur = conn.execute(
                "SELECT message_id, turn_index, role, content, 1.0 as score, created_at "
                "FROM history_messages WHERE session_id = ? AND content LIKE ? "
                "ORDER BY turn_index DESC LIMIT ?",
                (session_id, f"%{query}%", top_k),
            )
            return [
                HistorySearchResult(
                    message_id=r[0],
                    turn_index=r[1],
                    role=r[2],
                    content=r[3],
                    score=1.0,
                    created_at=r[5],
                )
                for r in like_cur.fetchall()
            ]

    def get_stats(self, session_id: str) -> Dict[str, Any]:
        notes = self.get_or_create_notes(session_id)
        notes_tokens = notes.estimate_tokens()
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(token_count), 0) FROM history_messages WHERE session_id = ?",
                (session_id,),
            )
            count, total_hist_tokens = cur.fetchone()

        saving_ratio = (
            max(0.0, 1.0 - (notes_tokens / max(1, total_hist_tokens)))
            if total_hist_tokens > notes_tokens
            else 0.0
        )

        return {
            "session_id": session_id,
            "notes_version": notes.version,
            "notes_tokens": notes_tokens,
            "history_count": count,
            "history_total_tokens": total_hist_tokens,
            "token_saving_ratio": round(saving_ratio, 4),
            "fidelity_rate": 1.0,  # History remains 100% uncompressed and unperturbed
            "active_goal": notes.active_goal,
            "constraints_count": len(notes.working_constraints),
            "facts_count": len(notes.discovered_facts),
        }
