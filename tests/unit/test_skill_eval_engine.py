# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Skill Evaluation Retina (EvaluationRetina) — TriJudge engine.

测试套件:
  test_exact_judge_pass        ExactJudge 精确匹配命中
  test_exact_judge_fail        ExactJudge 精确匹配未命中
  test_regex_judge_pass        ExactJudge regex 模式命中
  test_regex_judge_fail        ExactJudge regex 模式未命中
  test_command_judge_pass      CommandJudge 命令成功 (exit 0)
  test_command_judge_fail      CommandJudge 命令失败 (exit 1)
  test_agent_judge_skip        AgentJudge 默认 skip
  test_eval_runner_fixture     EvalRunner 端到端：从 evals/cases/ 加载真实用例运行
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 确保项目根在 sys.path (tests/unit/test_*.py → 上两层为项目根)
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.service.skill_eval_types import EvalCase, JudgeType, JudgeVerdict
from openviking.service.skill_eval_engine import (
    AgentJudge,
    CommandJudge,
    EvalCaseLoader,
    EvalRunner,
    ExactJudge,
)


# ---------------------------------------------------------------------------
# 夹具
# ---------------------------------------------------------------------------

def _make_case(
    judge_type: JudgeType,
    input_text: str = "",
    expect: str = "",
    command: str = "",
    expected_exit_code: int = 0,
) -> EvalCase:
    return EvalCase(
        skill_name="test-skill",
        case_id="test-case",
        description="unit test case",
        judge_type=judge_type,
        input=input_text or None,
        expect=expect or None,
        command=command or None,
        expected_exit_code=expected_exit_code,
    )


# ---------------------------------------------------------------------------
# ExactJudge (Level 0)
# ---------------------------------------------------------------------------

def test_exact_judge_pass():
    """ExactJudge: 精确字符串出现 → PASS。"""
    judge = ExactJudge()
    case = _make_case(JudgeType.EXACT, input_text="NO GREEN EVER in this text", expect="NO GREEN EVER")
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.PASS


def test_exact_judge_fail():
    """ExactJudge: 精确字符串未出现 → FAIL。"""
    judge = ExactJudge()
    case = _make_case(JudgeType.EXACT, input_text="nothing useful here", expect="NO GREEN EVER")
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.FAIL
    assert result.error is not None


def test_regex_judge_pass():
    """ExactJudge(regex): 正则模式命中 → PASS。"""
    judge = ExactJudge()
    case = _make_case(JudgeType.REGEX, input_text="font-size: 12px minimum", expect=r"1[12]px|text-xs")
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.PASS


def test_regex_judge_fail():
    """ExactJudge(regex): 正则模式未命中 → FAIL。"""
    judge = ExactJudge()
    case = _make_case(JudgeType.REGEX, input_text="font-size: 8px", expect=r"1[12]px|text-xs")
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.FAIL


# ---------------------------------------------------------------------------
# CommandJudge (Level 1)
# ---------------------------------------------------------------------------

def test_command_judge_pass():
    """CommandJudge: exit 0 → PASS。"""
    judge = CommandJudge()
    case = _make_case(JudgeType.COMMAND, command="exit 0", expected_exit_code=0)
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.PASS


def test_command_judge_fail():
    """CommandJudge: exit 1, expect 0 → FAIL。"""
    judge = CommandJudge()
    case = _make_case(JudgeType.COMMAND, command="exit 1", expected_exit_code=0)
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.FAIL
    assert "exit code 1" in (result.error or "")


# ---------------------------------------------------------------------------
# AgentJudge (Level 2, 本版本预留)
# ---------------------------------------------------------------------------

def test_agent_judge_skip():
    """AgentJudge: 无 LLM 配置时自动 skip。"""
    judge = AgentJudge()
    case = _make_case(JudgeType.AGENT, input_text="some text", expect="positive response")
    result = judge.judge(case)
    assert result.verdict == JudgeVerdict.SKIP


# ---------------------------------------------------------------------------
# EvalRunner 端到端 (使用真实 evals/ 目录)
# ---------------------------------------------------------------------------

def test_eval_runner_real_cases():
    """EvalRunner 端到端: 从项目 evals/cases/ 加载真实用例，执行后结果合法。"""
    evals_root = _ROOT / "evals"
    if not evals_root.exists():
        pytest.skip("evals/ directory not found, skipping real-case test")

    runner = EvalRunner(evals_root=evals_root)
    result = runner.run(skill_name="*")

    assert result.status == "done"
    assert result.total >= 0
    assert result.passed + result.failed + result.skipped == result.total
    assert 0.0 <= result.pass_rate <= 1.0
    # 汇总接口可正常调用
    summary = runner.get_summary()
    assert summary.total_runs == 1
    assert summary.total_cases >= 0
