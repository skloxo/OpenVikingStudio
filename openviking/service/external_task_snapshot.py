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


class _ExternalTaskSnapshotMixin:

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    async def _apply_snapshot(
        self,
        snapshot: ExternalTaskSnapshot,
        *,
        task_id: str,
        account_id: str,
        user_id: str,
        auth: dict[str, Any],
    ) -> bool:
        """Apply state; return False while execution or finalization is active.

        ``auth`` is this delivery's private Task auth snapshot. Its cleanup
        failure marker changes only after the matching patch is persisted.
        """
        tracker = get_task_tracker()
        task = await tracker.get(task_id, account_id=account_id, user_id=user_id)
        if task is None:
            return True
        if task.status == TaskStatus.CANCELLED:
            if snapshot.status in _ACTIVE_STATUSES:
                return False
            if snapshot.status not in {"completed", "failed", "cancelled"}:
                raise ExternalTaskError(
                    "INVALID_RESPONSE",
                    f"Unknown external task status: {snapshot.status}",
                    transient=False,
                )
            task.auth = dict(auth)
            finished = await self._provider(task.task_type).on_finish(
                task, replace(snapshot, status="cancelled")
            )
            if finished.status in _ACTIVE_STATUSES:
                return False
            if finished.status not in {"completed", "failed", "cancelled"}:
                raise ExternalTaskError(
                    "INVALID_RESPONSE",
                    f"Unknown external task status: {finished.status}",
                    transient=False,
                )
            self._release(task)
            return True
        if task.is_terminal() or task.result is not None or task.error is not None:
            # The outcome may already be recorded while QueueFS still owns this Work.
            self._release(task)
            return True
        if snapshot.stage is not None or snapshot.meta:
            # Runtime termination can still require local finalization before the Task ends.
            stage = (
                task.stage
                if task is not None and snapshot.status in {"completed", "failed", "cancelled"}
                else snapshot.stage or snapshot.status
            )
            meta = snapshot.meta or {}
            if task is not None and (
                task.stage != stage
                or any(
                    key not in task.meta or task.meta[key] != value for key, value in meta.items()
                )
            ):
                await tracker.patch_task(
                    task_id,
                    TaskPatch(stage=stage, meta=meta),
                    account_id=account_id,
                    user_id=user_id,
                )
        if snapshot.status in _ACTIVE_STATUSES:
            return False
        if snapshot.status not in {"completed", "failed", "cancelled"}:
            raise ExternalTaskError(
                "INVALID_RESPONSE",
                f"Unknown external task status: {snapshot.status}",
                transient=False,
            )
        if task is not None:
            terminal = asdict(snapshot)
            if auth.get("external_terminal_snapshot") != terminal:
                await tracker.patch_task(
                    task_id,
                    TaskPatch(auth={"external_terminal_snapshot": terminal}),
                    account_id=account_id,
                    user_id=user_id,
                )
                auth["external_terminal_snapshot"] = terminal
            task.auth = dict(auth)
            # Persist failure intent before a deferred rollback.
            if snapshot.status == "failed":
                cleanup_failure = {
                    "code": snapshot.error_code or "UNKNOWN",
                    "message": sanitize_error(snapshot.error_message or "External task failed"),
                }
                if auth.get("external_cleanup_failure") != cleanup_failure:
                    result = await run_to_completion(
                        lambda: tracker.patch_task(
                            task_id,
                            TaskPatch(auth={"external_cleanup_failure": cleanup_failure}),
                            account_id=account_id,
                            user_id=user_id,
                        )
                    )
                    if result.is_applied:
                        auth["external_cleanup_failure"] = cleanup_failure
            snapshot = await self._provider(task.task_type).on_finish(task, snapshot)
            if snapshot.status in _ACTIVE_STATUSES:
                stage = snapshot.stage or snapshot.status
                if task.stage != stage:
                    await tracker.patch_task(
                        task_id,
                        TaskPatch(stage=stage),
                        account_id=account_id,
                        user_id=user_id,
                    )
                return False

        async def finalize() -> None:
            if snapshot.status == "failed":
                await tracker.fail(
                    task_id,
                    self._format_error(
                        snapshot.error_code or "UNKNOWN",
                        snapshot.error_message or "External task failed",
                    ),
                    account_id=account_id,
                    user_id=user_id,
                )
            elif snapshot.status == "completed":
                await tracker.complete(
                    task_id,
                    snapshot.result or snapshot.meta or {},
                    account_id=account_id,
                    user_id=user_id,
                )
            else:
                await tracker.record_cancelled(
                    task_id,
                    account_id=account_id,
                    user_id=user_id,
                )

        for attempt in range(3):
            try:
                await run_to_completion(finalize)
                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt == 2:
                    raise ExternalTaskResultSaveError(f"Outcome save exhausted: {exc}") from exc
                await asyncio.sleep(0.2 * (attempt + 1))
        if task is not None:
            self._release(task)
        return True

    @staticmethod
    def _format_error(code: str, message: str) -> str:
        return f"{code}: {message}"
