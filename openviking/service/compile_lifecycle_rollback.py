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
    overlaps, parse_schedule, retry_git, split_control_args, summarize, task_ctx, logger,
)


class _CompileLifecycleRollbackMixin:

    async def _update_conflicts(self, task: Any, ctx: RequestContext) -> None:
        """Save the indexed conflict count after publication, capped at 100."""
        from openviking.server.dependencies import get_service

        service = get_service()
        target = task.meta["request"]["to"]
        # shortcut: counts stop at 100; add pagination when exact larger totals are needed.
        conflicts = await service.search.find(
            query="",
            ctx=ctx,
            target_uri=target,
            limit=100,
            filter=build_search_tags_filter(["has_conflict=true"]),
            level=[2],
        )
        async with self._store.edit(task.account_id, target) as record:
            record["conflicts_num"] = conflicts.total

    async def _release(
        self, account_id: str, target_to: str, task: Any, run: Optional[Dict[str, Any]]
    ) -> None:
        first_success = False
        try:
            async with self._store.edit(account_id, task.meta["request"]["to"]) as record:
                if not self._task_is_current(record, task):
                    return
                task_id = task.task_id
                if (
                    record["active_task_id"] == task_id
                    or (
                        record["active_task_id"] is None
                        and (record.get("last_run") or {}).get("task_id") == task_id
                    )
                ) and run is not None:
                    # Write hooks can publish their marker after final operation state is saved.
                    run = (
                        await self._store.get_operation(account_id, target_to, run["operation_id"])
                        or run
                    )
                    run_meta = run["meta"]
                    record["last_run"] = {
                        "task_id": task_id,
                        "status": run["status"],
                        "finished_at": run["finished_at"],
                        "error": run.get("error"),
                    }
                    if run["finished_at"] is not None and run_meta.get("content_changed"):
                        record["content_updated_at"] = max(
                            record.get("content_updated_at") or 0, run["finished_at"]
                        )
                    if run["status"] == "completed":
                        first_success = not record["initialized"]
                        record["initialized"] = True
                        if run_meta.get("head"):
                            progress_key = (
                                "scheduled_progress"
                                if run_meta["trigger"] == "scheduled"
                                else "progress"
                            )
                            record[progress_key] = {
                                "source_commit": run_meta["head"],
                                "processed_roots": list(run["params"]["from"]),
                                "instruction": (run["params"].get("instruction") or "").strip(),
                                "skill_snapshot": run_meta.get("skill_snapshot"),
                            }
                    # The head identifies the content published by completion or rollback.
                    synced = run_meta.get("target_head") or run_meta.get("target_base")
                    if synced:
                        record["versions_head"] = synced
                if record["active_task_id"] == task_id:
                    record["active_task_id"] = None
                    record["active_operation_id"] = None
        except LookupError:
            return
        if first_success and self.reschedule is not None:
            await self.reschedule(account_id, record)

    async def _rollback(self, to: str, run: Dict[str, Any], ctx: RequestContext) -> None:
        """Restore ``to`` to ``run``'s baseline; ``ctx`` provides snapshot access.

        Writes enforce the owner's USER ACL. Denied paths are recorded; storage
        errors propagate. A persisted head makes completion idempotent.
        """
        run_meta = run["meta"]
        restored, deleted = [], []
        try:
            async with self._locked_output(to, ctx) as lease:
                if run_meta.get("rollback_head"):
                    run_meta["target_head"] = run_meta["rollback_head"]
                    return
                actor_ctx = RequestContext(
                    user=ctx.user,
                    role=Role.USER,
                    bypass_acl=False,
                    group_ids=(
                        tuple(await self.resolve_groups(ctx.account_id, ctx.user.user_id))
                        if self.resolve_groups is not None
                        else ()
                    ),
                )
                head = await self._commit(
                    [to],
                    f"compile {run_meta['task_id']} rollback point",
                    ctx,
                    lease_ref=lease,
                    wait_busy=False,
                )
                if not head:
                    raise FailedPreconditionError("Compile rollback snapshot is unavailable")
                changes = await self._fs.diff_paths(
                    dirs=[to], base=run_meta["target_base"], head=head, ctx=ctx
                )
                access = await self._fs._can_access_many(
                    [change["uri"] for change in changes], actor_ctx, action=AclAction.WRITE
                )
                skipped = {uri for uri, allowed in access.items() if not allowed}
                # Check replacements before deleting any descendants.
                for change in changes:
                    uri = change["uri"]
                    if uri in skipped or not await self._fs.exists(uri, ctx=ctx):
                        continue
                    is_dir = (await self._fs.stat(uri, ctx=ctx, skip_count=True)).get("isDir")
                    # Deletion removes direct grants; rebuilding needs parent write access.
                    replaces_node = (is_dir and change["change_type"] != "added") or (
                        change["change_type"] == "added"
                        and any(
                            other["change_type"] != "added"
                            and uri_matches_prefix(other["uri"], uri)
                            for other in changes
                        )
                    )
                    if replaces_node:
                        parent_access = await self._fs._can_access_many(
                            [uri.rsplit("/", 1)[0]], actor_ctx, action=AclAction.WRITE
                        )
                    else:
                        parent_access = {}
                    if is_dir:
                        descendants = await self._fs._collect_uris(
                            self._fs._uri_to_path(uri, ctx=ctx), True, ctx=ctx, strict=True
                        )
                        permissions = await self._fs._can_access_many(
                            [uri, *descendants], actor_ctx, action=AclAction.MANAGE
                        )
                        if not all(permissions.values()):
                            skipped.add(uri)
                    if not all(parent_access.values()):
                        skipped.add(uri)
                applied = set()
                for change in sorted(
                    changes, key=lambda item: item["uri"].count("/"), reverse=True
                ):
                    uri = change["uri"]
                    if any(uri_matches_prefix(uri, denied) for denied in skipped):
                        skipped.add(uri)
                        continue
                    if change["change_type"] == "added" and await self._fs.exists(uri, ctx=ctx):
                        try:
                            await self._fs.rm(uri, recursive=True, ctx=actor_ctx, lease_ref=lease)
                        except PermissionDeniedError:
                            skipped.add(uri)
                            continue
                        deleted.append(self._fs._uri_to_tree_path(uri, ctx=ctx))
                        applied.add(uri)
                for change in sorted(changes, key=lambda item: item["uri"].count("/")):
                    if change["change_type"] == "added":
                        continue
                    uri = change["uri"]
                    if any(uri_matches_prefix(uri, denied) for denied in skipped):
                        skipped.add(uri)
                        continue
                    content = await self._fs.show(run_meta["target_base"], path=uri, ctx=ctx)
                    try:
                        if await self._fs.exists(uri, ctx=ctx):
                            if (await self._fs.stat(uri, ctx=ctx, skip_count=True)).get("isDir"):
                                await self._fs.rm(
                                    uri, recursive=True, ctx=actor_ctx, lease_ref=lease
                                )
                                deleted.append(self._fs._uri_to_tree_path(uri, ctx=ctx))
                                applied.add(uri)
                            elif await self._fs.read_file_bytes(uri, ctx=ctx) == content:
                                continue
                        await self._fs.write_file_bytes(
                            uri, content, ctx=actor_ctx, lease_ref=lease
                        )
                    except PermissionDeniedError:
                        skipped.add(uri)
                        continue
                    restored.append(self._fs._uri_to_tree_path(uri, ctx=ctx))
                    applied.add(uri)
                rollback_head = await self._commit(
                    [to],
                    f"compile {run_meta['task_id']} rollback",
                    ctx,
                    lease_ref=lease,
                    wait_busy=False,
                )
                if not rollback_head:
                    raise FailedPreconditionError("Compile rollback snapshot is unavailable")
                await self.versions.reconcile_rollback(
                    to, rollback_head, ctx, changed_uris=sorted(applied)
                )
                run_meta["target_head"] = run_meta["rollback_head"] = rollback_head
                run_meta["rollback_skipped"] = sorted(skipped)  # Paths retained by ACL.
                run_meta["rollback_complete"] = not skipped  # False for partial rollback.
                await self._store.put_operation(ctx.account_id, to, run)
        finally:
            if restored or deleted:
                try:
                    await self._fs._schedule_restore_reindex_for_paths(
                        written_paths=restored, deleted_paths=deleted, project_dir=to, real_ctx=ctx
                    )
                except Exception:
                    logger.exception("Compile rollback reindex scheduling failed")
                    self._fs._schedule_vector_rebuild(written=restored, deleted=deleted, ctx=ctx)

    async def _commit(
        self,
        paths: List[str],
        message: str,
        ctx: RequestContext,
        *,
        lease_ref: Optional[Dict[str, Any]] = None,
        wait_busy: bool = True,
    ) -> Optional[str]:
        return await commit_snapshot(
            self._fs, paths, message, ctx, lease_ref=lease_ref, wait_busy=wait_busy
        )
