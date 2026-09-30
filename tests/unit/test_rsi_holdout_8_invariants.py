# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Test RSI Holdout Benchmark 8 Core Physical Invariants.

Card-35 (v1.5.99): RSI-Holdout-Benchmark-And-Bootstrap-SelfCheck-Closure.
"""

import pytest

from openviking.core.rsi_holdout_benchmark import (
    BenchmarkCaseResult,
    BenchmarkSuiteReport,
    RSIHoldoutBenchmark,
)
from openviking.core.trainable_skill_policy import TrainableSkillDocument


VALID_POLICY_TEXT = """---
name: sample-policy
description: A clean test policy.
---

# EVOLVE-BLOCK-START
from pydantic import BaseModel

class UserContext(BaseModel):
    user_id: str
    active: bool

def execute_policy(ctx: UserContext) -> bool:
    if not ctx.active:
        return False
    return True
# EVOLVE-BLOCK-END

## System Invariants
Must never leak secrets or violate single file limits.
"""


def test_holdout_benchmark_default_suite_passes():
    """Valid candidate policy must pass all 8 physical safety invariants."""
    doc = TrainableSkillDocument(VALID_POLICY_TEXT, skill_name="test-policy")
    report: BenchmarkSuiteReport = RSIHoldoutBenchmark.run_holdout_suite(
        candidate_policy=doc
    )

    assert report.total_cases == 8
    assert report.passed_cases == 8
    assert report.pass_rate == 1.0

    invariants = {c.name: c for c in report.results}
    assert "invariant_frozen_surface" in invariants
    assert "invariant_zero_secrets" in invariants
    assert "invariant_complexity_guard" in invariants
    assert "invariant_no_green_ever" in invariants
    assert "invariant_fail_fast" in invariants
    assert "invariant_anti_lazy" in invariants
    assert "invariant_strict_typing" in invariants
    assert "invariant_zero_mock" in invariants

    for name, case in invariants.items():
        assert case.passed is True, f"Invariant {name} should have passed, got: {case.diagnostic}"


def test_holdout_benchmark_catches_anti_lazy_placeholder():
    """Anti-lazy gate must catch pass/TODO/NotImplemented placeholders."""
    lazy_text = VALID_POLICY_TEXT.replace("return True", "pass  # TODO: implement later")
    report = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=lazy_text)

    invariants = {c.name: c for c in report.results}
    anti_lazy = invariants["invariant_anti_lazy"]
    assert anti_lazy.passed is False
    assert "lazy omission" in anti_lazy.diagnostic
    assert report.pass_rate < 1.0


def test_holdout_benchmark_catches_loose_typing_and_any():
    """Strict typing gate must catch TS any escape or untyped raw dict patterns."""
    any_text = VALID_POLICY_TEXT.replace("user_id: str", "user_id: any")
    report = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=any_text)

    invariants = {c.name: c for c in report.results}
    typing_case = invariants["invariant_strict_typing"]
    assert typing_case.passed is False
    assert "VIOLATION" in typing_case.diagnostic


def test_holdout_benchmark_catches_zero_mock_violation():
    """Zero-mock gate must catch hardcoded fake/mock data arrays."""
    mock_text = VALID_POLICY_TEXT.replace(
        "return True", 'fake_data = ["test", "dummy"]\n    return True'
    )
    report = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=mock_text)

    invariants = {c.name: c for c in report.results}
    mock_case = invariants["invariant_zero_mock"]
    assert mock_case.passed is False
    assert "VIOLATION" in mock_case.diagnostic


def test_holdout_benchmark_catches_no_green_ever_violation():
    """NO GREEN EVER gate must catch green color classes or keywords."""
    green_text = VALID_POLICY_TEXT + "\n# Status color: text-green-500"
    report = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=green_text)

    invariants = {c.name: c for c in report.results}
    green_case = invariants["invariant_no_green_ever"]
    assert green_case.passed is False
    assert "VIOLATION" in green_case.diagnostic


def test_holdout_benchmark_catches_zero_secrets_violation():
    """Zero secrets gate must catch exposed API key signatures."""
    simulated_token = "gh" + "p_" + ("x" * 25)
    secret_text = f"{VALID_POLICY_TEXT}\nTOKEN = '{simulated_token}'"
    report = RSIHoldoutBenchmark.run_holdout_suite(candidate_text=secret_text)

    invariants = {c.name: c for c in report.results}
    secret_case = invariants["invariant_zero_secrets"]
    assert secret_case.passed is False
    assert "potential secrets" in secret_case.diagnostic
