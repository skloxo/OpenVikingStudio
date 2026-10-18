# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Tests for QueueFS Observer latching bug fix & DLQ self-healing mechanism.
Validates Card-Fix-QueueObserver-Latching-Bug (v1.5.26).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from openviking.storage.observers.queue_observer import QueueObserver
from openviking.storage.queuefs.named_queue import NamedQueue, QueueStatus
from openviking.storage.queuefs.queue_manager import QueueManager
from openviking.storage.queuefs.queue_types import evaluate_queue_health


class MockAGFS:
    def __init__(self):
        self.files = {}

    def mkdir(self, path):
        pass

    def write(self, path, data):
        self.files[path] = data
        return "msg_1001"

    def read(self, path):
        if path.endswith("/size"):
            return b"0"
        return None


def create_mock_named_queue(name="Embedding", agfs=None):
    if agfs is None:
        agfs = MockAGFS()
    queue = NamedQueue(
        agfs=agfs,
        mount_point="/queue",
        name=name,
    )
    return queue


def test_evaluate_queue_health_first_principles():
    """Verify health evaluation logic adheres to first principles."""
    # 1. Drained queue with 5187 processed and 5 errors (0.096% error rate)
    is_healthy, has_errors, rate = evaluate_queue_health(
        in_progress=0,
        processed=5187,
        error_count=5,
        recent_outcomes=[],
        pending=0,
    )
    assert is_healthy is True
    assert has_errors is False
    assert rate == 0.0

    # 2. Drained queue with total failure (0 processed, 5 errors)
    is_healthy, has_errors, _ = evaluate_queue_health(
        in_progress=0,
        processed=0,
        error_count=5,
        recent_outcomes=[],
        pending=0,
    )
    assert is_healthy is False
    assert has_errors is True

    # 3. Active queue with sliding-window high failure rate (>20%)
    recent = [False, False, True, False, False]  # 4 failures / 5 items = 80% failure rate
    is_healthy, has_errors, rate = evaluate_queue_health(
        in_progress=2,
        processed=10,
        error_count=4,
        recent_outcomes=recent,
        pending=5,
    )
    assert is_healthy is False
    assert has_errors is True
    assert rate == 0.80

    # 4. Active queue with minor transient error (1 failure / 20 items = 5% failure rate)
    recent_ok = [True] * 19 + [False]
    is_healthy, has_errors, rate = evaluate_queue_health(
        in_progress=2,
        processed=19,
        error_count=1,
        recent_outcomes=recent_ok,
        pending=10,
    )
    assert is_healthy is True
    assert has_errors is False
    assert rate == 0.05


@pytest.mark.asyncio
async def test_completed_queue_with_historical_errors_is_healthy():
    """Verify that a completed queue with historical transient errors is healthy (NO LATCHING)."""
    agfs = MockAGFS()
    queue = create_mock_named_queue("Embedding", agfs=agfs)

    # Simulate 5187 successful processing events and 5 historical transient errors
    queue._processed = 5187
    queue._error_count = 5
    queue._in_progress = 0

    assert queue.has_errors() is False
    assert queue.is_healthy() is True

    status = await queue.get_status()
    assert status.has_errors is False
    assert status.is_healthy is True
    assert status.is_complete is True
    assert status.error_count == 5
    assert status.processed == 5187

    # Wire to QueueManager
    qm = QueueManager(agfs=agfs)
    qm._queues["Embedding"] = queue

    assert qm.has_errors("Embedding") is False
    assert qm.is_healthy("Embedding") is True
    assert qm.has_errors() is False
    assert qm.is_healthy() is True

    # Wire to QueueObserver
    observer = QueueObserver(qm)
    assert observer.has_errors() is False
    assert observer.is_healthy() is True

    table = await observer.get_status_table_async()
    assert "Errors" in table
    assert "Embedding" in table
    assert "5" in table  # Raw error count must still be transparently visible


@pytest.mark.asyncio
async def test_dlq_recording_and_retry_self_healing():
    """Verify that failed items are preserved in DLQ and can self-heal via retry_failed."""
    agfs = MockAGFS()
    queue = create_mock_named_queue("Embedding", agfs=agfs)

    # Trigger 2 process failures with payloads
    queue._on_process_error("Timeout connecting to service", {"task_id": "task_1", "slice_idx": 42})
    queue._on_process_error("Rate limit exceeded", {"task_id": "task_1", "slice_idx": 43})

    assert queue._error_count == 2
    dlq_entries = queue.get_dlq(include_retried=False)
    assert len(dlq_entries) == 2
    assert dlq_entries[0]["queue"] == "Embedding"
    assert dlq_entries[0]["retryable"] is True
    assert dlq_entries[0]["data"]["slice_idx"] == 42
    assert dlq_entries[1]["data"]["slice_idx"] == 43

    # Wire to QueueManager
    qm = QueueManager(agfs=agfs)
    qm._queues["Embedding"] = queue

    dlq_audit = await qm.get_dlq(queue_name="Embedding")
    assert len(dlq_audit) == 2

    # Execute retry_failed self-healing
    result = await qm.retry_failed(queue_name="Embedding")
    assert result["success"] is True
    assert result["retried_count"] == 2
    assert result["remaining_dlq_count"] == 0

    # Error count self-heals by decrementing per retried task
    assert queue._error_count == 0

    # Drained queue with errors resolved is completely healthy
    assert queue.has_errors() is False
    assert queue.is_healthy() is True


@pytest.mark.asyncio
async def test_dlq_clear_purges_and_resets():
    """Verify that clear_dlq purges DLQ entries and resets counters."""
    agfs = MockAGFS()
    queue = create_mock_named_queue("Semantic", agfs=agfs)

    queue._on_process_error("Transient node error", {"node_id": "sem_1"})
    queue._on_process_error("Another node error", {"node_id": "sem_2"})

    assert queue._error_count == 2
    assert len(queue.get_dlq()) == 2

    qm = QueueManager(agfs=agfs)
    qm._queues["Semantic"] = queue

    cleared = qm.clear_dlq(queue_name="Semantic")
    assert cleared == 2
    assert queue._error_count == 0
    assert len(queue.get_dlq()) == 0
    assert queue.is_healthy() is True
