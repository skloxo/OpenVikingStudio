# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for EntropyGatekeeper (Card-Entropy-01-Gatekeeper)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.service.entropy_gatekeeper import (
    EntropyGatekeeper,
    GatekeeperDecision,
)


@pytest.fixture
def gatekeeper():
    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()
    return gk


def test_gatekeeper_singleton():
    gk1 = EntropyGatekeeper.get_instance()
    gk2 = EntropyGatekeeper.get_instance()
    assert gk1 is gk2


@pytest.mark.asyncio
async def test_gatekeeper_short_content_bypass(gatekeeper):
    """Very short strings or trivial tokens should directly pass without vector probing."""
    decision = await gatekeeper.evaluate_and_intercept(
        uri="viking://resources/test.md",
        content="short",
    )
    assert decision.action == "add"
    assert "too short" in decision.reason.lower()


@pytest.mark.asyncio
async def test_gatekeeper_noop_deduplication(gatekeeper):
    """Similarity >= 0.97 should be flagged as NOOP (deduplicated) to save file I/O."""
    mock_hit = MagicMock()
    mock_hit.score = 0.985
    mock_hit.uri = "viking://resources/master_memory/lesson_1.md"
    mock_hit.content = "Existing stable lesson about 2080Ti VRAM allocation."

    with patch.object(gatekeeper, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (mock_hit.score, mock_hit.uri, mock_hit.content)

        text = "Existing stable lesson about 2080Ti VRAM allocation."
        decision = await gatekeeper.evaluate_and_intercept(
            uri="viking://resources/master_memory/lesson_duplicate.md",
            content=text,
        )

        assert decision.action == "noop"
        assert decision.similarity == 0.985
        assert decision.matched_uri == mock_hit.uri
        assert decision.saved_bytes == len(text.encode("utf-8"))
        assert "noop" in decision.reason.lower() or "deduplicated" in decision.reason.lower()

    # Check telemetry stats
    stats = gatekeeper.get_stats()
    assert stats["stats"]["noop"] == 1
    assert stats["stats"]["saved_bytes"] > 0
    assert len(stats["history"]) == 1


@pytest.mark.asyncio
async def test_gatekeeper_update_gold_band(gatekeeper):
    """Similarity in [0.92, 0.97) is the counter-example & condition refinement gold band."""
    mock_hit = MagicMock()
    mock_hit.score = 0.942
    mock_hit.uri = "viking://resources/master_memory/lesson_1.md"
    mock_hit.content = "Support CUDA 12 on Linux x86_64 host."

    with patch.object(gatekeeper, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (mock_hit.score, mock_hit.uri, mock_hit.content)

        text = "Notice: CUDA 12 crashes on macOS arm64 host under emulation."
        decision = await gatekeeper.evaluate_and_intercept(
            uri="viking://resources/master_memory/lesson_macos_counter.md",
            content=text,
        )

        assert decision.action == "update"
        assert decision.similarity == 0.942
        assert decision.matched_uri == mock_hit.uri
        assert "gold band" in decision.reason.lower() or "refinement" in decision.reason.lower()

    stats = gatekeeper.get_stats()
    assert stats["stats"]["update"] == 1


@pytest.mark.asyncio
async def test_gatekeeper_add_new_knowledge(gatekeeper):
    """Similarity < 0.92 is independent new knowledge."""
    mock_hit = MagicMock()
    mock_hit.score = 0.450
    mock_hit.uri = "viking://resources/master_memory/other.md"
    mock_hit.content = "Unrelated database schema documentation."

    with patch.object(gatekeeper, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (mock_hit.score, mock_hit.uri, mock_hit.content)

        text = "Brand new financial technical analysis momentum factor formulation."
        decision = await gatekeeper.evaluate_and_intercept(
            uri="viking://resources/master_memory/factor_momentum.md",
            content=text,
        )

        assert decision.action == "add"
        assert decision.similarity == 0.450

    stats = gatekeeper.get_stats()
    assert stats["stats"]["add"] == 1


@pytest.mark.asyncio
async def test_gatekeeper_fail_open_on_exception(gatekeeper):
    """If vector probe encounters any runtime failure, Gatekeeper must fail-open safely."""
    with patch.object(gatekeeper, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.side_effect = RuntimeError("GPU memory bus timeout")

        decision = await gatekeeper.evaluate_and_intercept(
            uri="viking://resources/master_memory/lesson_safety.md",
            content="Critical safety lesson that should not be blocked by probe error.",
        )

        # Fail-open contract: must return "add" so business write continues normally
        assert decision.action == "add"
        assert "fail-open" in decision.reason.lower()


@pytest.mark.asyncio
async def test_gatekeeper_self_check_dedup_at_85(gatekeeper):
    """Self-check and audit reports should be deduplicated (NOOP) at similarity >= 0.85."""
    mock_hit = MagicMock()
    mock_hit.score = 0.8862
    mock_hit.uri = "viking://resources/master_memory/evolution_lessons/3070_self_check_1.md"
    mock_hit.content = "3070 卫星节点全链路自检通过，双向读写链路畅通验证。"

    with patch.object(gatekeeper, "_probe_nearest_vector", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (mock_hit.score, mock_hit.uri, mock_hit.content)

        text = "3070 WorkBuddy 卫星节点体外大脑全链路自检，4项自检通过。"
        decision = await gatekeeper.evaluate_and_intercept(
            uri="viking://resources/master_memory/evolution_lessons/3070_self_check_2.md",
            content=text,
        )

        assert decision.action == "noop"
        assert decision.similarity == 0.8862
        assert "自检去重" in decision.reason or "noop" in decision.reason.lower()


@pytest.mark.asyncio
async def test_gatekeeper_blocks_scratch_and_encoded_scripts(gatekeeper):
    """Temporary scratch scripts and Base64 encoded commands must be intercepted to DLQ."""
    # Test 1: URI containing _scratch_
    decision1 = await gatekeeper.evaluate_and_intercept(
        uri="viking://resources/windows_work_干部宿舍_docs_scratch_cmd_encoded.md",
        content="some powershell script content",
    )
    assert decision1.action == "dlq"
    assert "临时脚本阻断" in decision1.reason

    # Test 2: Content is Base64 encoded PowerShell blob
    raw_b64 = "CgAkAGQAYQB0AGEARABpAHIAIAA9ACAAJwBjADoAXABVAHMAZQByAHMAXABTAGsAbABcAE8AbgBlAEQAcgBpAHYAZQAgAC0AIABzAGsAbABvAHgAbwBcAFcAbwByAGsAXABy"
    decision2 = await gatekeeper.evaluate_and_intercept(
        uri="viking://resources/some_script.md",
        content=raw_b64,
    )
    assert decision2.action == "dlq"
    assert "临时脚本阻断" in decision2.reason

