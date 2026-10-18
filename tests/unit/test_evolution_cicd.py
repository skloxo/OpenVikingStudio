# -*- coding: utf-8 -*-
"""Unit tests for Evolution CI/CD Pipeline & Governance Engine."""

import pytest
from openviking.core.evolution_cicd import (
    AutonomousLevel,
    EvolutionCICDPipeline,
    PipelineStage,
    SecondOrderMetrics,
)


@pytest.fixture(autouse=True)
def reset_pipeline():
    pipeline = EvolutionCICDPipeline.get_instance()
    pipeline.packages.clear()
    pipeline.autonomous_level = AutonomousLevel.LEVEL_2_BOUNDED_AUTO
    pipeline.emergency_kill_switch_tripped = False
    pipeline.auto_downgrade_count = 0
    pipeline.metrics = SecondOrderMetrics()
    yield
    pipeline.packages.clear()


def test_package_creation_and_stage_transitions():
    pipeline = EvolutionCICDPipeline.get_instance()
    diff = "+- DO NOT hallucinate\n+- INSTEAD verify state"
    pkg = pipeline.create_package("test-skill", diff)

    assert pkg.target_skill == "test-skill"
    assert pkg.current_stage == PipelineStage.SIGNAL_AGGREGATION
    assert pkg.line_count == 2
    assert len(pkg.stage_history) == 1

    # Stage 1 -> 2
    success, msg = pipeline.advance_package(pkg.package_id)
    assert success
    assert pkg.current_stage == PipelineStage.CANDIDATE_GENERATION

    # Stage 2 -> 3
    success, msg = pipeline.advance_package(pkg.package_id)
    assert success
    assert pkg.current_stage == PipelineStage.ISOLATED_EVALUATION

    # Stage 3 -> 4
    success, msg = pipeline.advance_package(pkg.package_id)
    assert success
    assert pkg.current_stage == PipelineStage.SAFETY_GATE

    # Stage 4 -> 5 (Safety gate: <=300 lines sweet spot)
    success, msg = pipeline.advance_package(pkg.package_id)
    assert success
    assert pkg.current_stage == PipelineStage.CANARY_ROLLOUT
    assert pkg.canary_traffic_pct == 10

    # Stage 5 -> 6
    success, msg = pipeline.advance_package(pkg.package_id)
    assert success
    assert pkg.current_stage == PipelineStage.MONITORING_ROLLBACK
    assert pkg.canary_traffic_pct == 50

    # Stage 6 -> 7 (Normal metrics -> Final crystallization)
    success, msg = pipeline.advance_package(pkg.package_id)
    assert success
    assert pkg.current_stage == PipelineStage.EXPERIENCE_CRYSTALLIZATION
    assert pkg.canary_traffic_pct == 100


def test_safety_gate_blocking_large_patch():
    pipeline = EvolutionCICDPipeline.get_instance()
    huge_diff = "\n".join([f"+- line {i}" for i in range(350)])
    pkg = pipeline.create_package("huge-skill", huge_diff)

    # Advance to Safety Gate
    pipeline.advance_package(pkg.package_id) # to CANDIDATE_GENERATION
    pipeline.advance_package(pkg.package_id) # to ISOLATED_EVALUATION
    pipeline.advance_package(pkg.package_id) # to SAFETY_GATE

    # Should be rejected because > 300 lines
    success, msg = pipeline.advance_package(pkg.package_id)
    assert not success
    assert "exceeds 300-line sweet spot" in msg
    assert pkg.current_stage == PipelineStage.SAFETY_GATE


def test_second_order_metrics_drift_triggers_rollback_and_downgrade():
    pipeline = EvolutionCICDPipeline.get_instance()
    pipeline.autonomous_level = AutonomousLevel.LEVEL_3_FULL_EVOLVE
    diff = "+- DO NOT drift\n+- INSTEAD stay aligned"
    pkg = pipeline.create_package("drift-skill", diff)

    # Advance to MONITORING_ROLLBACK
    for _ in range(5):
        pipeline.advance_package(pkg.package_id)
    assert pkg.current_stage == PipelineStage.MONITORING_ROLLBACK

    # Inject hazardous 2nd-order metric drift (e.g. refusal rate spiked to 8%)
    pipeline.metrics.refusal_rate = 0.08
    assert pipeline.metrics.evaluate_drift() is True

    # Advancing should trip auto-rollback and downgrade from Level 3 to Level 2
    success, msg = pipeline.advance_package(pkg.package_id)
    assert not success
    assert "Auto-rollback triggered" in msg
    assert pkg.rolled_back is True
    assert pkg.canary_traffic_pct == 0
    assert pipeline.autonomous_level == AutonomousLevel.LEVEL_2_BOUNDED_AUTO
    assert pipeline.auto_downgrade_count == 1


def test_emergency_kill_switch_and_full_reversion():
    pipeline = EvolutionCICDPipeline.get_instance()
    pkg = pipeline.create_package("emergency-skill", "+- patch")
    pipeline.advance_package(pkg.package_id)
    pipeline.advance_package(pkg.package_id)
    pipeline.advance_package(pkg.package_id)
    pipeline.advance_package(pkg.package_id)  # at CANARY_ROLLOUT

    result = pipeline.trigger_emergency_rollback(pkg.package_id)
    assert result["status"] == "emergency_rollback_success"
    assert pkg.package_id in result["rolled_back_packages"]
    assert pipeline.emergency_kill_switch_tripped is True
    assert pipeline.autonomous_level == AutonomousLevel.LEVEL_0_OBSERVE

    # Cannot advance under tripped emergency kill-switch
    success, msg = pipeline.advance_package(pkg.package_id)
    assert not success
    assert "kill-switch is currently active" in msg
