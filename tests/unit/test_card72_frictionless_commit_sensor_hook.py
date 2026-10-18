# -*- coding: utf-8 -*-
"""Unit tests for Card-72: Frictionless session commit & telemetry ingestion hook consolidation.

Verifies:
1. Short session commit where all messages are retained within keep_recent_count window
   now accurately captures telemetry into AgentSensorsAggregator.
2. Full archived session commit records telemetry with context hits in Phase 1.
3. Deduplication guard prevents duplicate writes if queue replay or duplicate commit occurs.
4. Empty sessions (0 messages) do not generate spurious zero-token telemetry noise.
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from openviking.core.agent_sensors import AgentSensorsAggregator
from openviking.message.message import Message
from openviking.message.part import ContextPart, TextPart
from openviking.server.identity import RequestContext, Role
from openviking.session.session import Session
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def clean_sensors(tmp_path, monkeypatch):
    """Provide a completely isolated sensors aggregator instance."""
    metrics_file = str(tmp_path / "card72_metrics.jsonl")
    agg = AgentSensorsAggregator.get_instance()
    monkeypatch.setattr(agg, "metrics_file", metrics_file)
    monkeypatch.setattr(agg, "_history", [])
    return agg


@pytest.mark.asyncio
async def test_short_session_commit_within_keep_window_records_telemetry(clean_sensors):
    """Verify that sessions with total <= keep_recent_count record telemetry on commit."""
    session_id = "sess-card72-short-01"
    ctx = RequestContext(user=UserIdentifier.the_default_user(), role=Role.USER)

    messages = [
        Message(
            id="m1",
            role="user",
            parts=[TextPart("编写一个 Fibonacci 算法")],
        ),
        Message(
            id="m2",
            role="assistant",
            parts=[
                TextPart(
                    "实现如下：\n```python\ndef fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)\n```"
                )
            ],
        ),
        Message(
            id="m3",
            role="user",
            parts=[TextPart("不对，这个递归复杂度太高了，请重新修改为动态规划")],
        ),
    ]

    vfs_mock = MagicMock()
    vfs_mock._uri_to_path.return_value = "/tmp/test_session"
    vfs_mock.write_file = AsyncMock()
    vfs_mock.read_file = AsyncMock(side_effect=Exception("no meta"))
    vfs_mock.exists = AsyncMock(return_value=False)
    vfs_mock._async_agfs = MagicMock()
    vfs_mock._async_agfs.pathlock_acquire_tree = AsyncMock(return_value="fake-lease")
    vfs_mock._async_agfs.pathlock_release = AsyncMock()

    session = Session(session_id=session_id, viking_fs=vfs_mock, ctx=ctx)
    session._save_meta = AsyncMock()
    session._write_to_agfs_async = AsyncMock()
    session._read_live_messages_strict = AsyncMock(return_value=messages)

    res = await session.commit_async(keep_recent_count=10)
    assert res["status"] == "skipped"
    assert res["reason"] == "all_within_keep_window"

    # In Card-72, telemetry MUST be recorded despite archive skip!
    metrics = clean_sensors.get_aggregated_metrics()
    assert metrics["sample_count"] == 1
    recent = metrics["recent_timeline"][0]
    assert recent["session_id"] == session_id
    assert recent["token_snr"] > 0
    assert recent["effective_tokens"] > 0
    # "不对" and "重新" trigger human intervention flag
    assert recent["human_intervention_flag"] is True
    assert recent["interventions"] >= 1


@pytest.mark.asyncio
async def test_archived_session_commit_records_telemetry_with_context_hits(clean_sensors):
    """Verify that archived sessions record telemetry in Phase 1 with context usage."""
    session_id = "sess-card72-archived-02"
    ctx = RequestContext(user=UserIdentifier.the_default_user(), role=Role.USER)

    messages = [
        Message(
            id="m1",
            role="user",
            parts=[TextPart("查询当前系统状态")],
        ),
        Message(
            id="m2",
            role="assistant",
            parts=[
                TextPart("已从知识库召回：\n```python\nstatus = check_cluster()\n```"),
                ContextPart(uri="viking://resources/cluster/status.py", abstract="集群状态定义"),
            ],
        ),
    ]

    vfs_mock = MagicMock()
    vfs_mock._uri_to_path.return_value = "/tmp/test_session"
    vfs_mock.write_file = AsyncMock()
    vfs_mock.read_file = AsyncMock(side_effect=Exception("no meta"))
    vfs_mock.exists = AsyncMock(return_value=False)
    vfs_mock._async_agfs = MagicMock()
    vfs_mock._async_agfs.pathlock_acquire_tree = AsyncMock(return_value="fake-lease")
    vfs_mock._async_agfs.pathlock_release = AsyncMock()

    session = Session(session_id=session_id, viking_fs=vfs_mock, ctx=ctx)
    session._save_meta = AsyncMock()
    session._write_to_agfs_async = AsyncMock()
    session._write_phase1_marker = AsyncMock()
    session._write_phase1_ready_marker = AsyncMock()
    session._read_live_messages_strict = AsyncMock(return_value=messages)

    # Mock QueueFS enqueue and TaskTracker
    queue_mock = MagicMock()
    queue_mock.enqueue = AsyncMock()
    task_mock = MagicMock()
    task_mock.create = AsyncMock()

    usage_record = MagicMock()
    usage_record.uri = "viking://resources/cluster/status.py"
    session._usage_records = [usage_record]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("openviking.storage.queuefs.get_queue_manager", lambda: queue_mock)
        mp.setattr("openviking.service.task_tracker.get_task_tracker", lambda: task_mock)

        res = await session.commit_async(keep_recent_count=0)
        assert res["status"] == "accepted"
        assert res["archived"] is True

    metrics = clean_sensors.get_aggregated_metrics()
    assert metrics["sample_count"] == 1
    recent = metrics["recent_timeline"][0]
    assert recent["session_id"] == session_id
    assert recent["token_snr"] > 0
    assert recent["top5_hits"] >= 1
    assert recent["human_intervention_flag"] is False


def test_deduplication_guard_prevents_duplicate_commit_telemetry(clean_sensors):
    """Verify deduplication returns existing telemetry without inflating history or JSONL."""
    p1 = clean_sensors.record_telemetry(
        session_id="sess-card72-dedup",
        effective_tokens=150,
        total_tokens=200,
        top5_hits=2,
        interventions_count=0,
    )

    # Identical call within 60s
    p2 = clean_sensors.record_telemetry(
        session_id="sess-card72-dedup",
        effective_tokens=150,
        total_tokens=200,
        top5_hits=2,
        interventions_count=0,
    )

    assert p1 is p2
    assert len(clean_sensors._history) == 1

    # New turn with different tokens
    p3 = clean_sensors.record_telemetry(
        session_id="sess-card72-dedup",
        effective_tokens=280,
        total_tokens=350,
        top5_hits=3,
        interventions_count=1,
    )
    assert p3 is not p1
    assert len(clean_sensors._history) == 2


@pytest.mark.asyncio
async def test_empty_session_commit_does_not_record_telemetry(clean_sensors):
    """Verify empty sessions (0 messages) do not generate dummy 0-token metrics."""
    session_id = "sess-card72-empty"
    ctx = RequestContext(user=UserIdentifier.the_default_user(), role=Role.USER)

    vfs_mock = MagicMock()
    vfs_mock._uri_to_path.return_value = "/tmp/test_session"
    vfs_mock.write_file = AsyncMock()
    vfs_mock.read_file = AsyncMock(side_effect=Exception("no meta"))
    vfs_mock.exists = AsyncMock(return_value=False)
    vfs_mock._async_agfs = MagicMock()
    vfs_mock._async_agfs.pathlock_acquire_tree = AsyncMock(return_value="fake-lease")
    vfs_mock._async_agfs.pathlock_release = AsyncMock()

    session = Session(session_id=session_id, viking_fs=vfs_mock, ctx=ctx)
    session._save_meta = AsyncMock()
    session._messages = []
    session._read_live_messages_strict = AsyncMock(return_value=[])

    res = await session.commit_async(keep_recent_count=10)
    assert res["status"] == "skipped"
    assert res["reason"] == "no_messages"

    metrics = clean_sensors.get_aggregated_metrics()
    assert metrics["sample_count"] == 0
    assert len(metrics["recent_timeline"]) == 0
