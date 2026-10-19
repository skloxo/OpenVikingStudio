"""Integration tests for openviking_gateway API endpoints."""

import json
import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from openviking_gateway.config import GatewayConfig
from openviking_gateway.app import create_gateway_app


@pytest.fixture
def test_app():
    config = GatewayConfig(
        upstream_base_url="https://api.openai-mock.com/v1",
        upstream_api_key="mock-key-123",
        default_model="mock-gpt",
    )
    app = create_gateway_app(config)
    return app


def test_health_endpoint(test_app):
    client = TestClient(test_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["gateway"] == "openviking_gateway"
    assert data["port"] == 1934
    assert "version" in data


def test_models_endpoint(test_app):
    client = TestClient(test_app)
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert len(data["data"]) >= 1
    assert data["data"][0]["id"] == "mock-gpt"


def test_chat_completions_non_stream_direct(test_app):
    client = TestClient(test_app)

    mock_openai_resp = {
        "id": "chatcmpl-test-01",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "mock-gpt",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from mock LLM!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 6, "total_tokens": 11},
    }

    with patch.object(
        test_app.state.proxy,
        "forward_chat_completions",
        new_callable=AsyncMock,
    ) as mock_forward:
        from starlette.responses import JSONResponse
        mock_forward.return_value = JSONResponse(content=mock_openai_resp)

        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "mock-gpt",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "chatcmpl-test-01"
        assert data["choices"][0]["message"]["content"] == "Hello from mock LLM!"


def test_anthropic_messages_non_stream_with_openai_upstream(test_app):
    client = TestClient(test_app)

    mock_anthropic_resp = {
        "id": "msg-test-01",
        "type": "message",
        "role": "assistant",
        "model": "claude-3-opus",
        "content": [{"type": "text", "text": "Hello Claude client!"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }

    with patch.object(
        test_app.state.proxy,
        "forward_messages",
        new_callable=AsyncMock,
    ) as mock_forward:
        from starlette.responses import JSONResponse
        mock_forward.return_value = JSONResponse(content=mock_anthropic_resp)

        resp = client.post(
            "/v1/messages",
            json={
                "model": "claude-3-opus",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1024,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "message"
        assert data["content"][0]["text"] == "Hello Claude client!"


def test_chat_completions_streaming_sse(test_app):
    client = TestClient(test_app)

    async def mock_stream_gen():
        yield b'data: {"id":"c1","choices":[{"delta":{"content":"Hi"}}]}\n\n'
        yield b'data: [DONE]\n\n'

    from starlette.responses import StreamingResponse

    with patch.object(
        test_app.state.proxy,
        "forward_chat_completions",
        new_callable=AsyncMock,
    ) as mock_forward:
        mock_forward.return_value = StreamingResponse(
            mock_stream_gen(), media_type="text/event-stream"
        )

        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "mock-gpt",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert 'data: {"id":"c1"' in resp.text


def test_anthropic_messages_streaming_sse(test_app):
    client = TestClient(test_app)

    async def mock_stream_gen():
        yield b'event: message_start\ndata: {"type":"message_start"}\n\n'
        yield b'event: message_stop\ndata: {"type":"message_stop"}\n\n'

    from starlette.responses import StreamingResponse

    with patch.object(
        test_app.state.proxy,
        "forward_messages",
        new_callable=AsyncMock,
    ) as mock_forward:
        mock_forward.return_value = StreamingResponse(
            mock_stream_gen(), media_type="text/event-stream"
        )

        resp = client.post(
            "/v1/messages",
            json={
                "model": "claude-3-opus",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1024,
                "stream": True,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert "event: message_start" in resp.text


def test_invalid_json_body_returns_400(test_app):
    client = TestClient(test_app)
    resp = client.post(
        "/v1/chat/completions",
        content="not-valid-json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
    assert "Invalid JSON body" in resp.json()["error"]["message"]

    resp2 = client.post(
        "/v1/messages",
        content="not-valid-json",
        headers={"content-type": "application/json"},
    )
    assert resp2.status_code == 400
    assert "Invalid JSON body" in resp2.json()["error"]["message"]


def test_chat_completions_auto_memory_injection(test_app):
    client = TestClient(test_app)

    # Mock kernel.fetch_memories returning real memory chunks
    async def mock_memories(query: str, top_k: int = 3):
        return [{"text": "Special Viking Project Rule: NO GREEN EVER", "uri": "viking://rules"}]

    test_app.state.proxy.kernel.fetch_memories = mock_memories

    captured_payload = {}

    async def mock_post(url, json=None, headers=None):
        nonlocal captured_payload
        captured_payload = json
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "chatcmpl-test",
            "choices": [{"message": {"role": "assistant", "content": "Acknowledged rule."}}],
        }
        return mock_resp

    test_app.state.proxy._client = MagicMock()
    test_app.state.proxy._client.is_closed = False
    test_app.state.proxy._client.post = AsyncMock(side_effect=mock_post)
    test_app.state.proxy._owns_client = False

    resp = client.post(
        "/v1/chat/completions",
        json={"model": "mock-gpt", "messages": [{"role": "user", "content": "What is the UI rule?"}]},
    )
    assert resp.status_code == 200
    # Assert system message was injected with retrieved memory
    injected_system = captured_payload["messages"][0]
    assert injected_system["role"] == "system"
    assert "Special Viking Project Rule: NO GREEN EVER" in injected_system["content"]


def test_chat_completions_hidden_tool_loop_integration(test_app):
    client = TestClient(test_app)

    # Disable memory injection for clean tool loop isolation
    test_app.state.proxy.config.enable_auto_memory_injection = False

    # Mock tool dispatching
    async def mock_dispatch(name: str, args: dict):
        return json.dumps({"content": "Retrieved secretly: secret_val_999"})

    test_app.state.proxy.tool_loop.dispatch_tool = mock_dispatch

    call_count = 0

    async def mock_multi_turn_post(url, json=None, headers=None):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        if call_count == 1:
            # First turn: model requests tool call
            mock_resp.json.return_value = {
                "id": "chatcmpl-turn-1",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "openviking_read", "arguments": '{"uri":"viking://secret"}'},
                                }
                            ],
                        }
                    }
                ],
            }
        else:
            # Second turn: model sees tool output and answers user cleanly
            mock_resp.json.return_value = {
                "id": "chatcmpl-turn-2",
                "choices": [{"message": {"role": "assistant", "content": "The secret is secret_val_999."}}],
            }
        return mock_resp

    test_app.state.proxy._client = MagicMock()
    test_app.state.proxy._client.is_closed = False
    test_app.state.proxy._client.post = AsyncMock(side_effect=mock_multi_turn_post)
    test_app.state.proxy._owns_client = False

    resp = client.post(
        "/v1/chat/completions",
        json={"model": "mock-gpt", "messages": [{"role": "user", "content": "What is the secret?"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert call_count == 2
    assert data["choices"][0]["message"]["content"] == "The secret is secret_val_999."



