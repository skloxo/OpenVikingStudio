# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""昼夜双轮递归自演进调度引擎 (Daytime-Nighttime RSI Engine) 与双 Split 零退化门禁。

核心机制:
  1. 昼夜双轮真闭环:
     - 白昼 (DAYTIME_COLLECTION): 在确定性 Harness 下处理真实任务，收集真实轨迹并 SQLite 物理落盘；
     - 夜间 (NIGHTTIME_DREAMING): 离线进行弱点聚类、局部信用分配与双 Split 无退化回归门禁验证；
  2. 双 Split 零退化回归门禁 (Dual-Split Zero-Regression Gate):
     - Train Split: 基于真实会话轨迹发现弱点；
     - Holdout Split: 基于 RSIHoldoutBenchmark 5 大不变量盲测验证（零伪造通过）；
     - 门禁未过绝对物理拒绝写入！
  3. 物理受控演进 (Physical Evolve Write-Back):
     - 门禁通过后自动将更新物理回填至目标技能文件的 # EVOLVE-BLOCK 区域。

(Card-RSI-True-Closed-Loop v1.5.90)
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from openviking.core.rsi_credit_allocator import CreditAllocationResult, RSICreditAllocator
from openviking.core.rsi_holdout_benchmark import BenchmarkSuiteReport, RSIHoldoutBenchmark
from openviking.core.rsi_trajectory_store import RSITrajectoryStore
from openviking.core.trainable_skill_policy import TrainableSkillDocument


class RSIPhase(str, Enum):
    DAYTIME_COLLECTION = "daytime_collection"  # 白昼：确定性执行与轨迹收集
    NIGHTTIME_DREAMING = "nighttime_dreaming"  # 夜间：离线信用分配与门禁验证演进


class DualSplitGateResult(BaseModel):
    """双 Split 门禁验证结果。"""
    passed: bool
    train_pass_rate: float
    holdout_pass_rate: float
    baseline_holdout_pass_rate: float
    regression_detected: bool
    details: str
    benchmark_report: Optional[BenchmarkSuiteReport] = None


