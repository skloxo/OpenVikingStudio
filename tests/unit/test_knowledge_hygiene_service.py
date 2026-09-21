# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for KnowledgeHygieneService and async full-scale audit dispatching.
(Card-Hygiene-AsyncAuditTaskCenter / v1.5.56)
"""

import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.retrieval_benchmark import router as retrieval_benchmark_router
from openviking.service.knowledge_hygiene_service import (
    KnowledgeHygieneService,
    TASK_TYPE_HYGIENE_AUDIT,
)
from openviking.service.task_store import PersistentTaskStore
from openviking.service.task_tracker import TaskStatus, TaskTracker, set_task_tracker, get_task_tracker
from openviking_cli.session.user_id import UserIdentifier
from tests.test_task_tracker import _FakeAgfs


@pytest.fixture(autouse=True)
def setup_tracker():
    tracker = TaskTracker(store=PersistentTaskStore(_FakeAgfs()))
    set_task_tracker(tracker)
    yield
    set_task_tracker(None)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(retrieval_benchmark_router)

    async def _mock_ctx() -> RequestContext:
        return RequestContext(
            user=UserIdentifier("default", "root"),
            role=Role.ROOT,
        )

    app.dependency_overrides[get_request_context] = _mock_ctx
    return TestClient(app)


@pytest.mark.asyncio
async def test_knowledge_hygiene_service_full_scale_report():
    """Verify that get_latest_report returns full-scale total documents without LIMIT 200."""
    service = KnowledgeHygieneService.get_instance()
    report = service.get_latest_report()

    assert report is not None
    assert report.total_inspected >= 2000, f"Expected full-scale >= 2000 documents, got {report.total_inspected}"
    assert report.health_score >= 80
    assert report.inspection_ts > 0
    assert report.latency_ms >= 0


@pytest.mark.asyncio
async def test_knowledge_hygiene_service_dispatch_and_completion():
    """Verify dispatching an async audit task, tracking in TaskCenter, and completing."""
    service = KnowledgeHygieneService.get_instance()
    tracker = get_task_tracker()

    task = await service.dispatch_audit(account_id="default", user_id="root", trigger="test")
    assert task.task_id is not None
    assert task.task_type == TASK_TYPE_HYGIENE_AUDIT
    assert task.meta.get("is_business") is True

    # Wait for async execution to settle
    record = None
    for _ in range(50):
        record = await tracker.get(task.task_id, account_id="default", user_id="root")
        if record and record.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            break
        await asyncio.sleep(0.05)

    assert record is not None
    assert record.status == TaskStatus.COMPLETED
    assert record.result is not None
    assert record.result.get("health_score") >= 80
    assert record.result.get("total_inspected") >= 2000
    assert "deliverable" in record.result
    assert "全量巡检" in record.result["deliverable"]["title"]


def test_retrieval_benchmark_hygiene_endpoints(client: TestClient):
    """Verify REST API endpoints for dispatch and report retrieval."""
    # 1. GET /api/v1/retrieval/hygiene/report
    res = client.get("/api/v1/retrieval/hygiene/report")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    result = data.get("result")
    assert result is not None
    assert result.get("total_inspected") >= 2000
    assert result.get("health_score") >= 80

    # 2. POST /api/v1/retrieval/hygiene/dispatch
    post_res = client.post("/api/v1/retrieval/hygiene/dispatch?trigger=test")
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data.get("status") == "ok"
    assert "task_id" in post_data
