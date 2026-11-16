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


@dataclass(slots=True)
class RenderedBundle:
    operations: list[dict[str, Any]] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    wiki_uris: list[str] = field(default_factory=list)
    link_count: int = 0


def wiki_page_path_from_title(title: str) -> str:
    title = re.sub(r"\s+[-–—]\s+", " ", title.strip())
    return VikingURI.sanitize_segment(title)


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(content or "")
    if not match:
        return {}, content or ""
    parsed = yaml.safe_load(match.group(1)) or {}
    if not isinstance(parsed, dict):
        raise ValueError("existing OKF frontmatter must be a YAML object")
    return parsed, content[match.end() :]


def strip_okf_frontmatter(content: str) -> str:
    """Return the editable Wiki body from a materialized OKF Markdown file."""
    return _split_frontmatter(content)[1].lstrip("\r\n")


def has_unclosed_frontmatter(content: bytes) -> bool:
    opening = _FRONTMATTER_START_RE.match(content)
    return opening is not None and _FRONTMATTER_END_RE.search(content[opening.end() :]) is None


def validate_declared_okf_markdown(path: str, content: bytes) -> str | None:
    """Validate a Markdown artifact and return its declared OKF type, if any."""
    if not path.casefold().endswith(".md"):
        return
    opening = _FRONTMATTER_START_RE.match(content)
    if opening is None:
        return

    remainder = content[opening.end() :]
    closing = _FRONTMATTER_END_RE.search(remainder)
    raw_frontmatter = remainder[: closing.start()] if closing else remainder
    raw_declares_type = _OKF_TYPE_DECLARATION_RE.search(raw_frontmatter) is not None

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        if raw_declares_type:
            raise ValueError(f'OKF Markdown file "{path}" must be UTF-8') from exc
        return

    match = _FRONTMATTER_RE.match(text)
    if match is None:
        if raw_declares_type:
            raise ValueError(f'OKF Markdown file "{path}" has unterminated YAML frontmatter')
        return
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        if raw_declares_type:
            raise ValueError(f'OKF Markdown file "{path}" has invalid YAML frontmatter') from exc
        return
    if not isinstance(frontmatter, dict):
        if raw_declares_type:
            raise ValueError(f'OKF Markdown file "{path}" frontmatter must be a YAML object')
        return
    if "type" not in frontmatter:
        return
    if not isinstance(frontmatter["type"], str) or not frontmatter["type"].strip():
        raise ValueError(
            f'OKF Markdown file "{path}" frontmatter field "type" must be a non-empty string'
        )
    return frontmatter["type"].strip()


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in tags:
        tag = value.strip()
        if tag and tag not in normalized:
            normalized.append(tag)
    return normalized


def _frontmatter(
    *,
    old: Mapping[str, Any],
    page_type: str,
    title: str,
    summary: str,
    tags: list[str],
) -> str:
    data = {key: value for key, value in old.items() if key not in _PLATFORM_FRONTMATTER_FIELDS}
    data = {
        "type": page_type,
        "title": title,
        "description": summary,
        **data,
    }
    normalized_tags = _normalize_tags(tags)
    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**9)
    if normalized_tags:
        inline_tags = yaml.safe_dump(
            normalized_tags,
            allow_unicode=True,
            width=10**9,
            default_flow_style=True,
        ).strip()
        dumped += f"tags: {inline_tags}\n"
    return "---\n" + dumped + "---\n\n"


def _citation_target_allowed(target: str, source_roots: Mapping[str, str]) -> bool:
    if not target.startswith("viking://"):
        return False
    try:
        target = validate_safe_viking_uri_path(target)
    except ValueError:
        return False
    for root in source_roots.values():
        if target.rstrip("/") == root.rstrip("/") or relative_uri_path(root, target):
            return True
    return False


