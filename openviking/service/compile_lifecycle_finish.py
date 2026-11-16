# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Compile targets: registry, incremental lifecycle and per-file versions.

State lives under ``/local/{account}/_system/compile/``:
``target_folders/{sha256(to)}/state.json`` (source of truth, enumerated for summaries),
``target_folders/{sha256(to)}/operations/{operation_id}.json`` (one record per directory operation),
``target_folders/{sha256(to)}/operation_outputs/{operation_id}.json`` (immutable-path version references), and
``target_folders/{sha256(to)}/file_versions/{sha256(uri)}.json`` (one version index per output
file). Each JSON's read-modify-write takes its own PathLock, so the layout stays
consistent across instances when PathLock uses the cache provider.

CompileService delegates to :class:`CompileLifecycle` from ``create``,
``on_start``, ``submit`` and ``on_finish``. A task runs after the request that
authorized it has ended, so Git access uses an internal ``bypass_acl`` context
for the task owner. Version bodies stay in Git; an index entry points at the
snapshot (``snapshot_id`` + ``snapshot_path``) holding its content.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import sys
import time
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import (
    Annotated,
    Any,
    AsyncContextManager,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Union,
)
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from openviking.core.namespace import classify_uri
from openviking.pyagfs import AsyncAGFSClient
from openviking.pyagfs.async_client import fs_ctx_from_agfs_path
from openviking.pyagfs.exceptions import (
    AGFSAlreadyExistsError,
    AGFSNotFoundError,
    AGFSNotSupportedError,
    GitConcurrentCommitError,
)
from openviking.resource.watch_types import uri_matches_prefix
from openviking.server.identity import RequestContext, Role
from openviking.service.external_task_service import ExternalTaskSnapshot
from openviking.service.task_tracker_concurrency import KeyedAsyncLockPool, run_to_completion
from openviking.storage.acl import AclAction
from openviking.storage.errors import LockAcquisitionError, ResourceBusyError
from openviking.utils.tags import build_search_tags_filter
from openviking_cli.exceptions import (
    ConflictError,
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
    OpenVikingError,
    PermissionDeniedError,
)
from openviking_cli.session.user_id import UserIdentifier
from openviking.service.compile_targets_models import (
    _DERIVED, _NULL_OID, _RESULT_KEYS, _VERSION_META_DEFAULTS, CONTROL_ARGS, GIT_RETRIES,
    HISTORY_RETENTION_SECONDS, LOCK_TIMEOUT_SECONDS, MAX_VERSIONS, SNAPSHOT_BUSY_SECONDS,
    SUMMARY_FIELDS, TERMINAL, CompileStore, DailySchedule, UpdateSchedule, WeeklySchedule,
    _normalize_schedule, _operation_outputs, _params, commit_snapshot, compile_operation_id,
    is_versioned, make_operation_id, new_compile_operation, new_operation, new_record,
    overlaps, parse_schedule, retry_git, split_control_args, summarize, task_ctx,
)


