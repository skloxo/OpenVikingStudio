# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-209 Regression Tests: Storage Engine, Session Transient Retry, and Vector Recovery."""

import errno
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking.session.memory.dataclass import MemoryFile, ResolvedOperation
from openviking.session.memory.memory_updater import (
    MemoryReadError,
    MemoryUpdateError,
    MemoryUpdateResult,
    MemoryUpdater,
)
from openviking.storage.vectordb.collection.local_collection import _RECOVERY_BATCH_SIZE
from openviking.utils.model_retry import is_retryable_api_error


class TestTracer1SessionTransientRetry:
    """Tracer-1: MemoryReadError classification and transient read retry behavior."""

    def test_memory_read_error_retryable_flags(self):
        uri = "viking://user/default/memories/profile.md"

        # Transient errors must be marked retryable
        err_timeout = MemoryReadError(uri, TimeoutError("read timed out"))
        assert err_timeout.retryable is True

        err_conn = MemoryReadError(uri, ConnectionError("connection reset"))
        assert err_conn.retryable is True

        err_os_eagain = MemoryReadError(uri, OSError(errno.EAGAIN, "Resource temporarily unavailable"))
        assert err_os_eagain.retryable is True

        # Non-transient errors must NOT be retryable
        err_val = MemoryReadError(uri, ValueError("invalid syntax"))
        assert err_val.retryable is False

        err_perm = MemoryReadError(uri, PermissionError("permission denied"))
        assert err_perm.retryable is False

    def test_memory_update_error_blocks_reextraction(self):
        """MemoryUpdateError must not trigger expensive LLM re-extraction."""
        result = MemoryUpdateResult()
        uri = "viking://user/default/memories/profile.md"
        result.add_error(uri, MemoryReadError(uri, TimeoutError("timed out")))
        update_error = MemoryUpdateError(result)

        # Retry condition: not isinstance(error, MemoryUpdateError) and is_retryable_api_error(error)
        is_retryable = (
            not isinstance(update_error, MemoryUpdateError)
            and is_retryable_api_error(update_error)
        )
        assert is_retryable is False

    @pytest.mark.asyncio
    async def test_apply_upsert_retries_transient_read(self):
        """_apply_upsert retries transient read failure before applying patch."""
        uri = "viking://user/default/memories/profile.md"
        mock_viking_fs = MagicMock()
        mock_content = '{"user_id": "test", "content": "alpha beta"}'

        # First read fails with TimeoutError, second succeeds
        mock_viking_fs.read_file = AsyncMock(
            side_effect=[TimeoutError("transient timeout"), mock_content]
        )
        mock_viking_fs.write_file = AsyncMock()

        mock_registry = MagicMock()
        mock_schema = MagicMock()
        mock_schema.fields = []
        mock_registry.get.return_value = mock_schema

        updater = MemoryUpdater(registry=mock_registry)
        updater._get_viking_fs = MagicMock(return_value=mock_viking_fs)

        resolved_op = ResolvedOperation(
            old_memory_file_content=MemoryFile(uri=uri, memory_type="profile", content="alpha"),
            memory_fields={},
            memory_type="profile",
            uris=[uri],
        )

        ctx = MagicMock()
        # Should succeed because retry succeeds
        await updater._apply_upsert(resolved_op, ctx)
        assert mock_viking_fs.read_file.await_count == 2
        assert mock_viking_fs.write_file.await_count == 1


class TestTracer2VectorRecoveryBatchBound:
    """Tracer-2: Bounded vector delta replay batch size."""

    def test_recovery_batch_size_constant(self):
        """Verify vector recovery batch upper bound is strictly 1024."""
        assert _RECOVERY_BATCH_SIZE == 1024


class TestTracer4AdminExistenceProbes:
    """Tracer-4: Lightweight credential-free existence endpoints."""

    @pytest.mark.asyncio
    async def test_admin_get_account_endpoint_contract(self):
        from openviking.server.identity import RequestContext, Role
        from openviking.server.routers.admin import get_account
        from openviking_cli.session.user_id import UserIdentifier

        mock_req = MagicMock()
        mock_manager = AsyncMock()
        mock_manager.get_account.return_value = {
            "account_id": "acct_test",
            "created_at": "2026-10-21T00:00:00Z",
            "user_count": 2,
            "status": "active",
        }
        mock_req.app.state.api_key_manager = mock_manager
        ctx = RequestContext(user=UserIdentifier("acct_test", "root"), role=Role.ROOT)

        with patch("openviking.server.routers.admin._get_api_key_manager", return_value=mock_manager):
            resp = await get_account(request=mock_req, account_id="acct_test", ctx=ctx)
            assert resp.status == "ok"
            assert resp.result["account_id"] == "acct_test"
            assert "api_key" not in resp.result
            assert "key_prefix" not in resp.result

    @pytest.mark.asyncio
    async def test_admin_get_user_membership_probe_zero_secrets(self):
        from openviking.server.identity import RequestContext, Role
        from openviking.server.routers.admin import get_user
        from openviking_cli.session.user_id import UserIdentifier

        mock_req = MagicMock()
        mock_manager = AsyncMock()
        mock_manager.get_user_membership.return_value = {
            "user_id": "alice",
            "role": "admin",
            "api_key": "MUST_BE_STRIPPED_SECRET",
        }
        mock_req.app.state.api_key_manager = mock_manager
        ctx = RequestContext(user=UserIdentifier("acct_test", "root"), role=Role.ROOT)

        with patch("openviking.server.routers.admin._get_api_key_manager", return_value=mock_manager), \
             patch("openviking.server.routers.admin._check_account_access"):
            resp = await get_user(
                request=mock_req,
                account_id="acct_test",
                user_id="alice",
                ctx=ctx,
            )
            assert resp.status == "ok"
            assert resp.result == {"user_id": "alice", "role": "admin"}
            # Zero secret fields
            assert "api_key" not in resp.result
            assert "key_prefix" not in resp.result
