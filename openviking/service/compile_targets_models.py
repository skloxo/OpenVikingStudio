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
from openviking_cli.utils import VikingURI, get_logger

logger = get_logger(__name__)

# Per-call immutable output references are published under the content lease.
_operation_outputs: ContextVar[Optional[dict]] = ContextVar("operation_outputs", default=None)


# ==========================================================================
# Registry storage
# ==========================================================================


LOCK_TIMEOUT_SECONDS = 30.0
HISTORY_RETENTION_SECONDS = 7 * 24 * 3600
SUMMARY_FIELDS = (
    "to",
    "status",
    "deleted_at",
    "initialized",
    "auto_update",
    "update_schedule",
    "auto_update_enabled_at",
    "last_triggered_slot",
    "content_updated_at",
    "first_compile_created_at",
    "compile_type",
    "conflicts_num",
)


def new_record(to: str) -> Dict[str, Any]:
    """Build execution settings for a canonical target URI without claiming a task."""
    return {
        "to": to,
        "compile_type": "compile",  # Compile category for this target.
        "conflicts_num": 0,  # Conflicting files found at successful completion, capped at 100.
        "status": "active",
        "deleted_at": None,  # Last deletion Unix time; retained for operation boundary checks.
        "from": [],
        "skill": None,
        "instruction": None,
        "initialized": False,
        "auto_update": False,
        "schedule_configured": False,  # Explicit schedule settings survive ordinary submissions.
        "update_schedule": None,
        "auto_update_enabled_at": None,
        "last_triggered_slot": None,
        "last_error": None,
        "progress": {"source_commit": None, "processed_roots": []},
        "scheduled_progress": {},  # Successful scheduled inputs and source progress, isolated from manual runs.
        # Snapshot the per-file version indexes were last synced to.
        "versions_head": None,
        "active_task_id": None,
        "active_operation_id": None,  # Set and cleared with active_task_id.
        "last_run": None,
        "initial_operation_id": None,  # First Compile operation ID.
        "initial_actor": None,  # First Compile user's user_id; None when unknown.
        "content_updated_at": None,  # Business-file change time in Unix seconds; None when unknown.
        "first_compile_created_at": None,  # First task creation in Unix seconds; None when unknown.
        "execution_context": {"executor": None, "credential": None, "args": {}},
    }