def _linkify_source_uris(body: str, source_roots: Mapping[str, str]) -> str:
    protected = LinkRenderer.protected_markdown_spans(body)
    replacements: list[tuple[int, int, str]] = []
    for match in _BARE_VIKING_URI_RE.finditer(body):
        start = match.start()
        target = match.group(0).rstrip(".,;:!?")
        end = start + len(target)
        if any(not (end <= span_start or start >= span_end) for span_start, span_end in protected):
            continue
        if start > 0 and end < len(body) and body[start - 1] == "<" and body[end] == ">":
            continue
        if not _citation_target_allowed(target, source_roots):
            continue
        label = target.rstrip("/").rsplit("/", 1)[-1].removesuffix(".md")
        label = label.replace("[", r"\[").replace("]", r"\]") or "Source"
        encoded_target = LinkRenderer.encode_markdown_target(target)
        replacements.append((start, end, f"[{label}]({encoded_target})"))

    rendered = list(body)
    for start, end, replacement in reversed(replacements):
        rendered[start:end] = replacement
    return "".join(rendered)


def _wiki_page_basename(uri: str) -> str:
    name = uri.rstrip("/").rsplit("/", 1)[-1]
    return name[:-3] if name.casefold().endswith(".md") else name


def _wiki_mention_targets(uris: set[str]) -> dict[str, tuple[str, re.Pattern[str], str]]:
    """Return unique basename targets and patterns shared by a render batch, excluding indexes."""
    grouped: dict[str, list[tuple[str, str]]] = {}
    for uri in sorted(uris):
        name = _wiki_page_basename(uri).strip()
        if not name or name.casefold() == "index":
            continue
        grouped.setdefault(name.casefold(), []).append((name, uri))
    return {
        name: (
            uri,
            re.compile(re.escape(name), re.IGNORECASE),
            # Han characters have no case variants; absence rules out a regex match.
            max(re.findall(r"[\u3400-\u9fff]+", name), key=len, default=""),
        )
        for items in grouped.values()
        if len(items) == 1
        for name, uri in items
    }


def _has_link_to(body: str, source_uri: str, target_uri: str) -> bool:
    relative = LinkRenderer.relative_path(source_uri, target_uri)
    expected = {target_uri.rstrip("/")}
    if relative is not None:
        expected.add(posixpath.normpath(relative))
    return any(
        link.start == 0 or body[link.start - 1] != "!"
        for link in LinkRenderer.iter_markdown_links(body)
        if LinkRenderer.normalize_markdown_target(link.target) in expected
    )


def _strip_legacy_related_pages(body: str) -> str:
    rendered, count = _LEGACY_RELATED_PAGES_RE.subn("", body)
    return rendered.rstrip() if count else body


def _link_wiki_mentions(
    content: str,
    *,
    source_uri: str,
    targets: Mapping[str, tuple[str, re.Pattern[str], str]],
) -> tuple[str, int]:
    """Link unambiguous filename mentions outside titles and existing Markdown links."""
    frontmatter = _FRONTMATTER_RE.match(content)
    prefix = content[: frontmatter.end()] if frontmatter else ""
    body = content[frontmatter.end() :] if frontmatter else content
    title = _LEADING_H1_RE.match(body)
    if title:
        prefix += body[: title.end()]
        body = body[title.end() :]
    body = _strip_legacy_related_pages(body)

    links = [
        {
            "match_text": name,
            "to_uri": target_uri,
            "weight": len(name),
        }
        for name, (target_uri, pattern, literal) in targets.items()
        if target_uri != source_uri
        and literal in body
        and pattern.search(body)
        and not _has_link_to(body, source_uri, target_uri)
    ]
    rendered, count = LinkRenderer.render_links_with_count(body, source_uri, links)
    return prefix + rendered, count


def _body_markdown_links(body: str) -> list[MarkdownLink]:
    """Return editable inline links outside code, comments and image syntax."""
    links = list(LinkRenderer.iter_markdown_links(body))
    link_spans = {(link.start, link.end) for link in links}
    protected = [s for s in LinkRenderer.protected_markdown_spans(body) if s not in link_spans]
    protected.extend((m.start(), m.end()) for m in re.finditer(r"<!--.*?-->", body, re.DOTALL))
    protected.extend((m.start(), m.end()) for m in re.finditer(r"(?m)^(?: {4}|\t)[^\n]*", body))
    return [
        link
        for link in links
        if not (link.start > 0 and body[link.start - 1] == "!")
        and not any(link.start < end and link.end > start for start, end in protected)
    ]


