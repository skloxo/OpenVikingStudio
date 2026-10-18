# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import pytest

import openviking.pyagfs.async_client as async_client
from openviking.pyagfs import AsyncAGFSClient


class _SyncAGFS:
    """Minimal synchronous binding stub used by the async adapter tests."""

    def read(self, path, **kwargs):
        """Return read call arguments."""
        return ("read", path, kwargs)

    def write(self, path, data, **kwargs):
        """Return write call arguments."""
        return ("write", path, data, kwargs)

    def rm(self, path, **kwargs):
        """Return remove call arguments."""
        return ("rm", path, kwargs)

    def pathlock_is_locked(self, ctx, path, ignore_stale):
        """Return pathlock query arguments."""
        return ("pathlock_is_locked", ctx, path, ignore_stale)


class _PathLockRecordingAGFS:
    """Fail if a disabled Path Lock operation reaches the binding."""

    def __getattr__(self, name):
        if name.startswith("pathlock_"):
            raise AssertionError(f"unexpected backend Path Lock call: {name}")
        raise AttributeError(name)


class _PathLockBackend:
    """Return a sentinel so normal Path Lock forwarding is observable."""

    def pathlock_acquire_exact(self, ctx, path, timeout_secs, owner_lease_ref):
        return {"ctx": ctx, "path": path, "timeout_secs": timeout_secs}


class _WriteRecordingAGFS:
    """Capture the fs context passed to a normal file operation."""

    def __init__(self):
        self.contexts = []

    def write(self, path, data, *, ctx):
        self.contexts.append(ctx)
        return "written"


@pytest.mark.asyncio
async def test_async_agfs_client_hides_threadpool(monkeypatch):
    monkeypatch.setenv("OPENVIKING_DISABLE_PATH_LOCKS", "false")
    to_thread_calls = []

    async def fake_to_thread(func, *args, **kwargs):
        to_thread_calls.append((func.__name__, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr(async_client.asyncio, "to_thread", fake_to_thread)

    sync_agfs = _SyncAGFS()
    agfs = AsyncAGFSClient(sync_agfs)

    assert agfs._client is sync_agfs
    assert await agfs.write("/tasks/1", b"data") == (
        "write",
        "/tasks/1",
        b"data",
        {"ctx": {"account_id": "_system"}},
    )
    assert await agfs.read("/queue/dequeue") == (
        "read",
        "/queue/dequeue",
        {"ctx": {"account_id": "_system"}},
    )
    assert await agfs.rm("/redo/id", recursive=True) == (
        "rm",
        "/redo/id",
        {"recursive": True, "ctx": {"account_id": "_system"}},
    )

    assert to_thread_calls == [
        ("write", ("/tasks/1", b"data"), {"ctx": {"account_id": "_system"}}),
        ("read", ("/queue/dequeue",), {"ctx": {"account_id": "_system"}}),
        (
            "rm",
            ("/redo/id",),
            {"recursive": True, "ctx": {"account_id": "_system"}},
        ),
    ]


@pytest.mark.asyncio
async def test_path_locks_can_be_disabled_for_the_current_process(monkeypatch):
    monkeypatch.setenv("OPENVIKING_DISABLE_PATH_LOCKS", "true")
    agfs = AsyncAGFSClient(_PathLockRecordingAGFS())

    exact = await agfs.pathlock_acquire_exact("/local/default/a")
    exact_batch = await agfs.pathlock_acquire_exact_batch(["/local/default/a1"])
    tree = await agfs.pathlock_acquire_tree("/local/default/b")
    tree_batch = await agfs.pathlock_acquire_tree_batch(["/local/default/b1"])
    mixed_batch = await agfs.pathlock_acquire_exact_tree_batch(
        ["/local/default/c1"], ["/local/default/c2"]
    )
    batch = await agfs.pathlock_acquire_batch(
        [{"path": "/local/default/c", "kind": "exact"}]
    )

    assert exact["owned"] is True
    assert exact_batch["owned"] is True
    assert tree["owned"] is True
    assert tree_batch["owned"] is True
    assert mixed_batch["owned"] is True
    assert batch["owned"] is True
    assert await agfs.pathlock_as_borrowed(exact) == exact
    assert await agfs.pathlock_refresh(exact) == "refreshed"
    assert await agfs.pathlock_to_handoff(exact) == exact
    adopted = await agfs.pathlock_adopt({
        "owner_id": "handoff-owner",
        "lock_paths": ["/local/default/a"],
    })
    assert adopted["owned"] is True
    assert adopted["lock_paths"] == ["/local/default/a"]
    assert await agfs.pathlock_is_locked("/local/default/a") is False
    assert await agfs.pathlock_observe() == {
        "active_locks": 0,
        "waiting_locks": 0,
        "stale_locks_removed": 0,
        "conflicts": [],
    }

    await agfs.pathlock_release(exact)
    await agfs.pathlock_release_selected(exact, ["/local/default/a"])
    await agfs.pathlock_handoff(exact)


@pytest.mark.asyncio
async def test_path_locks_are_forwarded_when_bypass_is_not_enabled(monkeypatch):
    monkeypatch.setenv("OPENVIKING_DISABLE_PATH_LOCKS", "false")
    agfs = AsyncAGFSClient(_PathLockBackend())

    assert await agfs.pathlock_acquire_exact("/local/default/a", timeout_secs=3.5) == {
        "ctx": {"account_id": "default"},
        "path": "/local/default/a",
        "timeout_secs": 3.5,
    }


@pytest.mark.asyncio
async def test_path_locks_are_disabled_by_default_and_can_be_explicitly_restored(monkeypatch):
    agfs = AsyncAGFSClient(_PathLockRecordingAGFS())

    assert (await agfs.pathlock_acquire_exact("/local/default/a"))["owned"] is True

    monkeypatch.setenv("OPENVIKING_DISABLE_PATH_LOCKS", "false")
    restored = AsyncAGFSClient(_PathLockBackend())
    assert await restored.pathlock_acquire_exact("/local/default/a") == {
        "ctx": {"account_id": "default"},
        "path": "/local/default/a",
        "timeout_secs": 0.0,
    }


@pytest.mark.asyncio
async def test_disabled_path_locks_disable_auto_locking_for_normal_file_operations(monkeypatch):
    monkeypatch.setenv("OPENVIKING_DISABLE_PATH_LOCKS", "1")
    client = _WriteRecordingAGFS()
    agfs = AsyncAGFSClient(client)

    await agfs.write(
        "/local/default/a",
        b"data",
        fs_ctx={"account_id": "default", "lease_ref": "synthetic-lease"},
    )

    assert client.contexts == [
        {"account_id": "default", "disable_auto_pathlock": "true"}
    ]
