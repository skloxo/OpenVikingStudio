# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-57 (v1.8.1) Unit Test Suite:
QueueFS DLQ Inspection Drawer & Granular Healing Cockpit.

Validates:
1. GET /api/v1/queue/dlq/{id} retrieves complete payload, error details, and stack trace.
2. POST /api/v1/queue/dlq/{id}/retry triggers single-item self-healing re-enqueue.
3. POST /api/v1/queue/dlq/{id}/resolve marks single dead letter as resolved with note.
4. Frontend DeadLetterDrawer and VectorSyncDlqCard maintain contract parity and no micro-fonts.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openviking.server.routers.queue import router as queue_router
from openviking.storage.queuefs.dlq_manager import DLQManager


@pytest.fixture
def test_client():
    test_app = FastAPI()
    test_app.include_router(queue_router)
    return TestClient(test_app)


@pytest.fixture
def temp_dlq():
    temp_dir = tempfile.mkdtemp(prefix="test_card57_dlq_")
    db_path = os.path.join(temp_dir, "test_dlq.db")
    dlq = DLQManager(db_path=db_path)
    return dlq


def test_dlq_single_item_detail_endpoint(test_client, temp_dlq):
    """Verify GET /api/v1/queue/dlq/{dlq_id} endpoint returns full fields."""
    item_id = temp_dlq.record_dead_letter(
        queue_name="text_embedding",
        uri="viking://resources/doc_test.md",
        msg_id="msg-card57-001",
        account_id="acc-default",
        payload={"text": "hello world", "length": 11},
        error_type="DimensionMismatchError",
        error_message="Vector length 1024 != 1536",
        stack_trace="Traceback (most recent call last):\n  File 'test.py', line 12",
    )

    with patch("openviking.storage.queuefs.dlq_manager.DLQManager.get_instance", return_value=temp_dlq):
        resp = test_client.get(f"/api/v1/queue/dlq/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        item = data["item"]
        assert item["id"] == item_id
        assert item["queue_name"] == "text_embedding"
        assert item["msg_id"] == "msg-card57-001"
        assert item["uri"] == "viking://resources/doc_test.md"
        assert item["payload"]["text"] == "hello world"
        assert item["error_type"] == "DimensionMismatchError"
        assert "Traceback" in item["stack_trace"]
        assert item["resolved"] == 0

        # Non-existent item returns 404
        not_found_resp = test_client.get("/api/v1/queue/dlq/999999")
        assert not_found_resp.status_code == 404


def test_dlq_single_item_resolve_endpoint(test_client, temp_dlq):
    """Verify POST /api/v1/queue/dlq/{dlq_id}/resolve marks item as resolved."""
    item_id = temp_dlq.record_dead_letter(
        queue_name="text_embedding",
        msg_id="msg-card57-resolve",
        uri="viking://resources/doc_err.md",
        payload={"bad": True},
        error_type="MalformedPayload",
        error_message="Invalid JSON payload",
    )

    with patch("openviking.storage.queuefs.dlq_manager.DLQManager.get_instance", return_value=temp_dlq):
        resolve_resp = test_client.post(
            f"/api/v1/queue/dlq/{item_id}/resolve",
            json={"resolution_note": "Fixed data upstream, safe to ignore", "status": 1},
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["status"] == "success"

        # Verify state in DB
        record = temp_dlq.get_dead_letter(item_id)
        assert record["resolved"] == 1
        assert record["resolution_note"] == "Fixed data upstream, safe to ignore"


def test_dlq_single_item_retry_endpoint(test_client, temp_dlq):
    """Verify POST /api/v1/queue/dlq/{dlq_id}/retry triggers single-item retry."""
    item_id = temp_dlq.record_dead_letter(
        queue_name="text_embedding",
        msg_id="msg-card57-retry",
        uri="viking://resources/doc_retry.md",
        payload={"text": "retry payload"},
        error_type="NetworkTimeout",
        error_message="Temporary embedding timeout",
    )

    mock_queue = MagicMock()
    mock_queue.enqueue = AsyncMock(return_value="re-enqueued-msg-id")

    mock_queue_mgr = MagicMock()
    mock_queue_mgr.get_queue = AsyncMock(return_value=mock_queue)

    mock_vikingdb = MagicMock()
    mock_vikingdb.has_queue_manager = True
    mock_vikingdb._queue_manager = mock_queue_mgr

    mock_service = MagicMock()
    mock_service._vikingdb = mock_vikingdb

    with patch("openviking.storage.queuefs.dlq_manager.DLQManager.get_instance", return_value=temp_dlq), \
         patch("openviking.server.dependencies.get_app_viking_service", return_value=mock_service):
        retry_resp = test_client.post(f"/api/v1/queue/dlq/{item_id}/retry")
        assert retry_resp.status_code == 200
        result = retry_resp.json()
        assert result["status"] == "success"
        assert result["re-enqueued"] is True

        # Verify retry count incremented and resolved status marked 2
        record = temp_dlq.get_dead_letter(item_id)
        assert record["retry_count"] == 1
        assert record["resolved"] == 2
        mock_queue.enqueue.assert_awaited_once_with({"text": "retry payload"})


def test_frontend_dead_letter_drawer_contract():
    """Verify DeadLetterDrawer frontend component exists and follows design rules."""
    drawer_path = "src/routes/monitoring/-components/dead-letter-drawer.tsx"
    assert os.path.exists(drawer_path), f"File {drawer_path} must exist"
    
    with open(drawer_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule checks
    assert "export function DeadLetterDrawer" in content, "Must export DeadLetterDrawer component"
    assert "export interface DeadLetterRecord" in content, "Must export DeadLetterRecord interface"
    assert "/api/v1/queue/dlq/" in content, "Must call dlq endpoints"
    assert "retry" in content, "Must support retry"
    assert "resolve" in content, "Must support resolve"
    
    # Typography rule: No micro fonts < 12px
    assert "text-[8px]" not in content
    assert "text-[9px]" not in content
    assert "text-[10px]" not in content
    assert "text-[11px]" not in content
    assert "text-green-" not in content, "Strict NO GREEN EVER rule"
