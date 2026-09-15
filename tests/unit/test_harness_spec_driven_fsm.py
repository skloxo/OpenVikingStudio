# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for 12-State Deterministic Harness FSM and Spec-Driven Orchestrator.
(Card-Harness-SpecDrivenFSM - v1.5.07)
"""

import pytest

from openviking.core.harness_fsm import (
    HarnessFSM,
    HarnessState,
    InvalidTransitionError,
)
from openviking.core.spec_orchestrator import (
    AgentRoleType,
    EvaluatorCollusionError,
    RoleViolationError,
    SpecDrivenOrchestrator,
)


class TestHarnessFSM:
    """Tests deterministic 12-state transitions and safety invariants."""

    def test_canonical_happy_path_lifecycle(self):
        fsm = HarnessFSM()
        assert fsm.current_state == HarnessState.IDLE

        fsm.transition_to(HarnessState.SPEC_INGEST, "Ingesting user spec P")
        assert fsm.current_state == HarnessState.SPEC_INGEST

        fsm.transition_to(HarnessState.DECOMPOSE, "Decomposing into tracer tickets")
        assert fsm.current_state == HarnessState.DECOMPOSE

        fsm.transition_to(HarnessState.DISPATCH, "Assigning ticket to specialist")
        assert fsm.current_state == HarnessState.DISPATCH

        fsm.transition_to(HarnessState.RUNNING, "Specialist executing sandbox code")
        assert fsm.current_state == HarnessState.RUNNING

        fsm.transition_to(HarnessState.VERIFY, "Executing MultiMetricGate verification")
        assert fsm.current_state == HarnessState.VERIFY

        fsm.transition_to(HarnessState.EVALUATE, "Independent evaluator review")
        assert fsm.current_state == HarnessState.EVALUATE

        fsm.transition_to(HarnessState.CHECKPOINT, "Evaluation passed, snapshotting CP")
        assert fsm.current_state == HarnessState.CHECKPOINT

        fsm.transition_to(HarnessState.COMPLETED, "All tickets verified and delivered")
        assert fsm.current_state == HarnessState.COMPLETED
        assert fsm.is_terminal is True
        assert len(fsm.history) == 8

    def test_blocks_illegal_state_jumps(self):
        fsm = HarnessFSM()
        assert fsm.current_state == HarnessState.IDLE

        # Direct jump from IDLE to RUNNING is forbidden
        with pytest.raises(InvalidTransitionError) as exc_info:
            fsm.transition_to(HarnessState.RUNNING, "Skip spec")
        assert "Illegal state transition" in str(exc_info.value)

        # Direct jump from IDLE to COMPLETED is forbidden
        with pytest.raises(InvalidTransitionError):
            fsm.transition_to(HarnessState.COMPLETED, "Instant complete")

    def test_active_brake_aborts_immediately(self):
        fsm = HarnessFSM()
        fsm.transition_to(HarnessState.SPEC_INGEST)
        fsm.abort("Budget reached or user manual stop")
        assert fsm.current_state == HarnessState.ABORTED
        assert fsm.is_terminal is True

    def test_recovery_retry_budget_enforcement(self):
        fsm = HarnessFSM()
        fsm.transition_to(HarnessState.SPEC_INGEST)
        fsm.transition_to(HarnessState.DECOMPOSE)
        fsm.transition_to(HarnessState.DISPATCH)

        # Simulate 3 recovery cycles
        for i in range(3):
            fsm.transition_to(HarnessState.RECOVERING, f"Retry attempt {i+1}")
            fsm.transition_to(HarnessState.DISPATCH, "Re-dispatching")

        # 4th recovery attempt breaches budget -> terminal FAILED
        record = fsm.transition_to(HarnessState.RECOVERING, "Retry attempt 4")
        assert fsm.current_state == HarnessState.FAILED
        assert record.to_state == HarnessState.FAILED
        assert "budget exceeded" in record.reason.lower()


class TestSpecDrivenOrchestrator:
    """Tests role separation, anti-collusion evaluation, and checkpointing."""

    def test_enforces_specialist_role_for_dispatch(self):
        orch = SpecDrivenOrchestrator()
        orch.fsm.transition_to(HarnessState.SPEC_INGEST)
        orch.fsm.transition_to(HarnessState.DECOMPOSE)

        # Cannot dispatch to orchestrator to write code
        with pytest.raises(RoleViolationError):
            orch.dispatch_ticket(
                ticket_id="TICKET-101",
                specialist_id="orchestrator_main",
                role=AgentRoleType.ORCHESTRATOR,
            )

        # Valid dispatch to specialist
        orch.dispatch_ticket(
            ticket_id="TICKET-101",
            specialist_id="specialist_algo_1",
            role=AgentRoleType.SPECIALIST,
        )
        assert orch.current_state == HarnessState.RUNNING

    def test_blocks_generator_evaluator_collusion(self):
        orch = SpecDrivenOrchestrator()
        orch.fsm.transition_to(HarnessState.SPEC_INGEST)
        orch.fsm.transition_to(HarnessState.DECOMPOSE)

        # Generator runs ticket
        orch.dispatch_ticket(
            ticket_id="TICKET-102",
            specialist_id="specialist_bob",
            role=AgentRoleType.SPECIALIST,
        )
        orch.submit_for_verification(["/tmp/solution.py"])
        assert orch.current_state == HarnessState.VERIFY

        # Generator attempts to evaluate its own work -> BLOCKED
        with pytest.raises(EvaluatorCollusionError) as exc_info:
            orch.evaluate_delivery(
                evaluator_id="specialist_bob",
                evaluator_role=AgentRoleType.EVALUATOR,
                verdict_passed=True,
                notes="Looks good to me!",
            )
        assert "Evaluator collusion detected" in str(exc_info.value)

    def test_independent_evaluator_approval_and_checkpoint(self):
        orch = SpecDrivenOrchestrator()
        orch.fsm.transition_to(HarnessState.SPEC_INGEST)
        orch.fsm.transition_to(HarnessState.DECOMPOSE)

        orch.dispatch_ticket(
            ticket_id="TICKET-103",
            specialist_id="worker_alice",
            role=AgentRoleType.SPECIALIST,
        )
        orch.submit_for_verification(["/tmp/solution.py"])

        # Independent evaluator approves
        orch.evaluate_delivery(
            evaluator_id="evaluator_charlie",
            evaluator_role=AgentRoleType.EVALUATOR,
            verdict_passed=True,
            notes="Physical diff and retina tests verified.",
        )
        assert orch.current_state == HarnessState.CHECKPOINT

        # Snapshot checkpoint CP
        cp = orch.save_checkpoint("CP-2026-09-15-001")
        assert cp.checkpoint_id == "CP-2026-09-15-001"
        assert cp.state == HarnessState.CHECKPOINT
        assert len(cp.audit_trail) > 0

        # Complete
        orch.complete_lifecycle("Final delivery accepted")
        assert orch.current_state == HarnessState.COMPLETED

    def test_rejected_evaluation_routes_back_to_dispatch(self):
        orch = SpecDrivenOrchestrator()
        orch.fsm.transition_to(HarnessState.SPEC_INGEST)
        orch.fsm.transition_to(HarnessState.DECOMPOSE)

        orch.dispatch_ticket(
            ticket_id="TICKET-104",
            specialist_id="worker_dave",
            role=AgentRoleType.SPECIALIST,
        )
        orch.submit_for_verification(["/tmp/bad_code.py"])

        # Independent evaluator rejects
        orch.evaluate_delivery(
            evaluator_id="evaluator_eve",
            evaluator_role=AgentRoleType.EVALUATOR,
            verdict_passed=False,
            notes="Missing boundary assertion on negative inputs.",
        )
        # Automatically routed back to DISPATCH
        assert orch.current_state == HarnessState.DISPATCH
