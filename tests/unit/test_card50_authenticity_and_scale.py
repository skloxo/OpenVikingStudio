# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-50: Physical Authenticity, O(1) Dedup Index & Concurrency Hygiene."""

import asyncio
from unittest.mock import AsyncMock, patch, mock_open
import pytest

from openviking.server.routers.system_probes import (
    probe_gpu_telemetry,
    _read_host_mem,
    probe_system_host_resources,
)
from openviking.service.task_card_manager import TaskCardManager
from openviking.service.cache_tier2_engine import Tier2LRUCacheEngine
from openviking.service.test_retina_generator import TestRetinaGenerator
from openviking.service.code_fact_compiler import McpToolFactRecord


@pytest.mark.asyncio
async def test_probe_gpu_telemetry_authenticity_success():
    """Verify GPU probe returns available=True and correct parsed telemetry on success."""
    mock_stdout = b"2048, 12288, 35.5\n"
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (mock_stdout, b"")
    mock_proc.returncode = 0

    with patch("openviking.server.routers.system_probes._GPU_CACHE", None), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        res = await probe_gpu_telemetry()
        assert res["available"] is True
        assert res["used_gb"] == 2.0
        assert res["total_gb"] == 12.0
        assert res["gpu_percent"] == 35.5
        assert res["error"] is None


@pytest.mark.asyncio
async def test_probe_gpu_telemetry_authenticity_failure():
    """Verify GPU probe does not return fake 0.0 metrics on failure, but available=False and None."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"NVIDIA-SMI has failed")
    mock_proc.returncode = 12

    with patch("openviking.server.routers.system_probes._GPU_CACHE", None), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        res = await probe_gpu_telemetry()
        assert res["available"] is False
        assert res["used_gb"] is None
        assert res["total_gb"] is None
        assert res["gpu_percent"] is None
        assert "nvidia-smi" in res["error"]


def test_read_host_mem_fallback_authenticity():
    """Verify _read_host_mem returns available=False and None when meminfo is unreadable."""
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        res = _read_host_mem()
        assert res["available"] is False
        assert res["total_gb"] is None
        assert res["used_gb"] is None
        assert res["memory_percent"] is None


@pytest.mark.asyncio
async def test_task_card_o1_index_and_lifecycle(tmp_path):
    """Verify TaskCardManager maintains an in-memory O(1) fingerprint index for deduplication."""
    manager = TaskCardManager()
    manager._inbox_dir = tmp_path / "inbox"
    manager._resolved_dir = tmp_path / "resolved"
    manager._inbox_dir.mkdir(parents=True, exist_ok=True)
    manager._resolved_dir.mkdir(parents=True, exist_ok=True)
    manager._build_inbox_index()

    initial_count = manager.indexed_fingerprint_count
    assert initial_count == 0

    # 1. Create first card
    res1 = await manager.file_issue_card(
        title="Gateway 504 Timeout",
        priority="P1",
        module="router.search",
        symptom="HTTP 504 Gateway Timeout during heavy vector search",
        initiator="agent-3070",
    )
    assert res1["status"] == "created"
    card_id = res1["card_id"]
    assert manager.indexed_fingerprint_count == 1

    # 2. Second file with same module/symptom hits O(1) fast-path
    res2 = await manager.file_issue_card(
        title="Gateway 504 Timeout Duplicate",
        priority="P0",
        module="router.search",
        symptom="HTTP 504 Gateway Timeout during heavy vector search",
        initiator="agent-mac",
    )
    assert res2["status"] == "aggregated"
    assert res2["card_id"] == card_id
    assert res2["occurrence_count"] == 2
    assert res2["priority"] == "P0"  # Priority escalated

    # 3. Resolve card removes fingerprint from index
    resolve_res = await manager.resolve_card(
        card_id=card_id,
        resolution_tag="v1.7.4",
        commit_hash="abc1234",
        summary="Fixed gateway timeout via connection pooling",
    )
    assert resolve_res["status"] == "resolved"
    assert manager.indexed_fingerprint_count == 0


def test_cache_tier2_in_flight_guard_resilience():
    """Verify in_flight_guard automatically releases in_flight state even on unhandled exceptions."""
    cache = Tier2LRUCacheEngine()
    test_key = "key_concurrency_test"

    assert not cache.is_in_flight(test_key)

    # 1. Normal context exit
    with cache.in_flight_guard(test_key) as acquired:
        assert acquired is True
        assert cache.is_in_flight(test_key)
        val, hit = cache.get(test_key, wait=False, fallback="busy")
        assert hit is False
        assert val == "busy"

    assert not cache.is_in_flight(test_key)

    # 2. Exception raised inside context
    with pytest.raises(RuntimeError):
        with cache.in_flight_guard(test_key) as acquired:
            assert acquired is True
            assert cache.is_in_flight(test_key)
            raise RuntimeError("Backend source crashed!")

    # Verify RAII lock released
    assert not cache.is_in_flight(test_key)


def test_test_retina_genuine_mcp_contract_execution():
    """Verify TestRetinaGenerator produces callable, inspect-backed tests that can execute."""
    record = McpToolFactRecord(
        name="openviking_list_pending_cards",
        handler_name="openviking_list_pending_cards",
        is_async=True,
        parameters_signature="",
        return_type="str",
        docstring="List pending task cards",
        source_file="openviking/server/mcp_endpoint.py",
        line_number=10,
    )
    code = TestRetinaGenerator.generate_pytest_for_mcp_tool(record)

    assert "import inspect" in code
    assert "from openviking.server import mcp_endpoint" in code
    assert "assert callable(handler)" in code
    assert "sig.parameters" in code

    # Execute generated test string in an isolated namespace
    local_ns = {}
    exec(code, {}, local_ns)
    test_fn = local_ns["test_openviking_list_pending_cards_contract"]
    assert callable(test_fn)
    # Run the test function!
    test_fn()
