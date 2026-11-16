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


class _BotCompileSourcesMixin:

    def _build_compile_registry(
        self,
        request_loop: AgentLoop,
        *,
        target_uri: str,
        source_roots: Mapping[str, str],
        catalog_uris: set[str],
        wiki_uri_resolver: Callable[[str], Awaitable[bool]],
    ) -> ToolRegistry:
        """Reuse Bot reads and workspace tools; command execution follows the task policy."""
        registry = ToolRegistry(config=request_loop.config)
        for name in (*_COMPILE_CORE_TOOLS, *_COMPILE_READ_TOOLS, "spawn"):
            if name == "exec" and not self._compile_capabilities().exec_enabled:
                continue
            tool = request_loop.tools.get(name)
            if tool is not None:
                registry.register(tool)
        registry.register(
            SubmitWikiBundleTool(
                source_ids=set(source_roots),
                catalog_uris=catalog_uris,
                target_uri=target_uri,
                wiki_uri_resolver=wiki_uri_resolver,
            )
        )
        return registry

    async def _list_pipeline_source_files(
        self, client: VikingClient, request: SanitizedCompileRequest
    ) -> list[str]:
        """Select unique full-scan and added/modified inputs; listing errors propagate."""
        changes = request.changes
        if not (has_directory_plan(changes) and changes.get("head")):
            return await self._list_source_files(client, request.from_)
        files = set(await self._list_source_files(client, changes["full_dirs"], allow_empty=True))
        roots = changes["diff_dirs"]
        if roots:
            offset = 0
            while True:
                page = await client.diff_paths(
                    roots, base=changes["base"], head=changes["head"], offset=offset
                )
                for change in page["changes"]:
                    uri = str(change.get("uri") or "").rstrip("/")
                    if not uri or not any(
                        uri == root or relative_uri_path(root, uri) for root in roots
                    ):
                        raise ValueError(f"Source inventory returned an out-of-scope URI: {uri}")
                    if change["change_type"] in {"added", "modified"}:
                        files.add(uri)
                if not page["has_more"]:
                    break
                next_offset = page["next_offset"]
                if not isinstance(next_offset, int) or next_offset <= offset:
                    raise ValueError("Source inventory pagination did not advance")
                offset = next_offset
        return sorted(files)

    async def _list_source_files(
        self,
        client: VikingClient,
        roots: list[str],
        *,
        cutoff: datetime | None = None,
        allow_empty: bool = False,
    ) -> list[str]:
        """List unique sources, excluding files strictly older than the UTC cutoff.

        Unknown file times are retained; directory times never prune descendants.
        Full reprocessing allows empty roots; listing failures propagate.
        """

        async def inventory(root: str) -> list[dict[str, Any]]:
            entry = await client.stat(root)
            if not entry.get("isDir", entry.get("is_dir", False)):
                return [{**entry, "uri": root}]
            entries = []
            pending, seen = [root], {root}
            while pending:
                directory = pending.pop()
                offset = 0
                while True:
                    page = await client.list_resources(directory, node_limit=500, offset=offset)
                    for item in page:
                        uri = str(item.get("uri") or "").rstrip("/")
                        if not uri or (uri != root and not relative_uri_path(root, uri)):
                            raise ValueError(
                                f"Source inventory returned an out-of-scope URI: {uri}"
                            )
                        entries.append(item)
                        if item.get("isDir", item.get("is_dir", False)) and uri not in seen:
                            pending.append(uri)
                            seen.add(uri)
                    offset += len(page)
                    if len(page) < 500:
                        break
            return entries

        files: set[str] = set()
        for root in dict.fromkeys(roots):
            entries = await inventory(root)
            for entry in entries:
                uri = str(entry.get("uri") or "").rstrip("/")
                if not uri or (uri != root and not relative_uri_path(root, uri)):
                    raise ValueError(f"Source inventory returned an out-of-scope URI: {uri}")
                if entry.get("isDir", entry.get("is_dir", False)):
                    continue
                if cutoff is not None:
                    try:
                        if _compile_time(entry.get("modTime", entry.get("mtime"))) < cutoff:
                            continue
                    except ValueError:
                        pass
                files.add(uri)
        if not files and cutoff is None and not allow_empty:
            raise ValueError("Compile sources contain no files")
        return sorted(files)

    async def _prepare_source_batches(
        self, client: VikingClient, roots: list[str], *, files: list[str] | None = None
    ) -> list[list[CompileSourceRange]]:
        """Read selected files (or inventory roots) eight at a time; read errors propagate."""
        sources: list[tuple[str, str | CompileSourceRange]] = []
        ordered = files if files is not None else await self._list_source_files(client, roots)
        for start in range(0, len(ordered), 8):
            uris = ordered[start : start + 8]
            contents = await asyncio.gather(*(read_source(client, uri) for uri in uris))
            sources.extend(zip(uris, contents, strict=True))
        return pack_source_batches(sources, self.limits)

    def _configure_compile_subagents(
        self,
        request_loop: AgentLoop,
        registry: ToolRegistry,
        *,
        request: SanitizedCompileRequest,
        connection: dict[str, Any],
        usage: dict[str, int],
        skill_text: str,
        source_batches: list[list[CompileSourceRange]] | None = None,
    ) -> SubagentManager | None:
        """Reuse the request's spawn manager with isolated model histories and per-child drafts.

        Children use paths relative to their own draft roots in the shared task workspace.
        Only the parent submits final output; child usage is accumulated without transcripts.
        """
        spawn = registry.get("spawn")
        if spawn is None:
            return None
        manager = request_loop.subagents
        claimed_roots: set[str] = set()
        image_hashes = {
            part.uri: part.sha256
            for batch in source_batches or []
            for part in batch
            if part.image and part.sha256
        }

        async def run_child(
            child_id: str,
            assignment: str,
            session_key: SessionKey,
        ) -> dict[str, Any]:
            """Run a child in its bound directory and return its validated draft inventory."""
            draft_root = f"{COMPILE_DRAFT_ROOT}/{child_id}"
            sandbox = await request_loop.sandbox_manager.get_sandbox(session_key)
            await sandbox.execute(f"mkdir -p {shlex.quote(draft_root)}")
            system, user = self._build_prompts(
                request=request, draft_root=draft_root, skill_text=skill_text
            )
            system += (
                f"\nBudget: {self.limits.subagent_iterations} model/tool rounds, including checks and submission. "
                "Reserve rounds to check coverage and call submit_compile_draft."
            )
            saved_files = await sandbox.list_files(draft_root, max_entries=None)
            if saved_files:
                system += (
                    "\nYour draft directory contains unsubmitted work from an earlier attempt. "
                    "Reuse those files and compare relevant saved pages with the attached source ranges "
                    "to find gaps. Read a saved page before revising it; retain completed knowledge and "
                    "write only missing material or necessary repairs. Do not restart the batch from scratch. "
                    "File existence does not prove coverage or validity. Submit all retained and new pages "
                    "once the assigned coverage is complete. The inventory previews at most 100 files; "
                    "use `list_dir` to inspect further paths if needed."
                )
            user = json.dumps(
                {
                    "request": json.loads(user),
                    "assignment": assignment,
                    "existing_drafts": {
                        "file_count": len(saved_files),
                        "files": [
                            {
                                "path": posixpath.relpath(entry.path, draft_root),
                                "size_bytes": entry.size,
                            }
                            for entry in saved_files[:100]
                        ],
                    },
                },
                ensure_ascii=False,
            )
            child_tools = ToolRegistry(config=request_loop.config)
            submit_draft = SubmitCompileDraftTool(
                claimed_roots,
                draft_root,
            )
            child_tools.register(submit_draft)
            for name in _COMPILE_CORE_TOOLS:
                tool = registry.get(name)
                if tool is not None:
                    child_tools.register(
                        CompileChildTool(
                            tool,
                            draft_root,
                        )
                    )

            for name in _COMPILE_READ_TOOLS:
                tool = registry.get(name)
                if tool is not None:
                    if name == "openviking_multi_read" and image_hashes:
                        tool = CompileImageReadTool(tool, image_hashes)
                    child_tools.register(tool)

            async def require_draft_submission(context: _PlainTextContext) -> _PlainTextDelivered:
                """Retain a child's text and tool history until it writes and submits its drafts.

                Text replies remain available to the same child for completing its files;
                the existing iteration budget bounds retries without spawning another child.
                """
                messages = request_loop.context.add_assistant_message(
                    context.messages, context.text, []
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Drafts are not submitted. Reuse existing findings and files, finish the knowledge "
                            "pages, then call submit_compile_draft; a text summary does not submit files."
                        ),
                    }
                )
                return _PlainTextDelivered(messages=messages, tools_used=[])

            async def remind_submission(iteration: int) -> str | None:
                """Count remaining rounds, including the current call, and prompt timely submission."""
                remaining = self.limits.subagent_iterations - iteration + 1
                if remaining in (*_COMPILE_BUDGET_REMINDER_THRESHOLDS, 1):
                    return (
                        f"{remaining} model/tool rounds remain, including this one. Reuse saved pages and reserve time for "
                        "coverage checks and submit_compile_draft. Do not claim incomplete coverage is complete."
                    )
                return None

            _summary, _reasoning, _tools, tokens, iterations = await request_loop._run_agent_loop(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                session_key=session_key,
                publish_events=False,
                tool_registry=child_tools,
                stop_tool_names=[submit_draft.name],
                on_plain_text=require_draft_submission,
                openviking_tool_names=set(child_tools.tool_names),
                openviking_connection=connection,
                allow_final_fallback=False,
                inject_write_experience=False,
                context_compact_budget=None,
                status_note_provider=remind_submission,
                agent_id=child_id,
                max_iterations=self.limits.subagent_iterations,
            )
            usage.update(_merge_usage(usage, tokens))
            if submit_draft.result is None:
                raise ValueError(
                    f"Subagent stopped without submitting its draft files after {iterations} iterations; "
                    f"Saved files remain under {draft_root}."
                )
            return submit_draft.result

        manager.task_runner = run_child
        compile_spawn = CompileSpawnTool(spawn, source_batches)
        registry.register(compile_spawn)
        registry.register(WaitSubagentsTool(manager))

        def guard_submission(finalize: bool = False) -> str | None:
            """Require all planned sources to be dispatched and all child outcomes collected."""
            if source_batches and len(compile_spawn.dispatched_batches) < len(source_batches):
                return "Error: dispatch and collect every prepared source_batch before submitting."
            return manager.begin_submission(finalize)

        registry.get("submit_wiki_bundle").submission_guard = guard_submission
        return manager
