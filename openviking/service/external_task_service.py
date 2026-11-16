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
from openviking.service.external_task_models import (
    _ACTIVE_STATUSES, _CREDENTIAL_PROVIDER, _PRIVATE_AUTH_FIELDS,
    ExternalTaskCancellation, ExternalTaskError, ExternalTaskProvider,
    ExternalTaskResultSaveError, ExternalTaskRetryExhaustedError, ExternalTaskSnapshot,
    submission_request_hash, submission_task_id,
)
from openviking.service.external_task_exec import _ExternalTaskExecMixin
from openviking.service.external_task_snapshot import _ExternalTaskSnapshotMixin
from openviking.service.external_task_models import get_external_task_service, set_external_task_service

class ExternalTaskService(_ExternalTaskExecMixin, _ExternalTaskSnapshotMixin):
    """Durable execution of asynchronous tasks owned by external services."""

    def __init__(self, *, credential_encryptor: Any = None) -> None:
        self.credential_encryptor = credential_encryptor
        self._providers: dict[str, ExternalTaskProvider] = {}
        # Transitional reservations for pre-key deliveries; remove next version.
        # Restored before workers start, then accessed on the ExternalTask queue loop.
        self._owners: dict[tuple[str | None, str, str], set[str]] = {}
        self._executing: set[str] = set()
        self._submission_locks = KeyedAsyncLockPool[str]()
        self._submission_dispatcher = OwnerLoopDispatcher()

    def _credential_encryptor(self) -> Any:
        if self.credential_encryptor is None:
            from openviking_cli.utils.config.open_viking_config import get_openviking_config

            self.credential_encryptor = build_credential_encryptor(
                get_openviking_config().encryption
            )
        return self.credential_encryptor

    async def _encrypt_auth(self, account_id: str, auth: Mapping[str, Any]) -> dict[str, Any]:
        encrypted = dict(auth)
        try:
            for field in _PRIVATE_AUTH_FIELDS:
                value = self._mapping(auth.get(field))
                if not value:
                    continue
                plaintext = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
                ciphertext = await self._credential_encryptor().encrypt(account_id, plaintext)
                encrypted[field] = {
                    "provider": _CREDENTIAL_PROVIDER,
                    "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
                }
        except Exception as exc:
            raise FailedPreconditionError(
                "Cannot encrypt external task credentials; check encryption key configuration"
            ) from exc
        return encrypted

    def register(self, provider: ExternalTaskProvider) -> None:
        if provider.task_type in self._providers:
            raise ValueError(f"External task provider already registered: {provider.task_type}")
        self._providers[provider.task_type] = provider

    def _provider(self, task_type: str) -> ExternalTaskProvider:
        provider = self._providers.get(task_type)
        if provider is None:
            raise ExternalTaskError(
                "UNAVAILABLE",
                f"External task provider is not registered: {task_type}",
                transient=False,
            )
        return provider

    def _serialization_key(self, task: TaskRecord) -> tuple[str | None, str, str] | None:
        target = self._provider(task.task_type).serialization_key(task.meta["request"])
        return (task.account_id, task.task_type, target) if target is not None else None

    def queue_serial_key(self, task: TaskRecord) -> str | None:
        """Scope an explicit provider key across users of the same account."""
        key = self._serialization_key(task)
        if key is None:
            return None
        account_id, task_type, target = key
        scope = [account_id, task_type, "target", target]
        return json.dumps(scope, ensure_ascii=False, separators=(",", ":"))

    async def restore_tasks(self, tasks: Iterable[TaskRecord]) -> None:
        """Reserve submitted work before any recovered queue delivery can run."""
        for task in tasks:
            if task.task_type not in self._providers or (
                task.status != TaskStatus.CANCELLED
                and (task.result is not None or task.error is not None)
            ):
                continue
            if task.status not in {
                TaskStatus.RUNNING,
                TaskStatus.CANCELLING,
                TaskStatus.CANCELLED,
            }:
                continue
            if task.status == TaskStatus.CANCELLING and task.stage in {None, "queued"}:
                auth = await self._task_auth(task.task_id, task.account_id, task.user_id)
                if not auth.get("external_task_id"):
                    continue
            key = self._serialization_key(task)
            if key is not None:
                self._owners.setdefault(key, set()).add(task.task_id)

    def _release(self, task: TaskRecord) -> None:
        key = self._serialization_key(task)
        if key is not None and key in self._owners:
            self._owners[key].discard(task.task_id)
            if not self._owners[key]:
                del self._owners[key]

    async def create(
        self,
        task_type: str,
        *,
        resource_id: str | None,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any] | None = None,
        connection: Mapping[str, Any] | None = None,
        ctx: RequestContext,
        idempotency_key: str | None = None,
        submission_payload: Mapping[str, Any] | None = None,
        task_id: str | None = None,
        on_task_created: Callable[[TaskRecord], Awaitable[None]] | None = None,
    ) -> TaskRecord:
        """``submission_payload`` (default ``payload``) is what idempotent retries must match."""

        async def create_task():
            return await self._create(
                task_type,
                resource_id=resource_id,
                payload=payload,
                private_payload=private_payload,
                connection=connection or {},
                ctx=ctx,
                idempotency_key=idempotency_key,
                submission_payload=submission_payload,
                task_id=task_id,
                on_task_created=on_task_created,
            )

        if not idempotency_key and task_id is None:
            return await create_task()
        key = task_id or submission_task_id(ctx, task_type, "", idempotency_key)

        async def serialized():
            async with self._submission_locks.acquire(key):
                return await run_to_completion(create_task)

        return await self._submission_dispatcher.run(serialized)

    async def _create(
        self,
        task_type: str,
        *,
        resource_id: str | None,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any] | None = None,
        connection: Mapping[str, Any],
        ctx: RequestContext,
        idempotency_key: str | None = None,
        submission_payload: Mapping[str, Any] | None = None,
        task_id: str | None = None,
        on_task_created: Callable[[TaskRecord], Awaitable[None]] | None = None,
    ) -> TaskRecord:
        # QueueFS imports parsers/VikingFS; providers must be importable without them.
        from openviking.storage.queuefs import QueueManager, get_queue_manager

        provider = self._provider(task_type)
        tracker = get_task_tracker()
        request_hash = submission_request_hash(
            payload if submission_payload is None else submission_payload, private_payload
        )
        token = uuid4().hex
        task_id = task_id or (
            submission_task_id(ctx, task_type, provider.task_id_prefix, idempotency_key)
            if idempotency_key
            else f"{provider.task_id_prefix}{token}"
        )
        task = await tracker.create(
            task_type,
            resource_id=resource_id,
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
            task_id=task_id,
            meta={
                "request": dict(payload),
                **(
                    {"submission_hash": request_hash, "submission_token": token}
                    if idempotency_key
                    else {}
                ),
            },
            auth=await self._encrypt_auth(
                ctx.account_id,
                {
                    "openviking_connection": dict(connection),
                    "external_request_private": dict(private_payload or {}),
                },
            ),
        )
        if idempotency_key and task.meta.get("submission_hash") != request_hash:
            raise ConflictError("Idempotency-Key was already used with different parameters")
        if idempotency_key and task.meta.get("submission_token") != token:
            # Recover a creation interrupted before queue delivery. Duplicate
            # deliveries are safe: execute claims each task before submitting.
            await self._resume_submission(task, ctx)
            return task
        enqueued = False
        try:
            if on_task_created is not None:
                await on_task_created(task)
            await tracker.patch_task(
                task.task_id,
                TaskPatch(stage="queued"),
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
            with bind_task_context(task.task_id, ctx.account_id, ctx.user.user_id):
                await get_queue_manager().enqueue(
                    QueueManager.EXTERNAL_TASK,
                    {
                        "task_id": task.task_id,
                        "account_id": ctx.account_id,
                        "user_id": ctx.user.user_id,
                    },
                    serial_key=self.queue_serial_key(task),
                )
            enqueued = True
            current = await tracker.get(
                task.task_id,
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
            if current is not None:
                task = current
        except BaseException:
            if not enqueued:
                current = await tracker.get(
                    task.task_id,
                    account_id=ctx.account_id,
                    user_id=ctx.user.user_id,
                )
                if current is not None and not current.is_terminal() and not current.error:
                    await tracker.fail(
                        task.task_id,
                        "Failed to enqueue external task",
                        account_id=ctx.account_id,
                        user_id=ctx.user.user_id,
                    )
            raise
        return task

    async def recover_submission(
        self,
        task_type: str,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        ctx: RequestContext,
        key: str,
    ) -> TaskRecord | None:
        async def recover():
            provider = self._provider(task_type)
            task = await get_task_tracker().get(
                submission_task_id(ctx, task_type, provider.task_id_prefix, key),
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
            if task is None:
                return None
            if task.meta.get("submission_hash") != submission_request_hash(
                payload, private_payload
            ):
                raise ConflictError("Idempotency-Key was already used with different parameters")
            await self._resume_submission(task, ctx)
            return task

        async def serialized():
            async with self._submission_locks.acquire(submission_task_id(ctx, task_type, "", key)):
                return await run_to_completion(recover)

        return await self._submission_dispatcher.run(serialized)

    async def _resume_submission(self, task: TaskRecord, ctx: RequestContext) -> None:
        from openviking.storage.queuefs import QueueManager, get_queue_manager

        if task.status == TaskStatus.PENDING:
            with bind_task_context(task.task_id, ctx.account_id, ctx.user.user_id):
                await get_queue_manager().enqueue(
                    QueueManager.EXTERNAL_TASK,
                    {
                        "task_id": task.task_id,
                        "account_id": ctx.account_id,
                        "user_id": ctx.user.user_id,
                    },
                    serial_key=self.queue_serial_key(task),
                )
