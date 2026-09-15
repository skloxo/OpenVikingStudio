# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Harness Four Invariants (Card-Harness-DeepSeek-AgentScope-SpecDriven - v1.5.03)

Verifies:
1. Terminability: BudgetEnforcer timeout, token limit, cost limit, and tool invocation limits.
2. Recoverability: CheckpointRegistry save, get, list, restore, and prune.
3. Observability: HarnessTrace events, metrics, and InvariantTelemetry counters.
"""

import time
import pytest

from openviking.core.harness_invariants import (
    BudgetEnforcer,
    BudgetExceededError,
    ExecutionBudget,
    Checkpoint,
    CheckpointRegistry,
    HarnessTrace,
    InvariantTelemetry,
)


def test_budget_enforcer_within_limits():
    """Test budget enforcer stays healthy when consumption is within limits."""
    budget = ExecutionBudget(
        max_wall_time_sec=10.0,
        max_total_tokens=1000,
        max_cost_usd=0.50,
        max_tool_invocations=10,
    )
    enforcer = BudgetEnforcer(budget)
    enforcer.record_tokens(prompt_tokens=100, completion_tokens=50, cost_usd=0.01)
    enforcer.record_tool_invocation(2)

    enforcer.check_budget()  # Should not raise
    snapshot = enforcer.get_snapshot()

    assert not snapshot.is_exhausted
    assert snapshot.total_tokens == 150
    assert snapshot.tool_invocations == 2
    assert snapshot.cost_usd == 0.01
    assert snapshot.exhaustion_reason is None


def test_budget_enforcer_token_breach():
    """Test budget enforcer raises error when token threshold is exceeded."""
    budget = ExecutionBudget(max_total_tokens=500)
    enforcer = BudgetEnforcer(budget)
    enforcer.record_tokens(prompt_tokens=300, completion_tokens=250)

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.check_budget()

    assert "Token budget exceeded" in str(exc_info.value)
    snapshot = enforcer.get_snapshot()
    assert snapshot.is_exhausted


def test_budget_enforcer_cost_breach():
    """Test budget enforcer raises error when cost threshold is exceeded."""
    budget = ExecutionBudget(max_cost_usd=0.05)
    enforcer = BudgetEnforcer(budget)
    enforcer.record_tokens(prompt_tokens=10, cost_usd=0.06)

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.check_budget()

    assert "Cost budget exceeded" in str(exc_info.value)


def test_budget_enforcer_tool_limit_breach():
    """Test budget enforcer raises error when tool invocations exceed limit."""
    budget = ExecutionBudget(max_tool_invocations=3)
    enforcer = BudgetEnforcer(budget)
    enforcer.record_tool_invocation(4)

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.check_budget()

    assert "Tool invocation budget exceeded" in str(exc_info.value)


def test_budget_enforcer_timeout():
    """Test budget enforcer detects wall-clock timeout."""
    budget = ExecutionBudget(max_wall_time_sec=0.05)
    enforcer = BudgetEnforcer(budget)
    time.sleep(0.08)

    with pytest.raises(BudgetExceededError) as exc_info:
        enforcer.check_budget()

    assert "Wall-clock timeout exceeded" in str(exc_info.value)


def test_checkpoint_registry_lifecycle():
    """Test saving, retrieving, and restoring checkpoints."""
    registry = CheckpointRegistry()
    session_id = "sess_test_101"

    cp1 = registry.save(
        session_id=session_id,
        turn_index=1,
        state_data={"step": "init", "count": 1},
        description="Initial state",
    )
    cp2 = registry.save(
        session_id=session_id,
        turn_index=2,
        state_data={"step": "processing", "count": 2},
        description="After processing",
    )

    assert cp1.checkpoint_id != cp2.checkpoint_id
    assert registry.get(cp1.checkpoint_id) == cp1

    history = registry.list_by_session(session_id)
    assert len(history) == 2
    assert history[0] == cp1
    assert history[1] == cp2

    latest = registry.latest(session_id)
    assert latest == cp2

    restored = registry.restore(cp1.checkpoint_id)
    assert restored["step"] == "init"
    assert restored["count"] == 1


def test_checkpoint_registry_prune():
    """Test pruning older checkpoints while retaining latest N."""
    registry = CheckpointRegistry()
    session_id = "sess_prune_test"

    for i in range(10):
        registry.save(session_id, turn_index=i, state_data={"index": i})

    assert len(registry.list_by_session(session_id)) == 10
    pruned = registry.prune(session_id, keep_latest=3)

    assert pruned == 7
    remaining = registry.list_by_session(session_id)
    assert len(remaining) == 3
    assert remaining[-1].turn_index == 9
    assert remaining[0].turn_index == 7


def test_harness_trace_and_telemetry():
    """Test HarnessTrace event recording and InvariantTelemetry counters."""
    trace = HarnessTrace(session_id="sess_trace_01")
    trace.record_event("prompt_received", {"length": 42})
    trace.set_metric("model_latency_ms", 120)
    trace.finish(status="completed")

    assert trace.status == "completed"
    assert trace.end_time is not None
    assert len(trace.events) == 2
    assert trace.events[0].event_type == "prompt_received"
    assert trace.events[1].event_type == "trace_finish"
    assert trace.metrics["model_latency_ms"] == 120

    telemetry = InvariantTelemetry()
    telemetry.record_budget_check(exceeded=False)
    telemetry.record_budget_check(exceeded=True)
    telemetry.record_checkpoint_saved()
    telemetry.record_checkpoint_restored()
    telemetry.record_trace_completed()

    assert telemetry.total_budget_checks == 2
    assert telemetry.total_budget_exceeded == 1
    assert telemetry.total_checkpoints_saved == 1
    assert telemetry.total_checkpoints_restored == 1
    assert telemetry.total_traces_recorded == 1
