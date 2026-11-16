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
from openviking.service.compile_lifecycle_finish import _CompileLifecycleFinishMixin
from openviking.service.compile_lifecycle_rollback import _CompileLifecycleRollbackMixin
from openviking.service.compile_versions import CompileVersions


class CompileLifecycle(_CompileLifecycleFinishMixin, _CompileLifecycleRollbackMixin):

    def __init__(self, store: CompileStore, viking_fs: Any) -> None:
        self.store = self._store = store
        self._fs = viking_fs
        self.versions = CompileVersions(store, viking_fs)
        # Installed by CompileScheduler: async (account_id, record) -> None.
        self.reschedule = None
        # Installed by CompileScheduler: async (ctx) -> (executor, credential).
        self.save_credential = None
        # Server callback: async (account_id, user_id) -> current groups.
        self.resolve_groups = None

    async def move_target(self, from_uri: str, to_uri: str, ctx: RequestContext) -> None:
        """Migrate scheduled settings after content and Watch state have moved.

        from_uri and to_uri identify directories in ctx.account_id.
        Only the two exact target states are inspected. An active source with no
        destination state migrates; running sources and invalid output layouts fail
        configuration migration. Execution history stays at its original URI. A schedule
        registration failure leaves committed states intact and reports partial success.
        """
        from openviking.service.compile_scheduler import now_iso
        from openviking.service.compile_service import CompileService

        from_uri, to_uri = from_uri.rstrip("/"), to_uri.rstrip("/")
        async with self._store.edit_move(ctx.account_id, from_uri, to_uri) as states:
            if states is None:
                return
            source, destination = states
            if source.get("active_task_id"):
                raise ConflictError(f"Compile is running on {from_uri}", resource="COMPILE_RUNNING")
            CompileService._validate_target(to_uri)
            self.validate_layout(to_uri, source["from"])
            if uri_matches_prefix(source["skill"], from_uri):
                raise InvalidArgumentError(
                    f"Compile Skill must be outside the moved target: {source['skill']}"
                )
            if source["auto_update"] and self.reschedule is None:
                raise FailedPreconditionError(
                    "Scheduled Compile is disabled on this instance",
                    details={"reason": "COMPILE_SCHEDULER_DISABLED"},
                )
            for key in ("from", "skill", "instruction", "auto_update", "update_schedule"):
                destination[key] = deepcopy(source[key])
            destination["schedule_configured"] = source.get(
                "schedule_configured", source["skill"] is not None
            )
            destination["execution_context"] = {
                key: deepcopy(source["execution_context"][key])
                for key in ("args", "executor", "credential")
            }
            destination["auto_update_enabled_at"] = (
                now_iso() if destination["auto_update"] else None
            )
            source.update(
                status="deleted",
                deleted_at=time.time(),
                auto_update=False,
                active_task_id=None,
                active_operation_id=None,
            )
            source["execution_context"]["credential"] = None
        if self.reschedule is not None:
            try:
                await self.reschedule(ctx.account_id, destination, raise_on_error=True)
                await self.reschedule(ctx.account_id, source, raise_on_error=True)
            except Exception as exc:
                raise OpenVikingError(
                    "Content and Compile configuration moved, but schedule registration failed",
                    code=getattr(exc, "code", "INTERNAL"),
                    details={
                        "from": from_uri,
                        "to": to_uri,
                        "move_committed": True,
                        "compile_config_migrated": True,
                        "phase": "compile_schedule",
                    },
                ) from exc

    async def prepare(
        self,
        payload: Dict[str, Any],
        ctx: RequestContext,
        *,
        instruction_set: bool,
        scheduled_record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save the registry for a manual request and return the task payload.

        Scheduled requests are built from an already locked record, so they
        only receive Compile metadata and never write the registry here.
        """
        control, runtime_args = split_control_args(payload.get("args"))
        task_payload = {key: value for key, value in payload.items() if key != "args"}
        if scheduled_record is None:
            record = await self.save_submission(
                payload, control, runtime_args, instruction_set, ctx
            )
            runtime_args = {**record["execution_context"]["args"], **runtime_args}
        if runtime_args:
            task_payload["args"] = runtime_args
        task_payload["compile"] = {
            "mode": control.get("mode", "incremental"),
            "trigger": "scheduled" if scheduled_record is not None else "manual",
        }
        return task_payload

    async def save_submission(
        self,
        payload: Dict[str, Any],
        control: Dict[str, Any],
        runtime_args: Dict[str, Any],
        instruction_set: bool,
        ctx: RequestContext,
    ) -> Dict[str, Any]:
        """Save validated submission settings and return the target state.

        Explicit schedule changes register before state is published, so failed
        registration leaves the saved target unchanged and propagates to the caller.
        """
        to, sources = payload["to"], payload["from"]
        self.validate_layout(to, sources)
        async with self._store.edit(ctx.account_id, to, create=True) as record:
            configures_schedule = "auto_update" in control or "update_schedule" in control
            # Legacy targets can hold disabled schedule settings without a configuration marker.
            has_schedule = (
                record.get("schedule_configured", record["skill"] is not None)
                or record["auto_update"]
            )
            if configures_schedule or not has_schedule:
                self.apply_sources(record, sources, payload["skill"])
                if instruction_set and configures_schedule:
                    record["instruction"] = payload.get("instruction") or None
                persisted = {k: v for k, v in runtime_args.items() if k != "last_compile_time"}
                if persisted:
                    record["execution_context"]["args"] = persisted
            if configures_schedule:
                await self.apply_schedule(
                    record,
                    ctx,
                    control.get(
                        "auto_update",
                        record["auto_update"] or control.get("update_schedule") is not None,
                    ),
                    control.get("update_schedule", record["update_schedule"]),
                )
                if self.reschedule is not None:
                    await self.reschedule(ctx.account_id, record, raise_on_error=True)
        if not configures_schedule and self.reschedule is not None:
            await self.reschedule(ctx.account_id, record)
        return record

    @staticmethod
    def validate_layout(to: str, sources: List[str]) -> None:
        """Reject overlapping source and destination directories before updating a target."""
        for source in sources:
            if overlaps(source, to):
                raise InvalidArgumentError(
                    f"Compile 'from' directories must not overlap 'to': {source}"
                )

    @staticmethod
    def apply_sources(record: Dict[str, Any], sources: List[str], skill: str) -> None:
        """Save configured sources and Skill without advancing successful execution progress."""
        record["from"] = list(sources)
        record["skill"] = skill

    async def apply_schedule(
        self,
        record: Dict[str, Any],
        ctx: RequestContext,
        auto_update: bool,
        schedule: Optional[Dict[str, Any]],
    ) -> None:
        """Save update settings; enabling requires a rule, and disabling clears it and the key."""
        from openviking.service.compile_scheduler import now_iso

        if auto_update and schedule is None:
            raise InvalidArgumentError("update_schedule is required when auto_update is true")
        if not auto_update:
            schedule = None
        changed = auto_update != record["auto_update"] or schedule != record["update_schedule"]
        if auto_update:
            if self.save_credential is None or self.reschedule is None:
                # Credentials are encrypted only on scheduler instances, where they are decrypted.
                raise FailedPreconditionError(
                    "Scheduled Compile is disabled on this instance "
                    "(compile_api.scheduler_enabled=false)",
                    details={"reason": "COMPILE_SCHEDULER_DISABLED"},
                )
            executor, credential = await self.save_credential(ctx)
            record["execution_context"]["executor"] = executor
            record["execution_context"]["credential"] = credential
            record["last_error"] = None
        else:
            record["execution_context"]["credential"] = None
        if changed:
            record["auto_update_enabled_at"] = now_iso() if auto_update else None
        record["auto_update"] = auto_update
        record["schedule_configured"] = True
        record["update_schedule"] = schedule

    @staticmethod
    def _record_identity(task: Any, record: Dict[str, Any]) -> None:
        """Keep the first operation's ID and user_id, and earliest task creation time."""
        if "initial_operation_id" in record and record["initial_operation_id"] is None:
            record["initial_operation_id"] = compile_operation_id(task)
            record["initial_actor"] = task.user_id
        # Missing fields identify legacy targets whose first creation time is unknown.
        if "first_compile_created_at" in record:
            first = record["first_compile_created_at"]
            record["first_compile_created_at"] = (
                min(first, task.created_at) if first is not None else task.created_at
            )

    async def record_queued(
        self, task: Any, *, locked_record: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save queued history and outputs under the target lock, reusing a caller-held record."""
        if locked_record is None:
            try:
                async with self._store.edit(task.account_id, task.meta["request"]["to"]) as record:
                    await self.record_queued(task, locked_record=record)
            except LookupError:
                return
            return
        if not self._task_is_current(locked_record, task):
            return
        target_to = locked_record["to"]
        operation_id = compile_operation_id(task)
        async with self._store.lock_operation(task.account_id, target_to, operation_id, "create"):
            run = await self._store.get_operation(task.account_id, target_to, operation_id)
            self._record_identity(task, locked_record)
            if run is None:
                await self._store.merge_outputs(task.account_id, target_to, operation_id, [])
                await self._store.put_operation(
                    task.account_id,
                    target_to,
                    new_compile_operation(task, locked_record),
                )
