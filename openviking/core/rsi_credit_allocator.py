# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""AgentOPSD 长轨迹局部信用分配引擎 (Local Credit Assignment Engine).

核心算法公理:
  1. 师生对齐 Gap 计算 (Teacher-Student Log-Prob Gap):
     - Student 在无技能引导下完成真实 Rollout;
     - Teacher 携带技能作为引导，沿着相同轨迹计算每个回合的期望对数概率;
     - credit_gap = teacher_log_prob - student_log_prob;
  2. 关键回合精准标定 (Critical Turn Identification):
     - 当某一 turn 的 gap 显著高于基线时，说明此处正是因缺少技能指导而偏离的关键 Seam;
     - 仅对关键回合提取规则微补丁，避免对全局无关步骤过度拟合。

(Card-Skill-TrainablePolicy-RSI v1.5.40)
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class TrajectoryTurn(BaseModel):
    """长轨迹中的单个回合。"""
    turn_id: int
    role: str
    action_type: str = "response"  # "thought" | "tool_call" | "response"
    content: str
    student_log_prob: float = 0.0
    teacher_log_prob: float = 0.0
    credit_gap: float = 0.0
    is_critical: bool = False


class CreditAllocationResult(BaseModel):
    """局部信用分配计算结果。"""
    rollout_id: str = Field(default_factory=lambda: f"rol-{uuid.uuid4().hex[:8]}")
    total_turns: int
    critical_turns_count: int
    critical_turn_ids: List[int]
    mean_gap: float
    max_gap: float
    turns: List[TrajectoryTurn]


# ---------------------------------------------------------------------------
# 信用分配器类
# ---------------------------------------------------------------------------

class RSICreditAllocator:
    """AgentOPSD 局部信用分配器。"""

    @classmethod
    def evaluate_trajectory(
        cls,
        turns_data: List[Dict[str, Any]],
        gap_threshold: Optional[float] = None,
    ) -> CreditAllocationResult:
        """评估轨迹回合，计算 teacher-student log prob gap 并标定关键回合。"""
        if not turns_data:
            return CreditAllocationResult(
                total_turns=0,
                critical_turns_count=0,
                critical_turn_ids=[],
                mean_gap=0.0,
                max_gap=0.0,
                turns=[],
            )

        turns: List[TrajectoryTurn] = []
        gaps: List[float] = []

        for idx, t in enumerate(turns_data):
            s_prob = float(t.get("student_log_prob", 0.0))
            t_prob = float(t.get("teacher_log_prob", 0.0))
            # credit_gap 代表教师策略对该动作的赋权增益
            gap = max(0.0, t_prob - s_prob)

            turns.append(
                TrajectoryTurn(
                    turn_id=t.get("turn_id", idx),
                    role=t.get("role", "assistant"),
                    action_type=t.get("action_type", "response"),
                    content=t.get("content", ""),
                    student_log_prob=s_prob,
                    teacher_log_prob=t_prob,
                    credit_gap=round(gap, 4),
                )
            )
            gaps.append(gap)

        mean_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)

        # 阈值判定：若未指定阈值，默认取 mean + 0.5 * std 或 0.5 * max_gap
        if gap_threshold is not None:
            cutoff = gap_threshold
        else:
            variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            std_dev = math.sqrt(variance)
            cutoff = max(mean_gap + 0.5 * std_dev, 0.1)

        critical_ids: List[int] = []
        for turn in turns:
            if turn.credit_gap >= cutoff:
                turn.is_critical = True
                critical_ids.append(turn.turn_id)

        return CreditAllocationResult(
            total_turns=len(turns),
            critical_turns_count=len(critical_ids),
            critical_turn_ids=critical_ids,
            mean_gap=round(mean_gap, 4),
            max_gap=round(max_gap, 4),
            turns=turns,
        )
