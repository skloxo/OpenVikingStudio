# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for GET /api/v1/tasks cursor pagination and query filtering."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking.server.identity import RequestContext, Role
from openviking.server.routers.tasks import list_tasks
from openviking.service.task_tracker import TaskRecord, TaskStatus
from openviking_cli.exceptions import InvalidArgumentError
from openviking_cli.session.user_id import UserIdentifier


def _make_compile_task(task_id: str, created_at: float, skill: str, to_uri: str) -> TaskRecord:
    return TaskRecord(
        task_id=task_id,
        task_type="compile",
        status=TaskStatus.COMPLETED,
        created_at=created_at,
        meta={
            "request": {
                "from": ["viking://resources/notes"],
                "to": to_uri,
                "skill": skill,
            }
        },
    )


@pytest.mark.asyncio
async def test_list_tasks_default_and_cursor_pagination():
    t1 = _make_compile_task("cmp_1", 100.0, "viking://skills/alpha", "viking://resources/a")
    t2 = _make_compile_task("cmp_2", 200.0, "viking://skills/wiki", "viking://resources/b")
    t3 = _make_compile_task("cmp_3", 300.0, "viking://skills/wiki", "viking://resources/c")

    mock_tracker = MagicMock()
    mock_tracker.list_tasks = AsyncMock(side_effect=[[t1, t2, t3], []])
    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.ADMIN)

    with patch("openviking.server.routers.tasks.get_task_tracker", return_value=mock_tracker):
        legacy_resp = await list_tasks(
            task_type="compile",
            status=None,
            resource_id=None,
            q=None,
            pagination=None,
            cursor=None,
            limit=30,
            _ctx=ctx,
        )
        assert isinstance(legacy_resp.result, list)
        assert [item["task_id"] for item in legacy_resp.result] == ["cmp_3", "cmp_2", "cmp_1"]

    mock_tracker.list_tasks = AsyncMock(side_effect=[[t1, t2, t3], [], [t1, t2, t3], []])
    with patch("openviking.server.routers.tasks.get_task_tracker", return_value=mock_tracker):
        page1 = await list_tasks(
            task_type="compile",
            status=None,
            resource_id=None,
            q="wiki",
            pagination="cursor",
            cursor=None,
            limit=1,
            _ctx=ctx,
        )
        assert page1.result["has_more"] is True
        assert page1.result["next_cursor"]
        assert [item["task_id"] for item in page1.result["items"]] == ["cmp_3"]

        page2 = await list_tasks(
            task_type="compile",
            status=None,
            resource_id=None,
            q="wiki",
            pagination="cursor",
            cursor=page1.result["next_cursor"],
            limit=1,
            _ctx=ctx,
        )
        assert page2.result["has_more"] is False
        assert page2.result["next_cursor"] is None
        assert [item["task_id"] for item in page2.result["items"]] == ["cmp_2"]


@pytest.mark.asyncio
async def test_list_tasks_rejects_invalid_pagination_or_cursor():
    mock_tracker = MagicMock()
    mock_tracker.list_tasks = AsyncMock(return_value=[])
    ctx = RequestContext(user=UserIdentifier("default", "default"), role=Role.ADMIN)

    with patch("openviking.server.routers.tasks.get_task_tracker", return_value=mock_tracker):
        with pytest.raises(InvalidArgumentError):
            await list_tasks(
                task_type="compile",
                status=None,
                resource_id=None,
                q=None,
                pagination="offset",
                cursor=None,
                limit=30,
                _ctx=ctx,
            )

        with pytest.raises(InvalidArgumentError):
            await list_tasks(
                task_type="compile",
                status=None,
                resource_id=None,
                q=None,
                pagination="cursor",
                cursor="not-valid-base64",
                limit=30,
                _ctx=ctx,
            )
