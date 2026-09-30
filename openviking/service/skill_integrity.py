# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill integrity computation, manifest generation, and snapshot locking."""

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
from typing import Any, AsyncGenerator, Dict, Optional

from openviking.privacy.service import UserPrivacyConfigVersion
from openviking.server.identity import RequestContext
from openviking.server.routers.skills_helpers import (
    _parse_abstract_meta,
    _relative_skill_path,
    _skill_file_kind,
    _skill_md_uri,
    _skill_name_from_uri,
    _skill_summary_from_meta,
)
from openviking.server.skill_source_metadata import (
    SOURCE_METADATA_FILENAME,
    read_skill_source_metadata,
)
from openviking_cli.exceptions import ResourceExhaustedError

_SKILL_INTEGRITY_MAX_ENTRIES = 512
_SKILL_INTEGRITY_MAX_FILE_BYTES = 16 * 1024 * 1024
_SKILL_INTEGRITY_MAX_TOTAL_BYTES = 64 * 1024 * 1024
_SKILL_INTEGRITY_READ_CONCURRENCY = 8


async def _list_skill_files(
    service,
    ctx: RequestContext,
    root_uri: str,
    *,
    node_limit: int = 10000,
    level_limit: int = 10,
) -> list[Dict[str, Any]]:
    entries: list[Dict[str, Any]] = []
    queue: list[tuple[str, int]] = [(root_uri, 0)]
    visited_dirs = {root_uri.rstrip("/")}

    while queue and len(entries) < node_limit:
        current_uri, depth = queue.pop(0)
        child_limit = max(node_limit - len(entries), 0)
        if child_limit <= 0:
            break
        children = await service.fs.ls(
            current_uri,
            ctx=ctx,
            output="agent",
            abs_limit=1024,
            show_all_hidden=True,
            node_limit=child_limit,
        )
        for entry in children:
            if not isinstance(entry, dict):
                continue
            entry_uri = entry.get("uri", "")
            if not entry_uri:
                continue
            entries.append(entry)
            if len(entries) >= node_limit:
                break
            if not entry.get("isDir", False) or depth + 1 >= level_limit:
                continue
            normalized_uri = entry_uri.rstrip("/")
            if normalized_uri in visited_dirs:
                continue
            visited_dirs.add(normalized_uri)
            queue.append((entry_uri, depth + 1))
    return entries


