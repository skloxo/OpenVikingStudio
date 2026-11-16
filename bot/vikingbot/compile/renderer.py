"""Deterministic OKF Wiki rendering for compile bundles."""

from __future__ import annotations

import base64
import posixpath
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

import yaml

from openviking.core.namespace import context_type_for_uri, relative_uri_path
from openviking.session.memory.dataclass import MemoryFile, StoredLink
from openviking.session.memory.utils.link_renderer import LinkRenderer, MarkdownLink
from openviking.session.memory.utils.link_resolver import resolve_wiki_links
from openviking.session.memory.utils.memory_file_utils import (
    MemoryFileUtils,
    next_memory_version,
)
from openviking.session.memory.utils.resource_refs import sync_memory_resource_refs
from openviking.utils.path_safety import (
    safe_join_viking_uri,
    sanitize_relative_viking_path,
    validate_safe_viking_uri_path,
)
from openviking_cli.utils import VikingURI
from vikingbot.compile.models import (
    COMPILE_STAGING_ROOT,
    WikiBundleDraft,
    WikiLanguage,
)

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_FRONTMATTER_START_RE = re.compile(rb"\A---[ \t]*\r?\n")
_FRONTMATTER_END_RE = re.compile(rb"\r?\n---[ \t]*(?:\r?\n|\Z)")
_OKF_TYPE_DECLARATION_RE = re.compile(rb"""(?m)^(?:type|["']type["'])[ \t]*:""")
_BARE_VIKING_URI_RE = re.compile(r"""viking://[^\s<>\[\](){}"'«»，。；：！？]+""")
_LEADING_H1_RE = re.compile(r"\A(?:[ \t]*\r?\n)*#[ \t]+[^\r\n]*(?:\r?\n|\Z)")
_LEGACY_RELATED_PAGES_RE = re.compile(
    r"(?mi)^##[ \t]+(?:Related pages|相关页面)[ \t]*\r?\n"
    r"(?:[ \t]*\r?\n)*(?:[ \t]*-[^\r\n]*(?:\r?\n|\Z))+"
)
_RESERVED_FILENAMES = frozenset({".abstract.md", ".overview.md", ".relations.json", ".source.json"})
_PLATFORM_FRONTMATTER_FIELDS = frozenset({"type", "title", "description", "tags"})


from vikingbot.compile.renderer_helpers import (
    RenderedBundle, _body_markdown_links, _citation_target_allowed, _frontmatter,
    _has_link_to, _link_uri, _link_wiki_mentions, _linkify_source_uris,
    _merge_stored_links, _normalize_tags, _render_source_fallback,
    _split_frontmatter, _strip_legacy_related_pages, _wiki_mention_targets,
    _wiki_page_basename, has_unclosed_frontmatter, is_reserved_wiki_page_uri,
    strip_okf_frontmatter, validate_declared_okf_markdown,
    validate_relative_file_path, validate_relative_page_path,
    wiki_page_path_from_title,
)

