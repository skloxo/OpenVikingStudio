"""Tests for openviking_gateway protocol translation and dual-track engine."""

import pytest
from openviking_gateway.protocols import (
    anthropic_to_openai_request,
    openai_to_anthropic_response,
    OpenAIToAnthropicStreamAdapter,
    AnthropicMessagesRequest,
    AnthropicMessage,
)


def test_anthropic_to_openai_request_basic():
    anthropic_req = AnthropicMessagesRequest(
        model="claude-3-5-sonnet",
        max_tokens=1024,
        system="You are a helpful coding assistant.",
        messages=[
            AnthropicMessage(role="user", content="Hello world"),
        ],
        temperature=0.7,
        stream=False,
    )

    openai_req = anthropic_to_openai_request(anthropic_req)
    assert openai_req["model"] == "claude-3-5-sonnet"
    assert openai_req["max_tokens"] == 1024
    assert openai_req["temperature"] == 0.7
    assert openai_req["stream"] is False

    # System message must be prepended
    msgs = openai_req["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "You are a helpful coding assistant."
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "Hello world"


def test_anthropic_to_openai_request_with_content_blocks():
    anthropic_req = AnthropicMessagesRequest(
        model="claude-3-opus",
        messages=[
            AnthropicMessage(
                role="user",
                content=[
                    {"type": "text", "text": "Part 1"},
                    {"type": "text", "text": "Part 2"},
                ],
            )
        ],
    )
    openai_req = anthropic_to_openai_request(anthropic_req)
    msgs = openai_req["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Part 1\nPart 2"


def test_openai_to_anthropic_response_basic():
    openai_resp = {
        "id": "chatcmpl-12345",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I am an assistant.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
        },
    }

    anthropic_resp = openai_to_anthropic_response(openai_resp)
    assert anthropic_resp["id"] == "chatcmpl-12345"
    assert anthropic_resp["type"] == "message"
    assert anthropic_resp["role"] == "assistant"
    assert anthropic_resp["model"] == "deepseek-chat"
    assert anthropic_resp["stop_reason"] == "end_turn"
    assert len(anthropic_resp["content"]) == 1
    assert anthropic_resp["content"][0]["type"] == "text"
    assert anthropic_resp["content"][0]["text"] == "Hello! I am an assistant."
    assert anthropic_resp["usage"]["input_tokens"] == 12
    assert anthropic_resp["usage"]["output_tokens"] == 8


def test_openai_stream_to_anthropic_events_adapter():
    adapter = OpenAIToAnthropicStreamAdapter(model="deepseek-chat")

    # Chunk 1: first token
    chunk1 = {
        "id": "chatcmpl-chunk1",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": "Hello"},
                "finish_reason": None,
            }
        ],
    }
    events1 = adapter.process_chunk(chunk1)
    event_types1 = [e[0] for e in events1]
    assert "message_start" in event_types1
    assert "content_block_start" in event_types1
    assert "content_block_delta" in event_types1

    # Chunk 2: middle token
    chunk2 = {
        "id": "chatcmpl-chunk1",
        "choices": [
            {
                "index": 0,
                "delta": {"content": " world"},
                "finish_reason": None,
            }
        ],
    }
    events2 = adapter.process_chunk(chunk2)
    assert len(events2) == 1
    assert events2[0][0] == "content_block_delta"
    assert events2[0][1]["delta"]["text"] == " world"

    # Chunk 3: finish chunk
    chunk3 = {
        "id": "chatcmpl-chunk1",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    events3 = adapter.process_chunk(chunk3)
    event_types3 = [e[0] for e in events3]
    assert "content_block_stop" in event_types3
    assert "message_delta" in event_types3
    assert "message_stop" in event_types3
