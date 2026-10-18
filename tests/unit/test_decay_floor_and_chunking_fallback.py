# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD suite for Category-Aware Score Floor and Overlength Chunking Fallback Pipeline.
(Card-42 / v1.6.6)
"""

import math
import os
import shutil
import tempfile
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from openviking.retrieve.asymmetric_decay import (
    AsymmetricDecayEngine,
    DecayConfig,
    DecayAssessment,
)
from openviking.storage.chunking_fallback import ChunkingFallbackEngine, ChunkItem
from openviking.service.vector_sync_tracker import VectorSyncTracker, SyncStatus
from openviking.storage.queuefs.dlq_manager import DLQManager


@pytest.fixture
def temp_test_env():
    temp_dir = tempfile.mkdtemp(prefix="ov_test_card42_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_category_aware_decay_floor_invariants_and_lessons():
    """Verify invariants, master memory, ADRs, and lessons maintain strict decay floors."""
    engine = AsymmetricDecayEngine()
    current_ts = time.time()
    half_year_ago = current_ts - (180 * 86400)
    one_year_ago = current_ts - (365 * 86400)

    # 1. Master memory root immunity: Any file under master_memory/ is 100% immune
    res_master = engine.evaluate_candidate(
        uri="viking://resources/master_memory/preferences.md",
        raw_score=0.90,
        updated_ts=one_year_ago,
        now_ts=current_ts,
    )
    assert res_master.is_immune is True
    assert res_master.decay_factor == 1.0
    assert res_master.adjusted_score == 0.90

    # 2. Skills URI immunity
    res_skill = engine.evaluate_candidate(
        uri="viking://skills/codebase-design/SKILL.md",
        raw_score=0.88,
        updated_ts=one_year_ago,
        now_ts=current_ts,
    )
    assert res_skill.is_immune is True
    assert res_skill.decay_factor == 1.0

    # 3. ADR / Architecture document: floor >= 0.85
    res_adr = engine.evaluate_candidate(
        uri="viking://resources/project/docs/adr/001_queue_isolation.md",
        raw_score=0.80,
        updated_ts=half_year_ago,
        now_ts=current_ts,
    )
    assert res_adr.decay_factor >= 0.85
    assert res_adr.adjusted_score >= 0.80 * 0.85

    # 4. Lessons learned document: floor >= 0.85
    res_lesson = engine.evaluate_candidate(
        uri="viking://resources/lessons/2026_09_evolution.md",
        raw_score=0.82,
        updated_ts=half_year_ago,
        now_ts=current_ts,
    )
    assert res_lesson.decay_factor >= 0.85
    assert res_lesson.adjusted_score >= 0.82 * 0.85

    # 5. Explicit memory_type="lesson" or "architecture": floor >= 0.85
    res_type_lesson = engine.evaluate_candidate(
        uri="viking://resources/custom/insight.md",
        raw_score=0.80,
        updated_ts=half_year_ago,
        memory_type="lesson",
        now_ts=current_ts,
    )
    assert res_type_lesson.decay_factor >= 0.85

    # 6. Experience memory: floor >= 0.60
    res_exp = engine.evaluate_candidate(
        uri="viking://resources/experience/debug_tips.md",
        raw_score=0.80,
        updated_ts=one_year_ago,
        memory_type="experience",
        now_ts=current_ts,
    )
    assert res_exp.decay_factor >= 0.60
    assert res_exp.adjusted_score >= 0.80 * 0.60


def test_chunking_fallback_engine_splits_text():
    """Verify ChunkingFallbackEngine splits large texts with preserved frontmatter and deterministic chunk URIs."""
    engine = ChunkingFallbackEngine(max_chunk_chars=500, overlap_chars=50)

    sample_doc = (
        "---\n"
        "title: Massive Architecture Spec\n"
        "author: Antigravity\n"
        "---\n\n"
        "# Section 1: Overview\n\n"
        + ("This is a detailed paragraph explaining core system invariants and memory absorption protocols. " * 15)
        + "\n\n# Section 2: Implementation Details\n\n"
        + ("Here we describe how NamedQueue and VikingDB interact during large payload processing. " * 15)
        + "\n\n# Section 3: Fallback Operations\n\n"
        + ("Final section on disaster recovery, SQLite dead letter queues, and sliding windows. " * 10)
    )

    chunks = engine.chunk_text(sample_doc, uri="viking://resources/docs/huge_spec.md")
    assert len(chunks) >= 3
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks == len(chunks)
    assert chunks[0].chunk_uri == "viking://resources/docs/huge_spec.md#chunk_0"
    assert "title: Massive Architecture Spec" in chunks[0].text
    # Check that frontmatter is propagated to subsequent chunks for context retention
    assert "title: Massive Architecture Spec" in chunks[1].text
    assert chunks[1].chunk_uri == "viking://resources/docs/huge_spec.md#chunk_1"


@pytest.mark.asyncio
async def test_chunking_fallback_execution(temp_test_env):
    """Verify ChunkingFallbackEngine embeds chunks and upserts them to VikingDB."""
    db_path = os.path.join(temp_test_env, "sync.db")
    tracker = VectorSyncTracker(db_path=db_path)

    mock_vikingdb = MagicMock()
    mock_vikingdb.uses_content_field = True
    mock_vikingdb.upsert = AsyncMock(return_value="rec_chunk_id")

    # Mock embedder that returns 128-dim mock vectors
    mock_embed_res = MagicMock()
    mock_embed_res.dense_vector = [0.1] * 128
    mock_embed_res.sparse_vector = {"term1": 1.0}

    mock_handler = MagicMock()
    mock_handler._vikingdb = mock_vikingdb
    mock_handler._vector_dim = 128
    mock_handler._dispatch_embed = AsyncMock(return_value=mock_embed_res)

    engine = ChunkingFallbackEngine(max_chunk_chars=300, overlap_chars=30)

    raw_text = "Important technical manual section. " * 40
    embedding_msg = MagicMock()
    embedding_msg.message = raw_text
    embedding_msg.telemetry_id = "tel-chunk-1"
    embedding_msg.context_data = {
        "uri": "viking://resources/manual.md",
        "account_id": "account_dev",
        "abstract": "A manual",
        "level": 2,
    }

    raw_data = {
        "id": "raw-msg-1",
        "uri": "viking://resources/manual.md",
        "account_id": "account_dev",
        "message": raw_text,
    }

    with patch("openviking.service.vector_sync_tracker.VectorSyncTracker.get_instance", return_value=tracker):
        result = await engine.execute_fallback(
            handler=mock_handler,
            embedding_msg=embedding_msg,
            raw_data=raw_data,
            ctx=MagicMock(),
        )

        assert result is not None
        # Verify VikingDB upsert was called for each chunk
        assert mock_vikingdb.upsert.call_count >= 2
        # Verify tracker marked the parent document as INDEXED
        sync_rec = tracker.get_record("viking://resources/manual.md")
        assert sync_rec is not None
        assert sync_rec.status == SyncStatus.INDEXED


@pytest.mark.asyncio
async def test_text_embedding_handler_recovers_from_input_too_large(temp_test_env):
    """Verify TextEmbeddingHandler intercepts ERROR_CLASS_INPUT_TOO_LARGE and completes chunking fallback."""
    from openviking.storage.collection_schemas import TextEmbeddingHandler

    dlq_db = os.path.join(temp_test_env, "dlq.db")
    sync_db = os.path.join(temp_test_env, "sync.db")
    dlq = DLQManager(db_path=dlq_db)
    tracker = VectorSyncTracker(db_path=sync_db)

    with patch("openviking.storage.queuefs.dlq_manager.DLQManager.get_instance", return_value=dlq), \
         patch("openviking.service.vector_sync_tracker.VectorSyncTracker.get_instance", return_value=tracker):

        mock_vikingdb = MagicMock()
        mock_vikingdb.is_closing = False
        mock_vikingdb.uses_content_field = True
        mock_vikingdb.upsert = AsyncMock(return_value="chunk_upsert_ok")
        mock_vikingdb.has_queue_manager = True

        handler = TextEmbeddingHandler(vikingdb=mock_vikingdb)
        handler._vector_dim = 64

        # Simulate embedder: fails with 'Input text too long' on the raw oversized text,
        # but succeeds with 64-dim vector on chunks!
        async def mock_embed_side_effect(text):
            if len(text) > 2000:
                raise ValueError("Input text too long: 12000 tokens exceed max limit 8192")
            res = MagicMock()
            res.dense_vector = [0.05] * 64
            res.sparse_vector = None
            return res

        handler._dispatch_embed = AsyncMock(side_effect=mock_embed_side_effect)
        handler._embedder = MagicMock()

        from openviking.storage.queuefs.embedding_msg import EmbeddingMsg

        oversized_text = "Detailed system specifications for agentic exocortex architecture. " * 100
        emb_msg = EmbeddingMsg(
            message=oversized_text,
            context_data={
                "uri": "viking://resources/master_memory/large_system_spec.md",
                "account_id": "default",
                "abstract": "Large spec",
                "level": 2,
            },
            telemetry_id="tel-large-001",
        )
        raw_msg_data = {
            "id": "msg-large-001",
            "data": emb_msg.to_json(),
        }

        # Process dequeued message
        result = await handler.on_dequeue(raw_msg_data)
        assert result is not None, "Handler must recover and return indexed data on chunking fallback"

        # Verify NO dead letters were recorded in DLQ
        dead_letters = dlq.list_dead_letters()
        assert len(dead_letters) == 0, "INPUT_TOO_LARGE should be healed by chunking fallback, not sent to DLQ"

        # Verify tracker has status INDEXED
        sync_rec = tracker.get_record("viking://resources/master_memory/large_system_spec.md")
        assert sync_rec is not None
        assert sync_rec.status == SyncStatus.INDEXED
