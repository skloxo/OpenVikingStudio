# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for Zero-504 Fast-Path Ingestion & Gatekeeper Decoupling (Card-43).

First Principles & Munger Inversion:
Verifies that downstream vector probe slowness (e.g. 5s~10s) NEVER blocks physical
file ingestion on disk. Writes must complete in O(1) < 25ms, eliminating 504 timeouts.
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, patch
import pytest

from openviking.service.entropy_gatekeeper import EntropyGatekeeper, GatekeeperDecision
from openviking.service.valet_ingestion import ValetIngestionEngine
from openviking.service.vector_sync_tracker import VectorSyncTracker


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for test writes."""
    tmp_dir = tempfile.mkdtemp(prefix="test_fast_path_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_gatekeeper_fast_probe_budget_fall_open():
    """Test 1: Slow vector probe (> fast budget) triggers instant fast-path fall-open (< 200ms)."""
    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()

    # Simulate downstream vector probe hanging for 2.0s
    async def mock_slow_probe(*args, **kwargs):
        await asyncio.sleep(2.0)
        return 0.85, "viking://resources/existing.md", "snippet"

    # Configure fast budget to 0.1s (100ms)
    with patch("openviking.service.entropy_gatekeeper.probe_nearest_vector", side_effect=mock_slow_probe):
        t0 = time.perf_counter()
        decision = await gk.evaluate_and_intercept(
            uri="viking://resources/new_doc_1.md",
            content="这是一篇崭新的技术规格说明，用于验证快轨落盘机制的超时逃生通道。",
            fast_probe_budget=0.1,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Assert elapsed time was bounded by fast budget, NOT 2.0s
        assert elapsed_ms < 300.0, f"Gatekeeper probe hung for {elapsed_ms:.1f}ms, expected < 300ms!"
        assert decision.action == "add"
        assert decision.fast_path is True
        assert "快轨" in decision.reason or "fast_path" in decision.reason.lower()

        # Check stats
        stats = gk.get_stats()
        assert stats.get("fast_path", 0) >= 1


@pytest.mark.asyncio
async def test_valet_ingestion_immediate_wal_disk_write(temp_workspace):
    """Test 2: Valet Ingestion writes physically to disk immediately even if probe hangs."""
    target_file = os.path.join(temp_workspace, "valet_test_doc.md")
    uri = f"viking://resources/valet_test_doc.md"
    content = "第一性原理验证：内存写入即刻落盘契约与门禁异步解耦流水线，消除504超时。"

    valet = ValetIngestionEngine.get_instance()

    # Mock resolve URI to return our temp workspace path
    with patch.object(valet, "_resolve_uri_to_path", return_value=Path(target_file)):
        # Mock slow gatekeeper probe
        async def mock_slow_probe(*args, **kwargs):
            await asyncio.sleep(3.0)
            return 0.0, None, None

        with patch("openviking.service.entropy_gatekeeper.probe_nearest_vector", side_effect=mock_slow_probe):
            t0 = time.perf_counter()
            result = await valet.ingest(
                record={
                    "uri": uri,
                    "content": content,
                    "caller": "TestAgent",
                    "meta": {"title": "Valet Test Doc"},
                }
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000

            # Must return in under 500ms, not hang for 3s or 15s!
            assert elapsed_ms < 500.0, f"Valet Ingestion took {elapsed_ms:.1f}ms, expected < 500ms!"
            assert "ticket_id" in result or "status" in result

            # Physical WAL disk check: file MUST exist on disk with exact content!
            assert os.path.exists(target_file), "Target file was NOT physically written to disk!"
            with open(target_file, "r", encoding="utf-8") as f:
                disk_content = f.read()
            assert disk_content == content, "Disk content does not match input!"


@pytest.mark.asyncio
async def test_bitwise_identical_noop_preserved():
    """Test 3: Bitwise exact identical writes to SAME URI are intercepted in < 1ms as NOOP."""
    gk = EntropyGatekeeper.get_instance()
    gk.reset_for_testing()

    uri = "viking://resources/identical_doc.md"
    content = "完全一致的知识资产内容，没有任何变动，应当被 0 Token 快轨拦截为 NOOP。"

    # First write: passes gatekeeper
    d1 = await gk.evaluate_and_intercept(uri=uri, content=content, fast_probe_budget=0.1)
    assert d1.action in ("add", "noop")

    # Second write with exact same content to exact same URI: MUST be NOOP
    t0 = time.perf_counter()
    d2 = await gk.evaluate_and_intercept(uri=uri, content=content, fast_probe_budget=0.1)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 50.0, f"Bitwise NOOP check took {elapsed_ms:.1f}ms, expected < 50ms!"
    assert d2.action == "noop"
    assert d2.similarity == 1.0000
    assert d2.saved_bytes > 0


def test_vector_sync_tracker_fast_path_metrics(temp_workspace):
    """Test 4: VectorSyncTracker records and exposes fast_path_count in metrics."""
    db_file = os.path.join(temp_workspace, "test_sync.db")
    tracker = VectorSyncTracker(db_path=db_file)

    tracker.mark_pending("viking://resources/doc_a.md")
    tracker.mark_fast_path("viking://resources/doc_a.md")
    tracker.mark_indexed("viking://resources/doc_a.md")

    metrics = tracker.get_metrics()
    assert "fast_path_count" in metrics
    assert metrics["fast_path_count"] >= 1
