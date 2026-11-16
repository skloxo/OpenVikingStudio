# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Watch management, resource submission and single-run settlement.

Permission and runtime conditions are evaluated by the store. Target stability comes
from PathLock: a Watch row is created, and a run starts occupying it, only
while its target's Tree lock is held; transfers rewrite rows inside their own
lock and check occupancy there.

Initialize after FS and TaskTracker; close after callers, Runtime, resource
monitors and queue callbacks stop. The Manager spawns no background coroutines.
"""

import asyncio
import inspect
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Sequence

from openviking.connector.auth import is_external_feishu_auth, restore_feishu_request
from openviking.connector.delegate import ConnectorDelegate
from openviking.observability.http_error_context import sanitize_public_http_error
from openviking.resource.git_watch_auth import (
    git_http_auth_config_from_state,
    is_git_http_auth_state,
)
from openviking.resource.processing_mode import DEFAULT_PROCESSING_MODE, ProcessingMode
from openviking.resource.watch_store import WatchListPage, WatchMoveResult, WatchStore
from openviking.resource.watch_types import (
    MUTABLE_FIELDS,
    PermissionDeniedError,
    WatchAuthority,
    WatchCandidate,
    WatchPatch,
    WatchReceipt,
    WatchRun,
    WatchRunning,
    WatchRunResult,
    WatchState,
    WatchTask,
)
from openviking.server.error_mapping import is_not_found_error
from openviking.server.identity import RequestContext, Role
from openviking.service.task_tracker import get_task_tracker
from openviking.service.task_tracker_concurrency import KeyedAsyncLockPool, run_to_completion
from openviking.storage.errors import LockAcquisitionError, ResourceBusyError
from openviking.utils.git_auth import GIT_AUTH_FAILED
from openviking.utils.network_guard import ensure_public_remote_target
from openviking_cli.exceptions import ConflictError, FailedPreconditionError
from openviking_cli.session.user_id import UserIdentifier


class _WatchManagerSettleMixin:

    @classmethod
    def result(
        cls,
        task: WatchTask,
        status: str,
        result: Optional[dict[str, Any]],
        error: Optional[str],
    ) -> WatchRunResult:
        return cls._result(
            status,
            result,
            error,
            connector=ConnectorDelegate.is_watch_auth_state(task.auth_state),
            instruction=task.instruction,
        )

    @staticmethod
    def _result(
        status: str,
        result: Optional[dict[str, Any]],
        error: Optional[str],
        *,
        connector: bool,
        instruction: str,
    ) -> WatchRunResult:
        result = result or {}
        if status == "completed" and result.get("import_complete") is False:
            status = "partial"
        states = result.get("connector_states")
        has_states = connector and status == "completed" and "connector_states" in result
        if has_states and not isinstance(states, dict):
            status, error, has_states = "failed", "connector_states must be an object", False
        if status in {"failed", "error"} and not error:
            errors = result.get("errors")
            error = "; ".join(str(item) for item in errors) if errors else "watch ingestion failed"
        # A successful source import may later fail in semantic/embedding Work.
        # Its explicit checkpoint still describes the revision actually imported.
        checkpoint = (
            result.get("source_checkpoint")
            if status != "cancelled" and result.get("import_complete") is not False
            else None
        )
        if status == "completed":
            from openviking.service.resource_service import ResourceService

            checkpoint = checkpoint or ResourceService._initial_source_checkpoint(
                result.get("meta"), instruction=instruction
            )
        return WatchRunResult(
            status=status,
            execution_task_id=result.get("task_id"),
            error=error,
            deactivate=result.get("code") == GIT_AUTH_FAILED,
            connector_states=states if has_states else None,
            has_connector_states=has_states,
            source_checkpoint=checkpoint,
        )

    async def settle(self, task_id: str, run_id: str) -> bool:
        """Settle callbacks that have IDs but no Watch run snapshot."""
        state = await self.store.get_state(task_id)
        if state is None or state.current_run_id != run_id:
            return False
        run = self.run(state)
        record = await self.tracker.get(
            run_id, account_id=run.task.account_id, user_id=run.task.user_id
        )
        return await self.settle_running(self.observation(state), record)

    @staticmethod
    def observation(state: WatchState) -> WatchRunning:
        assert state.run_started_at is not None
        return WatchRunning(
            task_id=state.task.task_id,
            account_id=state.task.account_id,
            user_id=state.task.user_id,
            current_run_id=state.current_run_id,
            run_started_at=state.run_started_at,
            now=state.now,
            connector=ConnectorDelegate.is_watch_auth_state(state.task.auth_state),
            instruction=state.task.instruction,
        )

    async def settle_record(self, run: WatchRun, record: Any) -> bool:
        """Use existing snapshots; the Store condition guards against stale runs."""
        if record is None or record.task_id != run.run_id or not record.is_terminal():
            return False
        result = {**(record.result or {}), "task_id": record.task_id}
        return await run_to_completion(
            lambda: self.finish_run(
                run.task_id,
                run.run_id,
                self.result(run.task, record.status.value, result, record.error),
                started_at=run.started_at,
            )
        )

    async def settle_running(self, state: WatchRunning, record: Any) -> bool:
        """Settle a scanned run without loading or decrypting the complete Watch."""
        if record is None or record.task_id != state.current_run_id or not record.is_terminal():
            return False
        result = {**(record.result or {}), "task_id": record.task_id}
        return await run_to_completion(
            lambda: self.finish_run(
                state.task_id,
                state.current_run_id,
                self._result(
                    record.status.value,
                    result,
                    record.error,
                    connector=state.connector,
                    instruction=state.instruction,
                ),
                started_at=state.run_started_at,
            )
        )

    async def delete_tasks(self, account_id: str, user_id: Optional[str] = None) -> None:
        """Identity cleanup uses durable rows, independently of any local Runtime."""
        states = await self.store.delete_tasks(account_id, user_id)
        for state in states:
            run = self.run(state)
            owner = {"account_id": run.task.account_id, "user_id": run.task.user_id}
            record = await self.tracker.get(run.run_id, **owner) if run.run_id else None
            if record is not None and not record.is_terminal():
                try:
                    await self.tracker.cancel(run.run_id, **owner)
                except ValueError:
                    await self.tracker.fail(run.run_id, "Watch deleted", **owner)
                record = await self.tracker.get(run.run_id, **owner)
            if record is None:
                await self.finish_run(
                    run.task_id,
                    run.run_id,
                    WatchRunResult(status="cancelled", execution_task_id=run.run_id),
                    started_at=run.started_at,
                )
            else:
                await self.settle_running(self.observation(state), record)
