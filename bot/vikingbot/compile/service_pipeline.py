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


class _BotCompilePipelineMixin:

    async def _run_pipeline(
        self,
        *,
        task_id,
        request,
        client,
        sandbox,
        skill_text,
        source_files,
        usage,
        agent_runner=None,
        tool_context=None,
    ) -> bool:
        """Run the shared collection pipeline and publish through the target namespace API.

        The API/task identity, admission, cancellation and target locks are owned by
        the surrounding lifecycle. Acknowledged partial output completes with diagnostic errors.
        Return whether the workspace must remain available for audit and replay.
        The surrounding lifecycle also preserves shards on failure/cancellation.
        """
        pipeline = Pipeline(
            client=client,
            sandbox=sandbox,
            provider=_CompileProvider(self.agent_loop.provider, self._model_slots),
            model=self.agent_loop.model,
            temperature=self.agent_loop.temperature,
            limits=self.limits,
            request=request,
            skill=skill_text,
            usage=usage,
        )
        pipeline.model.agent_runner = agent_runner
        pipeline.tools = {
            name: tool
            for name in ("openviking_search", "openviking_multi_read")
            if (tool := self.agent_loop.tools.get(name)) is not None
        }
        pipeline.tool_context = tool_context

        def record_metrics(task):
            """Expose token totals and existing error summaries, without per-call counters."""
            task.meta["pipeline"] = {
                "tokens": {
                    "input": usage.get("prompt_tokens", 0),
                    "output": usage.get("completion_tokens", 0),
                    "cached": usage.get("cache_read_input_tokens", 0),
                },
                "errors": list(
                    dict.fromkeys(e[:300] for e in pipeline.failures + pipeline.warnings)
                ),
            }

        await self._set_state(task_id, status="running", stage="pipeline")
        ordered = (
            source_files
            if source_files is not None
            else await self._list_pipeline_source_files(client, request)
        )
        await pipeline.files.put("inputs", dict.fromkeys(ordered, "pending"))

        source_limits = self.limits.model_copy(
            update={"source_batch_chars": min(self.limits.source_batch_chars, 10_000)}
        )

        async def source_batches():
            """Retain at most one read batch of source bodies while seeding task shards."""
            for start in range(0, len(ordered), 8):
                uris = ordered[start : start + 8]
                contents = await asyncio.gather(
                    *(read_source(client, uri) for uri in uris),
                    return_exceptions=True,
                )
                readable = []
                for uri, content in zip(uris, contents, strict=True):
                    if isinstance(content, Exception):
                        manifest = await pipeline.files.get("inputs")
                        manifest[uri] = "failed"
                        await pipeline.files.put("inputs", manifest)
                        pipeline.failures.append(f"Source read failed: {uri}: {str(content)[:400]}")
                    elif isinstance(content, BaseException):
                        raise content
                    else:
                        readable.append((uri, content))
                for batch in pack_source_batches(readable, source_limits):
                    yield batch

        try:
            rendered = await pipeline.run(source_batches())
            # Cancellation must stop recovery before any write, including a queued cancel.
            current = await self.store.get(task_id)
            if current.status in TERMINAL_STATUSES or current.status == "cancelling":
                raise asyncio.CancelledError()
            await self._set_state(task_id, status="committing", stage="writing")
            skill_target = classify_uri(request.to).context_type == "skill"
            result = {"created": [], "updated": [], "unchanged": []}
            if skill_target and not pipeline.noop:
                result = await self._write_skill_bundle(
                    client=client, target_uri=request.to, rendered=rendered
                )
            elif rendered.operations:
                result = await client.batch_write(
                    root_uri=request.to,
                    operations=rendered.operations,
                    wait=False,
                    skip_conflicts=True,
                    edit_source="compile",
                )
            conflicts = result.get("conflicts", [])
            for conflict in conflicts:
                pipeline.warnings.append(
                    f"Target left unchanged due to conflict: {conflict['uri']}: {conflict['message']}"
                )
            published = (
                [*rendered.created, *rendered.updated, *rendered.unchanged]
                if skill_target
                else [
                    *result.get("created", []),
                    *result.get("updated", []),
                    *result.get("unchanged", []),
                    *rendered.unchanged,
                ]
            )
            await pipeline.write_coverage(published)
            summary = await pipeline.files.get("summary")
            summary["committed"] = True
            summary["warnings"] = pipeline.warnings
            summary["conflicts"] = conflicts
            await pipeline.files.put("summary", summary)
            compiled = CompileResult(
                from_=request.from_,
                to=request.to,
                skill=request.skill,
                created=result.get("created", rendered.created),
                updated=result.get("updated", rendered.updated),
                conflicts=conflicts,
                unchanged=list(
                    dict.fromkeys(
                        [
                            *([] if skill_target else rendered.unchanged),
                            *result.get("unchanged", []),
                        ]
                    )
                ),
                page_count=len(set(published)),
                link_count=rendered.link_count,
                warnings=pipeline.warnings,
            )

            def complete(task):
                if task.status not in TERMINAL_STATUSES and task.status != "cancelling":
                    record_metrics(task)
                    task.status = "completed" if published or pipeline.noop else "failed"
                    task.stage = "completed" if published or pipeline.noop else "writing"
                    task.result = compiled
                    task.error = (
                        CompileErrorInfo(
                            code="COMPILE_INCOMPLETE", message="No output was acknowledged."
                        )
                        if not published and not pipeline.noop
                        else None
                    )

            await self.store.update(task_id, complete)
            # Retain accepted artifacts and call evidence for audit and same-workspace replay.
            return True
        except OpenVikingError as exc:
            code = "WRITE_CONFLICT" if exc.code in {"CONFLICT", "ALREADY_EXISTS"} else exc.code
            stage = (
                "refreshing" if exc.code in {"REFRESH_FAILED", "DEADLINE_EXCEEDED"} else "writing"
            )
            raise CompileFailure(code, str(exc), stage=stage) from exc
        finally:
            await self.store.update(task_id, record_metrics)

    @staticmethod
    def _log_compile_usage(
        task_id: str,
        *,
        elapsed_seconds: float,
        usage: Mapping[str, Any],
    ) -> None:
        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        cached_input_tokens = int(usage.get("cache_read_input_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)
        logger.info(
            "Compile {} finished in {:.1f}s — input_tokens={} "
            "cached_input_tokens={} output_tokens={}",
            task_id,
            elapsed_seconds,
            input_tokens,
            cached_input_tokens,
            output_tokens,
        )

    async def _cleanup_execution_resources(
        self,
        *,
        sandbox_manager: SandboxManager,
        session_key: SessionKey,
        client: VikingClient | None,
        workspace_parent: Path,
        preserve_workspace: bool = False,
    ) -> None:
        async def cleanup() -> None:
            try:
                if isinstance(sandbox_manager, CompileSandboxManager):
                    await sandbox_manager.clear_credentials()
                if preserve_workspace:
                    sandbox = await sandbox_manager.get_sandbox(session_key)
                    workspace = sandbox_manager.get_workspace_path(session_key)
                    for entry in await sandbox.list_files(max_entries=None):
                        if entry.path.startswith(f"{COMPILE_STAGING_ROOT}/"):
                            # Remote sandboxes can discard files on stop; retain drafts locally.
                            path = workspace / sanitize_relative_viking_path(entry.path)
                            if sandbox.local_file_path(entry.path) == path:
                                continue
                            payload = await sandbox.read_file_bytes(entry.path)
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_bytes(payload)
                # Destructive sandbox cleanup requires a complete recovery copy.
                await sandbox_manager.cleanup_session(session_key)
            finally:
                try:
                    if client is not None:
                        await client.close()
                finally:
                    if not preserve_workspace:
                        await asyncio.to_thread(
                            shutil.rmtree,
                            workspace_parent,
                            ignore_errors=True,
                        )

        try:
            await _await_with_hard_timeout(
                cleanup(),
                timeout=self.limits.cleanup_grace_seconds,
                label="cleanup",
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Compile cleanup exceeded its {}-second grace limit",
                self.limits.cleanup_grace_seconds,
            )
        except Exception:
            logger.exception(
                "Compile cleanup failed; incomplete recovery copies retain their sandbox"
            )

    async def _materialize_skill_package(
        self,
        *,
        client: VikingClient,
        skill_result: Mapping[str, Any],
        skill_dir: Path,
        stage: str = "loading_skill",
    ) -> None:
        """Copy a Skill package and reject attachment paths outside skill_dir."""
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = str(skill_result.get("content") or "")
        (skill_dir / "SKILL.md").write_bytes(content.encode("utf-8"))

        files = skill_result.get("files") or []
        for item in files:
            if not isinstance(item, Mapping) or item.get("is_dir"):
                continue
            relative = str(item.get("path") or "")
            if relative == "SKILL.md" or Path(relative).name in _SKILL_EXCLUDED_FILES:
                continue
            try:
                relative = sanitize_relative_viking_path(relative)
                local = (skill_dir / relative).resolve()
                if skill_dir.resolve() not in local.parents:
                    raise ValueError("path escapes Skill root")
            except ValueError as exc:
                raise CompileFailure("SKILL_INVALID", str(exc), stage=stage) from exc
            data = await client.download_bytes(str(item.get("uri") or ""))
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(data)

    async def _write_skill_bundle(
        self,
        *,
        client: VikingClient,
        target_uri: str,
        rendered: RenderedBundle,
    ) -> dict[str, list[str]]:
        """Publish one validated package, retaining untouched existing attachments.

        The returned URIs identify Skill roots, as required by Compile's Skill result.
        """
        result = {"created": [], "updated": [], "unchanged": []}
        uris = [*(op["uri"] for op in rendered.operations), *rendered.unchanged]
        if not uris:
            return result
        paths = [relative_uri_path(target_uri, uri) for uri in uris]
        if any(not path or "/" not in path for path in paths):
            raise CompileFailure(
                "AGENT_OUTPUT_INVALID", "Skill files require <skill-name>/ paths", stage="rendering"
            )
        names = {sanitize_relative_viking_path(path).split("/")[0] for path in paths}
        if len(names) != 1:
            raise CompileFailure(
                "AGENT_OUTPUT_INVALID", "Compile requires one Skill package", stage="rendering"
            )
        skill_name = names.pop()
        root_uri = f"{target_uri.rstrip('/')}/{skill_name}"
        if not rendered.operations:
            result["unchanged"].append(root_uri)
            return result
        with TemporaryDirectory(prefix="openviking-compile-skill-") as temp_dir:
            temp_root = Path(temp_dir).resolve()
            skill_dir = temp_root / skill_name
            try:
                stat = await client.stat(root_uri)
                if not stat.get("isDir"):
                    raise CompileFailure(
                        "WRITE_CONFLICT",
                        f"Skill target is not a directory: {root_uri}",
                        stage="writing",
                    )
                exists = True
            except OpenVikingError as exc:
                if exc.code != "NOT_FOUND":
                    raise
                exists = False
            if exists:
                await self._materialize_skill_package(
                    client=client,
                    skill_result=await client.get_skill(skill_name, target_uri=target_uri),
                    skill_dir=skill_dir,
                    stage="writing",
                )
            for operation in rendered.operations:
                relative = sanitize_relative_viking_path(
                    relative_uri_path(target_uri, operation["uri"])
                )
                local = temp_root / relative
                if operation["mode"] == "create" and local.exists():
                    raise CompileFailure(
                        "WRITE_CONFLICT", f"Skill file changed: {operation['uri']}", stage="writing"
                    )
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_bytes(file_ops.file_bytes(operation))
            skill_md = skill_dir / "SKILL.md"
            validation = validate_skill_format(
                skill_md.read_text(encoding="utf-8") if skill_md.is_file() else "",
                strict=True,
                skill_dir_name=skill_name,
                source_path=str(skill_md),
            )
            if not validation["valid"]:
                raise CompileFailure(
                    "AGENT_OUTPUT_INVALID",
                    "; ".join(issue["message"] for issue in validation["errors"]),
                    stage="rendering",
                )
            if exists:
                published = await client.update_skill(
                    skill_name,
                    str(skill_dir),
                    target_uri=target_uri,
                    wait=True,
                )
            else:
                published = await client.add_skill(str(skill_dir), target_uri=target_uri, wait=True)
            result["updated" if exists else "created"].append(
                str(published.get("root_uri") or published.get("uri") or root_uri)
            )
            return result

    async def _read_target_page_type(
        self,
        client: VikingClient,
        uri: str,
        *,
        entry: Mapping[str, Any],
    ) -> str | None:
        prefix = await client.read_raw(
            uri,
            offset=0,
            limit=_CATALOG_FRONTMATTER_LINES,
        )
        payload = prefix.encode("utf-8")
        if has_unclosed_frontmatter(payload):
            payload = (await client.read_raw(uri)).encode("utf-8")
        return validate_declared_okf_markdown(uri, payload)