class WikiRenderer:
    """Validate and render complete Wiki bundles without count or byte quotas."""

    def render(
        self,
        *,
        bundle: WikiBundleDraft,
        target_uri: str,
        source_roots: Mapping[str, str],
        catalog_uris: set[str],
        existing_raw: Mapping[str, str],
        wiki_language: WikiLanguage | None = None,
        file_catalog_uris: set[str] | None = None,
        existing_bytes: Mapping[str, bytes] | None = None,
        file_payloads: list[bytes | None] | None = None,
    ) -> RenderedBundle:
        file_catalog_uris = set(catalog_uris) | set(file_catalog_uris or ())
        existing_bytes = existing_bytes or {}
        file_payloads = file_payloads or []
        if not bundle.pages and bundle.links:
            raise ValueError("an empty Wiki bundle cannot contain links")
        target_type = context_type_for_uri(target_uri)
        memory_target = target_type == "memory"
        if memory_target and bundle.files:
            raise ValueError("raw artifact files are only supported for Resource targets")

        page_ids: set[int] = set()
        page_uris: dict[int, list[str]] = {}
        page_by_id = {}
        output_uris: set[str] = set()
        for page in bundle.pages:
            if page.page_id in page_ids:
                raise ValueError(f"duplicate page_id: {page.page_id}")
            page_ids.add(page.page_id)
            page_by_id[page.page_id] = page
            title = page.title.strip()
            page_type = page.page_type.strip()
            summary = page.summary.strip()
            if not title or not page_type or not summary:
                raise ValueError(f"page {page.page_id} title, page_type and summary are required")
            if "\n" in summary or "\r" in summary:
                raise ValueError(f"page {page.page_id} summary must be a single line")
            if _FRONTMATTER_RE.match(page.body_markdown.lstrip()):
                raise ValueError(f"page {page.page_id} body_markdown must not contain frontmatter")
            source_ids = list(
                dict.fromkeys(value.strip() for value in page.source_ids if value.strip())
            )
            if not source_ids or any(source_id not in source_roots for source_id in source_ids):
                raise ValueError(f"page {page.page_id} must reference valid source_ids")

            if page.update_uri:
                uri = page.update_uri.rstrip("/")
                if is_reserved_wiki_page_uri(uri):
                    raise ValueError(f"reserved Wiki page cannot be updated: {uri}")
                if uri not in catalog_uris:
                    raise ValueError(f"update_uri is not in the target catalog: {uri}")
                if page.path_hint:
                    raise ValueError("path_hint is not allowed with update_uri")
                if uri not in existing_raw:
                    raise ValueError(f"raw content was not loaded for update_uri: {uri}")
            else:
                hint = page.path_hint or wiki_page_path_from_title(title)
                relative = validate_relative_page_path(hint)
                uri = safe_join_viking_uri(target_uri, relative).rstrip("/")
                if uri in file_catalog_uris:
                    raise ValueError(f"Wiki page already exists; use update_uri: {uri}")
            if uri in output_uris:
                raise ValueError(f"duplicate final Wiki path: {uri}")
            output_uris.add(uri)
            page_uris[page.page_id] = [uri]

        file_uris: list[str] = []
        for index, file in enumerate(bundle.files):
            if file.update_uri:
                uri = validate_safe_viking_uri_path(file.update_uri).rstrip("/")
                if is_reserved_wiki_page_uri(uri):
                    raise ValueError(f"reserved output file cannot be updated: {uri}")
                if uri not in file_catalog_uris:
                    raise ValueError(f"file update_uri is not in the target catalog: {uri}")
                if uri not in existing_bytes:
                    raise ValueError(f"raw bytes were not loaded for file update_uri: {uri}")
            else:
                relative = validate_relative_file_path(file.path or "")
                uri = safe_join_viking_uri(target_uri, relative).rstrip("/")
                if uri in file_catalog_uris:
                    raise ValueError(f"output file already exists; use update_uri: {uri}")
            if uri in output_uris:
                raise ValueError(f"duplicate final output path: {uri}")
            output_uris.add(uri)
            file_uris.append(uri)

            if file.workspace_path is not None and (
                index >= len(file_payloads) or file_payloads[index] is None
            ):
                raise ValueError(f"workspace payload was not loaded for file {index}")

        for link in bundle.links:
            if link.f is None or link.t is None or link.f == link.t:
                raise ValueError("WikiLink endpoints must be non-null and non-self")
            source_page = page_by_id.get(link.f)
            if source_page is None or link.t not in page_by_id:
                raise ValueError(f"WikiLink references an unknown page_id: f={link.f}, t={link.t}")
            if not link.match_text:
                raise ValueError("WikiLink match_text is required")
            if not LinkRenderer.can_render_link(
                source_page.body_markdown,
                link.match_text,
                page_uris[link.f][0],
                page_uris[link.t][0],
            ):
                raise ValueError(
                    f"WikiLink match_text is not a satisfiable body anchor: {link.match_text!r}"
                )

        resolved_links = resolve_wiki_links(bundle.links, page_uris, strict=True)
        mention_targets = (
            _wiki_mention_targets(set(existing_raw) | {uris[0] for uris in page_uris.values()})
            if not memory_target and bundle.pages
            else {}
        )
        result = RenderedBundle()
        for page in bundle.pages:
            uri = page_uris[page.page_id][0]
            result.wiki_uris.append(uri)
            is_update = page.update_uri is not None
            old_raw = existing_raw.get(uri, "")
            if memory_target and is_update:
                old_memory = MemoryFileUtils.read(old_raw, uri=uri)
                old_visible = old_memory.content
            else:
                old_memory = None
                old_visible = old_raw
            old_frontmatter, _ = _split_frontmatter(old_visible)

            outgoing = (
                [link for link in resolved_links if link.from_uri == uri] if memory_target else []
            )
            incoming = (
                [link for link in resolved_links if link.to_uri == uri] if memory_target else []
            )
            if memory_target:
                rendered_body, rendered_count = LinkRenderer.render_links_with_count(
                    page.body_markdown.strip(),
                    uri,
                    [link.model_dump() for link in outgoing],
                )
            else:
                rendered_body = page.body_markdown.strip()
                rendered_count = 0
            result.link_count += rendered_count
            rendered_body = _linkify_source_uris(rendered_body, source_roots)
            source_ids = list(
                dict.fromkeys(value.strip() for value in page.source_ids if value.strip())
            )
            rendered_body = _render_source_fallback(
                rendered_body,
                source_ids=source_ids,
                source_roots=source_roots,
                wiki_language=wiki_language,
            )
            visible = (
                _frontmatter(
                    old=old_frontmatter,
                    page_type=page.page_type.strip(),
                    title=page.title.strip(),
                    summary=page.summary.strip(),
                    tags=page.tags,
                )
                + rendered_body
            )

            if not memory_target:
                visible, automatic_count = _link_wiki_mentions(
                    visible,
                    source_uri=uri,
                    targets=mention_targets,
                )
                result.link_count += automatic_count

            if memory_target:
                mf = old_memory or MemoryFile(uri=uri)
                mf.uri = uri
                mf.content = visible
                mf.extra_fields["category"] = page.page_type.strip()
                mf.extra_fields["version"] = (
                    int(mf.extra_fields.get("version", 1) or 1) if old_memory else 1
                )
                mf.links = _merge_stored_links(mf.links, outgoing)
                mf.backlinks = _merge_stored_links(mf.backlinks, incoming)
                sync_memory_resource_refs(mf, source="compile")
                candidate = MemoryFileUtils.write(mf, render_links=False)
                if old_memory is not None and candidate != old_raw:
                    mf.extra_fields["version"] = next_memory_version(old_memory)
                    candidate = MemoryFileUtils.write(mf, render_links=False)
            else:
                candidate = visible

            if candidate == old_raw:
                result.unchanged.append(uri)
                continue
            if is_update:
                result.updated.append(uri)
            else:
                result.created.append(uri)
            result.operations.append({"uri": uri, "content": candidate, "mode": "upsert"})

        if not memory_target and bundle.pages:
            for uri, old_raw in sorted(existing_raw.items()):
                if uri in output_uris:
                    continue
                candidate, automatic_count = _link_wiki_mentions(
                    old_raw,
                    source_uri=uri,
                    targets=mention_targets,
                )
                if candidate == old_raw:
                    continue
                result.link_count += automatic_count
                result.updated.append(uri)
                result.wiki_uris.append(uri)
                result.operations.append(
                    {
                        "uri": uri,
                        "content": candidate,
                        "mode": "upsert",
                    }
                )

        for index, file in enumerate(bundle.files):
            uri = file_uris[index]
            if file.content is not None:
                candidate = file.content.encode("utf-8")
                operation_content = {"content": file.content}
            else:
                candidate = file_payloads[index]
                assert candidate is not None
                operation_content = {"content_base64": base64.b64encode(candidate).decode("ascii")}

            if target_type == "resource":
                page_type = validate_declared_okf_markdown(uri, candidate)
                if page_type is not None:
                    result.wiki_uris.append(uri)
                if file.update_uri and uri in catalog_uris and page_type is None:
                    raise ValueError(
                        "an existing Wiki page updated as a raw file must retain "
                        "valid OKF frontmatter with a non-empty type"
                    )

            is_update = file.update_uri is not None
            old = existing_bytes.get(uri)
            if old is not None and candidate == old:
                result.unchanged.append(uri)
                continue
            if is_update:
                assert old is not None
                result.updated.append(uri)
            else:
                result.created.append(uri)
            result.operations.append({"uri": uri, **operation_content, "mode": "upsert"})
        return result


__all__ = [
    "RenderedBundle",
    "WikiRenderer",
    "has_unclosed_frontmatter",
    "strip_okf_frontmatter",
    "is_reserved_wiki_page_uri",
    "validate_declared_okf_markdown",
    "validate_relative_file_path",
    "validate_relative_page_path",
    "wiki_page_path_from_title",
]
