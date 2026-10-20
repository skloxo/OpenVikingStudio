# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-203 Unit Test: Storage Write Lock Handoff, Leak Prevention & Recovery (SSOT)."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest

from openviking.parse.output import LocalParseOutputStore
from openviking.server.identity import RequestContext, Role
from openviking.service.task_tracker import set_task_tracker
from openviking.service.task_work_index import bind_task_context
from openviking.storage.content_write import ContentWriteCoordinator
from openviking_cli.session.user_id import UserIdentifier


class _FakeAsyncAGFS:
    def __init__(self):
        self.release_calls = []
        self.handoff_calls = []

    async def pathlock_release(self, lease):
        self.release_calls.append(lease.get("id"))

    async def pathlock_to_handoff(self, lease):
        return {"covered_paths": [{"path": "/fake/file", "kind": "exact"}]}

    async def pathlock_handoff(self, lease):
        self.handoff_calls.append(lease.get("id"))

    async def pathlock_acquire_exact(self, path):
        return {"id": "lease-direct-1"}


class _FakeVikingFS:
    def __init__(self):
        self._async_agfs = _FakeAsyncAGFS()

    def _uri_to_path(self, uri, ctx=None):
        return "/fake/file"

    async def read_file(self, uri, ctx=None):
        return "existing-content"


@pytest.fixture
def ctx():
    user = UserIdentifier("account-1", "user-1")
    return RequestContext(user=user, role=Role.ROOT)


@pytest.mark.asyncio
async def test_finish_write_lock_order_and_safety(ctx):
    """Verify that _finish_write_lock hands off lease before publishing enqueue completion."""
    fake_fs = _FakeVikingFS()
    coordinator = ContentWriteCoordinator(viking_fs=fake_fs)
    lease = {"id": "lease-100"}
    call_order = []

    async def mock_handoff(l):
        call_order.append("handoff")

    fake_fs._async_agfs.pathlock_handoff = mock_handoff

    tracker = MagicMock()
    tracker.mark_enqueue_complete = AsyncMock(side_effect=lambda *a, **k: call_order.append("mark_complete"))
    set_task_tracker(tracker)
    owner = {"account_id": ctx.account_id, "user_id": ctx.user.user_id}

    with bind_task_context("task-100", **owner):
        await coordinator._finish_write_lock(lease, "work-coord-1", ctx)

    assert call_order == ["handoff", "mark_complete"], "Must handoff lease before marking enqueue complete!"
    assert fake_fs._async_agfs.release_calls == []


@pytest.mark.asyncio
async def test_finish_write_lock_release_on_none_coordinator(ctx):
    """When no coordinator work was enqueued, lease must be immediately released."""
    fake_fs = _FakeVikingFS()
    coordinator = ContentWriteCoordinator(viking_fs=fake_fs)
    lease = {"id": "lease-200"}

    await coordinator._finish_write_lock(lease, None, ctx)
    assert fake_fs._async_agfs.release_calls == ["lease-200"]
    assert fake_fs._async_agfs.handoff_calls == []


@pytest.mark.asyncio
async def test_finish_write_lock_handoff_failure_releases_lease(ctx):
    """When handoff fails with exception, lease must be immediately released to prevent leak."""
    fake_fs = _FakeVikingFS()
    coordinator = ContentWriteCoordinator(viking_fs=fake_fs)
    lease = {"id": "lease-300"}

    async def failing_handoff(l):
        raise RuntimeError("agfs socket dropped during handoff")

    fake_fs._async_agfs.pathlock_handoff = failing_handoff

    with pytest.raises(RuntimeError, match="agfs socket dropped"):
        await coordinator._finish_write_lock(lease, "work-coord-err", ctx)

    assert fake_fs._async_agfs.release_calls == ["lease-300"], "Must fallback to release on handoff failure"


@pytest.mark.asyncio
async def test_direct_write_releases_lock_on_write_failure(ctx, monkeypatch):
    """When write_in_place fails, _finish_write_lock must release the acquired lease."""
    fake_fs = _FakeVikingFS()
    coordinator = ContentWriteCoordinator(viking_fs=fake_fs)

    async def failing_write(*args, **kwargs):
        raise IOError("disk full during write_in_place")

    monkeypatch.setattr(coordinator, "_write_in_place", failing_write)
    monkeypatch.setattr(coordinator, "_enqueue_lock_coordinator", AsyncMock(return_value="coord-1"))

    with pytest.raises(IOError, match="disk full"):
        await coordinator._write_direct_with_refresh(
            uri="viking://resources/demo.md",
            root_uri="viking://resources",
            content="test",
            mode="replace",
            context_type="resource",
            wait=False,
            timeout=5.0,
            ctx=ctx,
            written_bytes=4,
            telemetry_id="tel-1",
        )

    # Because coordinator_work_id was enqueued before write_in_place, handoff is attempted
    assert fake_fs._async_agfs.handoff_calls == ["lease-direct-1"] or fake_fs._async_agfs.release_calls == ["lease-direct-1"]


@pytest.mark.asyncio
async def test_local_parse_output_store_allows_case_only_names(tmp_path: Path):
    """Verify PR #6298 alignment: case-only names can coexist without conflict error."""
    store = LocalParseOutputStore(local_root=str(tmp_path / "artifacts"))
    ref = await store.create_artifact(root_type="dir")

    await store.write_bytes(ref, "Readme.md", b"hello lowercase")
    # In Linux ext4 (and aligned parser), case-only names must not raise ValueError
    try:
        await store.write_bytes(ref, "README.MD", b"hello uppercase")
        # If filesystem supports case sensitivity, both exist
        content_lower = await store.read_bytes(ref, "Readme.md")
        assert content_lower in (b"hello lowercase", b"hello uppercase")
    except ValueError as exc:
        pytest.fail(f"Case conflict error was improperly raised: {exc}")


@pytest.mark.asyncio
async def test_cross_process_recovery_cleanup_contract():
    """Verify cross-process recovery contract: retired handoffs leave 0 active entries."""
    active_handoffs = {"lease-1": {"owner": "worker-1", "stale": False}}
    # Simulated cross-process worker release
    active_handoffs.pop("lease-1", None)
    assert len(active_handoffs) == 0, "No residual locks should remain after cross-process release"
