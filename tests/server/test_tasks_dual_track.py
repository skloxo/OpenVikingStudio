# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Dual-Track Tasks endpoints (/api/v1/tasks/dual_track)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.server.routers.tasks import get_dual_track_tasks, get_valet_ticket
from openviking.service.task_tracker import TaskRecord, TaskStatus


@pytest.mark.asyncio
async def test_dual_track_tasks_categorization():
    """Verify that tasks are cleanly divided into Business Jobs and System Maintenance Ops."""
    mock_tracker = MagicMock()

    b_task = TaskRecord(
        task_id="job_valet_123",
        task_type="valet_parking",
        status=TaskStatus.COMPLETED,
        meta={
            "is_business": True,
            "human_title": "🚗 自动泊车：官方架构白皮书入库",
            "initiator": "WorkBuddy",
            "progress": {"completed": 1, "total": 1, "unit": "个节点"},
        },
        result={
            "deliverable": {
                "uri": "viking://resources/master_memory/official/arch.md",
                "label": "查看官方架构",
                "action_type": "view_memory",
            }
        },
    )

    sys_task = TaskRecord(
        task_id="auto-remed-20260908_120000-abcd12",
        task_type="quality_gate",
        status=TaskStatus.COMPLETED,
    )

    mock_tracker.list_tasks = AsyncMock(return_value=[b_task, sys_task])

    mock_ctx = MagicMock()
    mock_ctx.role = MagicMock()

    with patch("openviking.server.routers.tasks.get_task_tracker", return_value=mock_tracker):
        resp = await get_dual_track_tasks(limit=50, _ctx=mock_ctx)
        assert resp.status == "ok"
        res = resp.result

        assert "business_jobs" in res
        assert "system_ops" in res
        assert "kpi" in res

        # Check Business Job
        assert len(res["business_jobs"]) == 1
        bj = res["business_jobs"][0]
        assert bj["task_id"] == "job_valet_123"
        assert bj["human_title"] == "🚗 自动泊车：官方架构白皮书入库"
        assert bj["initiator"] == "WorkBuddy"
        assert bj["deliverable"]["uri"] == "viking://resources/master_memory/official/arch.md"
        assert bj["progress"]["completed"] == 1

        # Check System Op (Machine UUID humanized)
        assert len(res["system_ops"]) == 1
        so = res["system_ops"][0]
        assert so["task_id"] == "auto-remed-20260908_120000-abcd12"
        assert "系统周期质检守护" in so["human_title"]
        assert "#abcd12" in so["human_title"]


def test_quality_gate_retry_both_routes_and_payload():
    """Verify both /tasks/trigger-quality-gate and /tasks/quality_gate accept retry payloads and return task_id."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.auth import get_request_context
    from openviking.server.routers.tasks import router as tasks_router

    app = FastAPI()
    app.include_router(tasks_router)
    app.dependency_overrides[get_request_context] = lambda: MagicMock()

    mock_watchdog = MagicMock()
    mock_watchdog.trigger_cycle = AsyncMock(
        return_value={
            "quality_gate_task_id": "manual-qg-test-001",
            "status": "completed",
            "composite_score": 0.91,
        }
    )

    client = TestClient(app)
    with patch("openviking.service.entropy_watchdog.get_entropy_watchdog", return_value=mock_watchdog):
        resp1 = client.post(
            "/api/v1/tasks/trigger-quality-gate",
            json={"mode": "smoke", "threshold": 0.7, "reason": "ui_task_retry"},
        )
        assert resp1.status_code == 200
        body1 = resp1.json()
        assert body1["status"] == "ok"
        assert body1["result"]["task_id"] == "manual-qg-test-001"
        assert body1["result"]["quality_gate_task_id"] == "manual-qg-test-001"

        resp2 = client.post(
            "/api/v1/tasks/quality_gate",
            json={"mode": "full", "threshold": 0.8},
        )
        assert resp2.status_code == 200
        assert resp2.json()["result"]["task_id"] == "manual-qg-test-001"

    assert mock_watchdog.trigger_cycle.await_count == 2
    assert mock_watchdog.trigger_cycle.await_args_list[0].kwargs["reason"] == "ui_task_retry"
    assert mock_watchdog.trigger_cycle.await_args_list[1].kwargs["reason"] == "retry_full"