def _link_uri(target: str, source_uri: str) -> str:
    """Resolve a Markdown destination to an absolute URI for deduplication and lookup."""
    target = LinkRenderer.normalize_markdown_target(target)
    if re.match(r"^[A-Za-z][\w+.-]*:", target):
        return target
    directory = posixpath.dirname(source_uri.removeprefix("viking://"))
    return "viking://" + posixpath.normpath(posixpath.join(directory, target))


def _render_source_fallback(
    body: str,
    *,
    source_ids: list[str],
    source_roots: Mapping[str, str],
    wiki_language: WikiLanguage | None,
) -> str:
    linked_targets = {
        LinkRenderer.normalize_markdown_target(link.target)
        for link in LinkRenderer.iter_markdown_links(body)
        if _citation_target_allowed(
            LinkRenderer.normalize_markdown_target(link.target), source_roots
        )
    }
    missing: list[tuple[str, str]] = []
    for source_id in source_ids:
        target = source_roots[source_id]
        if any(
            linked.rstrip("/") == target.rstrip("/") or relative_uri_path(target, linked)
            for linked in linked_targets
        ):
            continue
        label = target.rstrip("/").rsplit("/", 1)[-1] or f"Source {source_id}"
        missing.append((label, LinkRenderer.encode_markdown_target(target)))
    if not missing:
        return body.rstrip()
    heading = "来源" if wiki_language == "zh-CN" else "Sources"
    lines = [f"- [{label}]({target})" for label, target in missing]
    return body.rstrip() + f"\n\n## {heading}\n\n" + "\n".join(lines) + "\n"


def validate_relative_page_path(path: str) -> str:
    relative = sanitize_relative_viking_path(path).strip("/")
    if not relative.lower().endswith(".md"):
        relative += ".md"
    segments = [segment for segment in relative.split("/") if segment]
    if not segments or any(segment.startswith(".") for segment in segments):
        raise ValueError(f"invalid Wiki page path: {path}")
    if segments[-1].lower() in _RESERVED_FILENAMES:
        raise ValueError(f"reserved Wiki page path: {path}")
    return "/".join(segments)


def validate_relative_file_path(path: str) -> str:
    """Validate an output-relative path, rejecting metadata and internal staging directories."""
    relative = sanitize_relative_viking_path(path).strip("/")
    segments = relative.split("/")
    if (
        not relative
        or any(not segment or segment in {".", ".."} for segment in segments)
        or any(segment.startswith(".") for segment in segments)
    ):
        raise ValueError(f"invalid output file path: {path}")
    if segments[-1].lower() in _RESERVED_FILENAMES:
        raise ValueError(f"reserved output file path: {path}")
    if COMPILE_STAGING_ROOT.casefold() in (segment.casefold() for segment in segments):
        raise ValueError(f"reserved staging directory in output path: {path}")
    return relative


def is_reserved_wiki_page_uri(uri: str) -> bool:
    return uri.rstrip("/").rsplit("/", 1)[-1].lower() in _RESERVED_FILENAMES


def _merge_stored_links(
    existing: list[dict[str, Any]], new_links: list[StoredLink]
) -> list[dict[str, Any]]:
    result = [dict(item) for item in existing if isinstance(item, dict)]
    seen = {
        (
            item.get("from_uri"),
            item.get("to_uri"),
            item.get("link_type"),
            item.get("weight"),
            item.get("match_text"),
            item.get("description"),
        )
        for item in result
    }
    for link in new_links:
        item = link.model_dump()
        key = (
            item.get("from_uri"),
            item.get("to_uri"),
            item.get("link_type"),
            item.get("weight"),
            item.get("match_text"),
            item.get("description"),
        )
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


