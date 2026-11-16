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
from openviking_cli.utils import get_logger

logger = get_logger(__name__)
from openviking.service.task_tracker_concurrency import KeyedAsyncLockPool, run_to_completion
from openviking.storage.errors import LockAcquisitionError, ResourceBusyError
from openviking.utils.git_auth import GIT_AUTH_FAILED
from openviking.utils.network_guard import ensure_public_remote_target
from openviking_cli.exceptions import ConflictError, FailedPreconditionError
from openviking_cli.session.user_id import UserIdentifier


class _WatchManagerSyncMixin:

    @property
    def tracker(self) -> Any:
        return self._tracker if self._tracker is not None else get_task_tracker()

    @staticmethod
    def context(task: WatchTask) -> RequestContext:
        try:
            role = Role(task.original_role)
        except ValueError:
            role = Role.USER
        return RequestContext(
            user=UserIdentifier(task.account_id, task.user_id),
            role=role,
            bypass_acl=True,
        )

    @staticmethod
    def run(state: WatchState) -> WatchRun:
        return WatchRun(
            state.task.task_id,
            state.current_run_id,
            state.task.model_copy(deep=True),
            started_at=state.run_started_at,
        )

    async def trigger(self, task_id: str, *, manual: bool = True) -> Optional[WatchReceipt]:
        """Submit once through ResourceService and return its actual Task ID."""
        if self._resource_service is None or self._viking_fs is None:
            raise RuntimeError("Watch resource submission dependencies are not initialized")

        async def submit() -> Optional[WatchReceipt]:
            async with self._trigger_locks.acquire(task_id):
                return await self._trigger(task_id, manual=manual)

        return await run_to_completion(submit)

    async def _trigger(self, task_id: str, *, manual: bool) -> Optional[WatchReceipt]:
        task = await self.store.get_candidate(task_id)
        if task is None:
            return None
        if task.run_started_at is not None:
            state = await self.store.get_state(task_id)
            if state is None or state.deleted:
                return None
            if state.run_started_at is not None:
                return await self._reuse(state, retry_terminal=True, manual=manual)
        run = None
        lock_error = None
        try:
            async with self.locks.tree(
                task.account_id, task.to_uri, timeout=5.0 if manual else 0.0
            ):
                if await self._owner_deleting(task.account_id, task.user_id):
                    raise FailedPreconditionError("Identity deletion is in progress")
                run = await self.store.begin_run(task, manual=manual)
        except LockAcquisitionError as exc:
            lock_error = exc
        if run is None:
            # Another caller may have attached its Task since the entry read.
            latest = await self.store.get_state(task_id)
            receipt = (
                await self._reuse(latest, retry_terminal=True, manual=manual)
                if latest and not latest.deleted
                else None
            )
            if receipt is None and manual and lock_error is not None:
                raise ResourceBusyError(
                    "Watch target is being changed; retry the trigger",
                    uri=task.to_uri,
                ) from lock_error
            return receipt
        return await self._execute(run)

    async def due(self, limit: int) -> list[WatchRun]:
        """Return already occupied runs; all execution parameters are fixed here."""
        runs: list[WatchRun] = []
        offset = 0
        try:
            while len(runs) < limit:
                size = limit - len(runs)
                candidates = await self.store.due_candidates(size, offset=offset)
                for task in candidates:
                    try:
                        async with self.locks.tree(task.account_id, task.to_uri, timeout=0.0):
                            if await self._owner_deleting(task.account_id, task.user_id):
                                offset += 1
                                continue

                            async def claim(candidate: WatchCandidate = task) -> None:
                                run = await self.store.begin_run(candidate)
                                if run is not None:
                                    runs.append(run)

                            # Keep the target locked until a reservation commits.
                            # Record its result before propagating cancellation.
                            await run_to_completion(claim)
                    except LockAcquisitionError:
                        offset += 1
                if len(candidates) < size:
                    break
            return runs
        except BaseException:

            async def release() -> None:
                for run in runs:
                    await self.finish_run(
                        run.task_id,
                        None,
                        WatchRunResult(status="error", error="Watch dispatch interrupted"),
                        started_at=run.started_at,
                    )

            await run_to_completion(release)
            raise

    async def execute(self, run: WatchRun) -> Optional[WatchReceipt]:
        """Submit a reserved snapshot without re-reading the Watch."""
        return await run_to_completion(lambda: self._execute(run))

    async def _execute(self, run: WatchRun) -> Optional[WatchReceipt]:
        task, task_id = run.task, run.task_id
        # Release the data target lock before preparation or an external
        # Connector request, whose callback may import into this target.
        actual_run = run

        async def on_task_created(record: Any) -> None:
            nonlocal actual_run
            actual_run = replace(run, run_id=record.task_id)
            if not await self.store.attach_task(task_id, record.task_id, started_at=run.started_at):
                raise FailedPreconditionError("Watch submission is no longer current")

        try:
            if task.to_uri and not ConnectorDelegate.is_watch_auth_state(task.auth_state):
                try:
                    await self._viking_fs.stat(task.to_uri, ctx=self.context(task), skip_count=True)
                except Exception as exc:
                    if not is_not_found_error(exc):
                        raise
                    await self.finish_run(
                        task_id,
                        None,
                        WatchRunResult(
                            status="failed",
                            error=f"Watched target URI does not exist: {task.to_uri}",
                            deactivate=True,
                        ),
                        started_at=run.started_at,
                    )
                    return None
            result = await self._submit_resource(run, on_task_created)
            if actual_run.run_id is None:
                if isinstance(result, WatchRunResult):
                    outcome = result
                elif (result or {}).get("status") in {
                    "completed",
                    "partial",
                    "failed",
                    "error",
                    "cancelled",
                }:
                    outcome = self.result(run.task, result["status"], result, None)
                else:
                    raise RuntimeError("Resource submission did not create a Task")
                await self.finish_run(task_id, None, outcome, started_at=run.started_at)
                return None
            record = await self.tracker.get(
                actual_run.run_id, account_id=task.account_id, user_id=task.user_id
            )
            await self.settle_record(actual_run, record)
            return WatchReceipt(task_id, actual_run.run_id, False)
        except Exception as exc:
            if actual_run.run_id is not None:
                owner = {"account_id": task.account_id, "user_id": task.user_id}
                record = await self.tracker.get(actual_run.run_id, **owner)
                if record is not None and not record.is_terminal():
                    await self.tracker.fail(actual_run.run_id, str(exc), **owner)
                    record = await self.tracker.get(actual_run.run_id, **owner)
                await self.settle_record(actual_run, record)
            await self.finish_run(
                task_id,
                None,
                WatchRunResult(
                    status="failed",
                    error=str(exc),
                    deactivate=isinstance(exc, FileNotFoundError)
                    or getattr(exc, "code", None) == GIT_AUTH_FAILED,
                ),
                started_at=run.started_at,
            )
            raise

    async def _reuse(
        self, state: WatchState, *, retry_terminal: bool = False, manual: bool = True
    ) -> Optional[WatchReceipt]:
        if not state.current_run_id:
            return None
        run = self.run(state)
        record = await self.tracker.get(
            run.run_id, account_id=run.task.account_id, user_id=run.task.user_id
        )
        if record is None:
            return None
        if record.is_terminal():
            await self.settle_running(self.observation(state), record)
            if retry_terminal:
                return await self._trigger(run.task_id, manual=manual)
        return WatchReceipt(run.task_id, run.run_id, True)

    async def _submit_resource(self, run: WatchRun, on_task_created: Any) -> Any:
        # Keep parser-backed Feishu dependencies out of WatchManager's import boundary.
        from openviking.resource.feishu_watch_auth import (
            FeishuOAuthClient,
            FeishuTokenRefreshError,
            apply_feishu_refreshed_token,
            feishu_auth_state_needs_refresh,
            is_feishu_auth_state,
        )

        task, auth = run.task, run.task.auth_state
        connector = ConnectorDelegate.is_watch_auth_state(auth)
        ctx = self.context(task)
        if (
            not connector
            and not task.path.startswith(("http://", "https://", "git@", "ssh://", "git://"))
            and not Path(task.path).exists()
        ):
            return WatchRunResult(
                status="failed",
                error=f"Resource path does not exist: {task.path}",
                deactivate=True,
            )
        kwargs = dict(task.processor_kwargs or {})
        kwargs.pop("build_index", None)
        kwargs.pop("summarize", None)
        if is_external_feishu_auth(auth):
            ctx.api_key, kwargs["args"] = await restore_feishu_request(
                self._resource_service._connector, auth, path=task.path, ctx=ctx
            )
        elif is_feishu_auth_state(auth):
            try:
                if feishu_auth_state_needs_refresh(auth):
                    from openviking.config.feishu import get_effective_feishu_config

                    if self._runtime_config_manager is None:
                        raise RuntimeError("Runtime config manager is not initialized")
                    config = await get_effective_feishu_config(
                        self._runtime_config_manager, task.account_id
                    )
                    refreshed = await FeishuOAuthClient.from_auth_state(
                        auth, config=config
                    ).refresh_user_access_token(auth.get("refresh_token"))
                    auth = apply_feishu_refreshed_token(auth, refreshed)
                    await self.update_auth_state(task.task_id, auth, run_id=run.run_id)
                kwargs["feishu_access_token"] = auth["access_token"]
            except FeishuTokenRefreshError as exc:
                if not exc.permanent:
                    raise
                return WatchRunResult(status="failed", error=str(exc), deactivate=True)
        elif is_git_http_auth_state(auth):
            kwargs["auth_config"] = git_http_auth_config_from_state(auth, task.path)
        elif connector:
            (
                ctx.api_key,
                kwargs["add_type"],
                kwargs["args"],
                connector_auth,
            ) = await self._resource_service._connector.restore_watch_request(
                auth, account_id=task.account_id, path=task.path
            )
            if connector_auth is not None:
                kwargs["connector_auth_config"] = connector_auth
            kwargs["connector_states"] = task.connector_states
        if not connector:
            checkpoint = await self._probe_git_checkpoint(task, kwargs, ctx)
            if checkpoint is not None:
                kwargs["git_head_sha_hint"] = checkpoint["head_sha"]
                if checkpoint == task.source_checkpoint:
                    return WatchRunResult(status="completed", execution_task_id=task.last_task_id)
        return await self._resource_service.refresh_resource(
            path=task.path,
            ctx=ctx,
            to=task.to_uri,
            to_is_directory=task.to_is_directory,
            parent=task.parent_uri,
            reason=task.reason,
            instruction=task.instruction,
            build_index=task.build_index,
            summarize=task.summarize,
            processing_mode=task.processing_mode,
            watch_interval=task.watch_interval,
            enforce_public_remote_targets=True,
            wait_for_completion=False,
            on_task_created=on_task_created,
            **kwargs,
        )

    async def _probe_git_checkpoint(
        self, task: WatchTask, kwargs: Dict[str, Any], ctx: RequestContext
    ) -> Optional[Dict[str, Any]]:
        from openviking.parse.accessors.git_accessor import GitAccessor
        from openviking.utils.code_hosting_utils import is_git_repo_url

        if not is_git_repo_url(task.path):
            return None
        try:
            probe_kwargs = dict(kwargs)
            probe_kwargs["request_validator"] = ensure_public_remote_target
            if probe_kwargs.get("auth_config") is None:
                processor = getattr(self._resource_service, "_resource_processor", None)
                if processor is not None:
                    token = await processor.github_token_for(task.path, ctx)
                    if token:
                        probe_kwargs["auth_config"] = {"token": token}
            probed = await asyncio.wait_for(
                GitAccessor().probe_git_remote_head(task.path, **probe_kwargs),
                timeout=self.DEFAULT_GIT_PROBE_TIMEOUT,
            )
        except Exception as exc:
            logger.warning(
                "[WatchManager] Git probe failed for %s: %s; falling back to refresh",
                task.path,
                self._public_error(str(exc)),
            )
            return None
        if probed is None:
            return None
        return {"kind": "git", "head_sha": probed[1], "instruction": task.instruction}
