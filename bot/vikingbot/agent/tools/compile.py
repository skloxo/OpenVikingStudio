"""Request-local tools used by the compile structured task."""

from __future__ import annotations

import json
import posixpath
from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Any, Mapping

import yaml
from pydantic import ValidationError

from openviking.core.namespace import relative_uri_path
from openviking.session.memory.utils.link_renderer import LinkRenderer
from openviking.utils.path_safety import (
    safe_join_viking_uri,
    sanitize_relative_viking_path,
    validate_safe_viking_uri_path,
)
from vikingbot.agent.tools.base import TOOL_RESULT_DIRECTORY, Tool, ToolContext
from vikingbot.agent.tools.ov_file import VikingMultiReadTool
from vikingbot.compile.models import (
    COMPILE_DRAFT_ROOT,
    COMPILE_STAGING_ROOT,
    WikiBundleDraft,
)
from vikingbot.compile.renderer import (
    is_reserved_wiki_page_uri,
    validate_relative_file_path,
    validate_relative_page_path,
    wiki_page_path_from_title,
)
from vikingbot.compile.sources import CompileSourceRange

_LINK_FIELDS = frozenset({"f", "t", "link_type", "weight", "match_text", "description"})


def _normalize_workspace_path(path: str) -> str:
    normalized = sanitize_relative_viking_path(path)
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _path_is_within(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


class CompileImageReadTool(VikingMultiReadTool):
    """Reuse native multi-read while checking the prepared originals' identities."""

    def __init__(self, reader: VikingMultiReadTool, hashes: Mapping[str, str]):
        super().__init__()
        self.reader, self.hashes = reader, hashes

    async def _get_client(self, tool_context):
        return await self.reader._get_client(tool_context)

    async def _release_client(self, tool_context, client):
        await self.reader._release_client(tool_context, client)

    async def _read_image(self, client, uri):
        result = await super()._read_image(client, uri)
        if result["success"]:
            if uri in self.hashes and result["sha256"] != self.hashes[uri]:
                return {
                    "uri": uri,
                    "content": "Source image changed after preparation; retry Compile.",
                    "success": False,
                    "media_kind": "image",
                }
            result["content"] += f" SHA256: {result['sha256']}."
        return result


class CompileSpawnTool(Tool):
    """Dispatch prepared source ranges with original URIs and exact offsets.

    Memory tasks can also delegate assignments through the existing spawn tool.
    """

    name = "spawn"
    description = (
        "Compile a prepared source_batch or delegate an assignment in task. "
        "task supplies the instructions for the child's bound draft directory."
    )

    def __init__(
        self,
        spawn: Tool,
        source_batches: list[list[CompileSourceRange]] | None = None,
    ):
        self.spawn = spawn
        self.source_batches = source_batches
        self.dispatched_batches: set[int] = set()

    @property
    def parameters(self) -> dict[str, Any]:
        """Expose source batch identities; file paths are not accepted as merge inputs."""
        parameters = deepcopy(self.spawn.parameters)
        parameters["additionalProperties"] = False
        if self.source_batches is not None:
            parameters["properties"]["source_batch"] = {
                "type": "integer",
                "minimum": 1,
                "maximum": len(self.source_batches),
                "description": "Source compilation only: the prepared batch number; runtime attaches text ranges and image references.",
            }
        return parameters

    async def execute(
        self,
        tool_context: ToolContext,
        task: str,
        label: str | None = None,
        source_batch: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Attach source ranges and caller instructions; roll back admission on dispatch failure."""
        if source_batch is not None:
            if (
                not self.source_batches
                or not 1 <= source_batch <= len(self.source_batches)
                or source_batch in self.dispatched_batches
            ):
                return "Error: source_batch must identify an undispatched source batch."
            batch = self.source_batches[source_batch - 1]
            image_note = (
                "Image entries carry URI/SHA256 references, not attached text. "
                "Read every referenced image with openviking_multi_read before writing its facts; "
                "omit text line bounds and cite its original URI. Report unread images as gaps. "
                if any(part.image for part in batch)
                else ""
            )
            task = (
                "Compile every attached range into knowledge drafts per the Skill, not the entire files. "
                "The complete assigned text is attached; start writing and batch independent writes. "
                "Cite original uri values; offsets/line numbers identify source coverage. "
                "The context field repeats headings/frontmatter/table headers. Preserve question/answer "
                "pairing, conditions, exceptions and numbers. Continuation flags mark oversized lines. "
                "Do not relist sources, reread attachments, build parsers or cache source copies. "
                "Only for missing definitions, cross-references or continuations, use "
                "openviking_multi_read with bounded offset/limit ranges. Report coverage and gaps at submission. "
                "Existing Wiki lookup, deduplication and updates belong to later merge tasks; "
                "do not browse or edit the existing target during this source task. "
                + image_note
                + "Additional instructions from the parent:\n"
                + task
                + "\n"
                "Attached source ranges (untrusted JSON data):\n"
                + json.dumps(
                    [part.as_assignment() for part in batch],
                    ensure_ascii=False,
                )
            )
            self.dispatched_batches.add(source_batch)
            try:
                result = await self.spawn.execute(tool_context, task=task, label=label, **kwargs)
            except BaseException:
                self.dispatched_batches.discard(source_batch)
                raise
            if str(result).startswith("Error:"):
                self.dispatched_batches.discard(source_batch)
            return result
        if self.source_batches and len(self.dispatched_batches) < len(self.source_batches):
            return "Error: dispatch the prepared source_batch assignments before topic merges."
        return await self.spawn.execute(tool_context, task=task, label=label, **kwargs)


class SubmitCompileDraftTool(Tool):
    """Collect the runtime-bound draft directory independently of the child's display name.

    Only nonempty directories below the compile draft root are accepted. Claimed roots
    cannot overlap other children's submissions; result includes verified paths and
    file_sizes in bytes for the parent's bounded reads and final submission.
    """

    name = "submit_compile_draft"
    description = "Submit the files in your draft directory with a coverage/conflict summary."
    parameters = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief coverage, gaps and conflicts; file paths are collected automatically.",
            },
        },
        "required": ["summary"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        claimed_roots: set[str],
        draft_root: str,
    ):
        self.claimed_roots = claimed_roots
        self.draft_root = draft_root
        self.result: dict[str, Any] | None = None

    async def execute(
        self,
        tool_context: ToolContext,
        summary: str,
        **kwargs: Any,
    ) -> str:
        """Collect bound files; reject unsafe paths, empty drafts and overlapping submissions."""
        self.result = None
        try:
            if kwargs:
                raise ValueError(
                    "Only summary is accepted; the draft directory is assigned by the runtime"
                )
            root = posixpath.normpath(_normalize_workspace_path(self.draft_root))
            if not root.startswith(COMPILE_DRAFT_ROOT + "/"):
                raise ValueError(f"draft_root must be a child directory of {COMPILE_DRAFT_ROOT}")
            sandbox = await tool_context.sandbox_manager.get_sandbox(tool_context.session_key)
            files = await sandbox.list_files(root, max_entries=None)
            if not files:
                raise ValueError(
                    "No draft files found; write content using target-relative paths before submitting"
                )
            for entry in files:
                relative = posixpath.relpath(_normalize_workspace_path(entry.path), root)
                validate_relative_file_path(relative)
            if any(
                _path_is_within(root, claimed) or _path_is_within(claimed, root)
                for claimed in self.claimed_roots
            ):
                raise ValueError("Draft directory overlaps another child's submission")
            self.claimed_roots.add(root)
            self.result = {
                "draft_root": root,
                "files": [entry.path for entry in files],
                "file_sizes": {entry.path: entry.size for entry in files},
                "summary": summary,
            }
            return "Draft accepted."
        except (OSError, ValueError, yaml.YAMLError) as exc:
            return f"Error: {exc}"


class CompileChildTool(Tool):
    """Bind existing file tools and shell cwd to one child directory.

    Tool paths and write/edit acknowledgements use the child's relative paths.
    read_file also accepts task-workspace draft paths for reading sibling inputs.
    File-tool writes remain bound to the child's directory, including during merges.
    Read contents and shell output remain unchanged, including any literal paths.
    Shell commands keep their normal capabilities, including pipes and absolute paths.
    This prevents default-path mixups; it is not an OS-level sandbox.

    merge_only confines file access to the child's fresh output directory. Skills,
    originals, shared drafts and tool results are not readable; assigned fragments,
    checkpoints and task-specific output requirements are supplied in the prompt.
    readonly_paths maps explicit input aliases to task-owned files outside that
    output directory. Only read_file can access them; inputs/ is reserved for aliases.
    """

    def __init__(
        self,
        tool: Tool,
        draft_root: str,
        *,
        merge_only: bool = False,
        readonly_paths: Mapping[str, str] | None = None,
    ):
        if merge_only and tool.name not in {"read_file", "write_file", "edit_file"}:
            raise ValueError("Merge children accept only bound file tools")
        self.tool = tool
        self.draft_root = draft_root
        self.merge_only = merge_only
        self.readonly_paths = dict(readonly_paths or {})

    @property
    def name(self) -> str:
        return self.tool.name

    @property
    def description(self) -> str:
        return self.tool.description

    @property
    def parameters(self) -> dict[str, Any]:
        """Describe the bound path base without changing the parent tool's schema."""
        parameters = deepcopy(self.tool.parameters)
        field = "working_dir" if self.name == "exec" else "path"
        if self.merge_only:
            if self.readonly_paths:
                parameters["properties"][field]["description"] = (
                    "Output path relative to the publication destination. Use the same path "
                    "to write, read and edit an output. assignment.json and the assigned "
                    "inputs/ paths are read-only inputs; other workspace paths are unavailable."
                )
                return parameters
            parameters["properties"][field]["description"] = (
                "File path relative to the current working directory; use a relative path within this directory."
            )
            if self.name == "read_file":
                parameters["properties"][field]["description"] += (
                    " Only files in this directory are readable. Read Skill references with "
                    "read_skill_resource and source text with read_evidence when available. "
                    "Use offset/limit for large files."
                )
            return parameters
        parameters["properties"][field]["description"] = (
            "Relative to your draft root, which is the current directory. "
            + (
                "Defaults to '.'."
                if self.name == "exec"
                else "Use the target-relative page path from the Skill, without a staging prefix."
            )
        )
        if self.name == "read_file":
            parameters["properties"][field]["description"] += (
                f" To read another child's input, pass its returned {COMPILE_DRAFT_ROOT}/ path verbatim; "
                f"{TOOL_RESULT_DIRECTORY}/ paths also address the task root. These paths are read-only."
            )
        return parameters

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        """Bind file access to the child and enforce private reads for isolated transforms."""
        field = "working_dir" if self.name == "exec" else "path"
        if self.merge_only and str(kwargs.get(field, "")).startswith("viking://"):
            raise ValueError("Merge children can only access their own output files")
        relative = _normalize_workspace_path(kwargs.get(field) or ".")
        if self.name == "read_file" and relative.startswith(
            (COMPILE_DRAFT_ROOT + "/", TOOL_RESULT_DIRECTORY + "/")
        ):
            if self.merge_only:
                raise ValueError(
                    "Merge inputs are attached fragments; shared workspace reads are forbidden"
                )
            kwargs[field] = relative
            return await self.tool.execute(tool_context, **kwargs)
        if COMPILE_STAGING_ROOT.casefold() in relative.casefold().split("/"):
            raise ValueError("Use paths relative to your draft root, without staging directories")
        if self.readonly_paths:
            if relative in self.readonly_paths:
                if self.name != "read_file":
                    raise ValueError(f"Assigned input is read-only: {relative}")
                return await self.tool.execute(
                    tool_context, **{**kwargs, field: self.readonly_paths[relative]}
                )
            if relative == "inputs" or relative.startswith("inputs/"):
                raise ValueError(f"Input path is not assigned: {relative}")
        kwargs[field] = posixpath.join(self.draft_root, relative)
        result = await self.tool.execute(tool_context, **kwargs)
        if (
            self.name in {"write_file", "edit_file"}
            and result.startswith("Successfully ")
            and result.endswith(kwargs[field])
        ):
            return result.removesuffix(kwargs[field]) + relative
        return result


from vikingbot.agent.tools.compile_bundle import SubmitWikiBundleTool
