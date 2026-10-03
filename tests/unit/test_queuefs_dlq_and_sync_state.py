# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD suite for QueueFS Dead Letter Queue (DLQ) and Vector Sync State Tracker."""

import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from openviking.storage.queuefs.dlq_manager import DLQManager, DeadLetterRecord
from openviking.service.vector_sync_tracker import VectorSyncTracker, SyncStatus, VectorSyncRecord


@pytest.fixture
def temp_data_dir():
    temp_dir = tempfile.mkdtemp(prefix="ov_test_dlq_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_dlq_manager_lifecycle(temp_data_dir):
    """Test recording, listing, filtering, and resolving dead letters in DLQManager."""
    db_path = os.path.join(temp_data_dir, "test_dlq.db")
    dlq = DLQManager(db_path=db_path)

    # 1. Record dead letters
    dlq_id1 = dlq.record_dead_letter(
        queue_name="embedding_queue",
        msg_id="msg-101",
        payload={"message": "long content" * 1000, "telemetry_id": "t-1"},
        error_type="INPUT_TOO_LARGE",
        error_message="Input text length 8500 exceeds model limit 8192",
        uri="viking://resources/docs/huge_doc.md",
        account_id="default",
    )
    assert dlq_id1 > 0

    dlq_id2 = dlq.record_dead_letter(
        queue_name="embedding_queue",
        msg_id="msg-102",
        payload={"message": "broken content", "telemetry_id": "t-2"},
        error_type="PERMANENT",
        error_message="Permanent embedding provider 500 error",
        uri="viking://resources/docs/broken.md",
        account_id="default",
    )
    assert dlq_id2 > 0

    # 2. List dead letters
    pending_items = dlq.list_dead_letters(resolved=0)
    assert len(pending_items) == 2
    assert pending_items[0]["msg_id"] in ["msg-101", "msg-102"]

    # Filter by error_type
    large_items = dlq.list_dead_letters(error_type="INPUT_TOO_LARGE")
    assert len(large_items) == 1
    assert large_items[0]["uri"] == "viking://resources/docs/huge_doc.md"

    # 3. Check stats
    stats = dlq.get_stats()
    assert stats["total_count"] == 2
    assert stats["pending_count"] == 2
    assert stats["resolved_count"] == 0
    assert stats["by_error_type"].get("INPUT_TOO_LARGE") == 1
    assert stats["by_error_type"].get("PERMANENT") == 1

    # 4. Resolve dead letter
    success = dlq.resolve_dead_letter(dlq_id1, resolution_note="Manually chunked and re-indexed")
    assert success is True

    stats_after = dlq.get_stats()
    assert stats_after["pending_count"] == 1
    assert stats_after["resolved_count"] == 1


def test_vector_sync_tracker_lifecycle(temp_data_dir):
    """Test VectorSyncTracker states, metrics calculation, and unindexed detection."""
    db_path = os.path.join(temp_data_dir, "test_sync_tracker.db")
    tracker = VectorSyncTracker(db_path=db_path)

    # 1. Mark files as PENDING
    tracker.mark_pending("viking://resources/f1.md", account_id="default", content_hash="hash1")
    tracker.mark_pending("viking://resources/f2.md", account_id="default", content_hash="hash2")
    tracker.mark_pending("viking://resources/f3.md", account_id="default", content_hash="hash3")

    rec1 = tracker.get_record("viking://resources/f1.md")
    assert rec1 is not None
    assert rec1.status == SyncStatus.PENDING

    # 2. Transition f1 and f2 to INDEXED
    tracker.mark_indexed("viking://resources/f1.md", account_id="default", content_hash="hash1")
    tracker.mark_indexed("viking://resources/f2.md", account_id="default", content_hash="hash2")

    rec1_after = tracker.get_record("viking://resources/f1.md")
    assert rec1_after.status == SyncStatus.INDEXED

    # 3. Mark f3 as FAILED
    tracker.mark_failed("viking://resources/f3.md", account_id="default", error="Embedding timeout")
    rec3 = tracker.get_record("viking://resources/f3.md")
    assert rec3.status == SyncStatus.FAILED
    assert "timeout" in rec3.last_error

    # 4. Check metrics
    metrics = tracker.get_metrics(account_id="default")
    assert metrics["total_files"] == 3
    assert metrics["indexed_count"] == 2
    assert metrics["pending_count"] == 0
    assert metrics["failed_count"] == 1
    # sync_rate_pct = 2 / 3 * 100 = 66.67%
    assert 66.0 <= metrics["sync_rate_pct"] <= 67.0

    # 5. Find unindexed or failed
    unindexed = tracker.find_unindexed_or_failed(account_id="default")
    assert len(unindexed) == 1
    assert unindexed[0]["uri"] == "viking://resources/f3.md"


def test_queue_dlq_and_sync_endpoints(temp_data_dir):
    """Test REST API routes for DLQ listing, resolving, metrics, and healing."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.routers.dlq import router as dlq_router

    dlq_db = os.path.join(temp_data_dir, "api_dlq.db")
    sync_db = os.path.join(temp_data_dir, "api_sync.db")

    with patch("openviking.storage.queuefs.dlq_manager.DLQManager.get_instance") as mock_dlq_inst, \
         patch("openviking.service.vector_sync_tracker.VectorSyncTracker.get_instance") as mock_sync_inst:

        dlq = DLQManager(db_path=dlq_db)
        tracker = VectorSyncTracker(db_path=sync_db)
        mock_dlq_inst.return_value = dlq
        mock_sync_inst.return_value = tracker

        # Record a sample dead letter
        dlq_id = dlq.record_dead_letter(
            queue_name="embedding_queue",
            msg_id="m-api-1",
            payload={"text": "broken"},
            error_type="INPUT_TOO_LARGE",
            error_message="Too big for context window",
            uri="viking://resources/big.md",
        )
        tracker.mark_failed("viking://resources/big.md", error="Too big")
        tracker.mark_indexed("viking://resources/ok.md")

        app = FastAPI()
        app.include_router(dlq_router)
        client = TestClient(app)

        # 1. Test GET /api/v1/queue/dlq
        resp = client.get("/api/v1/queue/dlq")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["pending"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["error_type"] == "INPUT_TOO_LARGE"

        # 2. Test POST /api/v1/queue/dlq/{id}/resolve
        resolve_resp = client.post(
            f"/api/v1/queue/dlq/{dlq_id}/resolve",
            json={"resolution_note": "Manually split into chunks", "status": 1},
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["resolved_id"] == dlq_id

        # 3. Test GET /api/v1/queue/sync-metrics
        metric_resp = client.get("/api/v1/queue/sync-metrics")
        assert metric_resp.status_code == 200
        m_data = metric_resp.json()
        assert m_data["status"] == "success"
        assert m_data["total_files"] == 2
        assert m_data["indexed_count"] == 1
        assert m_data["failed_count"] == 1
        assert m_data["sync_rate_pct"] == 50.0

        # 4. Test POST /api/v1/queue/sync-heal
        heal_resp = client.post("/api/v1/queue/sync-heal")
        assert heal_resp.status_code == 200
        h_data = heal_resp.json()
        assert h_data["status"] == "success"
        assert h_data["healed_count"] >= 1


@pytest.mark.asyncio
async def test_embedding_handler_terminal_failure_writes_dlq(temp_data_dir):
    """Test TextEmbeddingHandler records unprocessable messages to DLQ and marks sync FAILED."""
    from openviking.storage.collection_schemas import TextEmbeddingHandler

    dlq_db = os.path.join(temp_data_dir, "handler_dlq.db")
    sync_db = os.path.join(temp_data_dir, "handler_sync.db")

    with patch("openviking.storage.queuefs.dlq_manager.DLQManager.get_instance") as mock_dlq_inst, \
         patch("openviking.service.vector_sync_tracker.VectorSyncTracker.get_instance") as mock_sync_inst:

        dlq = DLQManager(db_path=dlq_db)
        tracker = VectorSyncTracker(db_path=sync_db)
        mock_dlq_inst.return_value = dlq
        mock_sync_inst.return_value = tracker

        mock_vikingdb = MagicMock()
        handler = TextEmbeddingHandler(vikingdb=mock_vikingdb)

        # Trigger terminal failure
        raw_data = {
            "id": "msg-oversized-99",
            "uri": "viking://resources/huge_essay.md",
            "account_id": "default",
            "message": "x" * 20000,
        }
        handler._record_terminal_failure(
            embedding_msg=None,
            raw_data=raw_data,
            error_type="INPUT_TOO_LARGE",
            error_msg="Text length exceeds 8192 token limit",
        )

        # Verify DLQ received the dead letter
        dlq_records = dlq.list_dead_letters()
        assert len(dlq_records) == 1
        assert dlq_records[0]["uri"] == "viking://resources/huge_essay.md"
        assert dlq_records[0]["error_type"] == "INPUT_TOO_LARGE"

        # Verify tracker recorded state as FAILED
        sync_rec = tracker.get_record("viking://resources/huge_essay.md")
        assert sync_rec is not None
        assert sync_rec.status == SyncStatus.FAILED
        assert "INPUT_TOO_LARGE" in sync_rec.last_error

        # Trigger terminal success
        handler._record_terminal_success(
            embedding_msg=None,
            raw_data=raw_data,
            record_id="vec-rec-123",
        )
        sync_rec_after = tracker.get_record("viking://resources/huge_essay.md")
        assert sync_rec_after.status == SyncStatus.INDEXED


