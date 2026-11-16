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


class _CompileVersionsOpsMixin:

    async def record_operation(
        self,
        uris: List[str],
        ctx: RequestContext,
        operation_type: str,
        params: Dict[str, Any],
        operation: Callable[[], Awaitable[Any]],
        *,
        recursive: bool = False,
    ) -> Any:
        """Execute one call and persist its outcome once per managed target.

        Parameters contain references, never file bodies. Recursive restores include
        overlapping targets; per-target URI lists prevent exposing sibling directories.
        Exceptions and cancellation retain their original behavior after history is saved.
        """
        entries = []
        created_at = time.time()
        operation_id = make_operation_id(created_at, f"op_{uuid4().hex}")
        if recursive:
            targets = await self._store.list_summaries(ctx.account_id)
        else:
            by_to = {}
            for uri in dict.fromkeys(uris):
                record = await self.owning_target(ctx.account_id, uri)
                if record is not None:
                    by_to[record["to"]] = summarize(record)
            targets = list(by_to.values())
        for target in targets:
            to = target["to"]
            affected = [uri for uri in uris if uri == to or uri.startswith(f"{to}/")]
            if recursive and any(uri == "viking://" or overlaps(uri, to) for uri in uris):
                affected = affected or [to]
            if target.get("status") == "active" and affected:
                scoped_params = {
                    key: value for key, value in params.items() if key not in {"from", "to"}
                }
                for key in ("from", "to"):
                    value = params.get(key)
                    if isinstance(value, str) and uri_matches_prefix(value, to):
                        scoped_params[key] = value
                    elif isinstance(value, str) and recursive and uri_matches_prefix(to, value):
                        scoped_params[key] = to
                if operation_type in {"cp", "mv"} and "to" in params:
                    scoped_params["to"] = params["to"]
                entries.append(
                    (
                        target,
                        new_operation(
                            operation_id,
                            operation_type,
                            scoped_params | {"uris": affected},
                            ctx.user.user_id,
                            created_at=created_at,
                        ),
                    )
                )
        if not entries:
            return await operation()
        for uri in uris:
            await self._fs._ensure_access(
                uri,
                ctx,
                action=AclAction.READ
                if recursive and operation_type == "restore"
                else AclAction.WRITE,
            )
        context = {
            "account_id": ctx.account_id,
            "operation_id": operation_id,
            "outputs": {target["to"]: {} for target, _ in entries},
            "targets": {target["to"]: target for target, _ in entries},
            "changed": set(),
            "batch": params.get("batch", False),
        }
        token = _operation_outputs.set(context)
        outcome = {}
        operation_error = None
        try:
            for target, entry in entries:
                async with self._store.edit(ctx.account_id, target["to"]) as record:
                    if record["deleted_at"] != target.get("deleted_at"):
                        raise ConflictError("Compile target changed", resource="COMPILE_TARGET")
                    if record["status"] == "active" and record["deleted_at"] == target.get(
                        "deleted_at"
                    ):
                        await self._store.merge_outputs(
                            ctx.account_id, target["to"], operation_id, []
                        )
                    await self._store.put_operation(ctx.account_id, target["to"], entry)
            result = await operation()
        except BaseException as exc:
            operation_error = exc
            outcome = {key: getattr(exc, key, []) for key in ("written_paths", "deleted_paths")}
            for _, entry in entries:
                entry["status"] = (
                    "cancelled" if isinstance(exc, asyncio.CancelledError) else "failed"
                )
                entry["error"] = (
                    type(exc).__name__
                    if len(entries) > 1 or operation_type in {"cp", "mv"}
                    else str(exc) or type(exc).__name__
                )
            raise
        else:
            outcome = result if isinstance(result, dict) else {}
            for _, entry in entries:
                entry["status"] = "completed"
            return result
        finally:
            _operation_outputs.reset(token)

            # shortcut: history uses the captured URI; coordinate finalization if moves overlap writes.
            async def finish():
                for target, entry in entries:
                    entry["finished_at"] = time.time()
                    entry["result"] = {
                        key: outcome[key]
                        for key in (
                            "result",
                            "version_id",
                            "version_number",
                            "written_bytes",
                            "mode",
                        )
                        if key in outcome
                    }
                    for key in ("created", "updated", "unchanged", "conflicts"):
                        if isinstance(outcome.get(key), list):
                            entry["result"][key] = [
                                item
                                for item in outcome[key]
                                if (item.get("uri") if isinstance(item, dict) else item)
                                and uri_matches_prefix(
                                    item.get("uri") if isinstance(item, dict) else item,
                                    target["to"],
                                )
                            ]
                    if recursive:
                        for key in ("written_paths", "deleted_paths"):
                            entry["result"][key] = [
                                path
                                for path in outcome.get(key, [])
                                if (self._fs._tree_path_to_uri(path).startswith(f"{target['to']}/"))
                            ]
                    async with self._store.edit(ctx.account_id, target["to"]) as record:
                        if (
                            await self._store.get_operation(
                                ctx.account_id, target["to"], operation_id
                            )
                            is None
                        ):
                            continue
                        current = record["status"] == "active" and record[
                            "deleted_at"
                        ] == target.get("deleted_at")
                        if current:
                            await self._store.merge_outputs(
                                ctx.account_id,
                                target["to"],
                                operation_id,
                                list(context["outputs"][target["to"]].values()),
                            )
                        if (
                            current
                            and recursive
                            and any(
                                is_versioned(path)
                                for key in ("written_paths", "deleted_paths")
                                for path in entry["result"][key]
                            )
                        ):
                            record["content_updated_at"] = time.time()
                        await self._store.put_operation(ctx.account_id, target["to"], entry)

            try:
                await run_to_completion(finish)
            except Exception as exc:
                for target, entry in entries:
                    if entry["status"] == "completed":
                        entry.update(
                            status="failed", error=f"Failed to persist operation outputs: {exc}"
                        )
                    entry["finished_at"] = time.time()
                    try:
                        if (
                            await self._store.get_operation(
                                ctx.account_id, target["to"], operation_id
                            )
                            is not None
                        ):
                            await self._store.put_operation(ctx.account_id, target["to"], entry)
                    except Exception:
                        logger.exception("Failed to persist operation failure %s", operation_id)
                raise exc from operation_error

    async def register_transfer(self, ctx: RequestContext) -> None:
        """Update content timestamps for the current account's active package operation.

        The caller holds the content lease; calls outside an operation have no effect.
        """
        context = _operation_outputs.get()
        if context is not None and context["account_id"] == ctx.account_id:
            for target in context["targets"].values():
                await self._store.mark_content_updated(ctx.account_id, target["to"])

    async def _managed(self, uri: str, ctx: RequestContext) -> Dict[str, Any]:
        record = await self.owning_target(ctx.account_id, uri)
        if record is None or not is_versioned(uri):
            raise FailedPreconditionError(
                f"Not a Compile output file: {uri}", details={"reason": "NOT_COMPILE_MANAGED"}
            )
        return record

    async def _running(self, account_id: str, record: Dict[str, Any]) -> bool:
        owner = record["active_operation_id"]
        if not owner:
            return False
        run = await self._store.get_operation(account_id, record["to"], owner)
        return run is not None and run["status"] not in TERMINAL

    async def record_compile(
        self,
        account_id: str,
        record: Dict[str, Any],
        run: Dict[str, Any],
        head: str,
        changes: List[Dict[str, str]],
        ctx: RequestContext,
    ) -> None:
        """Register final Compile versions under the caller's output tree lease.

        Ordinary versions remain immutable; full runs record all sources, while
        incremental runs extend the latest version's provenance with changed roots.
        Each file belongs to its nearest target; output references stay with this run.
        """
        if not head:
            await self._store.merge_outputs(account_id, record["to"], run["operation_id"], [])
            return
        run_meta = run["meta"]
        indexes = {index["uri"]: index for index in await self._indexes(account_id, record["to"])}
        ordinary = {
            uri: version
            for uri, index in indexes.items()
            if (version := self._ordinary_version(index, run_meta["task_id"]))
        }
        changes = {change["uri"]: change["change_type"] for change in changes}
        full = (
            run_meta.get("execution", {}).get("mode") == "full"
            or run["params"]["args"]["mode"] == "full"
        )
        manifest = await self._store.get_outputs(account_id, record["to"], run["operation_id"])
        outputs = list((manifest or {}).get("outputs", []))
        recorded = {item["uri"] for item in outputs if item["snapshot_id"] is not None}
        try:
            # Ordinary edits can differ even when final output matches the start snapshot.
            for uri in changes.keys() | ordinary.keys():
                if not is_versioned(uri):
                    continue
                if uri in recorded:
                    continue
                # shortcut: retries assume stable ownership; persist owners to support ownership changes.
                owner = await self.owning_target(account_id, uri)
                target_to = owner["to"] if owner is not None else record["to"]
                index = (
                    indexes.get(uri)
                    if target_to == record["to"]
                    else await self.load(account_id, target_to, uri)
                )
                existing = next(
                    (
                        version
                        for version in (index or {}).get("versions", [])
                        if version["source"] == "compile"
                        and version["meta"]["task_id"] == run_meta["task_id"]
                        and version["snapshot_id"] == head
                    ),
                    None,
                )
                if existing is not None:
                    outputs.append(
                        {
                            "uri": uri,
                            "version_id": existing["version_id"],
                            "snapshot_id": existing["snapshot_id"],
                        }
                    )
                    continue
                version = self._ordinary_version(index, run_meta["task_id"])
                change_type = changes.get(uri, "modified")
                if target_to != record["to"]:
                    # Nested ordinary edits have no parent task marker; compare live bytes.
                    exists = await self._fs.exists(uri, ctx=ctx)
                    if change_type == "deleted":
                        if exists and not (await self._fs.stat(uri, ctx=ctx, skip_count=True)).get(
                            "isDir"
                        ):
                            continue
                    elif not exists or (await self._fs.stat(uri, ctx=ctx, skip_count=True)).get(
                        "isDir"
                    ):
                        continue
                    elif await self._fs.read_file_bytes(uri, ctx=ctx) != await self._fs.show(
                        head, path=uri, ctx=ctx
                    ):
                        continue
                if version:
                    if version["meta"]["after_compile_snapshot"]:
                        continue
                    if change_type != "deleted":
                        try:
                            if not await self._changed(ctx, target_to, uri, head):
                                continue
                        except (AGFSNotFoundError, NotFoundError):
                            change_type = "deleted"
                if change_type == "deleted":
                    if version is None:
                        await self._store.delete_version_index(account_id, target_to, uri)
                    continue
                if full or not (index or {}).get("versions"):
                    roots = list(run["params"]["from"])
                else:
                    previous_roots = (
                        index["versions"][-1].get("provenance", {}).get("source_roots", [])
                    )
                    roots = sorted(set(previous_roots) | set(run_meta["changed_roots"]))
                created = await self.append(
                    account_id,
                    target_to,
                    uri,
                    head,
                    {
                        "source": "compile",
                        "actor": run["actor"],
                        "meta": {"task_id": run_meta["task_id"]},
                        "provenance": {
                            "trigger": run_meta["trigger"],
                            "skill": run["params"]["skill"],
                            "source_roots": roots,
                        },
                    },
                    operation_id=run["operation_id"],
                )
                outputs.append(
                    {
                        "uri": uri,
                        "version_id": created["version_id"],
                        "snapshot_id": created["snapshot_id"],
                    }
                )
        finally:
            error = sys.exc_info()[1]
            try:
                await run_to_completion(
                    lambda: self._store.merge_outputs(
                        account_id, record["to"], run["operation_id"], outputs
                    )
                )
            except BaseException:
                if error is None:
                    raise
                logger.exception("Failed to persist Compile outputs for %s", run["operation_id"])
