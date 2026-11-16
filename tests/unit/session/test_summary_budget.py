# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Unit tests for #6771 Working Memory summary budget and rolling compression."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from openviking.message import Message, TextPart
from openviking.session.session import Session
from openviking.session.summary_budget import limit_summary_output_tokens
from openviking.utils.token_estimation import estimate_text_tokens


def _msg(msg_id: str, role: str, text: str) -> Message:
    return Message(
        id=msg_id,
        role=role,
        parts=[TextPart(text)],
    )


def test_limit_summary_output_tokens_respects_configured_and_failover_vlm():
    plain_vlm = SimpleNamespace(max_tokens=2048)
    assert limit_summary_output_tokens(plain_vlm, 5000) == 2048
    assert limit_summary_output_tokens(plain_vlm, 512) == 512

    failover = SimpleNamespace(
        _vlm_instances=[SimpleNamespace(max_tokens=4096), SimpleNamespace(max_tokens=1024)]
    )
    assert limit_summary_output_tokens(failover, 3000) == 1024

    primary_backup = SimpleNamespace(
        primary=SimpleNamespace(max_tokens=None),
        backup=SimpleNamespace(max_tokens=768),
    )
    assert limit_summary_output_tokens(primary_backup, 1500) == 768


@pytest.mark.asyncio
async def test_session_context_reserves_summary_before_active_messages():
    overview = "Working summary " * 40
    overview_tokens = estimate_text_tokens(overview)
    session = Session(viking_fs=None, session_id="ctx-budget")
    session._collect_session_context_components = AsyncMock(
        return_value={
            "latest_archive": {
                "archive_id": "archive_001",
                "archive_uri": "viking://user/default/sessions/ctx-budget/history/archive_001",
                "overview": overview,
                "overview_tokens": overview_tokens,
            },
            "pre_archive_abstracts": [],
            "total_archives": 1,
            "failed_archives": 0,
            "messages": [
                _msg("m1", "user", "first user message " * 30),
                _msg("m1_a", "assistant", "older reply " * 10),
                _msg("m2_u", "user", "hi"),
                _msg("m2", "assistant", "latest answer"),
            ],
        }
    )

    budget = overview_tokens + 20
    ctx = await session.get_session_context(token_budget=budget)
    assert ctx["latest_archive_overview"] == overview
    assert ctx["estimatedTokens"] <= budget
    assert [m["id"] for m in ctx["messages"]] == ["m2_u", "m2"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "retry_enabled,summary_ratio",
    [(False, 0.0002), (True, 0.0002), (True, None)],
)
async def test_wm_creation_retries_over_budget_summary_with_reasoning_effort(
    monkeypatch, retry_enabled, summary_ratio
):
    session = Session(viking_fs=None)
    calls: list[dict] = []
    outputs = ["x" * 12000, "y" * 12000, "final compact summary"]

    class FakeVLM:
        @staticmethod
        def is_available() -> bool:
            return True

        async def get_completion_async(self, *args, **kwargs):
            if args:
                kwargs["prompt"] = args[0]
            calls.append(kwargs)
            return outputs[len(calls) - 1]

    vlm = FakeVLM()
    monkeypatch.setattr(
        "openviking.session.session.get_openviking_config",
        lambda: SimpleNamespace(
            vlm=vlm, memory=SimpleNamespace(summary_budget_retry_enabled=retry_enabled)
        ),
    )

    kwargs = {"session_window_context": 10000, "reasoning_effort": "low"}
    if summary_ratio is not None:
        kwargs["summary_token_ratio"] = summary_ratio

    result = await session._generate_archive_summary_async(
        [_msg("u1", "user", "summarize the latest deployment status")],
        **kwargs,
    )

    if not retry_enabled:
        assert result == outputs[0]
        assert len(calls) == 1
        assert calls[0]["reasoning_effort"] == "low"
        return

    assert result == "final compact summary"
    assert calls[0]["max_tokens"] == 10000 - estimate_text_tokens(calls[0]["prompt"]) - 4
    assert calls[1]["max_tokens"] < calls[0]["max_tokens"]
    assert calls[2]["max_tokens"] == (2500 if summary_ratio is None else 2)
    assert [call["reasoning_effort"] for call in calls] == ["low", "low", "low"]
    assert calls[1]["messages"][0]["role"] == "system"
    assert calls[1]["messages"][1]["content"] == outputs[0]


@pytest.mark.asyncio
async def test_rolling_summary_splits_oversized_archive_and_carries_overview(monkeypatch):
    session = Session(viking_fs=None)
    seen_priors: list[str] = []

    class FakeVLM:
        @staticmethod
        def is_available() -> bool:
            return True

        async def get_completion_async(self, *args, **kwargs):
            return "compact overview"

    vlm = FakeVLM()
    monkeypatch.setattr(
        "openviking.session.session.get_openviking_config",
        lambda: SimpleNamespace(vlm=vlm, memory=SimpleNamespace(summary_budget_retry_enabled=False)),
    )

    async def fake_single(messages, latest_archive_overview="", **kwargs):
        del kwargs
        seen_priors.append(latest_archive_overview)
        return f"overview-step-{len(seen_priors)}"

    monkeypatch.setattr(session, "_generate_archive_summary_async", fake_single)

    long_messages = [
        _msg(f"m{i}", "user" if i % 2 == 0 else "assistant", ("detail token segment " * 80))
        for i in range(6)
    ]
    overview = await session._generate_archive_summary_with_batching(
        long_messages,
        latest_archive_overview="",
        session_window_context=2000,
    )

    assert len(seen_priors) >= 2
    assert seen_priors[0] == ""
    assert seen_priors[1] == "overview-step-1"
    assert overview == f"overview-step-{len(seen_priors)}"


@pytest.mark.asyncio
async def test_commit_validates_ratios_and_enable_working_memory_type():
    session = Session(viking_fs=None, session_id="validate-commit")
    with pytest.raises(ValueError, match="summary_token_ratio"):
        await session.commit_async(summary_token_ratio=0)
    with pytest.raises(ValueError, match="retained_token_ratio"):
        await session.commit_async(retained_token_ratio=0)
    with pytest.raises(ValueError, match="enable_working_memory"):
        await session.commit_async(enable_working_memory="yes")  # type: ignore[arg-type]
