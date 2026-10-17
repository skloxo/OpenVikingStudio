# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VikingFS Skill Ingestion SQLite Staging Store (Card-95).

核心物理公理:
  1. 毫秒级写入响应: 前台接收请求后立即存入 SQLite `skill_ingestion_inbox` 暂存表 (< 50ms)；
  2. 原子性认领流转: 基于 SQLite 事务性单写原子认领，防止多 Worker 并发争抢与脑裂；
  3. 状态机严格单调: PENDING ➔ VALIDATING ➔ STAGED / REJECTED ➔ COMMITTED。
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    """技能准入状态机枚举。"""
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    STAGED = "STAGED"
    REJECTED = "REJECTED"
    COMMITTED = "COMMITTED"
    ERROR = "ERROR"


class IngestionRecord(BaseModel):
    """准入收件箱暂存条目。"""
    receipt_id: str
    skill_name: str
    raw_content: str
    author: str = "anonymous"
    status: IngestionStatus = IngestionStatus.PENDING
    status_message: str = ""
    validation_report: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class SkillIngestionStore:
    """技能准入收件箱暂存存储 (SQLite + WAL)."""

    _instance: Optional[SkillIngestionStore] = None
    _singleton_lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path.home() / ".openviking" / "data" / "viking" / "default"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "skill_ingestion_inbox.db"
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> SkillIngestionStore:
        """双检锁单例。"""
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_ingestion_inbox (
                    receipt_id TEXT PRIMARY KEY,
                    skill_name TEXT NOT NULL,
                    raw_content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_message TEXT DEFAULT '',
                    validation_report TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inbox_status ON skill_ingestion_inbox(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inbox_created ON skill_ingestion_inbox(created_at);")

    def enqueue_skill(self, skill_name: str, raw_content: str, author: str = "anonymous") -> IngestionRecord:
        """毫秒级写入暂存队列，立即返回回执。"""
        now = time.time()
        receipt_id = f"ingest_{uuid.uuid4().hex[:12]}"
        record = IngestionRecord(
            receipt_id=receipt_id,
            skill_name=skill_name,
            raw_content=raw_content,
            author=author,
            status=IngestionStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO skill_ingestion_inbox
                (receipt_id, skill_name, raw_content, author, status, status_message, validation_report, retry_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.receipt_id,
                    record.skill_name,
                    record.raw_content,
                    record.author,
                    record.status.value,
                    record.status_message,
                    None,
                    record.retry_count,
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def get_record(self, receipt_id: str) -> Optional[IngestionRecord]:
        """根据 receipt_id 获取单条暂存记录。"""
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT * FROM skill_ingestion_inbox WHERE receipt_id = ?", (receipt_id,)).fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def fetch_and_claim_pending(self, batch_size: int = 1) -> List[IngestionRecord]:
        """原子认领待处理任务，防止多 Worker 争抢脑裂。"""
        now = time.time()
        claimed: List[IngestionRecord] = []
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT receipt_id FROM skill_ingestion_inbox WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (IngestionStatus.PENDING.value, batch_size),
            )
            rows = cursor.fetchall()
            if not rows:
                return []

            ids = [r["receipt_id"] for r in rows]
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE skill_ingestion_inbox SET status = ?, updated_at = ? WHERE receipt_id IN ({placeholders})",
                [IngestionStatus.VALIDATING.value, now] + ids,
            )

            # Retrieve full records after claim
            cursor_full = conn.execute(
                f"SELECT * FROM skill_ingestion_inbox WHERE receipt_id IN ({placeholders})",
                ids,
            )
            for r in cursor_full.fetchall():
                claimed.append(self._row_to_record(r))
        return claimed

    def update_status(
        self,
        receipt_id: str,
        status: IngestionStatus,
        status_message: str = "",
        validation_report: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新处理状态与验证报告。"""
        now = time.time()
        report_json = json.dumps(validation_report, ensure_ascii=False) if validation_report else None
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE skill_ingestion_inbox
                SET status = ?, status_message = ?, validation_report = ?, updated_at = ?
                WHERE receipt_id = ?
                """,
                (status.value, status_message, report_json, now, receipt_id),
            )
            return cursor.rowcount > 0

    def list_records(self, status: Optional[IngestionStatus] = None, limit: int = 50) -> List[IngestionRecord]:
        """查询列表。"""
        with self._lock, self._get_connection() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM skill_ingestion_inbox WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM skill_ingestion_inbox ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_record(r) for r in cursor.fetchall()]

    def get_queue_depth(self) -> Dict[str, int]:
        """获取各状态积压与总深度度量。"""
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("SELECT status, COUNT(*) as cnt FROM skill_ingestion_inbox GROUP BY status")
            counts = {r["status"].lower(): r["cnt"] for r in cursor.fetchall()}
            total = sum(counts.values())
            return {
                "total": total,
                "pending": counts.get("pending", 0),
                "validating": counts.get("validating", 0),
                "staged": counts.get("staged", 0),
                "rejected": counts.get("rejected", 0),
                "committed": counts.get("committed", 0),
                "error": counts.get("error", 0),
            }

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> IngestionRecord:
        report_raw = row["validation_report"]
        report = json.loads(report_raw) if report_raw else None
        return IngestionRecord(
            receipt_id=row["receipt_id"],
            skill_name=row["skill_name"],
            raw_content=row["raw_content"],
            author=row["author"],
            status=IngestionStatus(row["status"]),
            status_message=row["status_message"],
            validation_report=report,
            retry_count=row["retry_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
