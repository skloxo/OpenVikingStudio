# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Search Key Usage Accounting & 45-Day Rolling Pruning Store.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-SEARCH-ACCOUNTING

First Principles:
1. "Zero Memory/Disk Explosion": Raw usage logs older than 45 days are strictly rolled up
   into daily aggregated summaries and physically deleted.
2. "Authoritative Credit Tracking": Records physical credits returned by official APIs.
3. "Strict Singleton & Thread-Safe SQLite": Double-checked locking prevents connection leaks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from openviking_cli.utils import get_logger

logger = get_logger(__name__)


class SearchAccountingStore:
    """线程安全的网络搜索调用流水账与 45 天滚动归档存储 (单例模式)。"""

    _instance: Optional[SearchAccountingStore] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            data_dir = Path.home() / ".openviking" / "data" / "search"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "search_accounting.db"
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_path = db_path
        self._db_lock = threading.Lock()
        self._last_prune_ts = time.monotonic()
        self._prune_interval_sec = 3600.0  # 每 1 小时最多触发一次自动滚动清理
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> SearchAccountingStore:
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
        conn = sqlite3.connect(str(self._db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """初始化表结构与高频查询索引。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                # 1. search_key_usage: 45 天以内的单次物理流水明细
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS search_key_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key_fingerprint TEXT NOT NULL,
                        engine TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        status_code INTEGER NOT NULL,
                        credits_cost REAL NOT NULL DEFAULT 0.0,
                        latency_ms REAL NOT NULL DEFAULT 0.0,
                        error_msg TEXT DEFAULT '',
                        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_usage_key_time "
                    "ON search_key_usage(key_fingerprint, created_at);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_usage_created_at "
                    "ON search_key_usage(created_at);"
                )

                # 2. search_key_daily_summary: 45 天以前（以及历史归档）的日度统计汇总表
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS search_key_daily_summary (
                        date TEXT NOT NULL,
                        key_fingerprint TEXT NOT NULL,
                        engine TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        total_calls INTEGER NOT NULL DEFAULT 0,
                        success_calls INTEGER NOT NULL DEFAULT 0,
                        error_calls INTEGER NOT NULL DEFAULT 0,
                        rate_limit_calls INTEGER NOT NULL DEFAULT 0,
                        total_credits REAL NOT NULL DEFAULT 0.0,
                        avg_latency_ms REAL NOT NULL DEFAULT 0.0,
                        PRIMARY KEY (date, key_fingerprint, engine, tool_name)
                    );
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def record_usage(
        self,
        key_fingerprint: str,
        engine: str,
        tool_name: str,
        status_code: int,
        credits_cost: float,
        latency_ms: float,
        error_msg: str = "",
        created_at: Optional[str] = None,
    ) -> int:
        """记录一条搜索 Key 调用物理流水账，并在必要时触发 45 天自动滚动归档清理。"""
        now_str = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO search_key_usage (
                        key_fingerprint, engine, tool_name, status_code,
                        credits_cost, latency_ms, error_msg, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key_fingerprint,
                        engine,
                        tool_name,
                        status_code,
                        float(credits_cost),
                        float(latency_ms),
                        error_msg[:500],
                        now_str,
                    ),
                )
                row_id = cursor.lastrowid
                conn.commit()
            finally:
                conn.close()

        # 节流自动触发 45 天滚动清理
        self._maybe_auto_prune()
        return row_id or 0

    def _maybe_auto_prune(self) -> None:
        now = time.monotonic()
        if now - self._last_prune_ts > self._prune_interval_sec:
            self._last_prune_ts = now
            try:
                self.rollup_and_prune_older_than(retention_days=45)
            except Exception as exc:
                logger.warning("Search accounting auto-prune failed: %s", exc)

    def rollup_and_prune_older_than(self, retention_days: int = 45) -> Dict[str, Any]:
        """将超过 retention_days 的明细数据增量归档至日统计表，并物理删除过期明细。

        物理契约：
        1. 聚合 `<= datetime('now', '-45 days')` 的所有流水；
        2. 写入/合并到 search_key_daily_summary；
        3. 彻底 DELETE 原始流水明细，消灭数据库体积膨胀。
        """
        cutoff_query = f"datetime('now', 'localtime', '-{retention_days} days')"
        with self._db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # 1. 查找待归档的聚合数据
                cursor.execute(
                    f"""
                    SELECT 
                        substr(created_at, 1, 10) AS log_date,
                        key_fingerprint,
                        engine,
                        tool_name,
                        COUNT(*) AS total_calls,
                        SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) AS success_calls,
                        SUM(CASE WHEN status_code != 200 AND status_code != 429 THEN 1 ELSE 0 END) AS error_calls,
                        SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END) AS rate_limit_calls,
                        SUM(credits_cost) AS total_credits,
                        AVG(latency_ms) AS avg_latency_ms
                    FROM search_key_usage
                    WHERE created_at < {cutoff_query}
                    GROUP BY log_date, key_fingerprint, engine, tool_name;
                    """
                )
                rows = cursor.fetchall()

                # 2. 增量写入日度统计表
                for r in rows:
                    cursor.execute(
                        """
                        INSERT INTO search_key_daily_summary (
                            date, key_fingerprint, engine, tool_name,
                            total_calls, success_calls, error_calls, rate_limit_calls,
                            total_credits, avg_latency_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(date, key_fingerprint, engine, tool_name) DO UPDATE SET
                            total_calls = total_calls + excluded.total_calls,
                            success_calls = success_calls + excluded.success_calls,
                            error_calls = error_calls + excluded.error_calls,
                            rate_limit_calls = rate_limit_calls + excluded.rate_limit_calls,
                            total_credits = total_credits + excluded.total_credits,
                            avg_latency_ms = (
                                (avg_latency_ms * total_calls) + (excluded.avg_latency_ms * excluded.total_calls)
                            ) / (total_calls + excluded.total_calls)
                        """,
                        (
                            r["log_date"],
                            r["key_fingerprint"],
                            r["engine"],
                            r["tool_name"],
                            r["total_calls"],
                            r["success_calls"],
                            r["error_calls"],
                            r["rate_limit_calls"],
                            r["total_credits"],
                            r["avg_latency_ms"],
                        ),
                    )

                # 3. 物理删除明细数据
                cursor.execute(
                    f"DELETE FROM search_key_usage WHERE created_at < {cutoff_query};"
                )
                deleted_rows = cursor.rowcount
                conn.commit()

                logger.info(
                    "Search accounting pruned %d rows older than %d days into daily summary",
                    deleted_rows,
                    retention_days,
                )
                return {
                    "deleted_detail_rows": deleted_rows,
                    "aggregated_groups": len(rows),
                    "retention_days": retention_days,
                }
            finally:
                conn.close()

    def get_monthly_summary(self, year_month: Optional[str] = None) -> List[Dict[str, Any]]:
        """直出月度真实汇总（融合近 45 天明细 + 45 天前已归档日度数据）。

        Args:
            year_month: 格式 'YYYY-MM'，为空时默认当月。
        """
        ym = year_month or datetime.now().strftime("%Y-%m")
        pattern = f"{ym}%"

        with self._db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                # 联合查询：明细表 + 日度归档表
                cursor.execute(
                    """
                    WITH combined AS (
                        SELECT 
                            key_fingerprint,
                            engine,
                            COUNT(*) AS total_calls,
                            SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) AS success_calls,
                            SUM(CASE WHEN status_code != 200 AND status_code != 429 THEN 1 ELSE 0 END) AS error_calls,
                            SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END) AS rate_limit_calls,
                            SUM(credits_cost) AS total_credits,
                            AVG(latency_ms) AS avg_latency_ms,
                            MAX(created_at) AS last_call_at
                        FROM search_key_usage
                        WHERE created_at LIKE ?
                        GROUP BY key_fingerprint, engine

                        UNION ALL

                        SELECT 
                            key_fingerprint,
                            engine,
                            total_calls,
                            success_calls,
                            error_calls,
                            rate_limit_calls,
                            total_credits,
                            avg_latency_ms,
                            date || ' 23:59:59' AS last_call_at
                        FROM search_key_daily_summary
                        WHERE date LIKE ?
                    )
                    SELECT 
                        key_fingerprint,
                        engine,
                        SUM(total_calls) AS total_calls,
                        SUM(success_calls) AS success_calls,
                        SUM(error_calls) AS error_calls,
                        SUM(rate_limit_calls) AS rate_limit_calls,
                        ROUND(SUM(total_credits), 4) AS total_credits,
                        ROUND(AVG(avg_latency_ms), 1) AS avg_latency_ms,
                        MAX(last_call_at) AS last_call_at
                    FROM combined
                    GROUP BY key_fingerprint, engine
                    ORDER BY total_calls DESC;
                    """,
                    (pattern, pattern),
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def get_database_stats(self) -> Dict[str, Any]:
        """获取当前数据库容量与统计健康状态。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM search_key_usage;")
                detail_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM search_key_daily_summary;")
                summary_count = cursor.fetchone()[0]
                db_size = self._db_path.stat().st_size if self._db_path.exists() else 0
                return {
                    "db_size_bytes": db_size,
                    "detail_records": detail_count,
                    "archived_summary_records": summary_count,
                    "db_path": str(self._db_path),
                }
            finally:
                conn.close()
