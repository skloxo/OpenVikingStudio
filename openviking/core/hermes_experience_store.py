# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Hermes 经历与能力解耦存储引擎 (Experience vs Capability Decoupling Store).

核心物理公理:
  1. 经历 (Experience) 与能力 (Capability) 严格物理分层:
     - 经历 (SessionDB): 包含原始交互回合、消息、执行动作，只增不删 (Append-Only)
     - 能力 (Capability): 从经历中提纯出的规则、工具模式与微补丁，版本化演进
  2. 跨会话 FTS5 真实消息检索:
     - SQLite 原生 FTS5 虚拟表，拒绝虚假 LLM 摘要
     - 毫秒级支持精准词条匹配与上下文提取

(Card-Evolve-HermesEvolveLoop-Patch v1.5.39)
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class HermesExperienceMessage(BaseModel):
    """单条原始交互经历记录。"""
    msg_id: str = Field(default_factory=lambda: f"hmsg-{uuid.uuid4().hex[:10]}")
    session_id: str
    role: str                       # "user" | "assistant" | "tool" | "system"
    content: str
    tool_calls: Optional[str] = None # JSON 字符串
    created_at: float = Field(default_factory=time.time)
    meta: Dict[str, Any] = Field(default_factory=dict)


class FTS5SearchResult(BaseModel):
    """跨会话 FTS5 真实检索命中项。"""
    msg_id: str
    session_id: str
    role: str
    snippet: str
    created_at: float
    rank: float


# ---------------------------------------------------------------------------
# 经历存储 (SQLite + FTS5)
# ---------------------------------------------------------------------------

class HermesExperienceStore:
    """线程安全的经历与能力解耦存储。单例模式。"""

    _instance: Optional["HermesExperienceStore"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            base_dir = Path(os.path.expanduser("~/.openviking/data/viking/default"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "hermes_experiences.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "HermesExperienceStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """初始化经历明细表与 FTS5 倒排索引虚拟表。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                # 1. 原始经历明细表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS hermes_messages (
                        msg_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tool_calls TEXT,
                        created_at REAL NOT NULL,
                        meta_json TEXT
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_hermes_session ON hermes_messages(session_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_hermes_created ON hermes_messages(created_at);")

                # 2. FTS5 全文检索虚拟表
                cur.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_hermes_messages USING fts5(
                        msg_id UNINDEXED,
                        session_id UNINDEXED,
                        role UNINDEXED,
                        content,
                        tokenize = 'unicode61'
                    );
                """)
                conn.commit()
            finally:
                conn.close()

    def record_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[Any] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> HermesExperienceMessage:
        """写入单条真实经历消息（只增不删）。"""
        msg = HermesExperienceMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            meta=meta or {},
        )
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO hermes_messages (msg_id, session_id, role, content, tool_calls, created_at, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        msg.msg_id,
                        msg.session_id,
                        msg.role,
                        msg.content,
                        msg.tool_calls,
                        msg.created_at,
                        json.dumps(msg.meta, ensure_ascii=False),
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO fts_hermes_messages (msg_id, session_id, role, content)
                    VALUES (?, ?, ?, ?);
                    """,
                    (msg.msg_id, msg.session_id, msg.role, msg.content),
                )
                conn.commit()
            finally:
                conn.close()
        return msg

    def search_messages(self, query: str, limit: int = 20) -> List[FTS5SearchResult]:
        """跨会话 FTS5 真实消息检索。"""
        clean_query = query.strip().replace("'", "''").replace('"', '""')
        if not clean_query:
            return []

        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                sql = """
                    SELECT f.msg_id, f.session_id, f.role, snippet(fts_hermes_messages, 3, '<b>', '</b>', '...', 16), m.created_at, rank
                    FROM fts_hermes_messages f
                    JOIN hermes_messages m ON f.msg_id = m.msg_id
                    WHERE fts_hermes_messages MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                """
                cur.execute(sql, (clean_query, limit))
                rows = cur.fetchall()
                results: List[FTS5SearchResult] = []
                for r in rows:
                    results.append(
                        FTS5SearchResult(
                            msg_id=r[0],
                            session_id=r[1],
                            role=r[2],
                            snippet=r[3],
                            created_at=r[4],
                            rank=float(r[5]),
                        )
                    )
                return results
            except sqlite3.OperationalError:
                # 若查询包含非法 FTS 语法，回退为精确短语查询
                cur = conn.cursor()
                sql_fallback = """
                    SELECT f.msg_id, f.session_id, f.role, snippet(fts_hermes_messages, 3, '<b>', '</b>', '...', 16), m.created_at, rank
                    FROM fts_hermes_messages f
                    JOIN hermes_messages m ON f.msg_id = m.msg_id
                    WHERE fts_hermes_messages MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                """
                escaped = f'"{clean_query}"'
                cur.execute(sql_fallback, (escaped, limit))
                rows = cur.fetchall()
                return [
                    FTS5SearchResult(
                        msg_id=r[0],
                        session_id=r[1],
                        role=r[2],
                        snippet=r[3],
                        created_at=r[4],
                        rank=float(r[5]),
                    )
                    for r in rows
                ]
            finally:
                conn.close()

    def get_messages_by_session(self, session_id: str) -> List[HermesExperienceMessage]:
        """按会话 ID 查询所有原始经历回合。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT msg_id, session_id, role, content, tool_calls, created_at, meta_json
                    FROM hermes_messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC;
                    """,
                    (session_id,),
                )
                rows = cur.fetchall()
                return [
                    HermesExperienceMessage(
                        msg_id=r[0],
                        session_id=r[1],
                        role=r[2],
                        content=r[3],
                        tool_calls=r[4],
                        created_at=r[5],
                        meta=json.loads(r[6]) if r[6] else {},
                    )
                    for r in rows
                ]
            finally:
                conn.close()

    def stats(self) -> Dict[str, Any]:
        """获取经历存储全局统计。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*), COUNT(DISTINCT session_id) FROM hermes_messages;")
                total_messages, total_sessions = cur.fetchone()
                return {
                    "total_messages": total_messages or 0,
                    "total_sessions": total_sessions or 0,
                    "db_path": str(self.db_path),
                }
            finally:
                conn.close()
