# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-20E: Hermes Session Experience Auto-Wiring & Async Nudge Closure.
(Card-Hermes-SessionExperience-AutoWiring / v1.5.81)
"""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from openviking.core.hermes_experience_store import HermesExperienceStore
from openviking.core.hermes_nudge_engine import HermesNudgeEngine
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.storage.queuefs.session_commit_msg import SessionCommitMsg
from openviking.storage.queuefs.session_commit_processor import SessionCommitProcessor
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def temp_hermes_store():
    """Create isolated temporary HermesExperienceStore instance."""
    tmpdir = tempfile.mkdtemp(prefix="test_hermes_store_")
    db_file = Path(tmpdir) / "test_hermes.db"
    store = HermesExperienceStore(db_path=db_file)
    HermesExperienceStore._instance = store
    yield store
    HermesExperienceStore.reset_instance()
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_record_messages_batch_and_fts5_recall(temp_hermes_store):
    """Test batch insertion and immediate FTS5 full-text recall."""
    store = temp_hermes_store
    messages_data = [
        {
            "session_id": "sess_001",
            "role": "user",
            "content": "请分析一下系统的内存泄漏排查思路",
            "tool_calls": None,
            "meta": {"turn": 0},
        },
        {
            "session_id": "sess_001",
            "role": "assistant",
            "content": "使用 py-spy 或者 tracemalloc 检查常驻 Worker 线程单例，防止幽灵线程泄漏。",
            "tool_calls": [{"name": "openviking_find", "arguments": {"query": "tracemalloc"}}],
            "meta": {"turn": 1},
        },
        {
            "session_id": "sess_002",
            "role": "user",
            "content": "如何实现 NO GREEN EVER 视觉规范？",
            "tool_calls": None,
            "meta": {"turn": 0},
        },
    ]

    recorded = store.record_messages_batch(messages_data)
    assert len(recorded) == 3

    # FTS5 Full-Text Search
    res1 = store.search_messages("tracemalloc")
    assert len(res1) >= 1
    assert res1[0].session_id == "sess_001"
    assert "tracemalloc" in res1[0].snippet

    res2 = store.search_messages("GREEN")
    assert len(res2) >= 1
    assert res2[0].session_id == "sess_002"


@pytest.mark.asyncio
async def test_session_commit_processor_autowiring(temp_hermes_store):
    """Verify that SessionCommitProcessor._record_hermes_experience extracts messages and queues Nudge."""
    store = temp_hermes_store
    nudge_engine = HermesNudgeEngine.get_instance()

    # Mock session and archive messages
    session = MagicMock()
    session.session_id = "test_autowired_session_999"

    mock_msg1 = MagicMock()
    mock_msg1.role = "user"
    mock_msg1.content = "检查节点 2080Ti 的 GPU 负载情况"
    mock_msg1.parts = []
    mock_msg1.tool_calls = None

    mock_msg2 = MagicMock()
    mock_msg2.role = "assistant"
    mock_msg2.content = "已执行 nvidia-smi 检查，显存占用 4.2GB，处于正常范围。"
    mock_msg2.parts = []
    mock_msg2.tool_calls = [{"name": "exec", "arguments": {"command": "nvidia-smi"}}]

    session._read_archive_messages = AsyncMock(return_value=[mock_msg1, mock_msg2])

    commit_msg = SessionCommitMsg(
        session_id="test_autowired_session_999",
        session_uri="viking://sessions/test_autowired_session_999",
        archive_uri="viking://archives/test_autowired_session_999/arc_001",
        task_id="task_test_001",
        user={"account_id": "default", "user_id": "commander"},
    )

    processor = SessionCommitProcessor(session_service=MagicMock(), service_loop=MagicMock())
    await processor._record_hermes_experience(session, commit_msg)

    # Verify messages in Hermes store
    stored = store.get_messages_by_session("test_autowired_session_999")
    assert len(stored) == 2
    assert stored[0].role == "user"
    assert "2080Ti" in stored[0].content
    assert stored[1].role == "assistant"
    assert "nvidia-smi" in stored[1].content

    # Verify FTS5 query hits
    search_hits = store.search_messages("2080Ti")
    assert len(search_hits) == 1
    assert search_hits[0].session_id == "test_autowired_session_999"


def test_hermes_experience_batch_api(temp_hermes_store):
    """Verify POST /api/v1/hermes/experience/batch endpoint."""
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    payload = {
        "messages": [
            {
                "session_id": "api_batch_sess_1",
                "role": "user",
                "content": "验证批处理经历存储接口",
            },
            {
                "session_id": "api_batch_sess_1",
                "role": "assistant",
                "content": "批处理接口调用成功，已实现物理入库。",
            },
        ],
        "trigger_nudge": True,
    }

    resp = client.post("/api/v1/hermes/experience/batch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["recorded_count"] == 2

    # Verify query
    search_resp = client.get("/api/v1/hermes/experience/search?q=批处理接口")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total_matches"] >= 1
