# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Retina unit tests for Card-204: Upstream Gateway telemetry and anti-duplicate recall."""

from __future__ import annotations

import time
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from openviking_gateway.config import GatewayConfig
from openviking_gateway.kernel import GatewayKernel, extract_user_query
from openviking_gateway.protocols import (
    auxiliary,
    clean_dsh_noise,
    is_dsh_noise,
    normalize_arguments_json,
    reply_chain,
    safe_append_delta,
)
from openviking_gateway.capture import dehydrate_conversation_turn, SessionCaptureEngine
from openviking.server.routers.gateway import (
    clear_gateway_events,
    get_gateway_events,
    record_gateway_request_event,
)
from openviking_gateway.overview import cache_alerts, overview_summary


@pytest.fixture(autouse=True)
def clean_events():
    clear_gateway_events()
    yield
    clear_gateway_events()


def test_dsh_noise_detection_and_cleaning():
    """Verify DSH and Agent runtime snapshots are safely identified and stripped."""
    img_noise = "Attached image(s) from tool result:\n"
    ctx_noise = "Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\nProject path: /app"
    time_noise = "Time sampled while preparing turn 1, step 2: 2026-10-20T12:00:00Z"

    assert is_dsh_noise(img_noise) is True
    assert is_dsh_noise(ctx_noise) is True
    assert is_dsh_noise(time_noise) is True
    assert is_dsh_noise("Normal user query about VikingFS") is False

    cleaned = clean_dsh_noise(f"{ctx_noise}\n\nHow do I configure memory?")
    assert cleaned == "How do I configure memory?"


def test_extract_user_query_strips_pure_noise():
    """Extract query should return empty when user message is pure diagnostic noise."""
    messages = [
        {"role": "system", "content": "System prompt"},
        {
            "role": "user",
            "content": "Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\nMetadata...",
        },
    ]
    assert extract_user_query(messages) == ""

    # When meaningful content follows
    messages.append({"role": "user", "content": "Deploy the blue cluster"})
    assert extract_user_query(messages) == "Deploy the blue cluster"


def test_dsh_title_and_auxiliary_classification():
    """DSH title generation and auxiliary patterns must classify as auxiliary without recall."""
    cfg = GatewayConfig(enable_auto_memory_injection=True)
    kernel = GatewayKernel(cfg)

    # DSH session title generation prompt
    title_messages = [
        {
            "role": "user",
            "content": 'Generate the session title from this JSON array:\n[{"seq":8,"action":"read"}]',
        }
    ]
    kind, should_recall = kernel.classify_request(title_messages, tools=None, session_id="sess-dsh-1")
    assert kind == "auxiliary"
    assert should_recall is False


@pytest.mark.asyncio
async def test_tool_less_side_request_in_tool_session_bypasses_recall():
    """A tool-less side request in a session that used client tools must bypass recall."""
    cfg = GatewayConfig(enable_auto_memory_injection=True)
    kernel = GatewayKernel(cfg)
    kernel.fetch_memories = AsyncMock(return_value=[{"text": "mock memory"}])

    tools = [{"type": "function", "function": {"name": "Bash", "parameters": {}}}]
    session_id = "sess-tool-active-42"

    # Turn 1: Main conversation turn with tools -> should recall
    turn1_msgs = [{"role": "user", "content": "List files in directory"}]
    res1 = await kernel.pre_flight_inject(turn1_msgs, tools=tools, session_id=session_id)
    assert kernel.last_classified_kind == "user"
    assert kernel.fetch_memories.call_count == 1
    assert "<openviking_context>" in res1[0]["content"]

    # Turn 2: Claude Code or DSH side request (e.g. summarize fetched webpage)
    # No tools, no prior assistant reply in this side exchange -> auxiliary!
    side_msgs = [
        {"role": "user", "content": "Web page content:\n---\nExample Domain\n---\nWhat is the title?"}
    ]
    res2 = await kernel.pre_flight_inject(side_msgs, tools=None, session_id=session_id)
    assert kernel.last_classified_kind == "auxiliary"
    # Call count should remain 1 (no new recall triggered!)
    assert kernel.fetch_memories.call_count == 1
    assert res2 == side_msgs


