"""Tests for openviking_gateway hidden tool loop engine."""

import json
import pytest
from unittest.mock import AsyncMock
from openviking_gateway.config import GatewayConfig
from openviking_gateway.tool_loop import (
    HiddenToolLoopExecutor,
    VIKING_HIDDEN_TOOLS_OPENAI,
    has_viking_tool_calls,
)


def test_viking_hidden_tools_definition():
    assert len(VIKING_HIDDEN_TOOLS_OPENAI) >= 2
    tool_names = [t["function"]["name"] for t in VIKING_HIDDEN_TOOLS_OPENAI]
    assert "openviking_read" in tool_names
    assert "openviking_find" in tool_names


def test_has_viking_tool_calls():
    choice_with_tool = {
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "openviking_read", "arguments": '{"uri":"viking://a"}'},
                }
            ],
        }
    }
    assert has_viking_tool_calls(choice_with_tool) is True

    choice_without_tool = {
        "message": {"role": "assistant", "content": "Just text answer"}
    }
    assert has_viking_tool_calls(choice_without_tool) is False


@pytest.mark.asyncio
async def test_hidden_tool_loop_single_iteration():
    config = GatewayConfig()
    executor = HiddenToolLoopExecutor(config)

    # Mock tool dispatcher: executing openviking_read
    async def mock_execute(name: str, args: dict):
        if name == "openviking_read":
            return json.dumps({"status": "ok", "content": "File content from VikingFS"})
        return json.dumps({"error": "Unknown tool"})

    executor.dispatch_tool = mock_execute

    messages = [{"role": "user", "content": "Read my notes"}]
    tool_call_item = {
        "id": "call_abc",
        "type": "function",
        "function": {"name": "openviking_read", "arguments": '{"uri": "viking://notes.md"}'},
    }

    updated_messages = await executor.append_tool_execution(
        messages,
        assistant_message={"role": "assistant", "tool_calls": [tool_call_item]},
        tool_call=tool_call_item,
    )

    # Must contain original user message, assistant tool_call message, and tool result message
    assert len(updated_messages) == 3
    assert updated_messages[0]["role"] == "user"
    assert updated_messages[1]["role"] == "assistant"
    assert updated_messages[2]["role"] == "tool"
    assert updated_messages[2]["tool_call_id"] == "call_abc"
    assert "File content from VikingFS" in updated_messages[2]["content"]
