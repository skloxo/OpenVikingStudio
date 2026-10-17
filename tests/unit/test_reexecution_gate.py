"""
Unit tests for ReexecutionSandboxGate and DriftAwareRuleConsolidator.
"""

from openviking.core.reexecution_gate import (
    DriftAwareRuleConsolidator,
    ReexecutionSandboxGate,
    SkillKDStore,
)
from openviking.core.skill_kd_bifurcation import CandidateRulePatch


def test_reexecution_sandbox_gate_pass_and_reject() -> None:
    # 1. Valid actionable rule containing DO NOT and INSTEAD
    valid_rule = CandidateRulePatch(
        rule_content="When in state (AssertionError), DO NOT perform 'task.cancel()'. INSTEAD, execute 'await asyncio.gather'.",
        applicable_scenario="asyncio_concurrency",
        bifurcation_id="bif_123",
        derived_from_turn=1,
    )

    res_pass = ReexecutionSandboxGate.evaluate_rule_in_sandbox(
        patch=valid_rule,
        task_id="task_001",
        student_model_id="student_7b",
    )
    assert res_pass.turned_green is True
    assert res_pass.exit_code == 0
    assert res_pass.gate_verdict == "ACCEPTED"
    assert valid_rule.verified_green is True

    # 2. Vague reflective thought without actionable INSTEAD
    vague_rule = CandidateRulePatch(
        rule_content="I should be more careful next time when cancelling tasks.",
        applicable_scenario="asyncio_concurrency",
        bifurcation_id="bif_456",
        derived_from_turn=2,
    )

    res_fail = ReexecutionSandboxGate.evaluate_rule_in_sandbox(
        patch=vague_rule,
        task_id="task_001",
        student_model_id="student_7b",
    )
    assert res_fail.turned_green is False
    assert res_fail.exit_code == 1
    assert res_fail.gate_verdict == "REJECTED"
    assert vague_rule.verified_green is False


def test_rule_consolidation_and_sweet_spot() -> None:
    # Create 5 verified rules across 2 scenarios
    rules = [
        CandidateRulePatch(
            rule_content=f"DO NOT rule {i} INSTEAD action {i}",
            applicable_scenario="docker_ops" if i < 3 else "git_ops",
            bifurcation_id=f"bif_{i}",
            derived_from_turn=i,
            verified_green=True,
        )
        for i in range(5)
    ]

    summary = DriftAwareRuleConsolidator.consolidate(rules, max_lines_limit=300)
    assert summary.initial_rule_count == 5
    assert summary.consolidated_rule_count <= 4
    assert summary.compression_ratio_pct > 0.0
    assert summary.total_lines <= 300
    assert summary.within_sweet_spot is True


def test_skill_kd_store_metrics() -> None:
    store = SkillKDStore()
    rule = CandidateRulePatch(
        rule_content="DO NOT x INSTEAD y",
        applicable_scenario="test",
        bifurcation_id="bif_test",
        derived_from_turn=0,
        verified_green=True,
    )
    store.add_rule(rule)
    metrics = store.get_metrics()
    assert metrics["total_candidate_rules"] == 1
    assert metrics["verified_rules_in_store"] == 1
    assert metrics["sweet_spot_compliant"] is True
