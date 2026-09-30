# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Path, URI, and metadata summary helpers for skills router."""

from typing import Any, Dict, Optional
import yaml

from openviking.core.namespace import canonical_user_root
from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.identity import RequestContext
from openviking.service.skill_sanitizer import SkillSanitizer
from openviking.utils.skill_processor import validate_skill_name
from openviking_cli.exceptions import InvalidArgumentError, NotFoundError


def _agent_skills_root(ctx: RequestContext, target_uri: Optional[str] = None) -> str:
    user_root = f"{canonical_user_root(ctx)}/skills"
    if not target_uri:
        return user_root
    resolved_uri = validate_request_viking_uri(
        resolve_path_variables(target_uri), ctx, field_name="target_uri"
    ).rstrip("/")
    if resolved_uri == "viking://agent/skills" or resolved_uri.startswith("viking://agent/skills/"):
        return "viking://agent/skills"
    if resolved_uri == user_root or resolved_uri.startswith(f"{user_root}/"):
        return user_root
    raise InvalidArgumentError(
        f"Unsupported skill target URI: {target_uri}",
        details={
            "field": "target_uri",
            "allowed": [user_root, "viking://agent/skills"],
        },
    )


async def _list_skills_from_root(
    service, ctx: RequestContext, root_uri: str
) -> list[Dict[str, Any]]:
    """List skills from a specific root URI.

    Filters out directory entries that do not look like a valid skill — i.e.
    their abstract metadata does not yield a valid ``name`` (matching the same
    rules ``add_skill`` enforces via ``validate_skill_name``).  If the abstract
    is missing or unreadable we fall back to checking whether a SKILL.md file
    exists under the entry; only then is the directory accepted.  This keeps
    nested directories like ``<skill>/scripts`` out of the listing.
    """
    try:
        entries = await service.fs.ls(
            root_uri,
            ctx=ctx,
            output="agent",
            abs_limit=1024,
            node_limit=1000,
        )
    except NotFoundError:
        return []

    results: list[Dict[str, Any]] = []
    for entry in entries:
        if not (isinstance(entry, dict) and entry.get("isDir", False)):
            continue
        if not await _entry_looks_like_skill(service, ctx, entry):
            continue
        results.append(_skill_summary_from_entry(entry))
    return results


async def _entry_looks_like_skill(service, ctx: RequestContext, entry: Dict[str, Any]) -> bool:
    """Decide whether a directory entry from ``ls`` represents a real skill."""
    entry_uri = entry.get("uri", "")
    if not entry_uri:
        return False

    dir_name = entry.get("name") or _skill_name_from_uri(entry_uri)
    if not dir_name or SkillSanitizer.is_anomalous_dir_name(dir_name):
        return False

    meta = _parse_abstract_meta(entry.get("abstract", ""))
    if meta and isinstance(meta, dict) and isinstance(meta.get("name"), str):
        meta_name = meta["name"].strip()
        if not SkillSanitizer.is_anomalous_dir_name(meta_name):
            try:
                validate_skill_name(meta_name)
                description = meta.get("description")
                if isinstance(description, str) and description.strip():
                    return True
            except Exception:
                pass

    # Abstract is missing or unparsable — fall back to checking that the
    # directory actually contains a SKILL.md file before listing it.
    try:
        validate_skill_name(dir_name)
    except Exception:
        return False

    try:
        skill_md_stat = await service.fs.stat(_skill_md_uri(entry_uri), ctx=ctx)
    except Exception:
        return False
    if not skill_md_stat or skill_md_stat.get("isDir", False):
        return False
    return True


def _validate_skill_name(skill_name: str) -> str:
    return validate_skill_name(skill_name)


def _skill_root_uri(ctx: RequestContext, skill_name: str, target_uri: Optional[str] = None) -> str:
    return f"{_agent_skills_root(ctx, target_uri)}/{_validate_skill_name(skill_name)}"


def _skill_md_uri(root_uri: str) -> str:
    return f"{root_uri.rstrip('/')}/SKILL.md"