class RSIDayNightEngine:
    """昼夜双轮调度引擎。全服务单例。"""

    _instance: Optional["RSIDayNightEngine"] = None
    _lock = threading.Lock()

    def __init__(self, store: Optional[RSITrajectoryStore] = None, auto_load_db: bool = False) -> None:
        self._current_phase = RSIPhase.DAYTIME_COLLECTION
        self._store = store or RSITrajectoryStore.get_instance()
        self._trajectories: Dict[str, List[Dict[str, Any]]] = {}
        self._credit_results: List[CreditAllocationResult] = []
        self._gate_verifications: List[DualSplitGateResult] = []
        self._phase_switched_at = time.time()
        self._engine_lock = threading.RLock()

        if auto_load_db and self._store:
            try:
                recovered = self._store.load_trajectories(limit_sessions=50)
                if recovered:
                    self._trajectories.update(recovered)
            except Exception:
                pass

    def load_persisted_trajectories(self, limit_sessions: int = 50) -> int:
        """从持久化存储中显式恢复会话轨迹。返回恢复的会话数。"""
        with self._engine_lock:
            if self._store:
                recovered = self._store.load_trajectories(limit_sessions=limit_sessions)
                self._trajectories.update(recovered)
                return len(recovered)
            return 0

    @classmethod
    def get_instance(cls, store: Optional[RSITrajectoryStore] = None) -> "RSIDayNightEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(store=store)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    @property
    def current_phase(self) -> RSIPhase:
        with self._engine_lock:
            return self._current_phase

    def switch_phase(self, target_phase: Optional[RSIPhase] = None) -> RSIPhase:
        """手动或定时切换昼夜模式。"""
        with self._engine_lock:
            if target_phase is not None:
                self._current_phase = target_phase
            else:
                self._current_phase = (
                    RSIPhase.NIGHTTIME_DREAMING
                    if self._current_phase == RSIPhase.DAYTIME_COLLECTION
                    else RSIPhase.DAYTIME_COLLECTION
                )
            self._phase_switched_at = time.time()
            return self._current_phase

    def record_turn(self, session_id: str, turn_data: Dict[str, Any]) -> None:
        """白昼收集执行轨迹回合，并同步落盘至 SQLite。"""
        with self._engine_lock:
            if session_id not in self._trajectories:
                self._trajectories[session_id] = []
            self._trajectories[session_id].append(turn_data)

            if self._store:
                try:
                    self._store.record_turn(session_id, turn_data)
                except Exception:
                    pass

    def evaluate_session_credits(self, session_id: str) -> Optional[CreditAllocationResult]:
        """对指定会话的轨迹执行局部信用分配。"""
        with self._engine_lock:
            turns = self._trajectories.get(session_id)
            if not turns:
                return None
            res = RSICreditAllocator.evaluate_trajectory(turns)
            self._credit_results.insert(0, res)
            if len(self._credit_results) > 100:
                self._credit_results.pop()

            if self._store:
                try:
                    self._store.mark_evaluated(session_id)
                except Exception:
                    pass

            return res

    def verify_dual_split_gate(
        self,
        train_results: List[bool],
        holdout_results: List[bool],
        baseline_holdout_pass_rate: float = 0.8,
        benchmark_report: Optional[BenchmarkSuiteReport] = None,
    ) -> DualSplitGateResult:
        """执行双 Split 零退化门禁检验，并同步落盘至门禁历史。"""
        train_rate = sum(1 for r in train_results if r) / max(len(train_results), 1)
        holdout_rate = sum(1 for r in holdout_results if r) / max(len(holdout_results), 1)

        # 核心门禁：Holdout 集绝对不能低于基线 (零退化)
        regression = holdout_rate < baseline_holdout_pass_rate
        passed = (not regression) and (train_rate >= 0.7)

        details = (
            f"Dual-Split Gate {'PASS' if passed else 'BLOCKED'}: "
            f"Train {train_rate * 100:.1f}%, Holdout {holdout_rate * 100:.1f}% "
            f"(Baseline: {baseline_holdout_pass_rate * 100:.1f}%)"
        )

        result = DualSplitGateResult(
            passed=passed,
            train_pass_rate=round(train_rate, 4),
            holdout_pass_rate=round(holdout_rate, 4),
            baseline_holdout_pass_rate=round(baseline_holdout_pass_rate, 4),
            regression_detected=regression,
            details=details,
            benchmark_report=benchmark_report,
        )

        with self._engine_lock:
            self._gate_verifications.insert(0, result)
            if len(self._gate_verifications) > 50:
                self._gate_verifications.pop()

            if self._store:
                try:
                    self._store.record_gate_result(
                        passed=result.passed,
                        train_pass_rate=result.train_pass_rate,
                        holdout_pass_rate=result.holdout_pass_rate,
                        baseline_holdout_pass_rate=result.baseline_holdout_pass_rate,
                        regression_detected=result.regression_detected,
                        details=result.details,
                    )
                except Exception:
                    pass

        return result

    def run_nighttime_cycle(
        self,
        baseline_holdout_pass_rate: float = 0.8,
        train_results: Optional[List[bool]] = None,
        holdout_results: Optional[List[bool]] = None,
        candidate_policy: Optional[TrainableSkillDocument] = None,
    ) -> Dict[str, Any]:
        """运行夜间做梦与双 Split 零退化门禁自演进周期 (消除虚荣值，真实测试驱动)。"""
        with self._engine_lock:
            prev_phase = self._current_phase
            self._current_phase = RSIPhase.NIGHTTIME_DREAMING
            self._phase_switched_at = time.time()

            # 1. 评估所有白昼会话轨迹
            evaluated_count = 0
            session_evaluations: List[CreditAllocationResult] = []
            session_ids = list(self._trajectories.keys())
            for sid in session_ids:
                turns = self._trajectories.get(sid) or []
                if turns:
                    res = RSICreditAllocator.evaluate_trajectory(turns)
                    session_evaluations.append(res)
                    self._credit_results.insert(0, res)
                    evaluated_count += 1
            if len(self._credit_results) > 100:
                self._credit_results = self._credit_results[:100]

            # 2. 真实评估 Train Split
            actual_train_results: List[bool] = (
                train_results
                if train_results is not None
                else RSIHoldoutBenchmark.evaluate_train_results(session_evaluations)
            )

            # 3. 真实评估 Holdout Split 盲测集
            benchmark_report: Optional[BenchmarkSuiteReport] = None
            if holdout_results is not None:
                actual_holdout_results: List[bool] = holdout_results
            else:
                report = RSIHoldoutBenchmark.run_holdout_suite(candidate_policy)
                benchmark_report = report
                actual_holdout_results = [c.passed for c in report.results]

            # 4. 执行双 Split 门禁验证
            gate_res = self.verify_dual_split_gate(
                train_results=actual_train_results,
                holdout_results=actual_holdout_results,
                baseline_holdout_pass_rate=baseline_holdout_pass_rate,
                benchmark_report=benchmark_report,
            )

            # 5. 恢复之前阶段
            self._current_phase = prev_phase
            return {
                "status": "completed",
                "evaluated_sessions": evaluated_count,
                "gate_passed": gate_res.passed,
                "regression_detected": gate_res.regression_detected,
                "train_pass_rate": gate_res.train_pass_rate,
                "holdout_pass_rate": gate_res.holdout_pass_rate,
                "details": gate_res.details,
                "benchmark_report": benchmark_report.model_dump() if benchmark_report else None,
            }

    def evolve_skill_policy(
        self,
        target_skill_path: str | Path,
        block_index: int,
        new_content: str,
        baseline_holdout_pass_rate: float = 0.8,
    ) -> Dict[str, Any]:
        """物理受控演进闭环: 针对目标技能文档进行更新并进行双 Split 门禁核验。

        若门禁通过 -> 物理保存回写并持久化履历;
        若门禁阻断 -> 物理拒绝写入，保留原文档。
        """
        p = Path(target_skill_path)
        if not p.exists():
            raise FileNotFoundError(f"Skill document not found: {target_skill_path}")

        orig_doc = TrainableSkillDocument.from_file(p)
        orig_inspection = orig_doc.inspect()
        if block_index >= orig_inspection.block_count:
            raise IndexError(f"Block index {block_index} out of range ({orig_inspection.block_count} blocks)")

        old_sha = orig_inspection.blocks[block_index].sha256

        # 1. 尝试在内存中更新有界区块（若破坏外部冻结面会在此处直接抛出 ValueError）
        candidate_doc = orig_doc.update_block(block_index, new_content)
        cand_inspection = candidate_doc.inspect()
        new_sha = cand_inspection.blocks[block_index].sha256

        # 2. 提交候选策略进行双 Split 盲测门禁
        cycle_result = self.run_nighttime_cycle(
            baseline_holdout_pass_rate=baseline_holdout_pass_rate,
            candidate_policy=candidate_doc,
        )

        gate_passed = cycle_result["gate_passed"]

        # 3. 门禁决策
        if gate_passed:
            candidate_doc.save(p)
            status = "evolved_and_persisted"
        else:
            status = "blocked_regression_prevented"

        if self._store:
            try:
                self._store.record_evolution(
                    skill_name=orig_doc.skill_name,
                    block_index=block_index,
                    old_sha256=old_sha,
                    new_sha256=new_sha,
                    gate_passed=gate_passed,
                    file_path=str(p),
                )
            except Exception:
                pass

        return {
            "status": status,
            "gate_passed": gate_passed,
            "skill_name": orig_doc.skill_name,
            "block_index": block_index,
            "old_sha256": old_sha,
            "new_sha256": new_sha,
            "cycle_result": cycle_result,
        }

    def summary(self) -> Dict[str, Any]:
        with self._engine_lock:
            total_sessions = len(self._trajectories)
            total_turns = sum(len(t) for t in self._trajectories.values())
            passed_gates = sum(1 for g in self._gate_verifications if g.passed)
            persisted_info = {}
            if self._store:
                try:
                    persisted_info = self._store.count_summary()
                except Exception:
                    pass

            return {
                "current_phase": self._current_phase.value,
                "phase_switched_at": self._phase_switched_at,
                "total_trajectories_collected": total_sessions,
                "total_turns_collected": total_turns,
                "total_credit_evaluations": len(self._credit_results),
                "dual_split_verifications": len(self._gate_verifications),
                "gate_pass_rate": round(passed_gates / max(len(self._gate_verifications), 1), 2),
                "persistence": persisted_info,
            }
