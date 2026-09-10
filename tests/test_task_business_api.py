# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Unit tests for Business Job API and Dual-Track Task endpoints."""

import pytest
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.tasks import (
    BusinessJobPayload,
    get_dual_track_tasks,
    report_business_job,
)
from openviking.service.task_store import PersistentTaskStore
from openviking.service.task_tracker import (
    TaskTracker,
    set_task_tracker,
)
from openviking_cli.session.user_id import UserIdentifier

pytestmark = pytest.mark.asyncio


from tests.test_task_tracker import _FakeAgfs


@pytest.fixture(autouse=True)
def clean_tracker():
    tracker = TaskTracker(store=PersistentTaskStore(_FakeAgfs()))
    set_task_tracker(tracker)
    yield
    set_task_tracker(None)


def _make_ctx(role: Role = Role.ADMIN, account_id: str = "acme", user_id: str = "alice") -> RequestContext:
    return RequestContext(
        user=UserIdentifier(account_id, user_id),
        role=role,
    )


async def test_report_business_job_create_and_update():
    ctx = _make_ctx()

    # 1. Create a running business job
    payload = BusinessJobPayload(
        human_title="📚 72 篇官方文档深度提纯与语义入库",
        initiator="Agent (Claude 5.0)",
        status="running",
        progress={"completed": 12, "total": 72, "unit": "篇文档"},
    )
    resp = await report_business_job(payload, _ctx=ctx)
    assert resp.status == "ok"
    task_id = resp.result["task_id"]
    assert task_id.startswith("biz_")
    assert resp.result["status"] == "running"
    assert resp.result["human_title"] == "📚 72 篇官方文档深度提纯与语义入库"

    # 2. Update to completed with deliverable link
    update_payload = BusinessJobPayload(
        task_id=task_id,
        human_title="📚 72 篇官方文档深度提纯与语义入库",
        initiator="Agent (Claude 5.0)",
        status="completed",
        progress={"completed": 72, "total": 72, "unit": "篇文档"},
        deliverable={"uri": "viking://resources/master_memory/official_docs.md", "label": "成果物直达"},
    )
    update_resp = await report_business_job(update_payload, _ctx=ctx)
    assert update_resp.status == "ok"
    assert update_resp.result["status"] == "completed"

    # 3. Verify in dual track listing
    dual_resp = await get_dual_track_tasks(limit=50, _ctx=ctx)
    assert dual_resp.status == "ok"
    biz_jobs = dual_resp.result["business_jobs"]
    matching = [j for j in biz_jobs if j.get("task_id") == task_id]
    assert len(matching) == 1
    job = matching[0]
    assert job["human_title"] == "📚 72 篇官方文档深度提纯与语义入库"
    assert job["status"] == "completed"
    assert job["deliverable"]["uri"] == "viking://resources/master_memory/official_docs.md"
    assert job["progress"]["completed"] == 72
