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
from openviking_cli.utils import VikingURI
from openviking.service.compile_targets_models import (
    _DERIVED, _NULL_OID, _RESULT_KEYS, _VERSION_META_DEFAULTS, CONTROL_ARGS, GIT_RETRIES,
    HISTORY_RETENTION_SECONDS, LOCK_TIMEOUT_SECONDS, MAX_VERSIONS, SNAPSHOT_BUSY_SECONDS,
    SUMMARY_FIELDS, TERMINAL, CompileStore, DailySchedule, UpdateSchedule, WeeklySchedule,
    _normalize_schedule, _operation_outputs, _params, commit_snapshot, compile_operation_id,
    is_versioned, make_operation_id, new_compile_operation, new_operation, new_record,
    overlaps, parse_schedule, retry_git, split_control_args, summarize, task_ctx,
)
from openviking.service.compile_versions_ops import _CompileVersionsOpsMixin
from openviking.service.compile_versions_write import _CompileVersionsWriteMixin


class CompileVersions(_CompileVersionsOpsMixin, _CompileVersionsWriteMixin):
    """Persist immutable UUID versions with numbering scoped to each file index."""

    def __init__(self, store: CompileStore, viking_fs: Any) -> None:
        self._store = store
        self._fs = viking_fs
        # Installed by CompileScheduler: async (account_id, record) -> None.
        self.reschedule = None

    async def load(self, account_id: str, target_to: str, uri: str) -> Optional[Dict[str, Any]]:
        return self._normalize_index(
            await self._store.get_version_index(account_id, target_to, uri)
        )

    @staticmethod
    def _normalize_index(index: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Normalize legacy metadata in memory without changing persisted versions on read."""
        if index is not None:
            index.pop("source_roots", None)
            for version in index["versions"]:
                meta = {
                    key: version.pop(key, default)
                    for key, default in _VERSION_META_DEFAULTS.items()
                }
                version["meta"] = {**meta, **(version.get("meta") or {})}
        return index

    async def _indexes(self, account_id: str, target_to: str) -> List[Dict[str, Any]]:
        return [
            self._normalize_index(index)
            for index in await self._store.list_version_indexes(account_id, target_to)
        ]

    async def append(
        self,
        account_id: str,
        target_to: str,
        uri: str,
        snapshot_id: str,
        entry: Dict[str, Any],
        *,
        operation_id: Optional[str] = None,
        metadata_lease: Any = None,
    ) -> Dict[str, Any]:
        """Append a file version under its lock, reusing a version on operation retries.

        A whole-account restore supplies its covering lease for version metadata.
        Independent operations collect exact references before publishing completion.
        """
        context = _operation_outputs.get()
        collecting = (
            context and context["account_id"] == account_id and target_to in context["outputs"]
        )
        operation_id = operation_id or (context["operation_id"] if collecting else None)
        async with self._store.lock_version_index(
            account_id, target_to, uri, metadata_lease
        ) as token:
            index = await self.load(account_id, target_to, uri) or {
                "uri": uri,
                "next": 1,
                "versions": [],
            }
            version = next(
                (
                    v
                    for v in index["versions"]
                    if operation_id
                    and v["meta"].get("operation_id") == operation_id
                    and v["snapshot_id"] == snapshot_id
                    and v["snapshot_path"] == uri
                ),
                None,
            )
            if version is None:
                version = {
                    "version_id": uuid4().hex,
                    "version_number": index["next"],
                    "snapshot_id": snapshot_id,
                    "snapshot_path": uri,
                    "created_at": time.time(),
                    **entry,
                    "meta": {**_VERSION_META_DEFAULTS, **entry.get("meta", {})},
                }
                if operation_id:
                    version["meta"]["operation_id"] = operation_id
                index["next"] += 1
                index["versions"] = (index["versions"] + [version])[-MAX_VERSIONS:]

            async def persist():
                await self._store.put_version_index(account_id, target_to, index, token)
                if collecting and operation_id == context["operation_id"]:
                    context["outputs"][target_to][uri] = {
                        "uri": uri,
                        "version_id": version["version_id"],
                        "snapshot_id": version["snapshot_id"],
                    }

            await run_to_completion(persist)
        return version

    async def owning_target(
        self, account_id: str, uri: str, *, metadata_lease: Any = None
    ) -> Optional[Dict[str, Any]]:
        """Find an active target by URI ancestry; return None when none contains ``uri``."""
        # Mutation hooks strip trailing slashes from the root URI.
        if not uri.startswith("viking://"):
            return None
        classification = classify_uri(uri)
        content_index = classification.content_index
        # System assets and rule memories are outside Compile target ownership.
        if classification.is_system or (
            content_index is not None
            and classification.parts[content_index : content_index + 2] == ("memories", "rules")
        ):
            return None
        candidate: Optional[VikingURI] = VikingURI(uri)
        while candidate is not None and candidate.scope:
            record = await self._store.get_by_to(account_id, str(candidate))
            if record is not None:
                return record
            candidate = candidate.parent
        return None

    @staticmethod
    def _ordinary_version(index: Optional[Dict[str, Any]], task_id: str) -> Optional[dict]:
        """Return the run's latest ordinary version, or None; Compile entries are ignored."""
        for version in reversed((index or {}).get("versions", [])):
            if version["meta"]["task_id"] == task_id and version["source"] in {
                "manual",
                "agent",
                "restore",
            }:
                return version
        return None

    async def record_external(
        self,
        account_id: str,
        record: Dict[str, Any],
        target_base: Optional[str],
        ctx: RequestContext,
    ) -> None:
        """Version external changes since ``versions_head`` under the task owner's identity.

        Existing files start at ``v1``; files matching their latest version are skipped.
        """
        if not target_base:
            return
        changes = await self._fs.diff_paths(
            dirs=[record["to"]],
            base=record.get("versions_head"),
            head=target_base,
            ctx=ctx,
        )
        changed = False
        for change in changes:
            uri = change["uri"]
            if not is_versioned(uri):
                continue
            owner = await self.owning_target(account_id, uri)
            target_to = owner["to"] if owner is not None else record["to"]
            if change["change_type"] == "deleted":
                changed = changed or await self.load(account_id, target_to, uri) is not None
                await self._store.delete_version_index(account_id, target_to, uri)
            elif await self._changed(ctx, target_to, uri, target_base):
                changed = True
                await self.append(
                    account_id,
                    target_to,
                    uri,
                    target_base,
                    {"source": "external", "actor": None, "provenance": {}},
                )
        if changed and record.get("versions_head"):
            await self._store.mark_content_updated(account_id, record["to"])

    async def reconcile_rollback(
        self, to: str, snapshot: str, ctx: RequestContext, *, changed_uris: List[str]
    ) -> None:
        """Align current versions under ``to`` with a restored snapshot under its tree lease.

        Existing ancestor indexes are reconciled without duplicating new versions
        across targets. Files without history belong to their nearest active target.
        Intermediate versions remain available as history; missing files lose indexes.
        changed_uris identifies restored or removed business files for target timestamps.
        """
        live = {
            change["uri"]
            for change in await self._fs.diff_paths(dirs=[to], base=None, head=snapshot, ctx=ctx)
            if is_versioned(change["uri"])
        }
        owners = {}
        for uri in live:
            owner = await self.owning_target(ctx.account_id, uri)
            if owner is not None:
                owners[uri] = owner["to"]
        for target in await self._targets_under(ctx.account_id, to):
            target_to = target["to"]
            indexes = {
                index["uri"]: index
                for index in await self._indexes(ctx.account_id, target_to)
                if uri_matches_prefix(index["uri"], to)
            }
            uris = indexes.keys() | {uri for uri, owner in owners.items() if owner == target_to}
            for uri in sorted(uris):
                if uri not in live:
                    await self._store.delete_version_index(ctx.account_id, target_to, uri)
                elif await self._changed(ctx, target_to, uri, snapshot):
                    await self.append(
                        ctx.account_id,
                        target_to,
                        uri,
                        snapshot,
                        {"source": "external", "actor": None, "provenance": {}},
                    )
            async with self._store.edit(ctx.account_id, target_to) as record:
                record["versions_head"] = snapshot
                if any(uri_matches_prefix(uri, target_to) for uri in changed_uris):
                    record["content_updated_at"] = time.time()

    async def _changed(self, ctx: RequestContext, target_to: str, uri: str, snapshot: str) -> bool:
        """Compare blob IDs at their recorded paths using the caller's identity.

        Missing history counts as changed; other read errors propagate.
        """
        index = await self.load(ctx.account_id, target_to, uri)
        if index is None or not index["versions"]:
            return True
        latest = index["versions"][-1]
        try:
            before = await self._fs.show_blob_raw(
                latest["snapshot_id"], path=latest["snapshot_path"], ctx=ctx
            )
        except (AGFSNotFoundError, NotFoundError):
            return True
        after = await self._fs.show_blob_raw(snapshot, path=uri, ctx=ctx)
        return before["oid"] != after["oid"]

    async def drop_all(self, account_id: str, target_to: str) -> None:
        await self._store.clear_output_data(account_id, target_to)

    async def _commit(
        self,
        uris: List[str],
        message: str,
        ctx: RequestContext,
        *,
        lease_ref: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        return await commit_snapshot(
            self._fs, uris, message, task_ctx(ctx.account_id, ctx.user.user_id), lease_ref=lease_ref
        )