@pytest.mark.asyncio
async def test_capture_turn_skips_auxiliary_requests():
    """Session capture must strictly skip auxiliary requests to avoid ghost sessions."""
    cfg = GatewayConfig(enable_session_capture=True)
    capture_engine = SessionCaptureEngine(cfg)
    capture_engine.get_client = AsyncMock()

    messages = [{"role": "user", "content": "Generate the session title from..."}]
    # auxiliary request should immediately return without dispatching HTTP call
    await capture_engine.capture_turn(
        messages, "Session Title", model="deepseek-chat", kind="auxiliary"
    )
    capture_engine.get_client.assert_not_called()


def test_normalize_arguments_json():
    """Verify tool arguments compact spacing normalization."""
    raw = '{\n  "city": "Paris",\n  "count": 10\n}'
    normalized = normalize_arguments_json(raw)
    assert normalized == '{"city":"Paris","count":10}'
    assert normalize_arguments_json('{"city":"Paris"}') == '{"city":"Paris"}'
    assert normalize_arguments_json("invalid json") == "invalid json"


def test_reply_chain_incremental_continuity():
    """Incremental reply anchor hashing seeds from prior chain and continues deterministically."""
    prior = ["seed-digest-0"]
    chain1 = reply_chain(prior, "First assistant response")
    assert len(chain1) == 2
    assert chain1[0] == "seed-digest-0"

    chain2 = reply_chain(chain1, {"choices": [{"text": "Second turn"}]})
    assert len(chain2) == 3
    assert chain2[:2] == chain1


def test_safe_append_delta():
    """Verify in-place safe append for streaming buffers."""
    container = {}
    safe_append_delta(container, "text", "Hello")
    assert container["text"] == "Hello"
    safe_append_delta(container, "text", " World")
    assert container["text"] == "Hello World"
    safe_append_delta(container, "text", None)
    assert container["text"] == "Hello World"


def test_gateway_telemetry_event_recording_and_streak_alerts():
    """Verify gateway request events feed into overview summary and streak alerts."""
    now = time.time()
    sess_id = "sess-long-conversation"

    # Seed an earlier hit to confirm upstream-main supports caching
    record_gateway_request_event(
        {
            "time": now - 300,
            "duration_ms": 800.0,
            "status": 200,
            "protocol": "openai",
            "kind": "user",
            "session": "sess-prior-hit",
            "model": "deepseek-chat",
            "upstream_id": "upstream-main",
            "first_upstream_input_tokens": 10_000,
            "first_upstream_output_tokens": 100,
            "first_upstream_cached_tokens": 8_000,
            "first_upstream_cache_write_tokens": 0,
        }
    )

    # Simulate 3 consecutive requests with > 32k tokens missing prompt cache
    for i in range(3):
        record_gateway_request_event(
            {
                "time": now - (3 - i) * 60,
                "duration_ms": 1200.0,
                "status": 200,
                "protocol": "openai",
                "kind": "user" if i == 0 else "continuation",
                "session": sess_id,
                "model": "deepseek-chat",
                "upstream_id": "upstream-main",
                "first_upstream_input_tokens": 35_000,
                "first_upstream_output_tokens": 200,
                "first_upstream_cached_tokens": 0,
                "first_upstream_cache_write_tokens": 0,
            }
        )

    events = get_gateway_events()
    assert len(events) == 4

    # Check overview summary
    summary = overview_summary(events, now=now)
    assert summary["requests"] == 4
    assert summary["cache"]["first_call"]["requests"] == 2
    assert summary["cache"]["continuation"]["requests"] == 2

    # Check streak miss alerts
    alerts = cache_alerts(events, now=now)
    assert alerts is not None
    assert "misses" in alerts and alerts["misses"] is not None
    assert alerts["misses"]["conversations"] == 1
    assert alerts["misses"]["streak"] == 3
    assert alerts["misses"]["recent"][0]["upstream_id"] == "upstream-main"
