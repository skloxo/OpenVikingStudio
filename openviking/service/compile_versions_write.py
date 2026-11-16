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


class _CompileVersionsWriteMixin:

    async def record_write(
        self,
        uris: List[str],
        ctx: RequestContext,
        edit_source: str,
        *,
        lease_ref: Optional[Dict[str, Any]] = None,
        write: Optional[Callable[[], Awaitable[Any]]] = None,
        record_version: bool = True,
    ) -> Any:
        """Write under the content lease and register ordinary versions with provenance.

        Unversioned writes still record actual content changes.
        Ordinary batches save each target's change time during batch finalization.
        Active Compile writes defer the directory timestamp to task finalization.
        after_compile_snapshot protects newer ordinary versions from a retry of
        the frozen finish snapshot.
        """
        grouped: Dict[str, List[str]] = {}
        records = {}
        previous = {}
        for uri in uris:
            record = await self.owning_target(ctx.account_id, uri)
            if record is None or not is_versioned(uri):
                continue
            grouped.setdefault(record["to"], []).append(uri)
            records[record["to"]] = record
            # Working bytes can differ from the latest version during Compile.
            if write is not None:
                previous[uri] = (
                    await self._fs.read_file_bytes(uri, ctx=ctx)
                    if await self._fs.exists(uri, ctx=ctx)
                    else None
                )
        written = await write() if write is not None else None
        changed = {}
        context = _operation_outputs.get()
        for target_to, targets in grouped.items():
            targets = [
                uri
                for uri in targets
                if write is None or previous[uri] != await self._fs.read_file_bytes(uri, ctx=ctx)
            ]
            if not targets:
                continue
            changed[target_to] = targets
            run = None
            if edit_source == "compile":
                record = await self._store.get(ctx.account_id, records[target_to]["to"])
                run = (
                    await self._store.get_operation(
                        ctx.account_id, target_to, record["active_operation_id"]
                    )
                    if record["active_operation_id"]
                    else None
                )
                if run and run["started_at"] is not None and run["finished_at"] is None:
                    await self._store.mark_content_changed(
                        ctx.account_id, target_to, run["operation_id"]
                    )
                    if run["meta"]["target_base"] is None:
                        await self._store.merge_outputs(
                            ctx.account_id,
                            target_to,
                            run["operation_id"],
                            [
                                {"uri": uri, "version_id": None, "snapshot_id": None}
                                for uri in targets
                            ],
                        )
                else:
                    run = None
            is_batch = (
                context is not None
                and context["account_id"] == ctx.account_id
                and context.get("batch", False)
                and target_to in context["outputs"]
            )
            if run is None and (
                (write is not None and not is_batch) or (write is None and is_batch)
            ):
                await self._store.mark_content_updated(ctx.account_id, records[target_to]["to"])
            if context and context["account_id"] == ctx.account_id:
                context["changed"].update(targets)
                if target_to in context["outputs"]:
                    for uri in targets:
                        context["outputs"][target_to][uri] = {
                            "uri": uri,
                            "version_id": None,
                            "snapshot_id": None,
                        }
        if not record_version:
            return written
        if not changed:
            return written
        snapshot = await self._commit(
            [uri for targets in changed.values() for uri in targets],
            f"{edit_source} edit",
            ctx,
            lease_ref=lease_ref,
        )
        if context and context["account_id"] == ctx.account_id:
            for target_to, targets in changed.items():
                if target_to in context["outputs"]:
                    for uri in targets:
                        context["outputs"][target_to][uri]["snapshot_id"] = snapshot
        for target_to, targets in changed.items():
            record = await self._store.get(ctx.account_id, records[target_to]["to"])
            run_entry = await self._write_meta(ctx.account_id, record)
            for uri in targets:
                if snapshot:
                    await self.append(
                        ctx.account_id,
                        target_to,
                        uri,
                        snapshot,
                        {
                            "source": edit_source,
                            "actor": ctx.user.user_id,
                            "provenance": {"source_roots": [uri]},
                            "meta": run_entry,
                        },
                    )
        return written

    async def _write_meta(self, account_id: str, record: dict) -> dict:
        """Associate ordinary versions and operations with an unfinished Compile."""
        run = (
            await self._store.get_operation(account_id, record["to"], record["active_operation_id"])
            if record["active_operation_id"]
            else None
        )
        if (
            run
            and run["started_at"] is not None
            and run["finished_at"] is None
            and not run["meta"].get("rollback_head")
        ):
            return {
                "task_id": run["meta"]["task_id"],
                **(
                    {"after_compile_snapshot": True}
                    if run["meta"].get("snapshot_committed")
                    else {}
                ),
            }
        return {}

    async def finish_batch(self, *, ctx: RequestContext, edit_source: str, lease_ref: Any) -> None:
        """Version the batch's changed files once, before its content lease is released."""
        context = _operation_outputs.get()
        if context and context["account_id"] == ctx.account_id and context["changed"]:
            await self.record_write(
                sorted(context["changed"]), ctx, edit_source, lease_ref=lease_ref
            )

    async def record_restored(
        self,
        result: dict,
        *,
        ctx: RequestContext,
        lease_ref: Any,
        metadata_lease: Any = None,
    ) -> None:
        """Version successful snapshot-restore writes under the writeback lease.

        Partial failures expose only their confirmed written paths. Their new commit
        supplies immutable bytes; deleted paths and unchanged files are not outputs.
        """
        context = _operation_outputs.get()
        if context is None or context["account_id"] != ctx.account_id:
            return
        snapshot = result.get("new_commit_oid")
        files = []
        for path in result.get("written_paths", []):
            uri = self._fs._tree_path_to_uri(path)
            record = await self.owning_target(ctx.account_id, uri, metadata_lease=metadata_lease)
            if record is not None and is_versioned(uri):
                if record["to"] in context["outputs"]:
                    context["outputs"][record["to"]][uri] = {
                        "uri": uri,
                        "version_id": None,
                        "snapshot_id": snapshot,
                    }
                files.append((record, uri))
        for record, uri in files:
            if not snapshot:
                continue
            await self.append(
                ctx.account_id,
                record["to"],
                uri,
                snapshot,
                {
                    "source": "restore",
                    "actor": ctx.user.user_id,
                    "provenance": {"source_roots": [uri]},
                    "meta": await self._write_meta(ctx.account_id, record),
                },
                metadata_lease=metadata_lease,
            )

    async def _targets_under(self, account_id: str, uri: str) -> List[Dict[str, Any]]:
        """Return active targets equal to or inside the canonical directory URI."""
        return [
            item
            for item in await self._store.list_summaries(account_id)
            if item.get("status") == "active"
            and (item["to"] == uri or item["to"].startswith(f"{uri}/"))
        ]

    async def _reject_running(self, account_id: str, uri: str) -> List[Dict[str, Any]]:
        """Return targets under URI, rejecting any with an active Compile operation."""
        targets = await self._targets_under(account_id, uri)
        for item in targets:
            record = await self._store.get(account_id, item["to"])
            if record is not None and await self._running(account_id, record):
                raise ConflictError(
                    f"Compile is running on {item['to']}", resource="COMPILE_RUNNING"
                )
        return targets

    async def before_remove(self, uri: str, ctx: RequestContext) -> AsyncIterator[Any]:
        """Hold a managed descendant's content lease through deletion and metadata updates."""
        uri = uri.rstrip("/")
        await self._reject_running(ctx.account_id, uri)
        record = await self.owning_target(ctx.account_id, uri)
        if record is None or record["to"] == uri:
            yield None
            return
        lock_uri = uri
        while lock_uri != "viking://" and not await self._fs.exists(lock_uri, ctx=ctx):
            parts = lock_uri.removeprefix("viking://").split("/")
            lock_uri = "viking://" + "/".join(parts[:-1])
        try:
            lease = await self._fs._async_agfs.pathlock_acquire_tree(
                self._fs._uri_to_path(lock_uri, ctx=ctx)
            )
        except LockAcquisitionError as exc:
            raise ResourceBusyError("Resource is being processed", uri=uri) from exc
        try:
            yield lease
        finally:
            await self._fs._async_agfs.pathlock_release(lease)

    async def after_remove(self, uri: str, ctx: RequestContext) -> None:
        """Whole targets become ``deleted`` (runs kept); a single file loses its index."""
        uri = uri.rstrip("/")
        removed = await self._targets_under(ctx.account_id, uri)
        for item in removed:
            async with self._store.edit(ctx.account_id, item["to"]) as record:
                record["status"] = "deleted"
                record["deleted_at"] = time.time()
                record["auto_update"] = False
                record["active_task_id"] = None
                record["active_operation_id"] = None
                record["execution_context"]["credential"] = None
                await self.drop_all(ctx.account_id, item["to"])
            if self.reschedule is not None:
                await self.reschedule(ctx.account_id, record)
        if not removed:
            record = await self.owning_target(ctx.account_id, uri)
            if record is not None:
                for index in await self._indexes(ctx.account_id, record["to"]):
                    if index["uri"] == uri or index["uri"].startswith(f"{uri}/"):
                        await self._store.delete_version_index(
                            ctx.account_id, record["to"], index["uri"]
                        )
                if is_versioned(uri):
                    async with self._store.edit(ctx.account_id, record["to"]) as record:
                        record["content_updated_at"] = time.time()

    async def versions(
        self, uri: str, ctx: RequestContext, *, limit: int, before: Optional[str]
    ) -> Dict[str, Any]:
        """Return target, retained count and numbered history, newest-first with UUID cursors."""
        await self._fs._ensure_access(uri, ctx)
        record = await self._managed(uri, ctx)
        index = await self.load(ctx.account_id, record["to"], uri)
        entries = list(reversed((index or {}).get("versions", [])))
        total = len(entries)
        current = entries[0]["version_id"] if entries else None
        if before:
            ids = [entry["version_id"] for entry in entries]
            entries = entries[ids.index(before) + 1 :] if before in ids else []
        page = entries[:limit]
        return {
            "uri": uri,
            "to": record["to"],
            "current_version": current,
            "total": total,
            "versions": page,
            "next_before_version": page[-1]["version_id"] if len(entries) > limit else None,
        }

    async def restore(
        self,
        uri: str,
        restore_commit_id: str,
        current_commit_id: str,
        ctx: RequestContext,
        write: Callable[[bytes, Callable[..., Awaitable[Any]]], Awaitable[Any]],
    ) -> Dict[str, Any]:
        """Restore URI from a commit; reject stale file commits under lock, returning metadata or noop."""
        await self._fs._ensure_access(uri, ctx, action=AclAction.WRITE)
        record = await self._managed(uri, ctx)

        async def check_current_commit() -> None:
            """Reject a stale file commit; unrelated paths do not cause conflicts."""
            history = await self._fs.log(paths=[uri], limit=1, ctx=ctx)
            current = history[0]["oid"] if history else None
            if current != current_commit_id:
                raise ConflictError(
                    f"Current file commit is {current}, not {current_commit_id}",
                    resource="VERSION_CONFLICT",
                )

        await check_current_commit()
        try:
            content = await self._fs.show(restore_commit_id, path=uri, ctx=ctx)
        except AGFSNotFoundError as exc:
            raise NotFoundError(f"{restore_commit_id}:{uri}", "snapshot file") from exc
        result: Dict[str, Any] = {}

        async def commit_restore(uris, *, lease_ref, write):
            """Check, write and version under the content lease before refresh."""
            async with self._store.lock_version_index(ctx.account_id, target_to, uri):
                record = await self._store.get(ctx.account_id, target_to)
                if record is None or record["to"] != target_to:
                    raise ConflictError("Compile target changed", resource="COMPILE_TARGET")
                if await self._running(ctx.account_id, record):
                    raise ConflictError("Compile is running", resource="COMPILE_RUNNING")
                index = await self.load(ctx.account_id, target_to, uri) or {"versions": []}
                current = index["versions"][-1]["version_id"] if index["versions"] else None
                await check_current_commit()
                written = await self.record_write(
                    uris, ctx, "restore", write=write, record_version=False
                )
                snapshot = await self._commit(
                    uris, f"restore {uri} to {restore_commit_id}", ctx, lease_ref=lease_ref
                )
            if not snapshot or not await self._changed(ctx, target_to, uri, snapshot):
                result.update(
                    uri=uri,
                    version_id=current,
                    version_number=index["versions"][-1]["version_number"],
                    meta=dict(_VERSION_META_DEFAULTS),
                    result="noop",
                )
            else:
                version = await self.append(
                    ctx.account_id,
                    target_to,
                    uri,
                    snapshot,
                    {
                        "source": "restore",
                        "actor": ctx.user.user_id,
                        "meta": {"restored_from": restore_commit_id},
                        "provenance": {"source_roots": [uri]},
                    },
                )
                result.update(
                    uri=uri,
                    version_id=version["version_id"],
                    version_number=version["version_number"],
                    meta=dict(version["meta"]),
                )
            return written

        target_to = record["to"]

        async def restore_content():
            await write(content, commit_restore)
            return result

        return await self.record_operation(
            [uri],
            ctx,
            "restore",
            {"restore_commit_id": restore_commit_id, "current_commit_id": current_commit_id},
            restore_content,
        )