class _CompileLifecycleFinishMixin:

    @staticmethod
    def _task_is_current(record: Optional[Dict[str, Any]], task: Any) -> bool:
        """Accept task effects only for an active target at the task's output URI."""
        request = task.meta["request"]
        # shortcut: tasks use the current target at this URI; snapshot identity if isolation is needed.
        return record is not None and record["status"] == "active" and record["to"] == request["to"]

    async def _locked_output(self, to: str, ctx: RequestContext) -> AsyncIterator[Any]:
        """Yield a tree lease for snapshot/index reconciliation, never Runtime execution.

        Busy processors raise ResourceBusyError; every exit releases the lease.
        """
        try:
            lease = await self._fs._async_agfs.pathlock_acquire_tree(
                self._fs._uri_to_path(to, ctx=ctx)
            )
        except LockAcquisitionError as exc:
            raise ResourceBusyError("Compile output is being processed", uri=to) from exc
        try:
            yield lease
        finally:
            await self._fs._async_agfs.pathlock_release(lease)

    async def on_start(self, task: Any) -> Any:
        """Poll missing target state every five seconds for up to 30, then claim and plan."""
        meta = task.meta["request"].get("compile")
        if meta is None:
            return "proceed"
        account_id = task.account_id
        operation_id = compile_operation_id(task)
        to = task.meta["request"]["to"]
        deadline = time.monotonic() + 30.0
        while await self._store.get(account_id, to) is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return ExternalTaskSnapshot(
                    status="failed",
                    error_code="COMPILE_TARGET_STATE_TIMEOUT",
                    error_message=f"Compile target state is unavailable after 30 seconds: {to}",
                )
            await asyncio.sleep(min(5.0, remaining))
        try:
            async with self._store.edit(account_id, to) as record:
                if not self._task_is_current(record, task):
                    return ExternalTaskSnapshot(
                        status="cancelled", error_message="Compile target was deleted"
                    )
                target_to = record["to"]
                run = await self._store.get_operation(account_id, target_to, operation_id)
                if run and run["status"] in TERMINAL and run["finished_at"] is not None:
                    # Replayed completions must not claim the target and restore an older baseline.
                    return ExternalTaskSnapshot(
                        status=run["status"], result=run.get("result") or {}
                    )
                owner = record["active_task_id"]
                if owner and owner != task.task_id:
                    other = await self._store.get_operation(
                        account_id, target_to, record["active_operation_id"]
                    )
                    if other is not None and other["status"] not in TERMINAL:
                        return "busy"
                record["active_task_id"] = task.task_id
                record["active_operation_id"] = operation_id
                await self.record_queued(task, locked_record=record)
        except LookupError:
            return ExternalTaskSnapshot(
                status="cancelled", error_message="Compile target was moved or deleted"
            )
        run = await self._store.get_operation(account_id, target_to, operation_id)
        if run is None or run["status"] == "queued":
            try:
                run = await self._begin_run(task, record, run)
            except ResourceBusyError:
                return "busy"
        if run["status"] in TERMINAL or run["status"] == "committing":
            # Committing runs resume locally without querying the Runtime session.
            return ExternalTaskSnapshot(
                status="completed" if run["status"] == "committing" else run["status"],
                result=run.get("result") or {},
                error_message=run.get("error"),
            )
        return "proceed"

    async def _begin_run(
        self, task: Any, record: Dict[str, Any], run: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Return the persisted run planned from a task, target record and optional queued run.

        System Skills use live reads and URI identity; other Skills use snapshots.
        A missing output snapshot fails before Runtime execution; busy scopes raise ResourceBusyError.
        """
        meta, request = task.meta["request"]["compile"], task.meta["request"]
        ctx = task_ctx(task.account_id, task.user_id)
        incremental = meta["mode"] == "incremental"
        system_skill = classify_uri(request["skill"]).is_system
        run = run or new_compile_operation(task, record)
        run_meta = run["meta"]
        run["actor"] = task.user_id
        run["status"] = "running"
        run["started_at"] = time.time()
        run_meta["skill_snapshot"] = {"uri": request["skill"], "snapshot_id": None}
        if not system_skill:
            async with self._locked_output(request["skill"], ctx) as lease:
                run_meta["skill_snapshot"]["snapshot_id"] = await commit_snapshot(
                    self._fs,
                    [request["skill"]],
                    f"compile {task.task_id} skill",
                    ctx,
                    wait_busy=False,
                    lease_ref=lease,
                )
        progress_key = "scheduled_progress" if meta["trigger"] == "scheduled" else "progress"
        progress = record.get(progress_key) or {}
        previous_skill = progress.get("skill_snapshot") or {}
        mode = "full"
        skill_base = previous_skill.get("snapshot_id")
        skill_head = run_meta["skill_snapshot"]["snapshot_id"]
        if (
            incremental
            and (request.get("instruction") or "").strip() == progress.get("instruction")
            and previous_skill.get("uri") == request["skill"]
        ):
            if system_skill:
                mode = "incremental"
            elif skill_base and skill_head:
                # Skill dependencies include package files filtered from ordinary source diffs.
                skill_changes = await self._fs._async_agfs.run(
                    "git_diff_paths",
                    account=ctx.account_id,
                    base=skill_base,
                    head=skill_head,
                    paths=[self._fs._uri_to_tree_path(request["skill"], ctx=ctx)],
                )
                if not skill_changes:
                    mode = "incremental"
        paths = [request["to"], *request["from"]]
        async with self._locked_output(request["to"], ctx) as lease:
            run_meta["target_base"] = await commit_snapshot(
                self._fs,
                paths,
                f"compile {task.task_id} start",
                ctx,
                wait_busy=False,
                lease_ref=lease,
            )
            if not run_meta["target_base"]:
                run["status"] = "failed"
                run["error"] = "Compile requires an available start snapshot for rollback"
                await self._store.put_operation(task.account_id, record["to"], run)
                return run
            run_meta["execution"] = {"mode": mode}
            await self.versions.record_external(
                task.account_id, record, run_meta["target_base"], ctx
            )
            run_meta.update(
                await self._plan(
                    {} if mode == "full" else progress,
                    request["from"],
                    run_meta["target_base"],
                    ctx,
                )
            )
            if mode == "incremental" and not run_meta["changed_roots"] and record["initialized"]:
                run["status"] = "completed"
            await self._store.put_operation(task.account_id, record["to"], run)
        return run

    async def _plan(
        self, progress: Dict[str, Any], sources: List[str], head: Optional[str], ctx: RequestContext
    ) -> Dict[str, Any]:
        """Compare source roots against one trigger's successful baseline; empty progress scans all roots."""
        base = progress.get("source_commit")
        processed = set(progress.get("processed_roots") or [])
        compared = [source for source in sources if base and source in processed]
        added_roots = [source for source in sources if source not in compared]
        changes = (
            await self._fs.diff_paths(dirs=compared, base=base, head=head, ctx=ctx)
            if compared and head
            else []
        )
        summary = dict.fromkeys(_RESULT_KEYS, 0)
        for change in changes:
            summary[change["change_type"]] += 1
        changed_roots = added_roots + [
            root for root in compared if any(c["uri"].startswith(f"{root}/") for c in changes)
        ]
        return {
            "base": base,
            "head": head,
            "diff_dirs": compared,
            "full_dirs": added_roots,
            "changed_roots": changed_roots,
            "changes": summary,
        }

    async def runtime_changes(
        self, payload: Mapping[str, Any], account_id: str, task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return Skill identity and effective execution mode with the persisted source plan."""
        meta = payload.get("compile")
        if not meta:
            return None
        record = await self._store.get(account_id, payload["to"])
        if record is None or record["active_task_id"] != task_id:
            return None
        run = await self._store.get_operation(
            account_id, record["to"], record["active_operation_id"]
        )
        if run is None or run["meta"].get("changes") is None:
            return None
        run_meta = run["meta"]
        return {
            "base": run_meta["base"],
            "head": run_meta["head"],
            "diff_dirs": run_meta["diff_dirs"],
            "full_dirs": run_meta["full_dirs"],
            "execution": run_meta.get("execution"),
            "skill_snapshot": run_meta.get("skill_snapshot"),
        }

    async def on_finish(self, task: Any, snapshot: ExternalTaskSnapshot) -> ExternalTaskSnapshot:
        """Finalize output and versions; return active status on busy locks."""
        from openviking.server.dependencies import get_service
        from openviking.service.task_tracker import get_task_tracker

        meta, request = task.meta["request"].get("compile"), task.meta["request"]
        if meta is None:
            return snapshot
        account_id = task.account_id
        tracker = get_task_tracker()
        if await tracker.is_task_cancellation_requested(
            task.task_id, account_id=account_id, user_id=task.user_id
        ):
            snapshot = ExternalTaskSnapshot(status="cancelled")
        record = await self._store.get(account_id, request["to"])
        if record is None:
            if snapshot.error_code == "COMPILE_TARGET_STATE_TIMEOUT":
                return snapshot
            return ExternalTaskSnapshot(
                status="cancelled", error_message="Compile target was moved or deleted"
            )
        target_to = record["to"]
        operation_id = compile_operation_id(task)
        async with self._store.lock_operation(account_id, target_to, operation_id, "finish"):
            run = await self._store.get_operation(account_id, target_to, operation_id)
            if run is not None and run["finished_at"] is None:
                run_meta = run["meta"]
                ctx = task_ctx(task.account_id, task.user_id)
                record = await self._store.get(account_id, request["to"])
                current = self._task_is_current(record, task)
                if not current:
                    snapshot = ExternalTaskSnapshot(
                        status=run["status"] if run["status"] in TERMINAL else "cancelled",
                        result=run.get("result"),
                        error_message="Compile target was deleted",
                    )
                elif run["started_at"] is None or run["status"] == "completed":
                    # Unstarted and unchanged runs have no output to publish.
                    if snapshot.status == "failed":
                        run["error"] = snapshot.error_message or snapshot.status
                elif snapshot.status == "completed":
                    if run["status"] != "committing":
                        run["status"] = "committing"
                        await self._store.put_operation(account_id, target_to, run)
                    try:
                        await get_service().fs.finalize_compile_directories(request["to"], ctx)
                        async with self._locked_output(request["to"], ctx) as lease:
                            if await tracker.is_task_cancellation_requested(
                                task.task_id, account_id=account_id, user_id=task.user_id
                            ):
                                raise asyncio.CancelledError()

                            async def publish() -> None:
                                """Persist snapshot and versions under the output lease."""
                                if not run_meta.get("snapshot_committed"):
                                    head = await self._commit(
                                        [request["to"]],
                                        f"compile {task.task_id} finish",
                                        ctx,
                                        lease_ref=lease,
                                        wait_busy=False,
                                    )
                                    if not head:
                                        raise FailedPreconditionError(
                                            "Compile output snapshot is unavailable"
                                        )
                                    run_meta["target_head"] = head
                                    run_meta["snapshot_committed"] = True
                                    run_meta["target_committed_at"] = int(time.time() * 1000)
                                    await self._store.put_operation(account_id, target_to, run)
                                head = run_meta["target_head"]
                                if not head:
                                    raise FailedPreconditionError(
                                        "Compile output snapshot is unavailable"
                                    )
                                changes = await self._fs.diff_paths(
                                    dirs=[request["to"]],
                                    base=run_meta["target_base"],
                                    head=head,
                                    ctx=ctx,
                                )
                                run["result"] = dict.fromkeys(_RESULT_KEYS.values(), 0)
                                for change in changes:
                                    if is_versioned(change["uri"]):
                                        run["result"][_RESULT_KEYS[change["change_type"]]] += 1
                                record = await self._store.get(account_id, request["to"])
                                await self.versions.record_compile(
                                    account_id, record, run, head, changes, ctx
                                )
                                if not run_meta.get("target_committed_at"):
                                    run_meta["target_committed_at"] = int(time.time() * 1000)
                                    await self._store.put_operation(account_id, target_to, run)
                                from openviking.observability.reporting.facts import (
                                    emit_compile_outputs,
                                )

                                emit_compile_outputs(
                                    task,
                                    changes,
                                    snapshot_id=head,
                                    committed_at=run_meta["target_committed_at"],
                                )
                                if (
                                    any(is_versioned(change["uri"]) for change in changes)
                                    and (record.get("content_updated_at") or 0) < run["started_at"]
                                ):
                                    run_meta["content_changed"] = True

                            record = await self._store.get(account_id, request["to"])
                            current = self._task_is_current(record, task)
                            if current:
                                await run_to_completion(publish)
                            else:
                                snapshot = ExternalTaskSnapshot(
                                    status="cancelled", error_message="Compile target was deleted"
                                )
                        if await tracker.is_task_cancellation_requested(
                            task.task_id, account_id=account_id, user_id=task.user_id
                        ):
                            snapshot = ExternalTaskSnapshot(status="cancelled")
                    except ResourceBusyError as exc:
                        if not exc.retryable:
                            raise
                        return ExternalTaskSnapshot(status="running", stage="committing")
                if current and snapshot.status in {"failed", "cancelled"}:
                    if run_meta["target_base"] and not run_meta.get("snapshot_committed"):
                        try:
                            await run_to_completion(lambda: self._rollback(request["to"], run, ctx))
                        except ResourceBusyError as exc:
                            if not exc.retryable:
                                raise
                            return ExternalTaskSnapshot(
                                status="cancelling",
                                stage="cancelling",
                                result=snapshot.result,
                                error_code=snapshot.error_code,
                                error_message=snapshot.error_message,
                            )
                    run["error"] = snapshot.error_message or snapshot.status
                if snapshot.status == "completed" and run["started_at"] is not None:
                    if run["status"] == "completed":
                        await get_service().fs.finalize_compile_directories(request["to"], ctx)
                    await self._update_conflicts(task, ctx)
                run["status"] = snapshot.status
                run["finished_at"] = time.time()
                await self._store.put_operation(account_id, target_to, run)
            await self._release(account_id, target_to, task, run)
            return snapshot
