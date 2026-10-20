# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Retina unit tests for Card-205: Session write IO optimization and vector-free deletion."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.server.identity import RequestContext, Role
from openviking.service.session_service import SessionService
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.exceptions import NotFoundError
from openviking.session.memory.memory_updater import MemoryUpdater
from openviking.session.memory.dataclass import (
    MemoryFile,
    MemoryTypeSchema,
    ResolvedOperation,
    ResolvedOperations,
)


@pytest.fixture
def ctx() -> RequestContext:
    return RequestContext(
        user=UserIdentifier.the_default_user("test-user"),
        role=Role.USER,
    )


@pytest.mark.asyncio
async def test_viking_fs_rm_with_no_vector_skips_vector_store():
    """Verify rm(..., no_vector=True) bypasses directory traversal and vector DB cleanup."""
    from openviking.storage.viking_fs import VikingFS

    fs = VikingFS.__new__(VikingFS)
    test_ctx = RequestContext(user=UserIdentifier.the_default_user("test"), role=Role.USER)
    fs._ctx_or_default = MagicMock(return_value=test_ctx)
    fs._ensure_access = AsyncMock()
    fs._ensure_access_many = AsyncMock()
    fs._uri_to_path = MagicMock(return_value="/sessions/sess-123")
    fs._path_to_uri = MagicMock(return_value="viking://user/test/sessions/sess-123")
    fs._acl_enabled = MagicMock(return_value=False)
    fs._pathlock_fs_ctx = MagicMock(return_value={})

    # Mock AGFS stat and rm
    mock_agfs = MagicMock()
    mock_agfs.stat = AsyncMock(return_value={"isDir": True})
    mock_agfs.pathlock_acquire_tree = AsyncMock(return_value={"lease": "tree-lease"})
    mock_agfs.pathlock_release = AsyncMock()
    mock_agfs.rm = AsyncMock(return_value=True)
    fs._async_agfs = mock_agfs

    fs._collect_uris = AsyncMock()
    fs._delete_from_vector_store = AsyncMock()

    # Call with no_vector=True
    result = await fs.rm(
        "viking://user/test/sessions/sess-123",
        recursive=True,
        no_vector=True,
    )

    assert result == {"estimated_deleted_count": 0}
    # Crucial assertion: vector DB and collection traversal are completely bypassed!
    fs._collect_uris.assert_not_called()
    fs._delete_from_vector_store.assert_not_called()
    mock_agfs.rm.assert_called_once()
    mock_agfs.pathlock_release.assert_called_once()


@pytest.mark.asyncio
async def test_session_service_delete_uses_lightweight_exists_and_no_vector(ctx):
    """Verify SessionService.delete avoids full deserialization via get()."""
    service = SessionService()
    service._ensure_initialized = MagicMock()
    service._record_lifecycle_metric = MagicMock()

    mock_fs = MagicMock()
    mock_fs.rm = AsyncMock()
    service._viking_fs = mock_fs

    # Create session mock
    mock_session = MagicMock()
    mock_session.exists = AsyncMock(return_value=True)
    service.session = MagicMock(return_value=mock_session)

    # Spy on get() to ensure it is NEVER called
    service.get = AsyncMock()

    success = await service.delete("session-perf-42", ctx)

    assert success is True
    service.get.assert_not_called()
    mock_session.exists.assert_called_once()
    mock_fs.rm.assert_called_once_with(
        "viking://user/test-user/sessions/session-perf-42",
        recursive=True,
        ctx=ctx,
        no_vector=True,
    )
    service._record_lifecycle_metric.assert_called_with("delete", "ok")


@pytest.mark.asyncio
async def test_session_service_delete_raises_not_found_on_missing(ctx):
    """Verify SessionService.delete raises NotFoundError when session does not exist."""
    service = SessionService()
    service._ensure_initialized = MagicMock()
    service._record_lifecycle_metric = MagicMock()

    mock_session = MagicMock()
    mock_session.exists = AsyncMock(return_value=False)
    service.session = MagicMock(return_value=mock_session)

    with pytest.raises(NotFoundError):
        await service.delete("missing-session", ctx)

    service._record_lifecycle_metric.assert_called_with("delete", "error")


@pytest.mark.asyncio
async def test_memory_updater_preserves_memories_when_fresh_read_fails():
    """Verify MemoryUpdater blocks overwriting from a stale snapshot when disk read fails."""
    target_uri = "viking://user/u/memories/entities/person/alice.md"
    update_uri = "viking://user/u/memories/entities/person/bob.md"
    read_error = OSError("simulated disk read failure")

    mock_viking_fs = MagicMock()
    # First read for target returns NotFound (file is new), but second read for update raises OSError
    mock_viking_fs.read_file = AsyncMock(
        side_effect=[NotFoundError(target_uri, "file"), read_error]
    )
    mock_viking_fs.write_file = AsyncMock()

    registry = MagicMock()
    registry.get.return_value = MemoryTypeSchema(memory_type="entities")
    updater = MemoryUpdater(registry=registry)
    updater._get_viking_fs = MagicMock(return_value=mock_viking_fs)
    updater._apply_delete = AsyncMock()
    updater._sync_resource_refs_for_result = AsyncMock()

    operations = ResolvedOperations(
        upsert_operations=[
            ResolvedOperation(
                old_memory_file_content=None,
                memory_fields={"name": "Alice"},
                memory_type="entities",
                uris=[target_uri],
            ),
            ResolvedOperation(
                old_memory_file_content=MemoryFile(
                    uri=update_uri, memory_type="entities", content="stale snapshot content"
                ),
                memory_fields={"content": "new update content"},
                memory_type="entities",
                uris=[update_uri],
            ),
        ],
        delete_file_contents=[],
        errors=[],
    )

    result = await updater.apply_operations(operations, MagicMock())

    # When fresh read fails, the error must be recorded and NO writes should occur for update_uri
    assert any(error is read_error for _, error in result.errors)
    assert update_uri not in result.written_uris
    assert update_uri not in result.edited_uris
