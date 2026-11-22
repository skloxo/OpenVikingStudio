"""Tests for openviking_gateway async session capture."""

import json
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
async def test_capture_engine_fail_open(tmp_path):
    config = GatewayConfig(viking_core_url="http://127.0.0.1:1933")
    engine = SessionCaptureEngine(config)
    engine._local_ledger_dir = tmp_path

    # Mock client failure
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("Core service unreachable")
    engine._client = mock_client
    engine._owns_client = False

    # Should not raise exception and must fall back to local JSONL ledger
    await engine.capture_turn(
        messages=[{"role": "user", "content": "test"}],
        assistant_reply="response",
        model="gpt-4o",
    )

    mock_client.post.assert_awaited_once()
    call_args = mock_client.post.await_args
    assert call_args.args[0] == "http://127.0.0.1:1933/api/v1/sessions/capture"
    payload = call_args.kwargs["json"]
    assert payload["user_prompt"] == "test"
    assert payload["assistant_reply"] == "response"
    assert payload["model"] == "gpt-4o"

    ledger_file = tmp_path / "gateway_sessions.jsonl"
    assert ledger_file.exists()
    saved = json.loads(ledger_file.read_text(encoding="utf-8").strip().splitlines()[0])
    assert saved["user_prompt"] == "test"
    assert saved["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_capture_engine_http_500_fallback(tmp_path):
    config = GatewayConfig(viking_core_url="http://127.0.0.1:1933")
    engine = SessionCaptureEngine(config)
    engine._local_ledger_dir = tmp_path

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = httpx.Response(
        502,
        request=httpx.Request("POST", "http://127.0.0.1:1933/api/v1/sessions/capture"),
    )
    engine._client = mock_client
    engine._owns_client = False

    await engine.capture_turn(
        messages=[{"role": "user", "content": "retry check"}],
        assistant_reply="fallback logged",
        model="deepseek-chat",
    )

    mock_client.post.assert_awaited_once()
    ledger_file = tmp_path / "gateway_sessions.jsonl"
    assert ledger_file.exists()
    saved = json.loads(ledger_file.read_text(encoding="utf-8").strip().splitlines()[0])
    assert saved["user_prompt"] == "retry check"
    assert saved["assistant_reply"] == "fallback logged"
