"""Compile task lifecycle, collection pipelines and namespace-specific submissions."""

from __future__ import annotations

import asyncio
import json
import posixpath
import shlex
import shutil
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from loguru import logger
from pydantic import TypeAdapter

from openviking.core.namespace import classify_uri, relative_uri_path, uri_parts
from openviking.core.skill_loader import validate_skill_format
from openviking.utils.path_safety import (
    sanitize_relative_viking_path,
)
from openviking_cli.exceptions import OpenVikingError
from openviking_cli.utils.config.vlm_config import VLMConfig
from vikingbot.agent.loop import (
    AgentIterationLimitExceeded,
    AgentLoop,
    _PlainTextContext,
    _PlainTextDelivered,
)
from vikingbot.agent.subagent import SubagentManager
from vikingbot.agent.tools.base import ToolContext
from vikingbot.agent.tools.compile import (
    CompileChildTool,
    CompileImageReadTool,
    CompileSpawnTool,
    SubmitCompileDraftTool,
    SubmitWikiBundleTool,
)
from vikingbot.agent.tools.registry import ToolRegistry
from vikingbot.agent.tools.spawn import WaitSubagentsTool
from vikingbot.compile import file_ops, simple
from vikingbot.compile.models import (
    COMPILE_DRAFT_ROOT,
    COMPILE_STAGING_ROOT,
    DEFAULT_COMPILE_INSTRUCTION,
    TERMINAL_STATUSES,
    CompileAccepted,
    CompileErrorInfo,
    CompileFailure,
    CompileLimits,
    CompileRequest,
    CompileResult,
    CompileTask,
    SanitizedCompileRequest,
    has_directory_plan,
    utc_now,
)
from vikingbot.compile.pipeline import Pipeline
from vikingbot.compile.pipeline_agent import agent_runner as pipeline_agent_runner
from vikingbot.compile.renderer import (
    RenderedBundle,
    WikiRenderer,
    has_unclosed_frontmatter,
    validate_declared_okf_markdown,
)
from vikingbot.compile.sandbox import CompileSandboxManager
from vikingbot.compile.sources import CompileSourceRange, pack_source_batches, read_source
from vikingbot.compile.store import CompileTaskStore
from vikingbot.config.schema import SandboxBackend, SandboxMode, SessionKey
from vikingbot.openviking_mount.ov_server import VikingClient
from vikingbot.providers.base import LLMProvider, LLMResponse, LLMStreamEvent
from vikingbot.sandbox import SandboxManager
from vikingbot.sandbox.base import SandboxBackend as WorkspaceSandbox

_COMPILE_CORE_TOOLS = ("read_file", "write_file", "edit_file", "list_dir", "exec")
_COMPILE_READ_TOOLS = (
    "openviking_multi_read",
    "openviking_diff_paths",
    "openviking_list",
    "openviking_grep",
    "openviking_search",
    "openviking_glob",
)
_COMPILE_ISOLATED_EXEC_BACKENDS = frozenset(
    {
        SandboxBackend.SRT,
        SandboxBackend.DOCKER,
        SandboxBackend.OPENSANDBOX,
        SandboxBackend.AIOSANDBOX,
    }
)
_SKILL_EXCLUDED_FILES = frozenset(
    {".abstract.md", ".overview.md", ".relations.json", ".source.json"}
)
_CATALOG_FRONTMATTER_LINES = 128  # prefix read to detect unclosed OKF frontmatter
_COMPILE_BUDGET_REMINDER_THRESHOLDS = (15, 8, 3)  # remaining iterations


from vikingbot.compile.service_helpers import (
    CompileCapabilities, _CompileProvider, _await_with_hard_timeout,
    _compile_time, _consume_background_result, _merge_usage, _renew_compile_sandbox,
)
from vikingbot.compile.service_exec import _BotCompileExecMixin
from vikingbot.compile.service_pipeline import _BotCompilePipelineMixin
from vikingbot.compile.service_prompts import _BotCompilePromptsMixin
from vikingbot.compile.service_requests import _BotCompileRequestsMixin
from vikingbot.compile.service_sources import _BotCompileSourcesMixin


