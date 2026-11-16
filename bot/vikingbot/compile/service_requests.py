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


class _BotCompileRequestsMixin:

    async def _normalize_request(
        self,
        request: CompileRequest,
        *,
        connection: Mapping[str, Any],
    ) -> SanitizedCompileRequest:
        args = request.args or {}
        if args.keys() - {"last_compile_time", "changes"}:
            raise CompileFailure(
                "INVALID_ARGUMENT",
                "VikingBot Compile does not implement provider-specific args.",
                stage="queued",
            )
        changes = args.get("changes")
        if changes is not None:
            valid = (
                has_directory_plan(changes)
                and "base" in changes
                and "head" in changes
                and all(
                    isinstance(changes[key], list)
                    and all(isinstance(uri, str) and uri.strip() for uri in changes[key])
                    for key in ("diff_dirs", "full_dirs")
                )
            )
            valid = valid and all(
                changes.get(key) is None
                or isinstance(changes[key], str)
                and bool(changes[key].strip())
                for key in ("base", "head")
            )
            execution = changes.get("execution") if isinstance(changes, dict) else None
            valid = (
                valid
                and isinstance(execution, dict)
                and execution.get("mode") in ("full", "incremental")
            )
            if not valid:
                raise CompileFailure(
                    "INVALID_ARGUMENT", "Invalid args.changes directory plan", stage="queued"
                )
            if changes["diff_dirs"] and (
                not changes.get("base") or not changes.get("head") or execution["mode"] == "full"
            ):
                raise CompileFailure(
                    "INVALID_ARGUMENT", "diff_dirs require incremental base/head", stage="queued"
                )
            if not changes.get("head") and execution["mode"] != "full":
                raise CompileFailure(
                    "INVALID_ARGUMENT",
                    "Unavailable snapshots require full execution",
                    stage="queued",
                )
        raw_sources = [str(value).strip() for value in request.from_]
        if not raw_sources or any(not value for value in raw_sources):
            raise CompileFailure(
                "INVALID_ARGUMENT", "from must contain files or directories", stage="queued"
            )
        client = await VikingClient.create(connection=connection, config=self.config)
        try:
            cutoff = (
                _compile_time(args["last_compile_time"]) if "last_compile_time" in args else None
            )
            sources: list[str] = []
            for raw_uri in raw_sources:
                attrs = await client.attrs(raw_uri)
                canonical = str(attrs.get("uri") or "").rstrip("/")
                if canonical not in sources:
                    sources.append(canonical)
            if changes is not None:
                diff_dirs, full_dirs = changes["diff_dirs"], changes["full_dirs"]
                if set(diff_dirs) & set(full_dirs) or set(diff_dirs + full_dirs) != set(sources):
                    raise CompileFailure(
                        "INVALID_ARGUMENT",
                        "Directory plan must partition the canonical from list",
                        stage="queued",
                    )
            skill_uri = request.skill.strip().rstrip("/")
            if skill_uri.endswith("/SKILL.md"):
                skill_uri = skill_uri[: -len("/SKILL.md")]
            skill_attrs = await client.attrs(skill_uri)
            canonical_skill = str(skill_attrs.get("uri") or "").rstrip("/")
            skill_stat = await client.stat(canonical_skill)
            if not skill_stat.get("isDir"):
                raise CompileFailure(
                    "SKILL_INVALID",
                    "--skill must resolve to a Skill directory or SKILL.md",
                    stage="queued",
                )
            self._skill_name_and_target(canonical_skill)

            raw_target = request.to.strip().rstrip("/")
            try:
                target_stat = await client.stat(raw_target)
            except OpenVikingError as exc:
                if exc.code != "NOT_FOUND":
                    raise
                self._validate_target_directory(raw_target, {"isDir": True})
                await client.mkdir(raw_target, description="compile target folder")
                target_stat = await client.stat(raw_target)
            target = str(target_stat.get("uri") or "").rstrip("/")
            self._validate_target_directory(target, target_stat)
        except CompileFailure:
            raise
        except OpenVikingError as exc:
            raise CompileFailure(exc.code, str(exc), stage="queued") from exc
        except Exception as exc:
            raise CompileFailure("INVALID_ARGUMENT", str(exc), stage="queued") from exc
        finally:
            await client.close()

        instruction = (request.instruction or "").strip()
        return SanitizedCompileRequest(
            **{
                "from": sources,
                "to": target,
                "instruction": instruction or DEFAULT_COMPILE_INSTRUCTION,
                "instruction_provided": bool(instruction),
                "skill": canonical_skill,
                "last_compile_time": None if changes is not None else cutoff,
                "changes": changes,
            }
        )

    @staticmethod
    def _validate_target_directory(target: str, stat: Mapping[str, Any]) -> None:
        if not stat.get("isDir"):
            raise CompileFailure(
                "INVALID_ARGUMENT", "Compile target must be a directory", stage="queued"
            )
        if target.rsplit("/", 1)[-1] in _SKILL_EXCLUDED_FILES:
            raise CompileFailure(
                "INVALID_ARGUMENT",
                "Compile target must not be an OpenViking derived directory",
                stage="queued",
            )
        classification = classify_uri(target)
        parts = uri_parts(target)
        if classification.context_type == "skill":
            if not classification.is_skill_namespace or (
                classification.scope == "agent" and parts != ["agent", "skills"]
            ):
                raise CompileFailure(
                    "INVALID_ARGUMENT",
                    "Compile Skill target must be a supported skills namespace",
                    stage="queued",
                )
            return
        if classification.context_type not in {"resource", "memory"}:
            raise CompileFailure(
                "INVALID_ARGUMENT",
                "Compile target must be a resource, memory, or skills directory",
                stage="queued",
            )
        if classification.context_type == "memory":
            if (
                classification.content_index is None
                or len(parts) <= classification.content_index + 1
            ):
                raise CompileFailure(
                    "INVALID_ARGUMENT",
                    "Compile target must be inside a memory type directory",
                    stage="queued",
                )
        elif parts == ["resources"] or (
            classification.content_index is not None
            and len(parts) <= classification.content_index + 1
        ):
            raise CompileFailure(
                "INVALID_ARGUMENT",
                "Compile target must be inside a resource directory",
                stage="queued",
            )

    @staticmethod
    def _skill_name_and_target(skill_uri: str) -> tuple[str, str]:
        classification = classify_uri(skill_uri)
        if not classification.is_skill:
            raise CompileFailure(
                "SKILL_INVALID", "Skill URI is outside a skills namespace", stage="queued"
            )
        if not classification.is_skill_root:
            raise CompileFailure(
                "SKILL_INVALID", "Skill URI must identify one Skill root", stage="queued"
            )
        assert classification.content_index is not None
        parts = classification.parts
        return (
            parts[-1],
            "viking://" + "/".join(parts[: classification.content_index + 1]),
        )

    async def _retain_target_lock(self, target: tuple[str, str]) -> asyncio.Lock:
        """Retain a task lock keyed by effective account and canonical target URI."""
        async with self._target_locks_guard:
            lock, references = self._target_locks.get(target, (asyncio.Lock(), 0))
            self._target_locks[target] = (lock, references + 1)
            return lock

    async def _release_target_lock(self, target: tuple[str, str], lock: asyncio.Lock) -> None:
        """Remove an account-target lock after its last active or waiting task exits."""
        async with self._target_locks_guard:
            current, references = self._target_locks.get(target, (lock, 0))
            if current is not lock:
                return
            if references <= 1:
                self._target_locks.pop(target, None)
            else:
                self._target_locks[target] = (lock, references - 1)

    async def _acquire_execution_slot(self, target_lock: asyncio.Lock) -> None:
        await target_lock.acquire()
        try:
            await self._semaphore.acquire()
        except BaseException:
            target_lock.release()
            raise

    async def _admit(self, principal_scope: str) -> None:
        async with self._admission_guard:
            principal_tasks = self._admitted_by_principal.get(principal_scope, 0)
            if (
                self._admitted_tasks >= self.limits.accepted_tasks
                or principal_tasks >= self.limits.accepted_tasks_per_principal
            ):
                raise CompileFailure(
                    "RESOURCE_EXHAUSTED",
                    "Compile task admission limit exceeded.",
                    stage="queued",
                )
            self._admitted_tasks += 1
            self._admitted_by_principal[principal_scope] = principal_tasks + 1

    async def _release_admission(self, principal_scope: str) -> None:
        async with self._admission_guard:
            principal_tasks = self._admitted_by_principal.get(principal_scope, 0)
            if principal_tasks == 0:
                return
            if principal_tasks <= 1:
                self._admitted_by_principal.pop(principal_scope, None)
            else:
                self._admitted_by_principal[principal_scope] = principal_tasks - 1
            self._admitted_tasks -= 1

    async def _prune_terminal_tasks(self) -> None:
        await self.store.prune_terminal(
            retention_seconds=self.limits.terminal_task_retention_seconds,
            max_records=self.limits.terminal_task_records,
        )

    async def _run_admitted_task(
        self,
        task_id: str,
        request: SanitizedCompileRequest,
        connection: dict[str, Any],
        principal_scope: str,
    ) -> None:
        try:
            await self._run_task(task_id, request, connection)
        except asyncio.CancelledError:
            task = await self.store.get(task_id)
            if task is None or task.status != "cancelling":
                raise
        finally:
            try:
                await self._finish_cancellation(task_id)
            finally:
                await self._release_admission(principal_scope)
                await self._prune_terminal_tasks()

    async def _finish_cancellation(self, task_id: str) -> None:
        def finish(task: CompileTask) -> None:
            if task.status != "cancelling":
                return
            task.status = "cancelled"
            task.stage = "cancelled"
            task.result = None
            task.error = None

        try:
            await self.store.update(task_id, finish)
        except (FileNotFoundError, ValueError):
            return

    def _openviking_auth_mode(self) -> str:
        ov_server = getattr(self.config, "ov_server", None)
        return str(getattr(ov_server, "effective_auth_mode", "") or "").strip().lower()

    def _compile_capabilities(self) -> CompileCapabilities:
        sandbox = getattr(self.config, "sandbox", None)
        try:
            backend = SandboxBackend(getattr(sandbox, "backend", None))
        except (TypeError, ValueError):
            return CompileCapabilities(exec_enabled=False)
        if backend == SandboxBackend.DIRECT:
            direct = sandbox.backends.direct
            return CompileCapabilities(exec_enabled=direct.allow_exec and direct.allow_compile_exec)
        return CompileCapabilities(exec_enabled=backend in _COMPILE_ISOLATED_EXEC_BACKENDS)