def _normalize_schedule(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize stored records in place so disabled schedules are null on reads and writes."""
    if not record["auto_update"]:
        record["update_schedule"] = None
    return record


def summarize(record: Dict[str, Any]) -> Dict[str, Any]:
    summary = {key: record.get(key) for key in SUMMARY_FIELDS}
    summary["compile_type"] = record.get("compile_type", "compile")
    summary["conflicts_num"] = record.get("conflicts_num", 0)
    summary["running"] = bool(record.get("active_task_id"))
    return summary


class CompileStore(Protocol):
    """Target, operation and version-index persistence used by Compile.

    Edits save on clean exit. Object locks serialize their read-modify-write
    scopes; lock tokens are opaque and belong to the selected implementation.
    """

    async def get(self, account_id: str, to: str) -> Optional[Dict[str, Any]]: ...
    async def get_by_to(
        self, account_id: str, to: str, *, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]: ...
    def edit(
        self, account_id: str, to: str, *, create: bool = False
    ) -> AsyncContextManager[Dict[str, Any]]: ...
    def edit_move(
        self, account_id: str, from_uri: str, to_uri: str
    ) -> AsyncContextManager[Optional[tuple[Dict[str, Any], Dict[str, Any]]]]: ...
    async def list_summaries(self, account_id: str) -> List[Dict[str, Any]]: ...
    def iter_summaries(
        self, account_id: str, *, cursor: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]: ...
    async def list_accounts(self) -> List[str]: ...
    async def mark_content_updated(self, account_id: str, to: str) -> None: ...

    async def get_operation(
        self, account_id: str, target_to: str, operation_id: str
    ) -> Optional[Dict[str, Any]]: ...
    async def put_operation(
        self, account_id: str, target_to: str, operation: Dict[str, Any]
    ) -> None: ...
    async def mark_content_changed(
        self, account_id: str, target_to: str, operation_id: str
    ) -> None: ...
    async def list_operations(
        self,
        account_id: str,
        target_to: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...
    def lock_operation(
        self,
        account_id: str,
        target_to: str,
        operation_id: str,
        phase: Literal["create", "finish"],
    ) -> AsyncContextManager[None]: ...
    async def get_outputs(
        self, account_id: str, target_to: str, operation_id: str
    ) -> Optional[dict]: ...
    async def merge_outputs(
        self,
        account_id: str,
        target_to: str,
        operation_id: str,
        outputs: List[dict],
        *,
        metadata_lease: Any = None,
    ) -> None: ...

    async def get_version_index(
        self, account_id: str, target_to: str, uri: str
    ) -> Optional[Dict[str, Any]]: ...
    async def list_version_indexes(
        self, account_id: str, target_to: str
    ) -> List[Dict[str, Any]]: ...
    async def put_version_index(
        self, account_id: str, target_to: str, index: Dict[str, Any], lock_token: Any = None
    ) -> None: ...
    async def delete_version_index(self, account_id: str, target_to: str, uri: str) -> None: ...
    async def clear_output_data(self, account_id: str, target_to: str) -> None: ...
    def lock_version_index(
        self, account_id: str, target_to: str, uri: str, inherited_lock: Any = None
    ) -> AsyncContextManager[Any]: ...


# ==========================================================================
# Incremental lifecycle
# ==========================================================================


CONTROL_ARGS = ("mode", "auto_update", "update_schedule")
GIT_RETRIES = 3
SNAPSHOT_BUSY_SECONDS = 30.0
TERMINAL = frozenset({"completed", "failed", "cancelled"})
_RESULT_KEYS = {"added": "created", "modified": "updated", "deleted": "deleted"}
_NULL_OID = "0" * 40


def task_ctx(account_id: str, user_id: str) -> RequestContext:
    return RequestContext(
        user=UserIdentifier(account_id=account_id, user_id=user_id),
        role=Role.USER,
        bypass_acl=True,
    )


def overlaps(a: str, b: str) -> bool:
    return a == b or a.startswith(f"{b}/") or b.startswith(f"{a}/")


class DailySchedule(BaseModel):
    """Beijing-time trigger time; weekly adds ``weekday`` (1=Monday … 7=Sunday)."""

    model_config = ConfigDict(extra="forbid")

    frequency: Literal["daily"]
    hour: int = Field(default=0, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)


class WeeklySchedule(DailySchedule):
    frequency: Literal["weekly"]
    weekday: int = Field(default=1, ge=1, le=7)


UpdateSchedule = Annotated[Union[DailySchedule, WeeklySchedule], Field(discriminator="frequency")]


def parse_schedule(value: Any) -> Dict[str, Any]:
    """Validate a schedule and fill defaults."""
    try:
        return TypeAdapter(UpdateSchedule).validate_python(value).model_dump()
    except ValidationError as exc:
        error = exc.errors(include_url=False)[0]
        field = "".join(f".{part}" for part in error["loc"][1:])  # loc[0] is the frequency tag
        raise InvalidArgumentError(f"args.update_schedule{field}: {error['msg']}") from exc


def split_control_args(args: Optional[Mapping[str, Any]]) -> tuple[dict, dict]:
    """Separate kernel control args from Runtime args."""
    runtime = dict(args or {})
    control = {key: runtime.pop(key) for key in CONTROL_ARGS if key in runtime}
    if control.get("mode", "incremental") not in {"incremental", "full"}:
        raise InvalidArgumentError("args.mode must be 'incremental' or 'full'")
    if control.get("update_schedule") is not None:
        control["update_schedule"] = parse_schedule(control["update_schedule"])
    if not isinstance(control.get("auto_update", False), bool):
        raise InvalidArgumentError("args.auto_update must be a boolean")
    return control, runtime


def make_operation_id(created_at: float, suffix: str) -> str:
    """Return a sortable ID from Unix seconds (9 decimals) and a unique suffix."""
    return f"{created_at:020.9f}_{suffix}"


def compile_operation_id(task: Any) -> str:
    """Use persisted task time and ID so retries reuse the same operation."""
    return make_operation_id(task.created_at, task.task_id)


def new_operation(
    operation_id: str,
    operation_type: str,
    params: Dict[str, Any],
    actor: str,
    *,
    status: str = "running",
    created_at: Optional[float] = None,
) -> Dict[str, Any]:
    """Build an operation; ``created_at`` is Unix seconds, defaulting to the current time."""
    now = time.time() if created_at is None else created_at
    return {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "actor": actor,
        "status": status,
        "created_at": now,
        "started_at": now if status == "running" else None,
        "finished_at": None,
        "params": params,
        "result": None,
        "error": None,
        "meta": {},
    }


def new_compile_operation(task: Any, record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a queued operation linked to its task and trigger."""
    request = task.meta["request"]
    trigger = request["compile"]["trigger"]
    operation_id = compile_operation_id(task)
    operation_type = "schedule_compile" if trigger == "scheduled" else "manual_compile"
    if record.get("initial_operation_id") == operation_id:
        operation_type = "initial"
    return new_operation(
        operation_id,
        operation_type,
        _params(request),
        task.user_id,
        status="queued",
        created_at=task.created_at,
    ) | {
        "meta": {
            "task_id": task.task_id,
            "target_deleted_at": record["deleted_at"],  # Target lifecycle boundary.
            "trigger": trigger,
            "target_base": None,
            "target_head": None,
            "snapshot_committed": False,
            "content_changed": False,  # Content changes requiring a finalization timestamp.
            "base": None,
            "head": None,
            "changed_roots": [],
            "changes": None,
        },
    }


async def retry_git(action: Any) -> Any:
    """Retry a Git ref update that lost a CAS race, with a short random backoff."""
    for attempt in range(GIT_RETRIES):
        try:
            return await action()
        except GitConcurrentCommitError:
            if attempt == GIT_RETRIES - 1:
                raise
            await asyncio.sleep(random.uniform(0.1, 0.5))


async def commit_snapshot(
    viking_fs: Any,
    paths: List[str],
    message: str,
    ctx: RequestContext,
    *,
    lease_ref: Optional[Dict[str, Any]] = None,
    wait_busy: bool = True,
) -> Optional[str]:
    """Return the snapshot oid, or None when Git cannot provide a snapshot.

    Busy paths wait up to ``SNAPSHOT_BUSY_SECONDS`` unless ``wait_busy=False``
    lets the caller defer work through its queue.
    """
    deadline = time.monotonic() + SNAPSHOT_BUSY_SECONDS
    kwargs = {"lease_ref": lease_ref} if lease_ref is not None else {}
    while True:
        try:
            result = await retry_git(
                lambda: viking_fs.commit(message=message, paths=paths, ctx=ctx, **kwargs)
            )
            break
        except AGFSNotSupportedError:
            return None
        except ResourceBusyError:
            if not wait_busy or time.monotonic() >= deadline:
                raise
            await asyncio.sleep(0.2)
    oid = result.get("commit_oid")
    return None if not oid or oid == _NULL_OID else oid


def _params(request: Mapping[str, Any]) -> Dict[str, Any]:
    meta = request["compile"]
    return {
        "from": request["from"],
        "to": request["to"],
        "skill": request["skill"],
        "instruction": request.get("instruction"),
        "args": {"mode": meta["mode"], **(request.get("args") or {})},
    }


# ==========================================================================
# Per-file versions
# ==========================================================================


MAX_VERSIONS = 100
_DERIVED = frozenset({".abstract.md", ".overview.md", ".relations.json"})
_VERSION_META_DEFAULTS = {
    "task_id": None,
    "restored_from": None,
    "after_compile_snapshot": False,
}


def is_versioned(uri: str) -> bool:
    return uri.rsplit("/", 1)[-1] not in _DERIVED

