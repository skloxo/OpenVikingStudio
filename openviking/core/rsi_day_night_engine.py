# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""昼夜双轮递归自演进调度引擎 (Daytime-Nighttime RSI Engine) 与双 Split 零退化门禁。

核心机制:
  1. 昼夜双轮闭环:
     - 白昼 (DAYTIME_COLLECTION): 在确定性 Harness 下处理真实任务，收集真实轨迹；
     - 夜间 (NIGHTTIME_DREAMING): 离线进行弱点聚类、局部信用分配与双 Split 无退化回归门禁验证；
  2. 双 Split 零退化回归门禁 (Dual-Split Zero-Regression Gate):
     - Train Split: 用于发现弱点并微调可编辑区块；
     - Holdout Split: 盲测验证集，候选策略的 pass_rate 必须 >= baseline 且零破坏既有能力；
     - 门禁未过绝对物理拒绝写入！

(Card-Skill-TrainablePolicy-RSI v1.5.40)
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from openviking.core.rsi_credit_allocator import CreditAllocationResult, RSICreditAllocator
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


class RSIDayNightEngine:
    """昼夜双轮调度引擎。全服务单例。"""

    _instance: Optional["RSIDayNightEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._current_phase = RSIPhase.DAYTIME_COLLECTION
        self._trajectories: Dict[str, List[Dict[str, Any]]] = {}
        self._credit_results: List[CreditAllocationResult] = []
        self._gate_verifications: List[DualSplitGateResult] = []
        self._phase_switched_at = time.time()
        self._engine_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "RSIDayNightEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
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
        """白昼收集执行轨迹回合。"""
        with self._engine_lock:
            if session_id not in self._trajectories:
                self._trajectories[session_id] = []
            self._trajectories[session_id].append(turn_data)

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
            return res

    def verify_dual_split_gate(
        self,
        train_results: List[bool],
        holdout_results: List[bool],
        baseline_holdout_pass_rate: float = 0.8,
    ) -> DualSplitGateResult:
        """执行双 Split 零退化门禁检验。"""
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
        )

        with self._engine_lock:
            self._gate_verifications.insert(0, result)
            if len(self._gate_verifications) > 50:
                self._gate_verifications.pop()

        return result

    def summary(self) -> Dict[str, Any]:
        with self._engine_lock:
            total_sessions = len(self._trajectories)
            total_turns = sum(len(t) for t in self._trajectories.values())
            passed_gates = sum(1 for g in self._gate_verifications if g.passed)
            return {
                "current_phase": self._current_phase.value,
                "phase_switched_at": self._phase_switched_at,
                "total_trajectories_collected": total_sessions,
                "total_turns_collected": total_turns,
                "total_credit_evaluations": len(self._credit_results),
                "dual_split_verifications": len(self._gate_verifications),
                "gate_pass_rate": round(passed_gates / max(len(self._gate_verifications), 1), 2),
            }
