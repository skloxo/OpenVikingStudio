# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Agent Loop Telemetry & Observability (Card-Observability-AgentLoop-Telemetry - v1.5.09)
"""

import time
import pytest

from openviking.core.agent_loop import (
    AgentMessage,
    OnionGuardConfig,
    ToolCallResult,
    TwoTierAgentLoop,
)
from openviking.core.agent_loop_telemetry import (
    AgentLoopTelemetryCollector,
    get_agent_loop_telemetry_collector,
)


@pytest.fixture(autouse=True)
def reset_telemetry():
    """Reset telemetry collector before and after each test."""
    collector = get_agent_loop_telemetry_collector()
    collector.reset()
    yield
    collector.reset()


def test_telemetry_collector_singleton():
    c1 = get_agent_loop_telemetry_collector()
    c2 = AgentLoopTelemetryCollector.get_instance()
    assert c1 is c2
    snap = c1.get_snapshot()
    assert snap.status == "healthy"
    assert snap.interjection_queue_depth == 0
    assert snap.active_brake_count == 0


def test_interjection_queue_tracking():
    collector = get_agent_loop_telemetry_collector()
    collector.record_interjection_queued(2)
    snap = collector.get_snapshot()
    assert snap.interjection_queue_depth == 2
    assert snap.interjection_total_queued == 2

    collector.record_interjection_drained(1)
    snap2 = collector.get_snapshot()
    assert snap2.interjection_queue_depth == 1
    assert snap2.interjection_total_drained == 1

    collector.record_interjection_drained(1)
    snap3 = collector.get_snapshot()
    assert snap3.interjection_queue_depth == 0
    assert snap3.interjection_total_drained == 2


def test_active_brake_and_turn_completion():
    collector = get_agent_loop_telemetry_collector()
    collector.record_active_brake("multi_metric_gate")
    collector.record_turn_finished("completed", inner_steps=4, terminated_early=True)

    snap = collector.get_snapshot()
    assert snap.active_brake_count >= 1
    assert snap.turns_completed == 1
    assert snap.total_turns == 1
    assert snap.total_inner_steps == 4
    assert snap.last_turn_inner_steps == 4


def test_model_defense_metrics():
    collector = get_agent_loop_telemetry_collector()
    collector.record_model_retry(exhausted=False)
    collector.record_model_retry(exhausted=False)
    collector.record_model_retry(exhausted=True)

    snap = collector.get_snapshot()
    assert snap.model_defense_retries_total == 3
    assert snap.model_defense_exhausted_total == 1
    # 2 recovered out of 3 = 66.7%
    assert snap.model_recovery_rate == 66.7


def test_merkle_diff_recording():
    collector = get_agent_loop_telemetry_collector()
    collector.record_merkle_diff(1.234, file_count=50, version=2)

    snap = collector.get_snapshot()
    assert snap.merkle_last_diff_ms == 1.234
    assert snap.merkle_tree_file_count == 50
    assert snap.merkle_version == 2


def test_two_tier_agent_loop_telemetry_integration():
    """Verify that running a turn in TwoTierAgentLoop automatically records telemetry."""
    collector = get_agent_loop_telemetry_collector()

    def mock_invoker(messages):
        return AgentMessage(role="assistant", content="All tasks verified.")

    def mock_dispatcher(name, args):
        return ToolCallResult(call_id="c1", tool_name=name, output="ok")

    loop = TwoTierAgentLoop(model_invoker=mock_invoker, tool_dispatcher=mock_dispatcher)

    # Test interrupt queued before run
    loop.interrupt(AgentMessage(role="user", content="Interrupt 1"))
    snap_queued = collector.get_snapshot()
    assert snap_queued.interjection_total_queued == 1

    res = loop.run_turn("Do something")
    assert res.status.value == "completed"

    snap_after = collector.get_snapshot()
    assert snap_after.interjection_total_drained == 1
    assert snap_after.interjection_queue_depth == 0
    assert snap_after.turns_completed == 1
    assert snap_after.total_inner_steps >= 1


def test_two_tier_agent_loop_active_brake_telemetry():
    """Verify that returning terminate: true in a tool automatically records active brake."""
    collector = get_agent_loop_telemetry_collector()

    step = 0

    def mock_invoker(messages):
        nonlocal step
        step += 1
        if step == 1:
            return AgentMessage(
                role="assistant",
                content="Dispatching gate",
                tool_calls=[{"name": "multi_metric_gate", "id": "call_1", "args": {}}],
            )
        return AgentMessage(role="assistant", content="Done")

    def mock_dispatcher(name, args):
        # Trigger early termination
        return ToolCallResult(call_id="call_1", tool_name=name, output="Gate Passed. Early brake.", terminate=True)

    loop = TwoTierAgentLoop(model_invoker=mock_invoker, tool_dispatcher=mock_dispatcher)
    res = loop.run_turn("Verify codebase")

    assert res.terminated_early is True
    snap = collector.get_snapshot()
    assert snap.active_brake_count >= 1
    assert snap.turns_completed == 1


def test_simulation_probe():
    collector = get_agent_loop_telemetry_collector()

    res_inj = collector.simulate_probe("inject_interjection", count=3, auto_drain=True)
    assert res_inj["success"] is True

    res_brake = collector.simulate_probe("simulate_brake", tool_name="test_guard", steps=2)
    assert res_brake["success"] is True

    res_merkle = collector.simulate_probe("probe_merkle", file_count=99)
    assert res_merkle["success"] is True
    assert res_merkle["file_count"] == 99

    snap = collector.get_snapshot()
    assert snap.interjection_total_queued >= 3
    assert snap.active_brake_count >= 1
    assert snap.merkle_tree_file_count == 99
