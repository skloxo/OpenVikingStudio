# -*- coding: utf-8 -*-
"""Unit tests for Card-20A: Agent Sensors telemetry hook in SessionCommitProcessor and session lifecycle."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.core.agent_sensors import (
    AgentSensorsAggregator,
    extract_session_telemetry_metrics,
)
from openviking.message.message import Message
from openviking.message.part import ContextPart, TextPart, ToolPart
from openviking.server.identity import RequestContext, Role
from openviking.storage.queuefs.session_commit_msg import SessionCommitMsg
from openviking.storage.queuefs.session_commit_processor import SessionCommitProcessor
from openviking_cli.session.user_id import UserIdentifier


def test_extract_session_telemetry_metrics_pure():
    """Verify that extract_session_telemetry_metrics calculates SNR, P@5, and interventions accurately."""
    messages = [
        Message(
            id="m1",
            role="user",
            parts=[TextPart("请帮我写一个快速排序算法")],
        ),
        Message(
            id="m2",
            role="assistant",
            parts=[
                TextPart("好的，以下是快速排序实现：\n```python\ndef quicksort(arr):\n    if len(arr) <= 1: return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)\n```"),
                ContextPart(uri="viking://resources/algorithms/sort.py", abstract="快速排序标准实现"),
            ],
        ),
        Message(
            id="m3",
            role="user",
            parts=[TextPart("不对，这里有个 bug，没有处理空列表或者递归深度问题，请重写并修正")],
        ),
        Message(
            id="m4",
            role="assistant",
            parts=[
                TextPart("抱歉，我来修正：\n```python\ndef quicksort(arr):\n    if not arr: return []\n    ...\n```"),
            ],
        ),
    ]

    usage_uris = ["viking://resources/algorithms/sort.py"]
    metrics = extract_session_telemetry_metrics(
        messages=messages,
        usage_uris=usage_uris,
        session_id="sess-test-hook-01",
    )

    assert metrics["session_id"] == "sess-test-hook-01"
    assert metrics["total_tokens"] > 0
    assert metrics["effective_tokens"] > 0
    assert metrics["effective_tokens"] <= metrics["total_tokens"]
    # top5_hits should detect the used context
    assert metrics["top5_hits"] >= 1
    # User message 3 contains "不对" and "重写", so interventions_count must be >= 1
    assert metrics["interventions_count"] >= 1


@pytest.mark.asyncio
async def test_session_commit_processor_triggers_telemetry(tmp_path):
    """Verify that SessionCommitProcessor._process invokes telemetry recording on successful commit."""
    metrics_file = str(tmp_path / "agent_metrics.jsonl")
    aggregator = AgentSensorsAggregator.get_instance()
    aggregator.metrics_file = metrics_file
    aggregator._history.clear()

    # Mock session service and session
    mock_session = AsyncMock()
    mock_session.session_id = "sess-commit-real-123"
    mock_session.exists.return_value = True
    mock_session.load.return_value = None
    mock_session.resume_queued_commit.return_value = True

    # Sample messages
    msg1 = Message(id="1", role="user", parts=[TextPart("实现一个二分查找")])
    msg2 = Message(
        id="2",
        role="assistant",
        parts=[
            TextPart("代码如下：\n```python\ndef bsearch(arr, target):\n    pass\n```"),
            ContextPart(uri="viking://resources/bsearch.py", abstract="bsearch"),
        ],
    )
    mock_session._read_archive_messages.return_value = [msg1, msg2]
    mock_session._messages = [msg1, msg2]

    mock_service = MagicMock()
    mock_service.session.return_value = mock_session

    processor = SessionCommitProcessor(session_service=mock_service, service_loop=None)

    commit_msg = SessionCommitMsg(
        task_id="task-001",
        session_id="sess-commit-real-123",
        session_uri="viking://sessions/sess-commit-real-123",
        archive_uri="viking://sessions/sess-commit-real-123/archive/0",
        usage_uris=["viking://resources/bsearch.py"],
        user=UserIdentifier.the_default_user().to_dict(),
    )
    ctx = RequestContext(user=UserIdentifier.the_default_user(), role=Role.USER)

    result = await processor._process(commit_msg, ctx)
    assert result is True

    # Check that aggregator history received the new data point
    metrics = aggregator.get_aggregated_metrics()
    assert metrics["sample_count"] == 1
    assert metrics["recent_timeline"][0]["session_id"] == "sess-commit-real-123"
    assert metrics["recent_timeline"][0]["token_snr"] > 0
    assert metrics["recent_timeline"][0]["p5_precision"] > 0
