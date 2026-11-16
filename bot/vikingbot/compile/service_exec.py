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


class _BotCompileExecMixin:

    async def _execute_task(
        self,
        task_id: str,
        request: SanitizedCompileRequest,
        connection: dict[str, Any],
    ) -> None:
        snapshot = (request.changes or {}).get("skill_snapshot")
        if snapshot is not None:
            if not isinstance(snapshot, dict) or snapshot.get("uri") != request.skill:
                raise CompileFailure(
                    "SKILL_INVALID", "Invalid Compile Skill snapshot", stage="agent"
                )
            # Task-local connection follows existing parent, child and tool client propagation.
            connection = {**connection, "skill_snapshot": snapshot}
        target_type = classify_uri(request.to).context_type
        session_key = SessionKey(type="compile", channel_id=task_id, chat_id=task_id)
        task_config = self.config.model_copy(
            update={
                "skills": [],
                "sandbox": self.config.sandbox.model_copy(deep=True),
            }
        )
        task_config.sandbox.mode = SandboxMode.PER_SESSION
        if target_type in {"resource", "skill"}:
            task_config.agents = task_config.agents.model_copy(
                update={"subagent_max_concurrency": self.limits.source_concurrency}
            )
        workspace_parent = self.config.bot_data_path / "compile_workspaces" / task_id
        if task_config.uses_managed_opensandbox:
            workspace_parent = task_config.opensandbox_workspaces_path / "compile" / task_id
        sandbox_manager = CompileSandboxManager(
            task_config, workspace_parent, task_config.workspace_path, connection=connection
        )
        workspace = sandbox_manager.get_workspace_path(session_key)
        client: VikingClient | None = None
        sandbox: WorkspaceSandbox | None = None
        submit_tool: Any = None
        compile_started_at = time.monotonic()
        agent_usage: dict[str, int] = {}
        child_usage: dict[str, int] = {}
        subagents: SubagentManager | None = None
        preserve_workspace = False
        renewal_task = None
        try:
            await self._set_state(task_id, status="running", stage="collecting_context")
            client = await VikingClient.create(connection=connection, config=self.config)
            simple_mode = (await self.store.get(task_id)).meta["mode"] == "simple"
            if simple_mode and target_type == "skill":
                raise CompileFailure(
                    "INVALID_ARGUMENT",
                    "Publishing a Skill package requires bot.compile.mode=complex.",
                    stage="agent",
                )
            source_files = None
            source_request = request
            execution = (request.changes or {}).get("execution") or {}
            full_execution = execution.get("mode") == "full" or (
                not execution and request.instruction_provided
            )
            directory_plan = has_directory_plan(request.changes)
            if directory_plan and request.changes.get("head"):
                pass
            elif full_execution and not simple_mode:
                source_files = await self._list_source_files(
                    client, request.from_, allow_empty=True
                )
                source_request = request.model_copy(update={"last_compile_time": None})
            elif not full_execution and request.last_compile_time is not None:
                source_files = await self._list_source_files(
                    client, request.from_, cutoff=request.last_compile_time
                )
            if source_files is not None:
                if not full_execution and not source_files and request.changes is None:

                    def complete_without_sources(task: CompileTask) -> None:
                        """Finish an incremental no-op without model calls or target writes."""
                        if task.status == "cancelling":
                            return
                        task.status = task.stage = "completed"
                        task.error = None
                        task.result = CompileResult(
                            from_=request.from_, to=request.to, skill=request.skill
                        )

                    await self.store.update(task_id, complete_without_sources)
                    return
                source_request = source_request.model_copy(update={"from_": source_files})
            skill_text = await client.read_raw(f"{request.skill}/SKILL.md")
            if not skill_text.strip():
                raise ValueError("Compile Skill is empty")
            # An empty task workspace prevents bootstrap files from becoming outputs.
            workspace.mkdir(parents=True, exist_ok=True)
            sandbox = await sandbox_manager.get_sandbox(session_key)
            if task_config.sandbox.backend == SandboxBackend.OPENSANDBOX:
                interval = task_config.sandbox.backends.opensandbox.runtime.timeout / 3
                renewal_task = asyncio.create_task(
                    _renew_compile_sandbox(
                        sandbox,
                        interval,
                        asyncio.current_task(),
                        fail_task=lambda failure: self._fail(task_id, failure),
                    )
                )
            if simple_mode:
                await self._set_state(task_id, status="running", stage="agent")
                loop = AgentLoop(
                    bus=self.agent_loop.bus,
                    provider=_CompileProvider(self.agent_loop.provider, self._model_slots),
                    workspace=workspace,
                    model=self.agent_loop.model,
                    temperature=self.agent_loop.temperature,
                    max_iterations=self.limits.simple_agent_iterations,
                    sandbox_manager=sandbox_manager,
                    config=task_config,
                )

                async def save_progress(writer):
                    """Persist acknowledged and in-flight target URIs across cancellation or restart."""

                    def record(task):
                        task.meta["outputs"] = dict(writer.outcomes)
                        task.meta["unconfirmed"] = sorted(writer.unconfirmed)

                    await self.store.update(task_id, record)

                result = await simple.run(
                    loop,
                    client,
                    request,
                    source_request.from_,
                    skill_text,
                    session_key,
                    connection,
                    save_progress,
                    agent_usage,
                )

                def finish(task):
                    if task.status == "running":
                        task.status = task.stage = "completed"
                        task.result = result

                await self.store.update(task_id, finish)
                return
            if target_type in {"resource", "skill"} or directory_plan:
                focused_loop = None

                async def run_focused_agent(*args, **kwargs):
                    """Create the shared child-loop context only for required complex transforms."""
                    nonlocal focused_loop
                    if focused_loop is None:
                        focused_loop = AgentLoop(
                            bus=self.agent_loop.bus,
                            provider=_CompileProvider(self.agent_loop.provider, self._model_slots),
                            workspace=workspace,
                            model=self.agent_loop.model,
                            temperature=self.agent_loop.temperature,
                            sandbox_manager=sandbox_manager,
                            config=task_config,
                        )
                    return await pipeline_agent_runner(
                        focused_loop, session_key, connection, self.limits
                    )(*args, **kwargs)

                preserve_workspace = await self._run_pipeline(
                    task_id=task_id,
                    request=request,
                    client=client,
                    sandbox=sandbox,
                    skill_text=skill_text,
                    source_files=source_files,
                    usage=agent_usage,
                    agent_runner=run_focused_agent,
                    tool_context=ToolContext(
                        session_key=session_key, openviking_connection=connection
                    ),
                )
                return
            source_roots = {
                f"src_{index}": uri for index, uri in enumerate(source_request.from_, start=1)
            }
            catalog_uris: set[str] = set()

            async def resolve_wiki_uri(uri: str) -> bool:
                """Validate an explicitly submitted target page without preloading a catalog."""
                if not relative_uri_path(request.to, uri) or not uri.casefold().endswith(".md"):
                    return False
                try:
                    entry = await client.stat(uri)
                    return await self._read_target_page_type(client, uri, entry=entry) is not None
                except OpenVikingError as exc:
                    if exc.code == "NOT_FOUND":
                        return False
                    raise

            request_loop = AgentLoop(
                bus=self.agent_loop.bus,
                provider=_CompileProvider(self.agent_loop.provider, self._model_slots),
                workspace=workspace,
                model=self.agent_loop.model,
                temperature=self.agent_loop.temperature,
                max_iterations=self.limits.agent_iterations,
                memory_window=self.agent_loop.memory_window,
                brave_api_key=self.agent_loop.brave_api_key,
                exa_api_key=self.agent_loop.exa_api_key,
                gen_image_model=self.agent_loop.gen_image_model,
                exec_config=self.agent_loop.exec_config,
                sandbox_manager=sandbox_manager,
                config=task_config,
            )
            registry = self._build_compile_registry(
                request_loop,
                target_uri=request.to,
                source_roots=source_roots,
                catalog_uris=catalog_uris,
                wiki_uri_resolver=resolve_wiki_uri,
            )
            submit_tool = registry.get("submit_wiki_bundle")
            source_batches = (
                await self._prepare_source_batches(client, request.from_, files=source_files)
                if registry.get("spawn") is not None
                else None
            )
            subagents = self._configure_compile_subagents(
                request_loop,
                registry,
                request=source_request,
                connection=connection,
                usage=child_usage,
                skill_text=skill_text,
                source_batches=source_batches,
            )
            system_prompt, user_prompt = self._build_prompts(
                request=source_request,
                subagent_max_concurrency=(
                    task_config.agents.subagent_max_concurrency if subagents is not None else 0
                ),
                skill_text=skill_text,
                source_batches=source_batches,
            )
            await self._set_state(task_id, status="running", stage="agent")
            try:
                bundle, _tools, usage, _iterations = await request_loop.run_structured_task(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    session_key=session_key,
                    tool_registry=registry,
                    openviking_tool_names=set(registry.tool_names),
                    stop_tool_names=["submit_wiki_bundle"],
                    openviking_connection=connection,
                    context_compact_budget=None,
                    budget_reminder_thresholds=_COMPILE_BUDGET_REMINDER_THRESHOLDS,
                )
                agent_usage = _merge_usage(agent_usage, usage or {})
            except AgentIterationLimitExceeded as exc:
                agent_usage = _merge_usage(agent_usage, getattr(exc, "usage", None) or {})
                if subagents is not None:
                    await subagents.cancel_all()
                raise CompileFailure("AGENT_OUTPUT_INVALID", str(exc), stage="agent") from exc
            except ValueError as exc:
                raise CompileFailure("AGENT_OUTPUT_INVALID", str(exc), stage="agent") from exc

            await self._set_state(task_id, status="running", stage="rendering")
            existing_raw: dict[str, str] = {}
            for page in bundle.pages:
                if page.update_uri and page.update_uri not in existing_raw:
                    existing_raw[page.update_uri] = await client.read_raw(page.update_uri)
            try:
                rendered = self.renderer.render(
                    bundle=bundle,
                    target_uri=request.to,
                    source_roots=source_roots,
                    catalog_uris=catalog_uris,
                    existing_raw=existing_raw,
                )
            except ValueError as exc:
                raise CompileFailure("AGENT_OUTPUT_INVALID", str(exc), stage="rendering") from exc
            page_count = len(bundle.pages)
            output_file_count = len(bundle.pages)

            batch_result: dict[str, Any] = {"created": [], "updated": [], "unchanged": []}
            if rendered.operations:
                try:
                    await self._set_state(
                        task_id,
                        status="committing",
                        stage="writing",
                    )
                    batch_result = await client.batch_write(
                        root_uri=request.to,
                        operations=rendered.operations,
                        wait=False,
                        edit_source="compile",
                    )
                except OpenVikingError as exc:
                    if exc.code == "CONFLICT":
                        code = "WRITE_CONFLICT"
                        stage = "writing"
                    else:
                        code = "WRITE_FAILED"
                        stage = "writing"
                    raise CompileFailure(code, str(exc), stage=stage) from exc

            created = list(dict.fromkeys(batch_result.get("created", rendered.created)))
            updated = list(dict.fromkeys(batch_result.get("updated", rendered.updated)))
            unchanged = list(
                dict.fromkeys([*rendered.unchanged, *batch_result.get("unchanged", [])])
            )
            warnings = list(getattr(submit_tool, "warnings", []))
            warnings.extend(getattr(registry.get("wait_subagents"), "failures", []))
            preserve_workspace = preserve_workspace or bool(warnings)
            if output_file_count == 0:
                warnings.append("No reliable output was produced from the supplied materials.")
            result = CompileResult(
                **{
                    "from": request.from_,
                    "to": request.to,
                    "skill": request.skill,
                    "created": created,
                    "updated": updated,
                    "unchanged": unchanged,
                    "page_count": page_count,
                    "link_count": rendered.link_count,
                    "warnings": warnings,
                }
            )

            def complete(task: CompileTask) -> None:
                if task.status in TERMINAL_STATUSES or task.status == "cancelling":
                    return
                task.status = "completed"
                task.stage = "completed"
                task.result = result
                task.error = None

            await self.store.update(task_id, complete)
        except BaseException as exc:
            # Source and merge evidence must survive failed or cancelled pipeline execution.
            preserve_workspace = preserve_workspace or target_type in {"resource", "skill"}
            if (
                isinstance(exc, asyncio.CancelledError)
                and renewal_task is not None
                and renewal_task.done()
            ):
                renewal_task.result()
            raise
        finally:
            if renewal_task is not None:
                renewal_task.cancel()
                await asyncio.gather(renewal_task, return_exceptions=True)
            if subagents is not None:
                await subagents.cancel_all()
            agent_usage = _merge_usage(agent_usage, child_usage)
            await self._record_usage(task_id, agent_usage)
            self._log_compile_usage(
                task_id,
                elapsed_seconds=time.monotonic() - compile_started_at,
                usage=agent_usage,
            )
            await self._cleanup_execution_resources(
                sandbox_manager=sandbox_manager,
                session_key=session_key,
                client=client,
                workspace_parent=workspace_parent,
                preserve_workspace=preserve_workspace,
            )
