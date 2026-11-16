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


class _ExternalTaskExecMixin:

    async def execute(self, task_id: str, account_id: str, user_id: str) -> bool:
        """Execute a delivery; return False when it needs retrying."""
        tracker = get_task_tracker()
        try:
            return await self._retry(
                lambda: self._execute_once(task_id, account_id, user_id),
                task_id=task_id,
                operation_name="execute",
                poll_interval=0.2,
                max_attempts=3,
            )
        except asyncio.CancelledError:
            if await tracker.is_task_cancellation_requested(
                task_id, account_id=account_id, user_id=user_id
            ):
                await self.cancel_recovered(task_id, account_id, user_id)
                return True
            raise
        except ExternalTaskResultSaveError:
            raise
        except ExternalTaskRetryExhaustedError as exc:
            task = await tracker.get(task_id, account_id=account_id, user_id=user_id)
            if task is not None:
                auth = await self._task_auth(task_id, account_id, user_id)
                if auth.get("external_terminal_snapshot"):
                    await asyncio.sleep(self._provider(task.task_type).poll_interval_seconds)
                    return False
            await self.cancel_recovered(task_id, account_id, user_id, failure=exc)
            return True
        except Exception as exc:
            await self.cancel_recovered(task_id, account_id, user_id, failure=exc)
            return True

    async def _execute_once(self, task_id: str, account_id: str, user_id: str) -> bool:
        """Resume a delivery; return False while admission or finalization is pending."""
        tracker = get_task_tracker()
        claimed = False
        try:
            task = await tracker.get(task_id, account_id=account_id, user_id=user_id)
            if task is None:
                return True
            if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
                self._release(task)
                return True
            if task.status in {TaskStatus.CANCELLING, TaskStatus.CANCELLED}:
                raise asyncio.CancelledError()
            # A recovered delivery can ACK an already saved outcome without resubmission.
            if task.result is not None or task.error is not None:
                self._release(task)
                return True
            provider = self._provider(task.task_type)
            payload = task.meta.get("request")
            if not isinstance(payload, dict):
                await tracker.fail(
                    task_id,
                    "INVALID_ARGUMENT: External task request is missing",
                    account_id=account_id,
                    user_id=user_id,
                )
                return True
            key = self._serialization_key(task)
            owners = self._owners.get(key, set()) if key is not None else set()
            if task_id in self._executing or (owners and task_id not in owners):
                return False
            # No await between checking and claiming on the queue loop.
            if key is not None:
                self._owners.setdefault(key, set()).add(task_id)
            self._executing.add(task_id)
            claimed = True
            auth = await self._task_auth(task_id, account_id, user_id)
            task.auth = auth
            terminal = auth.get("external_terminal_snapshot")
            if auth.get("external_cleanup_failure") and terminal is None:
                await self.cancel_recovered(task_id, account_id, user_id)
                return True
            if terminal is not None:
                while not await self._apply_snapshot(
                    ExternalTaskSnapshot(**terminal),
                    task_id=task_id,
                    account_id=account_id,
                    user_id=user_id,
                    auth=auth,
                ):
                    await asyncio.sleep(provider.poll_interval_seconds)
                return True
            try:
                started = await provider.on_start(task)
            except (ResourceBusyError, GitConcurrentCommitError) as exc:
                if isinstance(exc, ResourceBusyError) and not exc.retryable:
                    raise
                started = "busy"
            if started == "busy":
                self._release(task)
                return False
            if isinstance(started, ExternalTaskSnapshot):
                finished = await self._apply_snapshot(
                    started,
                    task_id=task_id,
                    account_id=account_id,
                    user_id=user_id,
                    auth=auth,
                )
                if not finished:
                    await asyncio.sleep(provider.poll_interval_seconds)
                return finished
            await self._execute_task(task, provider, payload, account_id, user_id)
            return True
        finally:
            # Interrupted execution retains the reservation until cleanup confirms termination.
            if claimed:
                self._executing.remove(task_id)

    async def _execute_task(
        self,
        task: TaskRecord,
        provider: ExternalTaskProvider,
        payload: Mapping[str, Any],
        account_id: str,
        user_id: str,
    ) -> None:
        tracker = get_task_tracker()
        task_id = task.task_id
        auth = await self._task_auth(task_id, account_id, user_id)
        connection = {
            **self._mapping(auth.get("openviking_connection")),
            "account_id": task.account_id,
        }
        private_payload = self._mapping(auth.get("external_request_private"))
        external_task_id = str(auth.get("external_task_id") or "").strip() or None
        await tracker.start(
            task_id,
            account_id=account_id,
            user_id=user_id,
            stage="polling" if external_task_id else "submitting",
        )
        if external_task_id is None:
            external_task_id = await self._retry(
                lambda: provider.submit(task_id, payload, private_payload, connection),
                task_id=task_id,
                operation_name="submit",
                poll_interval=provider.poll_interval_seconds,
                max_attempts=provider.poll_max_attempts,
            )
            await tracker.patch_task(
                task_id,
                TaskPatch(
                    auth={"external_task_id": external_task_id},
                    meta=provider.submission_meta(external_task_id),
                ),
                account_id=account_id,
                user_id=user_id,
            )
        snapshot = None
        while True:
            if snapshot is None or snapshot.status in _ACTIVE_STATUSES:
                snapshot = await self._retry(
                    lambda: provider.get(
                        external_task_id,
                        connection,
                        payload=payload,
                        private_payload=private_payload,
                    ),
                    task_id=task_id,
                    operation_name="poll",
                    poll_interval=provider.poll_interval_seconds,
                    max_attempts=provider.poll_max_attempts,
                )
            if await self._apply_snapshot(
                snapshot,
                task_id=task_id,
                account_id=account_id,
                user_id=user_id,
                auth=auth,
            ):
                return
            await asyncio.sleep(provider.poll_interval_seconds)

    async def cancel_recovered(
        self, task_id: str, account_id: str, user_id: str, *, failure: Exception | None = None
    ) -> None:
        """Finish cleanup; persist failures for restart recovery."""
        tracker = get_task_tracker()
        try:
            # Repeated cancellation must not interrupt cleanup of the open Work.
            await tracker.unregister_running_task(task_id)
            auth = await self._task_auth(task_id, account_id, user_id)
            saved_failure = auth.get("external_cleanup_failure")
            if saved_failure:
                failure = ExternalTaskError(
                    saved_failure["code"], saved_failure["message"], transient=False
                )
            elif failure is not None:
                await run_to_completion(
                    lambda: tracker.patch_task(
                        task_id,
                        TaskPatch(
                            auth={
                                "external_cleanup_failure": {
                                    "code": getattr(failure, "code", None) or "INTERNAL",
                                    "message": sanitize_error(
                                        str(failure) or type(failure).__name__
                                    ),
                                }
                            }
                        ),
                        account_id=account_id,
                        user_id=user_id,
                    )
                )
            while True:
                try:
                    await self._retry(
                        lambda: self._cancel_recovered_once(task_id, account_id, user_id, failure),
                        task_id=task_id,
                        operation_name="cleanup",
                        poll_interval=0.2,
                        max_attempts=3,
                    )
                    return
                except ExternalTaskRetryExhaustedError as exc:
                    task = await tracker.get(task_id, account_id=account_id, user_id=user_id)
                    if task is None:
                        return
                    cleanup_error = sanitize_error(str(exc))
                    if task.meta.get("cleanup_error") != cleanup_error:
                        await tracker.patch_task(
                            task_id,
                            TaskPatch(meta={"cleanup_error": cleanup_error}),
                            account_id=account_id,
                            user_id=user_id,
                        )
                    await asyncio.sleep(
                        max(self._provider(task.task_type).poll_interval_seconds, 0.2)
                    )
        except asyncio.CancelledError:
            if await tracker.is_task_cancellation_requested(
                task_id, account_id=account_id, user_id=user_id
            ):
                raise ExternalTaskError(
                    "CLEANUP_INTERRUPTED", "External task cleanup was interrupted", transient=True
                ) from None
            raise
        except Exception as exc:
            await get_task_tracker().patch_task(
                task_id,
                TaskPatch(meta={"cleanup_error": sanitize_error(str(exc) or type(exc).__name__)}),
                account_id=account_id,
                user_id=user_id,
            )
            raise

    async def _cancel_recovered_once(
        self, task_id: str, account_id: str, user_id: str, failure: Exception | None = None
    ) -> None:
        """Resume cancellation without releasing a submitted task before Runtime stops."""
        tracker = get_task_tracker()
        task = await tracker.get(task_id, account_id=account_id, user_id=user_id)
        if task is None:
            return
        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED} or (
            task.status != TaskStatus.CANCELLED
            and (task.result is not None or task.error is not None)
        ):
            self._release(task)
            return
        payload = task.meta.get("request")
        if not isinstance(payload, dict):
            raise ExternalTaskError(
                "INVALID_ARGUMENT",
                "External task request is missing",
                transient=False,
            )
        auth = await self._task_auth(task_id, account_id, user_id)
        if (
            task.status in {TaskStatus.CANCELLING, TaskStatus.CANCELLED}
            and not auth.get("external_task_id")
            and "external_request_private" not in auth
            and "openviking_connection" not in auth
        ):
            # Cancellation outcome was recorded before its Work was ACKed.
            self._release(task)
            return
        provider = self._provider(task.task_type)
        private_payload = self._mapping(auth.get("external_request_private"))
        connection = {
            **self._mapping(auth.get("openviking_connection")),
            "account_id": task.account_id,
        }
        cancellation = await provider.on_cancel(
            task,
            external_task_id=str(auth.get("external_task_id") or "").strip() or None,
            payload=payload,
            private_payload=private_payload,
            connection=connection,
            failure=failure,
        )
        external_task_id = cancellation.external_task_id
        if external_task_id and auth.get("external_task_id") != external_task_id:
            await tracker.patch_task(
                task_id,
                TaskPatch(auth={"external_task_id": external_task_id}),
                account_id=account_id,
                user_id=user_id,
            )
            auth["external_task_id"] = external_task_id
        snapshot = cancellation.snapshot
        while True:
            if cancellation.terminal_snapshot is not None and snapshot.status in {
                "completed",
                "failed",
                "cancelled",
            }:
                snapshot = cancellation.terminal_snapshot
            if await self._apply_snapshot(
                snapshot,
                task_id=task_id,
                account_id=account_id,
                user_id=user_id,
                auth=auth,
            ):
                return
            await asyncio.sleep(provider.poll_interval_seconds)
            if snapshot.status not in _ACTIVE_STATUSES:
                continue
            if external_task_id is None:
                raise ExternalTaskError(
                    "INVALID_RESPONSE",
                    "Provider cancellation remained active without an external task ID",
                    transient=False,
                )
            snapshot = await provider.get(
                external_task_id,
                connection,
                payload=payload,
                private_payload=private_payload,
            )

    async def _task_auth(self, task_id: str, account_id: str, user_id: str) -> dict[str, Any]:
        auth = await get_task_tracker().get_task_auth(
            task_id,
            account_id=account_id,
            user_id=user_id,
        )
        try:
            for field in _PRIVATE_AUTH_FIELDS:
                value = auth.get(field)
                # Read tasks persisted before credential encryption was introduced.
                if not isinstance(value, dict) or value.get("provider") != _CREDENTIAL_PROVIDER:
                    continue
                ciphertext = base64.b64decode(value["ciphertext"], validate=True)
                if not ciphertext.startswith(MAGIC):
                    raise ValueError("Invalid encrypted credential envelope")
                plaintext = await self._credential_encryptor().decrypt(account_id, ciphertext)
                decoded = json.loads(plaintext)
                if not isinstance(decoded, dict):
                    raise ValueError("Invalid external task credentials")
                auth[field] = decoded
        except Exception as exc:
            raise FailedPreconditionError(
                "Cannot decrypt external task credentials; check encryption key configuration"
            ) from exc
        return auth

    @staticmethod
    async def _retry(
        action: Callable[[], Awaitable[Any]],
        *,
        task_id: str,
        operation_name: str,
        poll_interval: float,
        max_attempts: int,
    ) -> Any:
        """Try recoverable failures up to three times; permanent errors and cancellation propagate."""
        delay = max(poll_interval, 0.2)
        max_attempts = max(1, min(max_attempts, 3))
        for attempt in range(max_attempts):
            try:
                return await action()
            except (
                ExternalTaskError,
                ConnectionError,
                TimeoutError,
                AGFSConnectionError,
                AGFSNetworkError,
                AGFSTimeoutError,
                ResourceBusyError,
                GitConcurrentCommitError,
            ) as exc:
                if isinstance(exc, ExternalTaskError) and not exc.transient:
                    raise
                if isinstance(exc, ResourceBusyError) and not exc.retryable:
                    raise
                if attempt + 1 == max_attempts:
                    raise ExternalTaskRetryExhaustedError(
                        getattr(exc, "code", None) or "UNAVAILABLE",
                        sanitize_error(str(exc) or type(exc).__name__),
                        transient=False,
                    ) from exc
                logger.warning(
                    "External task %s will retry task=%s code=%s: %s",
                    operation_name,
                    task_id,
                    getattr(exc, "code", type(exc).__name__),
                    sanitize_error(str(exc)),
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
