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



class SubmitWikiBundleTool(Tool):
    """Validate Memory page submissions, source provenance and renderable page links."""

    def __init__(
        self,
        *,
        source_ids: set[str],
        catalog_uris: set[str],
        target_uri: str,
        wiki_uri_resolver: Callable[[str], Awaitable[bool]] | None = None,
    ):
        self.source_ids = source_ids
        self.catalog_uris = catalog_uris
        self.target_uri = target_uri.rstrip("/")
        self.wiki_uri_resolver = wiki_uri_resolver
        self.bundle: WikiBundleDraft | None = None
        self.submission_guard: Callable[[bool], str | None] | None = None

    @property
    def name(self) -> str:
        return "submit_wiki_bundle"

    @property
    def description(self) -> str:
        return "Submit Memory pages with source provenance and links after applying the selected Skill."

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        if "raw" in params:
            message = "use the tool schema directly; do not wrap the payload in a JSON string"
            return [message]
        return super().validate_params(params)

    @property
    def parameters(self) -> dict[str, Any]:
        schema = WikiBundleDraft.model_json_schema()
        schema["properties"].pop("files", None)
        schema.get("$defs", {}).pop("CompileFileDraft", None)
        link_def = schema.get("$defs", {}).get("WikiLink", {})
        match_schema = link_def.get("properties", {}).get("match_text")
        if isinstance(match_schema, dict):
            match_schema["description"] = (
                "Exact anchor text that must either appear in the source page draft body "
                "outside frontmatter, code, existing Markdown links, and Citations, or "
                "already be part of a Markdown link to the target page."
            )
        schema.pop("title", None)
        return schema

    @property
    def resource_inputs(self) -> dict[str, str]:
        return {
            "/pages/*/body_workspace_path": "local_file",
        }

    async def execute(
        self,
        tool_context: ToolContext,
        pages: list[dict[str, Any]] | None = None,
        files: list[dict[str, Any]] | None = None,
        links: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        del kwargs
        self.bundle = None
        if files:
            return "Error: Memory targets accept pages, not artifact files."
        if self.submission_guard is not None:
            error = self.submission_guard(False)
            if error:
                return error
        raw_links = links or []
        for index, link in enumerate(raw_links):
            if not isinstance(link, Mapping) or set(link) - _LINK_FIELDS:
                return f"Error: links[{index}] contains unknown fields."
        try:
            bundle = WikiBundleDraft.model_validate(
                {"pages": pages or [], "files": files or [], "links": raw_links}
            )
            bundle = await self._materialize_page_bodies(bundle, tool_context=tool_context)
            warnings = await self._validate_bundle(bundle)
        except (ValidationError, ValueError) as exc:
            return f"Error: Invalid Wiki bundle: {exc}"
        if self.submission_guard is not None:
            error = self.submission_guard(True)
            if error:
                return error
        self.bundle = bundle
        summary = f"Wiki bundle accepted with {len(bundle.pages)} page(s)."
        if warnings:
            summary += " Warnings: " + "; ".join(warnings)
        return summary

    async def _read_workspace_bytes(
        self,
        workspace_path: str,
        *,
        tool_context: ToolContext,
        label: str,
    ) -> bytes:
        try:
            relative = _normalize_workspace_path(workspace_path)
            if TOOL_RESULT_DIRECTORY in relative.split("/"):
                raise ValueError("Tool-result files cannot be submitted as page bodies")
            if tool_context.sandbox_manager is None:
                raise ValueError("task sandbox is unavailable")
            sandbox = await tool_context.sandbox_manager.get_sandbox(tool_context.session_key)
            return await sandbox.read_file_bytes(relative)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"{label} workspace path could not be read: {workspace_path}") from exc

    async def _materialize_page_bodies(
        self,
        bundle: WikiBundleDraft,
        *,
        tool_context: ToolContext,
    ) -> WikiBundleDraft:
        pages = []
        for page in bundle.pages:
            if page.body_workspace_path is None:
                pages.append(page)
                continue
            workspace_path = _normalize_workspace_path(page.body_workspace_path)
            raw = await self._read_workspace_bytes(
                workspace_path,
                tool_context=tool_context,
                label=f"page {page.page_id} body",
            )
            try:
                body = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"page {page.page_id} body_workspace_path must contain UTF-8 Markdown"
                ) from exc
            pages.append(
                page.model_copy(update={"body_markdown": body, "body_workspace_path": None})
            )
        return bundle.model_copy(update={"pages": pages})

    async def _validate_bundle(self, bundle: WikiBundleDraft) -> list[str]:
        if not bundle.pages and bundle.links:
            raise ValueError("empty bundle must not contain links")
        page_ids: set[int] = set()
        page_uris: dict[int, str] = {}
        final_uris: set[str] = set()
        for page in bundle.pages:
            if page.body_markdown is None:
                raise ValueError(f"page {page.page_id} body was not materialized")
            if page.page_id in page_ids:
                raise ValueError(f"duplicate page_id: {page.page_id}")
            page_ids.add(page.page_id)
            if not page.title.strip() or not page.page_type.strip() or not page.summary.strip():
                raise ValueError(f"page {page.page_id} has empty required fields")
            if "\n" in page.summary.strip() or "\r" in page.summary.strip():
                raise ValueError(f"page {page.page_id} summary must be one line")
            if page.body_markdown.lstrip().startswith("---"):
                raise ValueError(f"page {page.page_id} body must not include YAML frontmatter")
            source_ids = list(
                dict.fromkeys(source_id for source_id in page.source_ids if source_id)
            )
            if source_ids and any(source_id not in self.source_ids for source_id in source_ids):
                valid = ", ".join(sorted(self.source_ids))
                raise ValueError(
                    f"page {page.page_id} source_ids must reference supplied source roots "
                    f"(one of: {valid})"
                )
            page.source_ids = source_ids or sorted(self.source_ids)
            if page.update_uri:
                final_uri = page.update_uri.rstrip("/")
                if is_reserved_wiki_page_uri(final_uri):
                    raise ValueError(f"page {page.page_id} cannot update a reserved Wiki file")
                if not await self._is_wiki_uri(final_uri):
                    raise ValueError(
                        f"page {page.page_id} update_uri is not an existing OKF Wiki page"
                    )
                if page.path_hint:
                    raise ValueError(f"page {page.page_id} cannot rename an update")
            else:
                hint = page.path_hint or wiki_page_path_from_title(page.title)
                relative = validate_relative_page_path(hint)
                final_uri = safe_join_viking_uri(self.target_uri, relative).rstrip("/")
                if final_uri in self.catalog_uris:
                    raise ValueError(f"page {page.page_id} path exists; use its update_uri")
            if final_uri in final_uris:
                raise ValueError(f"duplicate final Wiki path: {final_uri}")
            final_uris.add(final_uri)
            page_uris[page.page_id] = final_uri

        page_by_id = {page.page_id: page for page in bundle.pages}
        link_errors: list[str] = []
        warnings: list[str] = []
        valid_links: list[Any] = []
        for index, link in enumerate(bundle.links):
            prefix = f"links[{index}]"
            if link.f is None or link.t is None:
                link_errors.append(f"{prefix} endpoints must be non-null")
                continue
            if link.f == link.t:
                link_errors.append(f"{prefix} must not be a self-link")
                continue
            if link.f not in page_ids or link.t not in page_ids:
                link_errors.append(f"{prefix} endpoints must reference bundle pages")
                continue
            if not link.match_text:
                warnings.append(f"{prefix} has no match_text and was dropped")
                continue
            source_page = page_by_id[link.f]
            if not LinkRenderer.can_render_link(
                source_page.body_markdown,
                link.match_text,
                page_uris[link.f],
                page_uris[link.t],
            ):
                warnings.append(
                    f"{prefix} anchor {link.match_text!r} was not found and the link was dropped"
                )
                continue
            valid_links.append(link)
        if link_errors:
            raise ValueError(f"{len(link_errors)} invalid link(s): " + "; ".join(link_errors))
        bundle.links = valid_links
        return warnings

    async def _is_wiki_uri(self, uri: str) -> bool:
        if not relative_uri_path(self.target_uri, validate_safe_viking_uri_path(uri)):
            return False
        if uri in self.catalog_uris:
            return True
        if self.wiki_uri_resolver is None:
            return False
        if await self.wiki_uri_resolver(uri):
            self.catalog_uris.add(uri)
            return True
        return False


__all__ = [
    "SubmitWikiBundleTool",
]
