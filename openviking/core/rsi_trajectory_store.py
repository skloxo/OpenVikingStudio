# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""SQLite 物理持久化存储: 记录白昼执行轨迹、夜间门禁核验履历与策略演进历史。

核心机制:
  1. 白昼轨迹落盘 (Zero-Loss Trajectory Persistence):
     - 每次 record_turn 同步写入 SQLite WAL 数据库，重启后 100% 自动恢复未完成会话;
  2. 门禁历史留痕 (Gate Verification Audit):
     - 每次双 Split 零退化门禁检验物理落盘，提供全生命周期演进追溯;
  3. 策略演进审计 (Policy Evolution Log):
     - 记录 # EVOLVE-BLOCK 更新前后的指纹与门禁判定状态。

(Card-RSI-True-Closed-Loop v1.5.90)
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class RSITrajectoryStore:
    """RSI 物理持久化存储引擎。线程安全。"""

    _instance: Optional["RSITrajectoryStore"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            base_dir = Path(os.path.expanduser("~/.openviking/data/viking/default"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "rsi_trajectories.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_lock = threading.Lock()
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "RSITrajectoryStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            elif db_path is not None and cls._instance.db_path != Path(db_path):
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
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                # 1. 轨迹表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS rsi_trajectories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        turn_index INTEGER NOT NULL,
                        turn_data_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        evaluated INTEGER DEFAULT 0
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rsi_traj_sess 
                    ON rsi_trajectories (session_id, turn_index);
                """)

                # 2. 门禁验证历史表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS rsi_gate_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        verified_at REAL NOT NULL,
                        passed INTEGER NOT NULL,
                        train_pass_rate REAL NOT NULL,
                        holdout_pass_rate REAL NOT NULL,
                        baseline_holdout_pass_rate REAL NOT NULL,
                        regression_detected INTEGER NOT NULL,
                        details TEXT NOT NULL
                    );
                """)

                # 3. 策略演进履历表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS rsi_policy_evolution_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        evolved_at REAL NOT NULL,
                        skill_name TEXT NOT NULL,
                        block_index INTEGER NOT NULL,
                        old_sha256 TEXT NOT NULL,
                        new_sha256 TEXT NOT NULL,
                        gate_passed INTEGER NOT NULL,
                        file_path TEXT
                    );
                """)

                # 4. SkillHone 演进决策历史表 (Card-254)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS skill_decision_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        package_id TEXT NOT NULL,
                        skill_name TEXT NOT NULL,
                        diagnosis TEXT NOT NULL,
                        candidate_patches_json TEXT NOT NULL,
                        eval_evidence_json TEXT NOT NULL,
                        patch_fingerprint TEXT NOT NULL,
                        decision TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        created_at REAL NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_skill_decision_skill_time
                    ON skill_decision_history (skill_name, created_at DESC);
                """)
                conn.commit()
            finally:
                conn.close()

    def record_turn(self, session_id: str, turn_data: Dict[str, Any], turn_index: Optional[int] = None) -> None:
        """物理落盘单条轨迹回合。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                if turn_index is None:
                    cur.execute(
                        "SELECT COALESCE(MAX(turn_index), -1) + 1 FROM rsi_trajectories WHERE session_id = ?",
                        (session_id,),
                    )
                    turn_index = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO rsi_trajectories (session_id, turn_index, turn_data_json, created_at, evaluated)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (session_id, turn_index, json.dumps(turn_data, ensure_ascii=False), time.time()),
                )
                conn.commit()
            finally:
                conn.close()

    def load_trajectories(self, limit_sessions: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """从 SQLite 恢复历史会话轨迹（按会话分组，并按 turn_index 排序）。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT session_id FROM rsi_trajectories 
                    ORDER BY id DESC LIMIT ?
                """, (limit_sessions,))
                session_ids = [row["session_id"] for row in cur.fetchall()]

                result: Dict[str, List[Dict[str, Any]]] = {}
                for sid in reversed(session_ids):
                    cur.execute("""
                        SELECT turn_data_json FROM rsi_trajectories 
                        WHERE session_id = ? 
                        ORDER BY turn_index ASC
                    """, (sid,))
                    turns = []
                    for row in cur.fetchall():
                        try:
                            turns.append(json.loads(row["turn_data_json"]))
                        except Exception:
                            continue
                    if turns:
                        result[sid] = turns
                return result
            finally:
                conn.close()

    def mark_evaluated(self, session_id: str) -> None:
        """标记会话为已完成信用评估。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    "UPDATE rsi_trajectories SET evaluated = 1 WHERE session_id = ?",
                    (session_id,),
                )
                conn.commit()
            finally:
                conn.close()

    def record_gate_result(
        self,
        passed: bool,
        train_pass_rate: float,
        holdout_pass_rate: float,
        baseline_holdout_pass_rate: float,
        regression_detected: bool,
        details: str,
    ) -> None:
        """落盘门禁验证记录。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO rsi_gate_history 
                    (verified_at, passed, train_pass_rate, holdout_pass_rate, baseline_holdout_pass_rate, regression_detected, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        time.time(),
                        1 if passed else 0,
                        float(train_pass_rate),
                        float(holdout_pass_rate),
                        float(baseline_holdout_pass_rate),
                        1 if regression_detected else 0,
                        details,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def get_gate_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近门禁核验历史。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, verified_at, passed, train_pass_rate, holdout_pass_rate, 
                           baseline_holdout_pass_rate, regression_detected, details
                    FROM rsi_gate_history 
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
                rows = cur.fetchall()
                return [
                    {
                        "id": row["id"],
                        "verified_at": row["verified_at"],
                        "passed": bool(row["passed"]),
                        "train_pass_rate": row["train_pass_rate"],
                        "holdout_pass_rate": row["holdout_pass_rate"],
                        "baseline_holdout_pass_rate": row["baseline_holdout_pass_rate"],
                        "regression_detected": bool(row["regression_detected"]),
                        "details": row["details"],
                    }
                    for row in rows
                ]
            finally:
                conn.close()

    def record_evolution(
        self,
        skill_name: str,
        block_index: int,
        old_sha256: str,
        new_sha256: str,
        gate_passed: bool,
        file_path: str = "",
    ) -> None:
        """落盘策略演进履历。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO rsi_policy_evolution_log
                    (evolved_at, skill_name, block_index, old_sha256, new_sha256, gate_passed, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        time.time(),
                        skill_name,
                        block_index,
                        old_sha256,
                        new_sha256,
                        1 if gate_passed else 0,
                        file_path,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def record_skill_decision(
        self,
        *,
        package_id: str,
        skill_name: str,
        diagnosis: str,
        candidate_patches: Any,
        eval_evidence: Any,
        patch_fingerprint: str,
        decision: str,
        rationale: str,
    ) -> int:
        """持久化每次 Skill 演进决策（含诊断、候选补丁、评估证据、判定与理由）。"""
        normalized = str(decision or "").strip().lower()
        if normalized not in ("accepted", "rejected"):
            raise ValueError(f"Invalid decision '{decision}': expected 'accepted' or 'rejected'.")
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO skill_decision_history (
                        package_id, skill_name, diagnosis, candidate_patches_json,
                        eval_evidence_json, patch_fingerprint, decision, rationale, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        package_id,
                        skill_name,
                        diagnosis,
                        json.dumps(candidate_patches or {}, ensure_ascii=False),
                        json.dumps(eval_evidence or {}, ensure_ascii=False),
                        patch_fingerprint,
                        normalized,
                        rationale,
                        time.time(),
                    ),
                )
                conn.commit()
                return int(cur.lastrowid or 0)
            finally:
                conn.close()

    def list_skill_decisions(
        self,
        *,
        skill_name: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """检索 Skill 演进决策历史。"""
        where: List[str] = []
        params: List[Any] = []
        if skill_name:
            where.append("skill_name = ?")
            params.append(skill_name)
        if decision:
            where.append("decision = ?")
            params.append(decision.strip().lower())
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        params.append(int(limit))
        with self._db_lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(
                    f"""
                    SELECT id, package_id, skill_name, diagnosis, candidate_patches_json,
                           eval_evidence_json, patch_fingerprint, decision, rationale, created_at
                    FROM skill_decision_history
                    {where_sql}
                    ORDER BY id DESC LIMIT ?
                    """,
                    params,
                ).fetchall()
                return [
                    {
                        "id": row["id"],
                        "package_id": row["package_id"],
                        "skill_name": row["skill_name"],
                        "diagnosis": row["diagnosis"],
                        "candidate_patches": json.loads(row["candidate_patches_json"] or "{}"),
                        "eval_evidence": json.loads(row["eval_evidence_json"] or "{}"),
                        "patch_fingerprint": row["patch_fingerprint"],
                        "decision": row["decision"],
                        "rationale": row["rationale"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
            finally:
                conn.close()

    def get_rejected_decisions(self, skill_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """生成补丁前检索目标 Skill 历史被拒方案及原因，避免重复踩坑。"""
        return self.list_skill_decisions(skill_name=skill_name, decision="rejected", limit=limit)

    def count_summary(self) -> Dict[str, int]:
        """获取持久化总览统计。"""
        with self._db_lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(DISTINCT session_id), COUNT(*) FROM rsi_trajectories")
                row = cur.fetchone()
                total_sessions = row[0] or 0
                total_turns = row[1] or 0

                cur.execute("SELECT COUNT(*), SUM(passed) FROM rsi_gate_history")
                grow = cur.fetchone()
                total_gates = grow[0] or 0
                passed_gates = grow[1] or 0

                cur.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN decision = 'rejected' THEN 1 ELSE 0 END) FROM skill_decision_history"
                )
                drow = cur.fetchone()
                total_decisions = drow[0] or 0
                rejected_decisions = drow[1] or 0

                return {
                    "persisted_sessions": total_sessions,
                    "persisted_turns": total_turns,
                    "total_gate_checks": total_gates,
                    "passed_gate_checks": passed_gates,
                    "skill_decisions_total": total_decisions,
                    "skill_decisions_rejected": rejected_decisions,
                }
            finally:
                conn.close()
