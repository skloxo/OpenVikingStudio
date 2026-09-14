# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Two-Tier Agent Loop and Four-Layer Onion Guard (Card-Runtime-TwoTierAgentLoop-OnionGuard - v1.5.01)

Verifies:
1. Two-tier event loop (outer session control + inner tool/interrupt loop)
2. Mid-turn user interrupt (pending message queue, zero message loss)
3. Tool early termination contract (terminate: true)
4. Cooperative abort signal
5. Error tolerance & model fallback
"""

import threading
import time
from typing import Any, Dict, List
import pytest

from openviking.core.agent_loop import (
    AgentLoopStatus,
    AgentMessage,
    OnionGuardConfig,
    ToolCallResult,
    TurnResult,
    TwoTierAgentLoop,
)


def test_basic_single_turn_completion():
    """Test standard single turn with no tool calls."""
    def mock_model(messages: List[AgentMessage]) -> AgentMessage:
        return AgentMessage(role="assistant", content="Hello world")

    def mock_tools(name: str, args: Dict[str, Any]) -> ToolCallResult:
        return ToolCallResult(call_id="c1", tool_name=name, output="ok")

    loop = TwoTierAgentLoop(model_invoker=mock_model, tool_dispatcher=mock_tools)
    result = loop.run_turn(initial_prompt="Hi")

    assert result.status == AgentLoopStatus.COMPLETED
    assert result.final_message is not None
    assert result.final_message.content == "Hello world"
    assert result.inner_turns == 1
    assert not result.terminated_early


def test_tool_iteration_and_resolution():
    """Test inner loop iterating through tool call and subsequent response."""
    step = 0

    def mock_model(messages: List[AgentMessage]) -> AgentMessage:
        nonlocal step
        step += 1
        if step == 1:
            return AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "call_1", "name": "get_weather", "args": {"city": "Beijing"}}],
            )
        return AgentMessage(role="assistant", content="The weather in Beijing is Sunny.")

    def mock_tools(name: str, args: Dict[str, Any]) -> ToolCallResult:
        return ToolCallResult(call_id="call_1", tool_name=name, output="Sunny, 22C")

    loop = TwoTierAgentLoop(model_invoker=mock_model, tool_dispatcher=mock_tools)
    result = loop.run_turn(initial_prompt="What is Beijing weather?")

    assert result.status == AgentLoopStatus.COMPLETED
    assert result.final_message.content == "The weather in Beijing is Sunny."
    assert result.inner_turns == 2
    assert any(m.role == "tool" for m in result.history)


def test_tool_early_termination_contract():
    """Test tool returning terminate=True immediately halts inner loop."""
    def mock_model(messages: List[AgentMessage]) -> AgentMessage:
        return AgentMessage(
            role="assistant",
            content="",
            tool_calls=[
                {"id": "call_term", "name": "early_exit", "args": {"reason": "done"}},
                {"id": "call_skipped", "name": "never_run", "args": {}},
            ],
        )

    dispatched_tools = []

    def mock_tools(name: str, args: Dict[str, Any]) -> ToolCallResult:
        dispatched_tools.append(name)
        if name == "early_exit":
            return ToolCallResult(
                call_id="call_term",
                tool_name=name,
                output="Goal reached immediately",
                terminate=True,
            )
        return ToolCallResult(call_id="call_skipped", tool_name=name, output="fail")

    loop = TwoTierAgentLoop(model_invoker=mock_model, tool_dispatcher=mock_tools)
    result = loop.run_turn(initial_prompt="Execute with brake")

    assert result.status == AgentLoopStatus.COMPLETED
    assert result.terminated_early is True
    assert "early_exit" in dispatched_tools
    assert "never_run" not in dispatched_tools
    assert result.final_message.content == "Goal reached immediately"


def test_mid_turn_user_interrupt_zero_message_loss():
    """Test queuing pending messages mid-turn is picked up by inner loop."""
    step = 0

    def mock_model(messages: List[AgentMessage]) -> AgentMessage:
        nonlocal step
        step += 1
        if step == 1:
            return AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "c1", "name": "slow_task", "args": {}}],
            )
        # Verify user interrupt message was injected
        has_interrupt = any("Stop and look" in m.content for m in messages if m.role == "user")
        if has_interrupt:
            return AgentMessage(role="assistant", content="Acknowledged interrupt and adjusted.")
        return AgentMessage(role="assistant", content="Normal finish.")

    def mock_tools(name: str, args: Dict[str, Any]) -> ToolCallResult:
        # Simulate user injecting message while tool is running
        loop.interrupt(AgentMessage(role="user", content="Stop and look at this urgent update!"))
        return ToolCallResult(call_id="c1", tool_name=name, output="task done")

    loop = TwoTierAgentLoop(model_invoker=mock_model, tool_dispatcher=mock_tools)
    result = loop.run_turn(initial_prompt="Start workflow")

    assert result.status == AgentLoopStatus.COMPLETED
    assert "Acknowledged interrupt" in result.final_message.content
    assert any("Stop and look" in m.content for m in result.history)


def test_cooperative_abort_signal():
    """Test abort() cleanly breaks inner loop with ABORTED status."""
    def mock_model(messages: List[AgentMessage]) -> AgentMessage:
        return AgentMessage(
            role="assistant",
            content="",
            tool_calls=[{"id": "c_abort", "name": "check_status", "args": {}}],
        )

    def mock_tools(name: str, args: Dict[str, Any]) -> ToolCallResult:
        loop.abort("Emergency halt by operator")
        return ToolCallResult(call_id="c_abort", tool_name=name, output="ok")

    loop = TwoTierAgentLoop(model_invoker=mock_model, tool_dispatcher=mock_tools)
    result = loop.run_turn(initial_prompt="Run dangerous command")

    assert result.status == AgentLoopStatus.ABORTED
    assert result.aborted_reason == "Emergency halt by operator"


def test_model_defense_retry_and_graceful_degrade():
    """Test layer 2 model defense retries on transient errors and degrades gracefully."""
    attempts = 0

    def mock_failing_model(messages: List[AgentMessage]) -> AgentMessage:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Transient network timeout")
        return AgentMessage(role="assistant", content="Recovered from transient error")

    def mock_tools(name: str, args: Dict[str, Any]) -> ToolCallResult:
        return ToolCallResult(call_id="c", tool_name=name, output="ok")

    config = OnionGuardConfig(max_retries=3)
    loop = TwoTierAgentLoop(
        model_invoker=mock_failing_model,
        tool_dispatcher=mock_tools,
        config=config,
    )
    result = loop.run_turn(initial_prompt="Try connection")

    assert result.status == AgentLoopStatus.COMPLETED
    assert result.final_message.content == "Recovered from transient error"
    assert attempts == 3
