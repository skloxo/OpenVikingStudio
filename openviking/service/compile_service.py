# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Compile API models and external task provider."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Mapping

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from openviking.core.namespace import classify_uri, uri_parts
from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.identity import RequestContext
from openviking.service.compile_targets import CompileLifecycle, UpdateSchedule, split_control_args
from openviking.service.external_task_service import (
    ExternalTaskCancellation,
    ExternalTaskError,
    ExternalTaskRetryExhaustedError,
    ExternalTaskService,
    ExternalTaskSnapshot,
)
from openviking.service.fs_service import FSService
from openviking.service.memory_compile import MemoryCompileRunner
from openviking.service.task_tracker import SENSITIVE_TASK_KEYS, TaskRecord
from openviking.session.memory.utils.memory_fields import strip_memory_fields_trailer
from openviking.storage.acl import AclAction
from openviking_cli.exceptions import (
    ConflictError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
    UnavailableError,
)
from openviking_cli.utils.config.open_viking_config import CompileApiConfig
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_ACTIVE_STATUSES = frozenset({"accepted", "pending", "running", "committing"})
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

# Sentinel --skill value that routes a Compile request to in-process memory
# consolidation instead of the VikingBot agent path. It is not a real Skill URI.
MEMORY_COMPILE_SKILL = "memory"
from openviking.service.compile_api_client import (
    CompileAPIClient, CompileConfigUpdate, CompileErrorInfo, CompileRequest,
    CompileSessionAccepted, CompileSessionStatus, _CompileEndpoint,
)
from openviking.service.compile_service_ops import _CompileServiceOpsMixin