async def _skill_manifest_with_integrity(
    service,
    ctx: RequestContext,
    root_uri: str,
    *,
    include_integrity: bool = True,
    max_entries: int = _SKILL_INTEGRITY_MAX_ENTRIES,
    max_file_bytes: int = _SKILL_INTEGRITY_MAX_FILE_BYTES,
    max_total_bytes: int = _SKILL_INTEGRITY_MAX_TOTAL_BYTES,
) -> tuple[list[Dict[str, Any]], str | None]:
    """Build a Skill manifest, optionally content-addressed for remote consumers."""
    entries = await _list_skill_files(
        service,
        ctx,
        root_uri,
        node_limit=max_entries + 2 if include_integrity else 10000,
    )
    visible_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and _relative_skill_path(root_uri, str(entry.get("uri") or "")) != SOURCE_METADATA_FILENAME
    ]
    if include_integrity and len(visible_entries) > max_entries:
        raise ResourceExhaustedError(f"Skill integrity manifest exceeds {max_entries} entries")
    if include_integrity:
        declared_total = 0
        for entry in visible_entries:
            if bool(entry.get("isDir", False)) or entry.get("size") is None:
                continue
            declared_size = int(entry["size"])
            path = _relative_skill_path(root_uri, str(entry.get("uri") or ""))
            if declared_size > max_file_bytes:
                raise ResourceExhaustedError(f"Skill file exceeds integrity size limit: {path}")
            declared_total += declared_size
            if declared_total > max_total_bytes:
                raise ResourceExhaustedError(
                    f"Skill integrity manifest exceeds {max_total_bytes} total bytes"
                )

    async def build_entry(entry: Dict[str, Any]) -> Dict[str, Any] | None:
        uri = str(entry.get("uri") or "")
        path = _relative_skill_path(root_uri, uri)
        if not uri or path == SOURCE_METADATA_FILENAME:
            return None
        is_dir = bool(entry.get("isDir", False))
        item: Dict[str, Any] = {
            "name": entry.get("name") or _skill_name_from_uri(uri),
            "uri": uri,
            "path": path,
            "is_dir": is_dir,
            "kind": _skill_file_kind(path, is_dir),
        }
        if not is_dir and include_integrity:
            declared_size = entry.get("size")
            if declared_size is not None and int(declared_size) > max_file_bytes:
                raise ResourceExhaustedError(f"Skill file exceeds integrity size limit: {path}")
            data = await service.fs.read_file_bytes(uri, ctx=ctx)
            if len(data) > max_file_bytes:
                raise ResourceExhaustedError(f"Skill file exceeds integrity size limit: {path}")
            item["size"] = len(data)
            item["sha256"] = hashlib.sha256(data).hexdigest()
        return item

    built: list[Dict[str, Any] | None] = []
    total_bytes = 0
    for offset in range(0, len(visible_entries), _SKILL_INTEGRITY_READ_CONCURRENCY):
        batch = visible_entries[offset : offset + _SKILL_INTEGRITY_READ_CONCURRENCY]
        batch_items = await asyncio.gather(*(build_entry(entry) for entry in batch))
        for item in batch_items:
            if item is not None and not item["is_dir"]:
                total_bytes += int(item.get("size") or 0)
                if total_bytes > max_total_bytes:
                    raise ResourceExhaustedError(
                        f"Skill integrity manifest exceeds {max_total_bytes} total bytes"
                    )
        built.extend(batch_items)
    files = [item for item in built if item is not None]
    if not include_integrity:
        return files, None
    revision_payload = [
        {
            "path": item["path"],
            "is_dir": item["is_dir"],
            "size": item.get("size"),
            "sha256": item.get("sha256"),
        }
        for item in sorted(files, key=lambda value: value["path"])
    ]
    revision = hashlib.sha256(
        json.dumps(revision_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return files, revision


@asynccontextmanager
async def _skill_snapshot_lock(
    service,
    ctx: RequestContext,
    root_uri: str,
) -> AsyncGenerator[None, None]:
    """Hold the storage tree lock while one content-addressed Skill view is read."""
    viking_fs = service.fs._ensure_initialized()  # noqa: SLF001
    await viking_fs._ensure_access(root_uri, ctx)  # noqa: SLF001
    path = viking_fs._uri_to_path(root_uri, ctx=ctx)  # noqa: SLF001
    fs_ctx = {"account_id": ctx.account_id}
    lease = await viking_fs._async_agfs.pathlock_acquire_tree(  # noqa: SLF001
        path,
        fs_ctx=fs_ctx,
    )
    try:
        yield
    finally:
        await viking_fs._async_agfs.pathlock_release(lease, fs_ctx=fs_ctx)  # noqa: SLF001


async def _read_skill_detail(
    service,
    ctx: RequestContext,
    *,
    skill_name: str,
    root_uri: str,
    include_content: Optional[bool],
    include_files: bool,
    include_integrity: bool,
    include_source: bool,
    level: Optional[int],
) -> Dict[str, Any]:
    """Read one Skill; integrity requests observe a storage-locked package snapshot."""

    async def read_fields() -> Dict[str, Any]:
        abstract = await service.fs.abstract(root_uri, ctx=ctx)
        result = _skill_summary_from_meta(skill_name, root_uri, _parse_abstract_meta(abstract))
        if level is None or level == 0:
            result["abstract"] = abstract
        if level is None or level == 1:
            result["overview"] = await service.fs.overview(root_uri, ctx=ctx)
        if (
            level == 2
            or include_content is True
            or (level is None and include_content is not False)
        ):
            content = await service.fs.read(_skill_md_uri(root_uri), ctx=ctx)
            result["content"] = content
            result["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if include_files:
            files, revision = await _skill_manifest_with_integrity(
                service,
                ctx,
                root_uri,
                include_integrity=include_integrity,
            )
            result["files"] = files
            if revision is not None:
                result["revision"] = revision
        if include_source:
            result["source"] = await read_skill_source_metadata(service, ctx, root_uri)
        return result

    if include_integrity:
        async with _skill_snapshot_lock(service, ctx, root_uri):
            return await read_fields()
    return await read_fields()


async def _restore_skill_privacy(
    service,
    ctx: RequestContext,
    skill_name: str,
    previous_privacy: Optional[UserPrivacyConfigVersion],
) -> None:
    privacy = service.privacy_configs
    if privacy is None:
        return
    if previous_privacy is None:
        await privacy.delete(ctx, "skill", skill_name)
        return
    await privacy.activate_version(
        ctx,
        "skill",
        skill_name,
        previous_privacy.version,
        updated_by=ctx.user.user_id,
    )
