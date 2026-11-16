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


def _compile_time(value: Any) -> datetime:
    """Parse ISO/Unix timestamps; naive values use UTC and invalid values raise ValueError."""
    parsed = TypeAdapter(datetime).validate_python(value)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _merge_usage(*values: Mapping[str, Any]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for usage in values:
        for key, value in usage.items():
            if isinstance(value, int):
                merged[key] = merged.get(key, 0) + value
    return merged


def _consume_background_result(future: asyncio.Future[Any], *, label: str) -> None:
    try:
        future.result()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("Compile {} failed after its grace deadline: {}", label, exc)


async def _renew_compile_sandbox(
    sandbox: WorkspaceSandbox,
    interval: float,
    owner: asyncio.Task[Any],
    *,
    fail_task: Callable[[CompileFailure], Awaitable[None]],
) -> None:
    """Renew the current sandbox immediately and every interval seconds until cancelled.

    Each health/renewal request is bounded by interval. On failure, fail_task
    persists the outcome before owner cancellation, independently of worker
    cleanup. The owner is cancelled even if persistence raises an error.
    """
    while True:
        try:
            if not await asyncio.wait_for(sandbox.is_healthy(), timeout=interval):
                raise RuntimeError("Sandbox is not healthy")
        except Exception as exc:
            failure = CompileFailure(
                "UNAVAILABLE",
                f"Sandbox renewal failed: {str(exc) or type(exc).__name__}",
                stage="sandbox",
            )
            try:
                await fail_task(failure)
            finally:
                owner.cancel()
            raise failure from exc
        await asyncio.sleep(interval)


async def _await_with_hard_timeout(
    awaitable: Awaitable[Any],
    *,
    timeout: float,
    label: str,
) -> Any:
    """Give bounded fallback work its full grace period, but never wait past it."""
    future = asyncio.ensure_future(awaitable)
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = max(0.0, deadline - asyncio.get_running_loop().time())
        try:
            done, _pending = await asyncio.wait({future}, timeout=remaining)
        except asyncio.CancelledError:
            # The task runtime may expire while an iteration-limit salvage is
            # already underway. Preserve the independent grace period.
            continue
        except BaseException:
            future.cancel()
            future.add_done_callback(
                lambda completed: _consume_background_result(completed, label=label)
            )
            raise
        if future in done:
            return future.result()
        future.cancel()
        future.add_done_callback(
            lambda completed: _consume_background_result(completed, label=label)
        )
        raise asyncio.TimeoutError


@dataclass(frozen=True)
class CompileCapabilities:
    exec_enabled: bool


class _CompileProvider(LLMProvider):
    """Share model-call capacity across Compile tasks."""

    def __init__(self, provider: LLMProvider, slots: asyncio.Semaphore):
        super().__init__()
        self._provider = provider
        self._slots = slots

    async def chat(self, *args: Any, **kwargs: Any) -> LLMResponse:
        """Forward a request under the shared capacity limit."""
        async with self._slots:
            return await self._provider.chat(*args, **kwargs)

    async def chat_stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[LLMStreamEvent]:
        """Hold capacity until the stream closes."""
        async with self._slots:
            async with aclosing(self._provider.chat_stream(*args, **kwargs)) as stream:
                async for event in stream:
                    yield event

    def should_inline_tool_result_media(self, model: str | None = None) -> bool:
        """Send original evidence; model capability is decided by the endpoint."""
        return True

    supports_tool_result_media = should_inline_tool_result_media

    def get_default_model(self) -> str:
        return self._provider.get_default_model()