class BotCompileService(
    _BotCompileRequestsMixin,
    _BotCompileExecMixin,
    _BotCompilePipelineMixin,
    _BotCompileSourcesMixin,
    _BotCompilePromptsMixin,
):

    def __init__(
        self,
        *,
        agent_loop: AgentLoop,
        limits: CompileLimits | None = None,
    ):
        self.agent_loop = agent_loop
        self.config = agent_loop.config
        self.store = CompileTaskStore(self.config.bot_data_path)
        self.renderer = WikiRenderer()
        root_vlm = getattr(self.config, "get_root_vlm_config", lambda: None)()
        model_concurrency = (root_vlm or VLMConfig()).max_concurrent
        if model_concurrency < 1:
            raise ValueError("Compile requires vlm.max_concurrent >= 1")
        self.limits = limits or CompileLimits(
            source_concurrency=self.config.compile.map_concurrency or model_concurrency,
            shuffle_concurrency=self.config.compile.shuffle_concurrency or model_concurrency,
            shuffle_batch_size=self.config.compile.shuffle_batch_size,
            merge_concurrency=self.config.compile.reduce_concurrency or model_concurrency,
        )
        self._semaphore = asyncio.Semaphore(self.limits.concurrent_tasks)
        self._model_slots = asyncio.Semaphore(model_concurrency)
        self._target_locks: dict[tuple[str, str], tuple[asyncio.Lock, int]] = {}
        self._target_locks_guard = asyncio.Lock()
        self._admission_guard = asyncio.Lock()
        self._admitted_tasks = 0
        self._admitted_by_principal: dict[str, int] = {}
        self._tasks: set[asyncio.Task[Any]] = set()
        self._start_lock = asyncio.Lock()
        self._started = False

    async def start(self) -> None:
        async with self._start_lock:
            if self._started:
                return
            await self.store.mark_interrupted_failed()
            await self._prune_terminal_tasks()
            self._started = True

    async def close(self) -> None:
        """Cancel active work and let task finally blocks release their sandboxes."""
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def create_task(
        self,
        request: CompileRequest,
        *,
        principal_scope: str,
        task_id: str | None = None,
    ) -> CompileAccepted:
        await self.start()
        if task_id is not None:
            try:
                existing = await self.store.get(task_id)
            except ValueError as exc:
                raise CompileFailure(
                    "INVALID_ARGUMENT",
                    "Idempotency-Key must be a valid Compile task ID.",
                    stage="queued",
                ) from exc
            if existing is not None:
                if existing.principal_scope != principal_scope:
                    raise CompileFailure(
                        "PERMISSION_DENIED",
                        "Compile session belongs to another principal.",
                        stage="queued",
                    )
                return CompileAccepted(
                    session_id=existing.task_id,
                    task_id=existing.task_id,
                    status="accepted",
                    to=existing.sanitized_request.to,
                )
        await self._admit(principal_scope)
        runner_started = False
        try:
            connection = (
                request.openviking_connection.model_dump(exclude_none=True)
                if request.openviking_connection is not None
                else None
            )
            if not connection and self._openviking_auth_mode() != "dev":
                raise CompileFailure(
                    "UNAVAILABLE",
                    "Compile requires an authenticated OpenViking connection.",
                    stage="queued",
                )
            connection = connection or {}
            account_id = connection.get("account_id")
            if self._openviking_auth_mode() != "dev" and not (account_id or "").strip():
                raise CompileFailure(
                    "UNAUTHENTICATED", "Compile requires account_id.", stage="queued"
                )
            normalized_request = await self._normalize_request(request, connection=connection)
            task_id = task_id or "cmp_" + uuid.uuid4().hex
            now = utc_now()
            task = CompileTask(
                task_id=task_id,
                principal_scope=principal_scope,
                sanitized_request=normalized_request,
                meta={"mode": self.config.compile.mode},
                status="accepted",
                stage="queued",
                created_at=now,
                updated_at=now,
            )
            try:
                await self.store.create(task)
            except FileExistsError:
                existing = await self.store.get(task_id)
                if existing is None or existing.principal_scope != principal_scope:
                    raise CompileFailure(
                        "PERMISSION_DENIED",
                        "Compile session belongs to another principal.",
                        stage="queued",
                    )
                return CompileAccepted(
                    session_id=existing.task_id,
                    task_id=existing.task_id,
                    status="accepted",
                    to=existing.sanitized_request.to,
                )
            runner = asyncio.create_task(
                self._run_admitted_task(
                    task_id,
                    normalized_request,
                    connection,
                    principal_scope,
                ),
                name=f"compile:{task_id}",
            )
            self._tasks.add(runner)
            runner.add_done_callback(self._tasks.discard)
            runner_started = True
            return CompileAccepted(
                session_id=task_id,
                task_id=task_id,
                to=normalized_request.to,
            )
        finally:
            if not runner_started:
                await self._release_admission(principal_scope)

    async def get_task(self, task_id: str, *, principal_scope: str) -> dict[str, Any] | None:
        await self.start()
        try:
            task = await self.store.get(task_id)
        except ValueError:
            return None
        if task is None or task.principal_scope != principal_scope:
            return None
        return task.public_dict()

    async def cancel_task(self, task_id: str, *, principal_scope: str) -> dict[str, Any] | None:
        """Request cooperative cancellation of one principal-owned Compile task."""
        await self.start()
        try:
            task = await self.store.get(task_id)
        except ValueError:
            return None
        if task is None or task.principal_scope != principal_scope:
            return None
        if task.status in TERMINAL_STATUSES:
            return task.public_dict()

        def request_cancellation(current: CompileTask) -> None:
            if current.principal_scope != principal_scope or current.status in TERMINAL_STATUSES:
                return
            current.status = "cancelling"

        task = await self.store.update(task_id, request_cancellation)
        if task.principal_scope != principal_scope:
            return None
        if task.status in TERMINAL_STATUSES:
            return task.public_dict()

        runner = next(
            (
                candidate
                for candidate in self._tasks
                if candidate.get_name() == f"compile:{task_id}"
            ),
            None,
        )
        if runner is None or not runner.cancel():
            await self._finish_cancellation(task_id)
        latest = await self.store.get(task_id)
        return latest.public_dict() if latest is not None else None

    async def _run_task(
        self,
        task_id: str,
        request: SanitizedCompileRequest,
        connection: dict[str, Any],
    ) -> None:
        account_id = (
            "default" if self._openviking_auth_mode() == "dev" else connection["account_id"]
        )
        target = (account_id, request.to)
        task_lock = await self._retain_target_lock(target)
        acquired = False
        try:
            await self._acquire_execution_slot(task_lock)
            acquired = True

            try:
                await self._execute_task(task_id, request, connection)
            except CompileFailure as exc:
                await self._fail(task_id, exc)
            except Exception as exc:
                logger.exception("Compile task {} failed", task_id)
                task = await self.store.get(task_id)
                stage = task.stage if task else "agent"
                code = self._unexpected_error_code(exc, stage=stage)
                await self._fail(task_id, CompileFailure(code, str(exc), stage=stage))
        finally:
            if acquired:
                self._semaphore.release()
                task_lock.release()
            await self._release_target_lock(target, task_lock)
