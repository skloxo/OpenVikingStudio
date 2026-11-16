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


class _CompileStateOpsMixin:

    def _outputs_path(self, account_id: str, target_to: str, operation_id: str) -> str:
        return f"{self._target_dir(account_id, target_to)}/operation_outputs/{operation_id}.json"

    async def get_outputs(
        self, account_id: str, target_to: str, operation_id: str
    ) -> Optional[dict]:
        """Read atomically published outputs without locking; return None when absent."""
        return await self.read_json(self._outputs_path(account_id, target_to, operation_id))

    async def merge_outputs(
        self,
        account_id: str,
        target_to: str,
        operation_id: str,
        outputs: List[dict],
        *,
        metadata_lease: Any = None,
    ) -> None:
        """Persist one reference per output URI; retries preserve already recorded outputs.

        Null version/snapshot references indicate unavailable versions. URI paths
        stay fixed at production time so moving a live file cannot change history.
        """
        path = self._outputs_path(account_id, target_to, operation_id)
        async with self.locked(path, metadata_lease) as lease:
            data = await self.read_json(path) or {"outputs": []}
            merged = {item["uri"]: item for item in data["outputs"]}
            merged.update((item["uri"], item) for item in outputs)
            data["outputs"] = [merged[uri] for uri in sorted(merged)]
            await self.write_json(path, data, lease)

    async def list_dir(self, directory: str) -> List[str]:
        """JSON file names in ``directory``; empty when it does not exist."""
        try:
            entries = await self._agfs.ls(directory)
        except (AGFSNotFoundError, FileNotFoundError):
            return []
        return [
            str(entry.get("name"))
            for entry in entries
            if str(entry.get("name") or "").endswith(".json")
        ]

    async def remove(self, path: str, *, recursive: bool = False, lease: Any = None) -> None:
        """Remove a path idempotently, reusing the caller's covering lease when supplied."""
        fs_ctx = fs_ctx_from_agfs_path(path)
        if lease is not None:
            fs_ctx["lease_ref"] = lease["lease_ref"]
        try:
            await self._agfs.rm(path, recursive=recursive, fs_ctx=fs_ctx)
        except (AGFSNotFoundError, FileNotFoundError):
            pass

    async def _iter_history(self) -> AsyncIterator[Optional[tuple[str, str, str]]]:
        """Yield history IDs, counting account/target visits before reading target state."""
        for account_id in await self.list_accounts():
            yield None
            try:
                async for directory in self._iter_target_dirs(account_id):
                    yield None
                    try:
                        record = await self.read_json(f"{directory}/state.json")
                        if record is None or record.get("active_task_id"):
                            continue
                        target_to = record["to"]
                        names = await self.list_dir(f"{directory}/operations")
                    except Exception:
                        logger.exception("Cannot scan Compile history in %s", directory)
                        continue
                    for name in names:
                        yield account_id, target_to, name[:-5]
            except Exception:
                logger.exception("Cannot scan Compile history for account %s", account_id)

    async def delete_expired(self, *, now: float, limit: int) -> int:
        """Scan at most ``limit`` visits and return the number of expired operations removed.

        ``now`` is Unix seconds. Scans resume across calls; failed records remain for
        the next pass. Only history JSON is removed; target state and versions stay.
        """
        if limit <= 0:
            return 0
        deleted = 0
        async with self._cleanup_locks.acquire("scan"):
            if self._cleanup_scan is None:
                self._cleanup_scan = self._iter_history()
            for _ in range(limit):
                try:
                    candidate = await anext(self._cleanup_scan)
                except StopAsyncIteration:
                    self._cleanup_scan = None
                    break
                except Exception:
                    self._cleanup_scan = None
                    logger.exception("Cannot enumerate Compile history")
                    break
                if candidate is None:
                    continue
                try:
                    deleted += await self._delete_expired_operation(
                        *candidate, cutoff=now - HISTORY_RETENTION_SECONDS
                    )
                except Exception:
                    logger.exception("Cannot clean Compile history %s/%s/%s", *candidate)
        return deleted

    async def _delete_expired_operation(
        self, account_id: str, target_to: str, operation_id: str, *, cutoff: float
    ) -> bool:
        """Return whether a terminal history pair older than Unix ``cutoff`` is removed."""
        operation_path = self._operation_path(account_id, target_to, operation_id)
        async with self.lock_operation(account_id, target_to, operation_id, "finish"):
            async with self.locked(self._record_path(account_id, target_to)):
                record = await self.get(account_id, target_to)
                if record is None or record["to"] != target_to or record.get("active_task_id"):
                    return False
                async with self.locked(operation_path) as operation_lease:
                    operation = await self.get_operation(account_id, target_to, operation_id)
                    finished_at = (operation or {}).get("finished_at")
                    if (
                        not operation
                        or operation.get("operation_id") != operation_id
                        or operation.get("status") not in TERMINAL
                        or isinstance(finished_at, bool)
                        or not isinstance(finished_at, (int, float))
                        or not math.isfinite(finished_at)
                        or finished_at < 0
                        or finished_at >= cutoff
                    ):
                        return False
                    outputs_path = self._outputs_path(account_id, target_to, operation_id)
                    async with self.locked(outputs_path) as outputs_lease:
                        await self.remove(outputs_path, lease=outputs_lease)
                    await self.remove(operation_path, lease=operation_lease)
                    return True

    async def list_operations(
        self,
        account_id: str,
        target_to: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read up to ``limit`` records below ``cursor``, skipping deleted files."""
        if limit is not None and limit <= 0:
            return []
        directory = f"{self._target_dir(account_id, target_to)}/operations"
        # shortcut: ls lists all names; add range listing if metadata scans dominate.
        names = await self.list_dir(directory)
        operations = []
        for name in sorted(names, reverse=True):
            if cursor and name[:-5] >= cursor:
                continue
            operation = await self.read_json(f"{directory}/{name}")
            if operation is None:
                continue
            operations.append(operation)
            if limit is not None and len(operations) >= limit:
                break
        return operations

    async def list_accounts(self) -> List[str]:
        try:
            entries = await self._agfs.ls("/local")
        except (AGFSNotFoundError, FileNotFoundError):
            return []
        return [
            str(entry.get("name"))
            for entry in entries
            if entry.get("name")
            and entry.get("name") != "_system"
            and entry.get("isDir", entry.get("is_dir", False))
        ]

    def _versions_dir(self, account_id: str, target_to: str) -> str:
        return f"{self._target_dir(account_id, target_to)}/file_versions"

    def _version_path(self, account_id: str, target_to: str, uri: str) -> str:
        name = hashlib.sha256(uri.encode("utf-8")).hexdigest()
        return f"{self._versions_dir(account_id, target_to)}/{name}.json"

    async def get_version_index(
        self, account_id: str, target_to: str, uri: str
    ) -> Optional[Dict[str, Any]]:
        """Read the stored index for an output URI, or None if it is absent."""
        return await self.read_json(self._version_path(account_id, target_to, uri))

    async def list_version_indexes(self, account_id: str, target_to: str) -> List[Dict[str, Any]]:
        """Read the target's existing indexes, ignoring files removed during enumeration."""
        directory = self._versions_dir(account_id, target_to)
        indexes = []
        for name in await self.list_dir(directory):
            index = await self.read_json(f"{directory}/{name}")
            if index is not None:
                indexes.append(index)
        return indexes

    async def put_version_index(
        self, account_id: str, target_to: str, index: Dict[str, Any], lock_token: Any = None
    ) -> None:
        """Save the index at its URI, using the caller's version lock when supplied."""
        await self.write_json(
            self._version_path(account_id, target_to, index["uri"]), index, lock_token
        )

    async def delete_version_index(self, account_id: str, target_to: str, uri: str) -> None:
        """Remove an output's index; a missing index is already deleted."""
        await self.remove(self._version_path(account_id, target_to, uri))

    async def clear_output_data(self, account_id: str, target_to: str) -> None:
        """Remove output manifests and version indexes, retaining operation history."""
        await self.remove(self._versions_dir(account_id, target_to), recursive=True)
        await self.remove(
            f"{self._target_dir(account_id, target_to)}/operation_outputs", recursive=True
        )

    async def lock_version_index(
        self, account_id: str, target_to: str, uri: str, inherited_lock: Any = None
    ) -> AsyncIterator[Any]:
        """Lock an index, reusing a covering content lock during whole-account restore.

        Pass the yielded opaque token to put_version_index while this scope is held.
        """
        async with self.locked(
            self._version_path(account_id, target_to, uri), inherited_lock
        ) as token:
            yield token
