"""Tests for openviking_gateway async session capture."""

import pytest
import httpx
from unittest.mock import AsyncMock
from openviking_gateway.config import GatewayConfig
from openviking_gateway.capture import SessionCaptureEngine, dehydrate_conversation_turn


def test_dehydrate_conversation_turn():
    messages = [
        {"role": "system", "content": "System prompt with memo"},
        {"role": "user", "content": "How to deploy?"},
    ]
    final_reply = "Use npm run release:sync to deploy."

    turn = dehydrate_conversation_turn(messages, final_reply, model="deepseek-chat")
    assert turn["user_prompt"] == "How to deploy?"
    assert turn["assistant_reply"] == "Use npm run release:sync to deploy."
    assert turn["model"] == "deepseek-chat"
    assert "timestamp" in turn


@pytest.mark.asyncio
async def test_capture_engine_fail_open():
    config = GatewayConfig(viking_core_url="http://127.0.0.1:1933")
    engine = SessionCaptureEngine(config)

    # Mock client failure
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("Core service unreachable")
    engine._client = mock_client
    engine._owns_client = False

    # Should not raise exception
    await engine.capture_turn(
        messages=[{"role": "user", "content": "test"}],
        assistant_reply="response",
        model="gpt-4o",
    )
