# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Tests for Card-187: Session IO De-duplication, Lock Decoupling & State Machine Unification."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from openviking.message import TextPart
from openviking.server.identity import RequestContext, Role, UserIdentifier
from openviking.service.task_store import PersistentTaskStore
from openviking.service.task_tracker import TaskTracker
from openviking.session.session import Session
from openviking.storage.viking_fs import VikingFS
from openviking_cli.exceptions import InternalError, NotFoundError, UnavailableError
from tests.utils.mock_agfs import MockLocalAGFS


@pytest.fixture
def test_ctx():
    return RequestContext(user=UserIdentifier("acme", "alice"), role=Role.USER)


@pytest.fixture
def mock_viking_fs(tmp_path):
    agfs = MockLocalAGFS(root_path=str(tmp_path))
    return VikingFS(agfs=agfs)


@pytest.mark.asyncio
async def test_phase1_unlocks_before_task_registration(tmp_path, test_ctx, monkeypatch):
    """Verify archive lock & lease are released BEFORE task_tracker.create is called."""
    agfs = MockLocalAGFS(root_path=str(tmp_path))
    fs = VikingFS(agfs=agfs)
    tracker = TaskTracker(PersistentTaskStore(fs.agfs))
    monkeypatch.setattr("openviking.service.task_tracker.get_task_tracker", lambda: tracker)
    monkeypatch.setattr("openviking.session.session._enabled_memory_types", lambda: set())

    session = Session(viking_fs=fs, session_id="test_lock_decouple_sess", ctx=test_ctx)
    await session.ensure_exists()
    await session.add_message_async("user", [TextPart("Hello world for archive")])

    # Intercept queue enqueue
    async def enqueue(_queue_name, data):
        assert len(await session._read_live_messages_strict()) == 1
        assert (await session._read_phase1_meta(data["archive_uri"]))["status"] == "preparing"

    # In task tracker create, verify session lock can be re-acquired (meaning it's NOT held!)
    async def create_task(task_type, *, resource_id=None, account_id=None, user_id=None, task_id=None, **kwargs):
        # If the archive lock / pathlock was still held, this acquire would fail or block!
        lease = await fs._async_agfs.pathlock_acquire_tree(
            fs._uri_to_path(session.uri, ctx=session.ctx)
        )
        await fs._async_agfs.pathlock_release(lease)
        raise RuntimeError("task store temporary failure")

    monkeypatch.setattr(tracker, "create", create_task)
    monkeypatch.setattr(
        "openviking.storage.queuefs.get_queue_manager", lambda: SimpleNamespace(enqueue=enqueue)
    )

    with pytest.raises((InternalError, RuntimeError)) as exc_info:
        await session.commit_async()

    # Even though task tracker registration failed, Phase 1 archive succeeded on disk
    assert not await fs.exists(f"{session.uri}/history/archive_001/.failed.json", ctx=session.ctx)
    archive_meta = await session._read_phase1_meta(f"{session.uri}/history/archive_001")
    assert archive_meta["status"] == "ready"
    assert await session._read_live_messages_strict() == []


@pytest.mark.asyncio
async def test_session_service_open_does_not_preload_messages(mock_viking_fs, test_ctx):
    """Verify session_service.open constructs a handle without loading full messages."""
    from openviking.service.session_service import SessionService

    service = SessionService(viking_fs=mock_viking_fs)
    session = await service.open("sess_open_test", test_ctx, auto_create=True)
    assert session is not None
    assert session.session_id == "sess_open_test"
    # open() should not mark session as fully loaded
    assert getattr(session, "_loaded", False) is False

    # Calling get() will load it
    session_loaded = await service.get("sess_open_test", test_ctx)
    assert getattr(session_loaded, "_loaded", False) is True


def test_independent_extract_endpoint_purged():
    """Verify independent extract endpoint is purged from SessionService and router."""
    from openviking.server.routers.sessions import router
    from openviking.service.session_service import SessionService

    # 1. SessionService should NOT have extract method
    assert not hasattr(SessionService, "extract")

    # 2. Router should not have any route ending with /extract
    extract_routes = [route for route in router.routes if route.path.endswith("/extract")]
    assert len(extract_routes) == 0
