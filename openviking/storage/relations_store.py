# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VikingFS Relations SQLite 物理持久化存储引擎 (RelationStore SSOT).

核心物理公理:
  1. 真实实体关联持久化: 拒绝内存虚无或空实现，所有显式 (from_uri, to_uri, reason, link_type)
     关系统一收口落地至 SQLite relations.db，保障跨进程、跨重启 100% 数据一致。
  2. 纯粹有向图索引: 支持基于出度 (Outbound) 与入度 (Inbound) 的亚毫秒级检索。
  3. 线程安全单例与 WAL 模式: 高并发读写零锁死。

(Card-20F: Card-Graph-RealTopology-DynamicWiring v1.5.82)
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RelationItem(BaseModel):
    """单条显式实体关联记录。"""
    from_uri: str
    to_uri: str
    reason: str = ""
    link_type: str = "related_to"
    weight: float = 1.0
    created_at: float = Field(default_factory=time.time)


class RelationStore:
    """线程安全的 Viking URI 实体关系 SQLite 存储。单例模式。"""

    _instance: Optional[RelationStore] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path.home() / ".openviking" / "data" / "viking" / "default"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "relations.db"
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_path = db_path
        self._db_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> RelationStore:
        """双检锁单例获取。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（用于单元测试隔离）。"""
        with cls._lock:
            cls._instance = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._db_lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_uri TEXT NOT NULL,
                    to_uri TEXT NOT NULL,
                    reason TEXT DEFAULT '',
                    link_type TEXT DEFAULT 'related_to',
                    weight REAL DEFAULT 1.0,
                    created_at REAL NOT NULL,
                    UNIQUE(from_uri, to_uri)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_uri);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_uri);")
            conn.commit()

    def add_link(
        self,
        from_uri: str,
        to_uri: str,
        reason: str = "",
        link_type: str = "related_to",
        weight: float = 1.0,
    ) -> RelationItem:
        """创建或更新单条显式关联。"""
        item = RelationItem(
            from_uri=from_uri,
            to_uri=to_uri,
            reason=reason or "",
            link_type=link_type or "related_to",
            weight=weight,
            created_at=time.time(),
        )
        with self._db_lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO relations (from_uri, to_uri, reason, link_type, weight, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(from_uri, to_uri) DO UPDATE SET
                    reason = excluded.reason,
                    link_type = excluded.link_type,
                    weight = excluded.weight,
                    created_at = excluded.created_at;
                """,
                (item.from_uri, item.to_uri, item.reason, item.link_type, item.weight, item.created_at),
            )
            conn.commit()
        return item

    def add_links_batch(
        self,
        from_uri: str,
        to_uris: List[str],
        reason: str = "",
        link_type: str = "related_to",
        weight: float = 1.0,
    ) -> List[RelationItem]:
        """批量建立一对多关联。"""
        now = time.time()
        items = [
            RelationItem(
                from_uri=from_uri,
                to_uri=tu,
                reason=reason or "",
                link_type=link_type or "related_to",
                weight=weight,
                created_at=now,
            )
            for tu in to_uris
            if tu and tu != from_uri
        ]
        if not items:
            return []

        with self._db_lock, self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO relations (from_uri, to_uri, reason, link_type, weight, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(from_uri, to_uri) DO UPDATE SET
                    reason = excluded.reason,
                    link_type = excluded.link_type,
                    weight = excluded.weight,
                    created_at = excluded.created_at;
                """,
                [(m.from_uri, m.to_uri, m.reason, m.link_type, m.weight, m.created_at) for m in items],
            )
            conn.commit()
        return items

    def remove_link(self, from_uri: str, to_uri: str) -> bool:
        """移除指定的显式关联。"""
        with self._db_lock, self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM relations WHERE from_uri = ? AND to_uri = ?",
                (from_uri, to_uri),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_outbound(self, from_uri: str) -> List[Dict[str, Any]]:
        """获取指定 URI 的所有出边（满足 GET /api/v1/relations 标准契约）。"""
        with self._db_lock, self._get_connection() as conn:
            rows = conn.execute(
                "SELECT to_uri, reason, link_type, weight, created_at FROM relations WHERE from_uri = ? ORDER BY created_at DESC",
                (from_uri,),
            ).fetchall()
            return [
                {
                    "uri": r["to_uri"],
                    "reason": r["reason"],
                    "link_type": r["link_type"],
                    "weight": r["weight"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_inbound(self, to_uri: str) -> List[Dict[str, Any]]:
        """获取指定 URI 的所有入边。"""
        with self._db_lock, self._get_connection() as conn:
            rows = conn.execute(
                "SELECT from_uri, reason, link_type, weight, created_at FROM relations WHERE to_uri = ? ORDER BY created_at DESC",
                (to_uri,),
            ).fetchall()
            return [
                {
                    "uri": r["from_uri"],
                    "reason": r["reason"],
                    "link_type": r["link_type"],
                    "weight": r["weight"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def list_all_links(self, limit: int = 500) -> List[RelationItem]:
        """全量查询系统内的显式关联关系。"""
        with self._db_lock, self._get_connection() as conn:
            rows = conn.execute(
                "SELECT from_uri, to_uri, reason, link_type, weight, created_at FROM relations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                RelationItem(
                    from_uri=r["from_uri"],
                    to_uri=r["to_uri"],
                    reason=r["reason"],
                    link_type=r["link_type"],
                    weight=r["weight"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def count_links(self) -> int:
        """统计关联总数。"""
        with self._db_lock, self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM relations").fetchone()
            return int(row["cnt"]) if row else 0
