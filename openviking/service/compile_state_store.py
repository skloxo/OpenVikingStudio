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
from openviking.service.compile_state_store_ops import _CompileStateOpsMixin


class CompileStateStore(_CompileStateOpsMixin, CompileStore):

    def __init__(self, agfs: Any) -> None:
        self._agfs = agfs if isinstance(agfs, AsyncAGFSClient) else AsyncAGFSClient(agfs)
        self._cleanup_locks = KeyedAsyncLockPool()
        self._cleanup_scan: Optional[AsyncIterator[Optional[tuple[str, str, str]]]] = None

    @staticmethod
    def root(account_id: str) -> str:
        return f"/local/{account_id}/_system/compile"

    def _target_dir(self, account_id: str, to: str) -> str:
        key = hashlib.sha256(to.rstrip("/").encode("utf-8")).hexdigest()
        return f"{self.root(account_id)}/target_folders/{key}"

    def _record_path(self, account_id: str, to: str) -> str:
        return f"{self._target_dir(account_id, to)}/state.json"

    def _operation_path(self, account_id: str, target_to: str, operation_id: str) -> str:
        return f"{self._target_dir(account_id, target_to)}/operations/{operation_id}.json"

    async def read_json(self, path: str) -> Optional[Any]:
        try:
            raw = await self._agfs.read(path)
        except (AGFSNotFoundError, FileNotFoundError):
            return None
        return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)

    async def _ensure_parent(self, path: str, fs_ctx: Any = None) -> None:
        try:
            await self._agfs.ensure_parent_dirs(path, fs_ctx=fs_ctx)
        except AGFSAlreadyExistsError:
            pass

    async def write_json(self, path: str, value: Any, lease: Any = None) -> None:
        """Write JSON; pass the held lease when ``path`` is already locked by the caller."""
        fs_ctx = fs_ctx_from_agfs_path(path)
        if lease is not None:
            fs_ctx["lease_ref"] = lease["lease_ref"]
        await self._ensure_parent(path, fs_ctx)
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        await self._agfs.write(path, data, fs_ctx=fs_ctx)

    async def locked(self, path: str, inherited_lease: Any = None) -> AsyncIterator[Any]:
        """Lock a JSON path, or reuse a caller-owned tree lease covering that path."""
        if inherited_lease is not None:
            yield inherited_lease
            return
        lease = await self._agfs.pathlock_acquire_exact(path, timeout_secs=LOCK_TIMEOUT_SECONDS)
        try:
            yield lease
        finally:
            await self._agfs.pathlock_release(lease)

    async def list_summaries(self, account_id: str) -> List[Dict[str, Any]]:
        """Read all target summaries without modifying stored metadata."""
        return [item async for item in self.iter_summaries(account_id)]

    async def iter_summaries(
        self, account_id: str, *, cursor: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield target summaries in SHA256(to) order after the target URI cursor.

        AGFS supplies name-sorted entries. States are read on demand without locks or writes.
        Missing states are skipped;
        other I/O and JSON errors propagate. Enumeration is not a point-in-time snapshot.
        """
        async for directory in self._iter_target_dirs(account_id, cursor=cursor):
            record = await self.read_json(f"{directory}/state.json")
            if record is not None:
                yield summarize(_normalize_schedule(record))

    async def _iter_target_dirs(
        self, account_id: str, *, cursor: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Yield metadata paths in hash order after a target URI cursor, without state reads."""
        directory = f"{self.root(account_id)}/target_folders"
        try:
            entries = await self._agfs.ls(directory)
        except (AGFSNotFoundError, FileNotFoundError):
            return
        after = hashlib.sha256(cursor.rstrip("/").encode("utf-8")).hexdigest() if cursor else ""
        # shortcut: ls lists all names; use range listing when enumeration dominates.
        for entry in entries:
            name = str(entry.get("name") or "")
            if (
                len(name) != 64
                or not entry.get("isDir", entry.get("is_dir", False))
                or name <= after
            ):
                continue
            yield f"{directory}/{name}"

    async def get(self, account_id: str, to: str) -> Optional[Dict[str, Any]]:
        """Read state by canonical URI without writes; return None when it is missing."""
        record = await self.read_json(self._record_path(account_id, to))
        return _normalize_schedule(record) if record is not None else None

    async def get_by_to(
        self, account_id: str, to: str, *, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Read state directly by canonical URI, optionally including a deleted target."""
        record = await self.get(account_id, to)
        if record is not None and not include_deleted and record.get("status") != "active":
            return None
        return record

    async def edit(
        self, account_id: str, to: str, *, create: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """Edit under the target lock and save on clean exit.

        Missing states raise LookupError unless ``create`` also creates or revives them.
        Revival preserves the operation history and deletion boundary.
        """
        to = to.rstrip("/")
        path = self._record_path(account_id, to)
        async with self.locked(path) as lease:
            record = await self.read_json(path)
            if record is None:
                if not create:
                    raise LookupError(f"Compile target not found: {to}")
                record = new_record(to)
            elif create and record["status"] != "active":
                defaults = new_record(to)
                for key in (
                    "status",
                    "initialized",
                    "progress",
                    "scheduled_progress",
                    "schedule_configured",
                    "versions_head",
                    "active_task_id",
                    "active_operation_id",
                    "last_run",
                    "content_updated_at",
                    "conflicts_num",
                    "last_error",
                    "auto_update",
                    "auto_update_enabled_at",
                    "last_triggered_slot",
                ):
                    record[key] = defaults[key]
                record["execution_context"]["credential"] = None
            yield _normalize_schedule(record)
            await self.write_json(path, _normalize_schedule(record), lease)

    async def mark_content_updated(self, account_id: str, to: str) -> None:
        """Save the observed business-file change time in Unix seconds."""
        async with self.edit(account_id, to) as record:
            record["content_updated_at"] = time.time()

    async def edit_move(
        self, account_id: str, from_uri: str, to_uri: str
    ) -> AsyncIterator[Optional[tuple[Dict[str, Any], Dict[str, Any]]]]:
        """Edit an active source and an unregistered destination under both state locks.

        account_id selects the registry; from_uri and to_uri are canonical target URIs.
        Yield None when migration does not apply; otherwise yield source and fresh
        destination states. Clean exit means content has moved and saves destination
        before source. Write failures attempt metadata compensation and report that
        content is committed. History files are neither read nor modified.
        """
        source = await self.get(account_id, from_uri)
        destination = await self.get(account_id, to_uri)
        if source is None or source["status"] != "active" or destination is not None:
            yield None
            return
        paths = {uri: self._record_path(account_id, uri) for uri in (from_uri, to_uri)}
        async with AsyncExitStack() as locks:
            leases = {}
            for uri in sorted(paths, key=paths.get):
                leases[uri] = await locks.enter_async_context(self.locked(paths[uri]))
            source = await self.get(account_id, from_uri)
            destination = await self.get(account_id, to_uri)
            if source is None or source["status"] != "active" or destination is not None:
                yield None
                return
            original = deepcopy(source)
            destination = new_record(to_uri)
            yield source, destination
            # shortcut: compensation covers request failures; crash-atomic moves need durable recovery.
            phase = "compile_target_state"
            try:
                await self.write_json(
                    paths[to_uri], _normalize_schedule(destination), leases[to_uri]
                )
                phase = "compile_source_state"
                await self.write_json(
                    paths[from_uri], _normalize_schedule(source), leases[from_uri]
                )
            except Exception as exc:
                compensated = False
                try:
                    if phase == "compile_source_state":
                        await self.write_json(paths[from_uri], original, leases[from_uri])
                    await self.remove(paths[to_uri], lease=leases[to_uri])
                    compensated = True
                except Exception:
                    logger.exception(
                        "Compile move metadata compensation failed: %s -> %s", from_uri, to_uri
                    )
                raise OpenVikingError(
                    "Content moved, but Compile configuration migration failed; "
                    "repair the Compile configuration separately",
                    code="INTERNAL",
                    details={
                        "from": from_uri,
                        "to": to_uri,
                        "move_committed": True,
                        "phase": phase,
                        "compensation_succeeded": compensated,
                    },
                ) from exc

    async def get_operation(
        self, account_id: str, target_to: str, operation_id: str
    ) -> Optional[Dict[str, Any]]:
        return await self.read_json(self._operation_path(account_id, target_to, operation_id))

    async def put_operation(
        self, account_id: str, target_to: str, operation: Dict[str, Any]
    ) -> None:
        """Save operation state without clearing a concurrently recorded content change.

        The merged marker also updates the caller's metadata so finalization uses
        the same durable value when publishing the target's content update time.
        """
        path = self._operation_path(account_id, target_to, operation["operation_id"])
        async with self.locked(path) as lease:
            stored = await self.read_json(path)
            if stored and stored["meta"].get("content_changed"):
                operation["meta"]["content_changed"] = True
            await self.write_json(path, operation, lease)

    async def mark_content_changed(
        self, account_id: str, target_to: str, operation_id: str
    ) -> None:
        """Persist an actual Compile write once; raise NotFoundError for a missing operation."""
        path = self._operation_path(account_id, target_to, operation_id)
        async with self.locked(path) as lease:
            operation = await self.read_json(path)
            if operation is None:
                raise NotFoundError(operation_id, "operation")
            if not operation["meta"].get("content_changed"):
                operation["meta"]["content_changed"] = True
                await self.write_json(path, operation, lease)

    async def lock_operation(
        self,
        account_id: str,
        target_to: str,
        operation_id: str,
        phase: Literal["create", "finish"],
    ) -> AsyncIterator[None]:
        """Serialize one operation phase; creation and finalization use separate locks."""
        async with self.locked(
            f"{self._operation_path(account_id, target_to, operation_id)}.{phase}"
        ):
            yield
