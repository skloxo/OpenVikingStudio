# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Hermes Experience Store & FTS5 search.

测试套件:
  test_record_and_retrieve_messages  写入经历消息并按会话检索
  test_fts5_search                   跨会话 FTS5 真实倒排索引全文检索
  test_store_stats                   经历存储统计指标
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.hermes_experience_store import HermesExperienceStore


@pytest.fixture
def temp_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    HermesExperienceStore.reset_instance()
    store = HermesExperienceStore(db_path=db_path)
    yield store
    HermesExperienceStore.reset_instance()
    db_path.unlink(missing_ok=True)


def test_record_and_retrieve_messages(temp_store):
    """测试经历消息的写入与基于会话 ID 的提取。"""
    msg1 = temp_store.record_message(
        session_id="sess-001",
        role="user",
        content="How to optimize SQLite WAL mode?",
    )
    assert msg1.msg_id.startswith("hmsg-")
    assert msg1.role == "user"

    msg2 = temp_store.record_message(
        session_id="sess-001",
        role="assistant",
        content="Use PRAGMA journal_mode=WAL and PRAGMA synchronous=NORMAL.",
    )
    assert msg2.session_id == "sess-001"

    msgs = temp_store.get_messages_by_session("sess-001")
    assert len(msgs) == 2
    assert msgs[0].content == "How to optimize SQLite WAL mode?"
    assert msgs[1].content == "Use PRAGMA journal_mode=WAL and PRAGMA synchronous=NORMAL."


def test_fts5_search(temp_store):
    """测试跨会话 FTS5 真实倒排索引检索与高亮片段。"""
    temp_store.record_message(
        session_id="sess-alpha",
        role="user",
        content="Deploying FastAPI service with Uvicorn on Linux cluster.",
    )
    temp_store.record_message(
        session_id="sess-beta",
        role="assistant",
        content="Configuring Rust RAGFS binding for high-throughput vector queries.",
    )

    # 1. 搜索特定术语
    results = temp_store.search_messages("FastAPI", limit=5)
    assert len(results) == 1
    assert results[0].session_id == "sess-alpha"
    assert "<b>FastAPI</b>" in results[0].snippet or "FastAPI" in results[0].snippet

    # 2. 搜索另一会话术语
    results_rag = temp_store.search_messages("RAGFS", limit=5)
    assert len(results_rag) == 1
    assert results_rag[0].session_id == "sess-beta"

    # 3. 搜索不存在的词
    assert len(temp_store.search_messages("QuantumComputing", limit=5)) == 0


def test_store_stats(temp_store):
    """测试经历存储全局统计指标。"""
    temp_store.record_message(session_id="s1", role="user", content="Hello")
    temp_store.record_message(session_id="s1", role="assistant", content="Hi")
    temp_store.record_message(session_id="s2", role="user", content="World")

    stats = temp_store.stats()
    assert stats["total_messages"] == 3
    assert stats["total_sessions"] == 2