class CompileService(_CompileServiceOpsMixin):
    """Validate Compile requests and own their external task lifecycle."""

    task_type = "compile"
    task_id_prefix = "cmp_"
    poll_max_attempts = 3

    def __init__(
        self,
        config: CompileApiConfig,
        tasks: ExternalTaskService,
        fs: FSService,
    ) -> None:
        self._config = config
        self._tasks = tasks
        self._fs = fs
        self._local_endpoint: _CompileEndpoint | None = None
        self._memory_runner: MemoryCompileRunner | None = None
        self._lifecycle: CompileLifecycle | None = None
        # Keep submission history tasks alive until their storage operations finish.
        self._history_tasks: set[asyncio.Task[None]] = set()

    def configure_lifecycle(self, lifecycle: CompileLifecycle) -> None:
        """Enable target registry, incremental planning and scheduled updates."""
        self._lifecycle = lifecycle

    @property
    def lifecycle(self) -> CompileLifecycle | None:
        return self._lifecycle

    def configure_memory_runner(
        self,
        vikingdb: Any = None,
        *,
        runtime_config_manager: Any = None,
        vlm_resolver=None,
    ) -> None:
        """Install the in-process memory-consolidation runner for `--skill memory`."""
        self._memory_runner = MemoryCompileRunner(
            self._fs,
            vikingdb=vikingdb,
            runtime_config_manager=runtime_config_manager,
            vlm_resolver=vlm_resolver,
        )

    @property
    def poll_interval_seconds(self) -> float:
        return self._endpoint().poll_interval_ms / 1000.0

    def serialization_key(self, payload: Mapping[str, Any]) -> str:
        return payload["to"]

    def configure_local_backend(self, base_url: str, gateway_token: str) -> None:
        if self._config.base_url:
            return
        self._local_endpoint = _CompileEndpoint(
            base_url=base_url.rstrip("/"),
            gateway_token=gateway_token,
            http_timeout_seconds=10.0,
            poll_interval_ms=30000,
            local=True,
        )

    def _endpoint(self) -> _CompileEndpoint:
        if self._config.base_url:
            return _CompileEndpoint(
                base_url=self._config.base_url,
                gateway_token=self._config.gateway_token,
                http_timeout_seconds=self._config.http_timeout_seconds,
                poll_interval_ms=self._config.poll_interval_ms,
            )
        if self._local_endpoint is not None:
            return self._local_endpoint
        raise UnavailableError("compile API", "compile_api.base_url is not configured")

    def _client(self) -> CompileAPIClient:
        return CompileAPIClient(self._endpoint())

    def capabilities(self, ctx: RequestContext) -> dict[str, Any]:
        try:
            endpoint = self._endpoint()
        except UnavailableError:
            return {"configured": False, "can_create": False, "reason_code": "NOT_CONFIGURED"}
        allowed = endpoint.local or bool(ctx.api_key)
        return {
            "configured": True,
            "can_create": allowed,
            "reason_code": None if allowed else "API_KEY_REQUIRED",
        }

    async def create(
        self,
        request: CompileRequest,
        *,
        connection: Mapping[str, Any],
        ctx: RequestContext,
        idempotency_key: str | None = None,
    ) -> TaskRecord | dict[str, Any]:
        """Save explicit update settings synchronously, or queue one immediate Compile run."""
        control, _ = split_control_args(request.args)
        configures_schedule = "auto_update" in control or "update_schedule" in control
        if request.is_memory_mode:
            if configures_schedule:
                raise InvalidArgumentError("Scheduled updates do not support --skill memory")
            if self._memory_runner is None:
                raise UnavailableError(
                    "memory compile", "memory consolidation runner is not configured"
                )
            return await self._memory_runner.create(
                target=request.to,
                instruction=request.instruction,
                ctx=ctx,
            )
        request = self._normalize_request_uris(request, ctx)
        CompileLifecycle.validate_layout(request.to, request.from_)
        if configures_schedule:
            lifecycle = self._require_lifecycle()
            normalized = await self._normalize_request(request, ctx)
            submitted, _ = self._split_payload(normalized)
            control, runtime_args = split_control_args(submitted.get("args"))
            record = await lifecycle.save_submission(
                submitted, control, runtime_args, request._instruction_sent, ctx
            )
            return self._config_view(record)
        if idempotency_key:
            payload, private_payload = self._split_payload(request)
            existing = await self._tasks.recover_submission(
                self.task_type, payload, private_payload, ctx, idempotency_key
            )
            if existing is not None:
                self._schedule_history(existing)
                return existing
        endpoint = self._endpoint()
        if not endpoint.local and not str(connection.get("api_key") or "").strip():
            raise UnauthenticatedError("Compile requires a forwardable OpenViking API key")
        normalized = await self._normalize_request(request, ctx)
        submitted, private_payload = self._split_payload(normalized)
        payload = submitted
        preparation = None
        if self._lifecycle is not None:
            control, runtime_args = split_control_args(submitted.get("args"))
            payload = {key: value for key, value in submitted.items() if key != "args"}
            if runtime_args:
                payload["args"] = runtime_args
            payload["compile"] = {
                "mode": control.get("mode", "incremental"),
                "trigger": "manual",
            }
            preparation = asyncio.create_task(
                self._lifecycle.prepare(submitted, ctx, instruction_set=request._instruction_sent)
            )
        return await self._create_task(
            payload,
            submitted,
            private_payload,
            normalized,
            connection,
            ctx,
            idempotency_key,
            preparation=preparation,
        )

    async def create_scheduled(
        self,
        record: dict[str, Any],
        *,
        ctx: RequestContext,
        connection: Mapping[str, Any],
        idempotency_key: str,
    ) -> TaskRecord:
        """Submit an incremental task from a locked target record (see CompileScheduler)."""
        assert self._lifecycle is not None
        request = CompileRequest.model_validate(
            {
                "from": record["from"],
                "to": record["to"],
                "skill": record["skill"],
                "instruction": record["instruction"],
                "args": {"mode": "incremental", **record["execution_context"]["args"]},
            }
        )
        normalized = await self._normalize_request(self._normalize_request_uris(request, ctx), ctx)
        submitted, private_payload = self._split_payload(normalized)
        payload = await self._lifecycle.prepare(
            submitted, ctx, instruction_set=False, scheduled_record=record
        )
        return await self._create_task(
            payload,
            submitted,
            private_payload,
            normalized,
            connection,
            ctx,
            idempotency_key,
            locked_record=record,
        )

    async def _create_task(
        self,
        payload: dict[str, Any],
        submitted: dict[str, Any],
        private_payload: dict[str, Any],
        normalized: CompileRequest,
        connection: Mapping[str, Any],
        ctx: RequestContext,
        idempotency_key: str | None,
        *,
        locked_record: dict[str, Any] | None = None,
        preparation: asyncio.Task[Any] | None = None,
    ) -> TaskRecord:
        """Enqueue work, recording scheduled history before releasing its caller-owned state lock."""
        task = await self._tasks.create(
            self.task_type,
            resource_id=", ".join(normalized.from_),
            payload=payload,
            private_payload=private_payload,
            connection=connection,
            ctx=ctx,
            idempotency_key=idempotency_key,
            submission_payload=submitted if idempotency_key else None,
        )
        if locked_record is not None:
            await self._require_lifecycle().record_queued(task, locked_record=locked_record)
        else:
            self._schedule_history(task, preparation=preparation)
        return task

    def _schedule_history(
        self, task: TaskRecord, *, preparation: asyncio.Task[Any] | None = None
    ) -> None:
        """Record history after optional preparation, logging background failures."""
        lifecycle = self._lifecycle
        if lifecycle is None:
            return

        async def record_history() -> None:
            try:
                if preparation is not None:
                    await preparation
                await lifecycle.record_queued(task)
            except Exception:
                logger.exception(
                    "Failed to record Compile submission history task_id=%s", task.task_id
                )

        background = asyncio.create_task(record_history())
        self._history_tasks.add(background)
        background.add_done_callback(self._history_tasks.discard)

    async def on_start(self, task: TaskRecord) -> str | ExternalTaskSnapshot | None:
        if self._lifecycle is None:
            return "proceed"
        return await self._lifecycle.on_start(task)

    async def on_finish(
        self,
        task: TaskRecord,
        snapshot: ExternalTaskSnapshot,
    ) -> ExternalTaskSnapshot:
        if self._lifecycle is None:
            return snapshot
        return await self._lifecycle.on_finish(task, snapshot)

    @staticmethod
    def submission_meta(_external_task_id: str) -> dict[str, Any]:
        return {}

    async def submit(
        self,
        ov_task_id: str,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        connection: Mapping[str, Any],
    ) -> str:
        request_payload = dict(payload)
        request_payload.pop("compile", None)
        args = self._merge_args(payload, private_payload)
        if self._lifecycle is not None:
            changes = await self._lifecycle.runtime_changes(
                payload, str(connection.get("account_id") or ""), ov_task_id
            )
            if changes is not None:
                args = {**(args or {}), "changes": changes}
        if args is not None:
            request_payload["args"] = args
        accepted = await self._client().create(
            {"task_type": self.task_type, "payload": request_payload},
            connection=connection,
            idempotency_key=ov_task_id,
        )
        return accepted.session_id

    async def get(
        self,
        external_task_id: str,
        connection: Mapping[str, Any],
        *,
        payload: Mapping[str, Any] | None = None,
        private_payload: Mapping[str, Any] | None = None,
    ) -> ExternalTaskSnapshot:
        """Query Runtime using args from the task's persisted public and private payloads."""
        return self._snapshot(
            await self._client().get(
                external_task_id,
                connection=connection,
                args=self._merge_args(payload, private_payload),
            )
        )

    async def cancel(
        self,
        external_task_id: str,
        connection: Mapping[str, Any],
        *,
        payload: Mapping[str, Any] | None = None,
        private_payload: Mapping[str, Any] | None = None,
    ) -> ExternalTaskSnapshot:
        """Cancel Runtime work using the original task payloads, including restored secrets."""
        return self._snapshot(
            await self._client().cancel(
                external_task_id,
                connection=connection,
                args=self._merge_args(payload, private_payload),
            )
        )

    async def on_cancel(
        self,
        task: TaskRecord,
        *,
        external_task_id: str | None,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        connection: Mapping[str, Any],
        failure: Exception | None,
    ) -> ExternalTaskCancellation:
        """Recover an uncertain Compile submission, then stop its Runtime session."""
        outcome = (
            ExternalTaskSnapshot(
                status="failed",
                error_code=getattr(failure, "code", None) or "INTERNAL",
                error_message=str(failure) or type(failure).__name__,
            )
            if failure is not None
            else ExternalTaskSnapshot(status="cancelled")
        )
        rejected = (
            task.stage == "submitting"
            and isinstance(failure, ExternalTaskError)
            and not isinstance(failure, ExternalTaskRetryExhaustedError)
            and not failure.transient
            and failure.code
            in {"INVALID_ARGUMENT", "NOT_FOUND", "PERMISSION_DENIED", "UNAUTHENTICATED"}
        )
        if external_task_id is None and (task.stage in {None, "queued"} or rejected):
            return ExternalTaskCancellation(None, outcome)
        if external_task_id is None:
            external_task_id = await self.submit(
                task.task_id,
                payload,
                private_payload,
                connection,
            )
        snapshot = await self.cancel(
            external_task_id,
            connection,
            payload=payload,
            private_payload=private_payload,
        )
        return ExternalTaskCancellation(
            external_task_id,
            snapshot,
            terminal_snapshot=outcome if failure is not None else None,
        )
