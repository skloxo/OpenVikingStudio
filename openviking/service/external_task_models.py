# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Durable execution of asynchronous tasks owned by external services."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Awaitable, Callable, Iterable, Mapping, Protocol
from uuid import uuid4

from openviking.crypto.encryptor import MAGIC, build_credential_encryptor
from openviking.pyagfs import GitConcurrentCommitError
from openviking.pyagfs.exceptions import AGFSConnectionError, AGFSNetworkError, AGFSTimeoutError
from openviking.server.identity import RequestContext
from openviking.service.task_domain import TaskPatch, sanitize_error
from openviking.service.task_tracker import TaskRecord, TaskStatus, get_task_tracker
from openviking.service.task_tracker_concurrency import (
    KeyedAsyncLockPool,
    OwnerLoopDispatcher,
    run_to_completion,
)
from openviking.service.task_work_index import bind_task_context
from openviking.storage.errors import ResourceBusyError
from openviking_cli.exceptions import ConflictError, FailedPreconditionError
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_ACTIVE_STATUSES = frozenset({"pending", "running", "cancelling"})
_CREDENTIAL_PROVIDER = "encrypted_external_task"
_PRIVATE_AUTH_FIELDS = ("openviking_connection", "external_request_private")
_instance: ExternalTaskService | None = None


class ExternalTaskResultSaveError(RuntimeError):
    """Remote execution finished, but its local outcome could not be saved."""


def set_external_task_service(service: ExternalTaskService | None) -> None:
    global _instance
    _instance = service


def get_external_task_service() -> ExternalTaskService:
    if _instance is None:
        raise RuntimeError("ExternalTaskService is not initialized")
    return _instance


class ExternalTaskError(RuntimeError):
    """A classified provider failure used by the durable retry loop."""

    def __init__(self, code: str, message: str, *, transient: bool) -> None:
        super().__init__(message)
        self.code = code
        self.transient = transient


class ExternalTaskRetryExhaustedError(ExternalTaskError):
    """Retries are exhausted and remote acceptance may be unknown."""


@dataclass(frozen=True)
class ExternalTaskSnapshot:
    """Provider-independent state returned by an external task API."""

    status: str
    stage: str | None = None
    result: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ExternalTaskCancellation:
    """Provider cancellation result and any recovered external task identity."""

    external_task_id: str | None
    snapshot: ExternalTaskSnapshot
    terminal_snapshot: ExternalTaskSnapshot | None = None


class ExternalTaskProvider(Protocol):
    """Adapter contract for one external asynchronous task type."""

    task_type: str
    task_id_prefix: str
    poll_max_attempts: int

    @property
    def poll_interval_seconds(self) -> float: ...

    def serialization_key(self, payload: Mapping[str, Any]) -> str | None:
        """Return the provider's serial scheduling key, or None for independent deliveries."""
        ...

    async def submit(
        self,
        ov_task_id: str,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        connection: Mapping[str, Any],
    ) -> str: ...

    async def get(
        self,
        external_task_id: str,
        connection: Mapping[str, Any],
        *,
        payload: Mapping[str, Any] | None = None,
        private_payload: Mapping[str, Any] | None = None,
    ) -> ExternalTaskSnapshot: ...

    async def on_start(self, task: TaskRecord) -> str | ExternalTaskSnapshot | None: ...

    async def on_finish(
        self,
        task: TaskRecord,
        snapshot: ExternalTaskSnapshot,
    ) -> ExternalTaskSnapshot: ...

    async def on_cancel(
        self,
        task: TaskRecord,
        *,
        external_task_id: str | None,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        connection: Mapping[str, Any],
        failure: Exception | None,
    ) -> ExternalTaskCancellation: ...

    def submission_meta(self, external_task_id: str) -> dict[str, Any]: ...


__all__ = [
    "ExternalTaskCancellation",
    "ExternalTaskError",
    "ExternalTaskRetryExhaustedError",
    "ExternalTaskProvider",
    "ExternalTaskService",
    "ExternalTaskSnapshot",
    "get_external_task_service",
    "set_external_task_service",
]


def submission_task_id(ctx: RequestContext, task_type: str, prefix: str, key: str) -> str:
    scope = json.dumps([ctx.account_id, ctx.user.user_id, task_type, key])
    return prefix + hashlib.sha256(scope.encode()).hexdigest()


def submission_request_hash(
    payload: Mapping[str, Any], private_payload: Mapping[str, Any] | None
) -> str:
    return hashlib.sha256(
        json.dumps(
            {"payload": dict(payload), "private": dict(private_payload or {})},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