def _skill_name_from_uri(uri: str) -> str:
    return uri.rstrip("/").split("/")[-1]


def _relative_skill_path(root_uri: str, uri: str) -> str:
    prefix = root_uri.rstrip("/") + "/"
    if uri.startswith(prefix):
        return uri[len(prefix) :]
    return _skill_name_from_uri(uri)


def _skill_file_kind(path: str, is_dir: bool) -> str:
    if is_dir:
        return "directory"
    if path == "SKILL.md":
        return "definition"
    if path in {".abstract.md", ".overview.md"}:
        return "summary"
    return "auxiliary"


def _parse_abstract_meta(abstract: str) -> Dict[str, Any]:
    try:
        parsed = yaml.safe_load(abstract or "") or {}
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _skill_summary_from_meta(name: str, root_uri: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "skill",
        "name": name,
        "uri": root_uri,
        "root_uri": root_uri,
        "skill_md_uri": _skill_md_uri(root_uri),
        "description": meta.get("description", ""),
        "tags": meta.get("tags") or [],
        "allowed_tools": meta.get("allowed_tools") or meta.get("allowed-tools") or [],
    }


def _skill_summary_from_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    root_uri = entry.get("uri", "")
    name = entry.get("name") or _skill_name_from_uri(root_uri)
    return _skill_summary_from_meta(name, root_uri, _parse_abstract_meta(entry.get("abstract", "")))


def _skill_summary_from_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    hit_uri = hit.get("uri", "")
    root_uri = _skill_root_from_hit_uri(hit_uri)
    name = _skill_name_from_uri(root_uri) if root_uri else _skill_name_from_uri(hit_uri)
    summary = _skill_summary_from_meta(
        name, root_uri or hit_uri, _parse_abstract_meta(hit.get("abstract", ""))
    )
    summary["score"] = hit.get("score", 0.0)
    summary["match_reason"] = hit.get("match_reason", "")
    summary["level"] = hit.get("level", 0)
    summary["abstract"] = hit.get("abstract", "")
    return summary


def _skill_root_from_hit_uri(hit_uri: str) -> str:
    """Strip a trailing chunk filename (e.g. ``.abstract.md``) from a hit URI.

    Search results point at the indexed chunk file (typically ``.abstract.md``
    sitting alongside ``SKILL.md`` inside the skill directory).  The summary
    consumed by the CLI expects the URI to identify the skill directory itself,
    so we trim a single trailing filename when one is present.
    """
    if not hit_uri:
        return ""
    trimmed = hit_uri.rstrip("/")
    last_segment = trimmed.rsplit("/", 1)[-1]
    if "." in last_segment:
        parent = trimmed.rsplit("/", 1)[0]
        if parent:
            return parent
    return trimmed


async def _require_skill(
    service, ctx: RequestContext, skill_name: str, target_uri: Optional[str] = None
) -> str:
    if target_uri:
        root_uri = _skill_root_uri(ctx, skill_name, target_uri)
        try:
            stat = await service.fs.stat(root_uri, ctx=ctx)
            if stat and stat.get("isDir", False):
                return root_uri
        except NotFoundError:
            pass
        except Exception as exc:
            raise NotFoundError(root_uri, "skill") from exc

    user_root_uri = _skill_root_uri(ctx, skill_name)
    try:
        stat = await service.fs.stat(user_root_uri, ctx=ctx)
        if stat and stat.get("isDir", False):
            return user_root_uri
    except NotFoundError:
        pass
    except Exception as exc:
        raise NotFoundError(user_root_uri, "skill") from exc

    agent_root_uri = _skill_root_uri(ctx, skill_name, "viking://agent/skills")
    try:
        stat = await service.fs.stat(agent_root_uri, ctx=ctx)
        if stat and stat.get("isDir", False):
            return agent_root_uri
    except NotFoundError:
        pass
    except Exception as exc:
        raise NotFoundError(agent_root_uri, "skill") from exc

    raise NotFoundError(_skill_root_uri(ctx, skill_name), "skill")
