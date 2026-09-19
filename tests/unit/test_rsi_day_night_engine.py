# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for RSIDayNightEngine and Dual-Split regression gate.

测试套件:
  test_phase_switching              昼夜模式状态流转
  test_trajectory_recording         白昼轨迹收集与会话信用分配
  test_dual_split_gate_pass_fail    双 Split 零退化门禁检验
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.rsi_day_night_engine import DualSplitGateResult, RSIDayNightEngine, RSIPhase


@pytest.fixture
def rsi_engine():
    RSIDayNightEngine.reset_instance()
    engine = RSIDayNightEngine.get_instance()
    yield engine
    RSIDayNightEngine.reset_instance()


def test_phase_switching(rsi_engine):
    """测试昼夜模式状态机流转。"""
    assert rsi_engine.current_phase == RSIPhase.DAYTIME_COLLECTION

    # 切换为夜间离线模式
    p1 = rsi_engine.switch_phase()
    assert p1 == RSIPhase.NIGHTTIME_DREAMING
    assert rsi_engine.current_phase == RSIPhase.NIGHTTIME_DREAMING

    # 切回白昼
    p2 = rsi_engine.switch_phase()
    assert p2 == RSIPhase.DAYTIME_COLLECTION


def test_trajectory_recording(rsi_engine):
    """测试白昼收集轨迹与评估。"""
    session_id = "sess-rsi-001"
    rsi_engine.record_turn(session_id, {"turn_id": 0, "student_log_prob": -1.0, "teacher_log_prob": -0.2})
    rsi_engine.record_turn(session_id, {"turn_id": 1, "student_log_prob": -0.3, "teacher_log_prob": -0.3})

    eval_res = rsi_engine.evaluate_session_credits(session_id)
    assert eval_res is not None
    assert eval_res.total_turns == 2

    # 不存在的 session 返回 None
    assert rsi_engine.evaluate_session_credits("non-existent") is None


def test_dual_split_gate_pass_fail(rsi_engine):
    """测试双 Split 零退化门禁检验。"""
    # 场景 1: 通过门禁 (Holdout rate >= 0.8 且 Train rate >= 0.7)
    gate_pass = rsi_engine.verify_dual_split_gate(
        train_results=[True, True, True, False],  # 75%
        holdout_results=[True, True, True, True, False],  # 80%
        baseline_holdout_pass_rate=0.8,
    )
    assert gate_pass.passed is True
    assert gate_pass.regression_detected is False

    # 场景 2: 阻断退化！(Holdout rate 60% < 基线 80%)
    gate_fail = rsi_engine.verify_dual_split_gate(
        train_results=[True, True, True, True],  # 100% (过拟合)
        holdout_results=[True, True, True, False, False],  # 60% < 80%
        baseline_holdout_pass_rate=0.8,
    )
    assert gate_fail.passed is False
    assert gate_fail.regression_detected is True
    assert "BLOCKED" in gate_fail.details
