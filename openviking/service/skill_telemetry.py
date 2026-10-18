# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Usage Telemetry, ROI Ranking & Auto-Promotion Engine.

Records real-time invocations, JIT readings, and evaluations across FastMCP & REST endpoints.
Computes multi-dimensional ROI scores and detects dormant/zombie skills.
Maintained within the 100-300 lines sweet spot.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import math
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from openviking_cli.utils import get_logger

logger = get_logger(__name__)


class SkillTelemetryStore:
    """Thread-safe SQLite store for skill usage telemetry and ROI evaluation."""

    _instance: Optional[SkillTelemetryStore] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            data_dir = Path.home() / ".openviking" / "data" / "skills"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "skill_telemetry.db"
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_path = db_path
        self._db_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> SkillTelemetryStore:
        """Double-checked locking singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (used for test isolation)."""
        with cls._lock:
            cls._instance = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._db_lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS skill_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id TEXT NOT NULL,
                    bundle_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    success INTEGER NOT NULL DEFAULT 1,
                    tokens_saved INTEGER NOT NULL DEFAULT 0,
                    latency_ms REAL NOT NULL DEFAULT 0.0,
                    caller_agent TEXT NOT NULL DEFAULT 'unknown',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_skill_events_skill ON skill_events(skill_id);
                CREATE INDEX IF NOT EXISTS idx_skill_events_bundle ON skill_events(bundle_name);
                CREATE INDEX IF NOT EXISTS idx_skill_events_created ON skill_events(created_at);
                """
            )

    def record_event(
        self,
        skill_id: str,
        bundle_name: Optional[str] = None,
        event_type: str = "invoke",
        success: bool = True,
        tokens_saved: int = 0,
        latency_ms: float = 0.0,
        caller_agent: str = "unknown",
        created_at: Optional[str] = None,
    ) -> int:
        """Record a single skill invocation/reading event. Fail-open on database error."""
        if not skill_id:
            return 0
        b_name = bundle_name or skill_id.split("/")[0] if "/" in skill_id else skill_id
        now_iso = created_at or datetime.now(timezone.utc).isoformat()
        try:
            with self._db_lock, self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO skill_events (
                        skill_id, bundle_name, event_type, success,
                        tokens_saved, latency_ms, caller_agent, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        skill_id,
                        b_name,
                        event_type,
                        1 if success else 0,
                        max(0, int(tokens_saved)),
                        max(0.0, float(latency_ms)),
                        str(caller_agent or "unknown"),
                        now_iso,
                    ),
                )
                conn.commit()
                return cursor.lastrowid or 0
        except Exception as e:
            logger.warning("Failed to record skill telemetry event for %s: %s", skill_id, e)
            return 0

    @staticmethod
    def calculate_roi(calls: int, success_rate: float, tokens_saved: int) -> float:
        """Calculate normalized ROI score (0.0 to 100.0)."""
        if calls <= 0:
            return 0.0
        calls_term = min(40.0, math.log10(calls + 1) * 25.0)
        success_term = max(0.0, min(1.0, success_rate)) * 30.0
        token_term = min(30.0, (tokens_saved / 10000.0) * 30.0)
        return round(min(100.0, calls_term + success_term + token_term), 1)

    def get_telemetry_report(
        self,
        days: int = 30,
        all_registered_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Aggregate skill usage, calculate ROI ranking, and detect dormant skills."""
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_dt.isoformat()

        skill_agg: Dict[str, Dict[str, Any]] = {}
        bundle_agg: Dict[str, Dict[str, Any]] = {}
        total_invocations = 0
        total_tokens_saved = 0
        total_successes = 0

        with self._db_lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    skill_id, bundle_name,
                    COUNT(*) as call_count,
                    SUM(success) as success_count,
                    SUM(tokens_saved) as total_tokens,
                    AVG(latency_ms) as avg_latency,
                    MAX(created_at) as last_seen
                FROM skill_events
                WHERE created_at >= ?
                GROUP BY skill_id, bundle_name
                """,
                (cutoff_iso,),
            ).fetchall()

            for r in rows:
                s_id = r["skill_id"]
                b_name = r["bundle_name"]
                c_cnt = r["call_count"]
                s_cnt = r["success_count"]
                t_saved = r["total_tokens"] or 0
                s_rate = (s_cnt / c_cnt) if c_cnt > 0 else 0.0
                roi = self.calculate_roi(c_cnt, s_rate, t_saved)

                total_invocations += c_cnt
                total_tokens_saved += t_saved
                total_successes += s_cnt

                skill_agg[s_id] = {
                    "skill_id": s_id,
                    "bundle_name": b_name,
                    "call_count": c_cnt,
                    "success_rate": round(s_rate, 3),
                    "tokens_saved": t_saved,
                    "avg_latency_ms": round(r["avg_latency"] or 0.0, 1),
                    "last_used_at": r["last_seen"],
                    "roi_score": roi,
                    "is_dormant": False,
                }

                if b_name not in bundle_agg:
                    bundle_agg[b_name] = {
                        "bundle_name": b_name,
                        "call_count": 0,
                        "success_count": 0,
                        "tokens_saved": 0,
                        "skills": set(),
                    }
                bundle_agg[b_name]["call_count"] += c_cnt
                bundle_agg[b_name]["success_count"] += s_cnt
                bundle_agg[b_name]["tokens_saved"] += t_saved
                bundle_agg[b_name]["skills"].add(s_id)

        # Detect dormant skills from registered list
        dormant_warnings: List[Dict[str, Any]] = []
        registered = set(all_registered_skills or [])
        for reg_id in registered:
            if reg_id not in skill_agg:
                dormant_warnings.append({
                    "skill_id": reg_id,
                    "days_inactive": days,
                    "reason": f"Zero invocations in the last {days} days",
                    "suggestion": "Review for possible consolidation into parent bundle or archiving.",
                })

        # Calculate Bundle ROI
        bundles_result: List[Dict[str, Any]] = []
        for b_name, b_info in bundle_agg.items():
            b_calls = b_info["call_count"]
            b_succ = b_info["success_count"]
            b_tokens = b_info["tokens_saved"]
            b_rate = (b_succ / b_calls) if b_calls > 0 else 0.0
            bundles_result.append({
                "bundle_name": b_name,
                "call_count": b_calls,
                "success_rate": round(b_rate, 3),
                "tokens_saved": b_tokens,
                "skill_count": len(b_info["skills"]),
                "roi_score": self.calculate_roi(b_calls, b_rate, b_tokens),
            })
        bundles_result.sort(key=lambda x: x["roi_score"], reverse=True)

        top_skills = sorted(skill_agg.values(), key=lambda x: x["roi_score"], reverse=True)
        overall_success_rate = (total_successes / total_invocations) if total_invocations > 0 else 1.0

        return {
            "summary": {
                "total_invocations": total_invocations,
                "total_tokens_saved": total_tokens_saved,
                "avg_success_rate": round(overall_success_rate, 3),
                "active_skills_count": len(skill_agg),
                "dormant_skills_count": len(dormant_warnings),
                "analyzed_days": days,
            },
            "top_roi_skills": top_skills[:10],
            "bundle_rankings": bundles_result,
            "dormant_warnings": dormant_warnings[:20],
        }

    def prune_old_events(self, retention_days: int = 90) -> int:
        """Prune telemetry events older than retention days."""
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
        try:
            with self._db_lock, self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM skill_events WHERE created_at < ?",
                    (cutoff_dt.isoformat(),),
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.warning("Failed to prune old skill telemetry events: %s", e)
            return 0
