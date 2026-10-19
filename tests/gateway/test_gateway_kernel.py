"""Tests for openviking_gateway kernel auto memory injection."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch
from openviking_gateway.config import GatewayConfig
from openviking_gateway.kernel import GatewayKernel, extract_user_query, inject_memory_context


def test_extract_user_query():
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "How do I use OpenViking?"},
        {"role": "assistant", "content": "OpenViking is a database..."},
        {"role": "user", "content": "Tell me more about VikingFS"},
    ]
    query = extract_user_query(messages)
    assert query == "Tell me more about VikingFS"


def test_inject_memory_context_existing_system():
    messages = [
        {"role": "system", "content": "Base system rules."},
        {"role": "user", "content": "Hello"},
    ]
    context_text = "VikingFS is an agent-native filesystem."
    new_messages = inject_memory_context(messages, context_text)

    assert len(new_messages) == 2
    assert new_messages[0]["role"] == "system"
    assert "<openviking_context>" in new_messages[0]["content"]
    assert "VikingFS is an agent-native filesystem." in new_messages[0]["content"]
    assert "Base system rules." in new_messages[0]["content"]


def test_inject_memory_context_no_system():
    messages = [
        {"role": "user", "content": "Hello without system"},
    ]
    context_text = "Context memo."
    new_messages = inject_memory_context(messages, context_text)

    assert len(new_messages) == 2
    assert new_messages[0]["role"] == "system"
    assert "<openviking_context>" in new_messages[0]["content"]
    assert new_messages[1]["role"] == "user"


@pytest.mark.asyncio
async def test_kernel_fetch_memories_fail_open_on_timeout():
    config = GatewayConfig(viking_core_url="http://127.0.0.1:1933")
    kernel = GatewayKernel(config)

    # Mock client raising timeout
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.TimeoutException("Search timeout")
    kernel._client = mock_client
    kernel._owns_client = False

    # Should not raise exception, but gracefully return empty list
    results = await kernel.fetch_memories("any query")
    assert results == []
