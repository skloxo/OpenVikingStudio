# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for RSICreditAllocator (AgentOPSD local credit assignment).

测试套件:
  test_credit_allocation_critical_turns  计算 teacher-student log prob gap 并标定关键回合
  test_empty_trajectory_handling         空轨迹安全处理
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.rsi_credit_allocator import RSICreditAllocator


def test_credit_allocation_critical_turns():
    """测试计算 teacher-student log prob gap 并标定关键回合。"""
    turns_data = [
        # Turn 0: 普通回合，师生概率接近 (gap 小)
        {
            "turn_id": 0,
            "role": "user",
            "content": "Please sort this list.",
            "student_log_prob": -0.2,
            "teacher_log_prob": -0.2,
        },
        # Turn 1: 关键回合！Student 盲目手搓冒泡排序，Teacher 期望使用内置 Timsort (gap 大)
        {
            "turn_id": 1,
            "role": "assistant",
            "action_type": "tool_call",
            "content": "Using custom bubble sort...",
            "student_log_prob": -2.8,
            "teacher_log_prob": -0.3,
        },
        # Turn 2: 普通回合 (gap 小)
        {
            "turn_id": 2,
            "role": "tool",
            "content": "Execution result: [1, 2, 3]",
            "student_log_prob": -0.1,
            "teacher_log_prob": -0.1,
        },
        # Turn 3: 关键回合！Student 未进行边界校验，Teacher 校验参数 (gap 大)
        {
            "turn_id": 3,
            "role": "assistant",
            "action_type": "response",
            "content": "Done without checks",
            "student_log_prob": -3.2,
            "teacher_log_prob": -0.5,
        },
    ]

    res = RSICreditAllocator.evaluate_trajectory(turns_data)
    assert res.total_turns == 4
    assert res.critical_turns_count >= 1
    # Turn 1 和 Turn 3 的 gap 远大于 Turn 0 和 Turn 2
    assert 1 in res.critical_turn_ids
    assert 3 in res.critical_turn_ids
    assert res.turns[1].is_critical is True
    assert res.turns[3].is_critical is True
    assert res.turns[0].is_critical is False
    assert res.max_gap >= 2.5


def test_empty_trajectory_handling():
    """测试空轨迹防御。"""
    res = RSICreditAllocator.evaluate_trajectory([])
    assert res.total_turns == 0
    assert res.critical_turns_count == 0
    assert len(res.turns) == 0
