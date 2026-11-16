# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Directory ZIP archive helpers for content router."""

import asyncio
import io
import zipfile
from pathlib import PurePosixPath

from openviking.server.identity import RequestContext
from openviking_cli.exceptions import InvalidArgumentError, PayloadTooLargeError

_DIRECTORY_ARCHIVE_MAX_BYTES = 10 * 1024 * 1024
_DIRECTORY_ARCHIVE_MAX_ENTRIES = 10_000


def _archive_size_limit_error(uri: str) -> PayloadTooLargeError:
    return PayloadTooLargeError(
        f"Directory archive exceeds the {_DIRECTORY_ARCHIVE_MAX_BYTES}-byte download limit: {uri}"
    )


def _archive_entry_limit_error(uri: str) -> PayloadTooLargeError:
    return PayloadTooLargeError(
        f"Directory archive exceeds the {_DIRECTORY_ARCHIVE_MAX_ENTRIES}-entry download limit: {uri}"
    )


def _safe_archive_path(root_name: str, rel_path: str = "") -> str:
    """Build a portable ZIP member path from server-produced tree entries."""
    relative = PurePosixPath(rel_path)
    if relative.is_absolute():
        raise InvalidArgumentError(f"Unsafe path in directory download: {rel_path}")
    parts = [root_name, *relative.parts]
    if any(part in {"", ".", ".."} or "\\" in part for part in parts):
        raise InvalidArgumentError(f"Unsafe path in directory download: {rel_path or root_name}")
    return "/".join(parts)


async def _build_directory_archive(
    service, uri: str, stat: dict, ctx: RequestContext
) -> tuple[bytes, str]:
    """Pack one visible Viking directory tree into an in-memory ZIP archive."""
    root_name = str(stat.get("name") or uri.rstrip("/").rsplit("/", 1)[-1] or "download")
    root_path = _safe_archive_path(root_name)

    entries = await service.fs.tree(
        uri,
        ctx=ctx,
        output="original",
        show_all_hidden=True,
        node_limit=_DIRECTORY_ARCHIVE_MAX_ENTRIES + 1,
        level_limit=None,
    )
    if len(entries) > _DIRECTORY_ARCHIVE_MAX_ENTRIES:
        raise _archive_entry_limit_error(uri)

    declared_total = 0
    for entry in entries:
        if entry.get("isDir", False):
            continue
        size = entry.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            file_stat = await service.fs.stat(str(entry["uri"]), ctx=ctx)
            size = file_stat.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise InvalidArgumentError(
                f"Cannot determine file size for directory download: {entry['uri']}"
            )
        declared_total += size
        if declared_total > _DIRECTORY_ARCHIVE_MAX_BYTES:
            raise _archive_size_limit_error(uri)

    buffer = io.BytesIO()
    actual_total = 0
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as archive:
        archive.writestr(f"{root_path}/", b"")
        for entry in entries:
            member_path = _safe_archive_path(root_name, str(entry["rel_path"]))
            if entry.get("isDir", False):
                archive.writestr(f"{member_path.rstrip('/')}/", b"")
            else:
                content = await service.fs.read_file_bytes(str(entry["uri"]), ctx=ctx)
                actual_total += len(content)
                if actual_total > _DIRECTORY_ARCHIVE_MAX_BYTES:
                    raise _archive_size_limit_error(uri)
                await asyncio.to_thread(archive.writestr, member_path, content)
            if buffer.tell() > _DIRECTORY_ARCHIVE_MAX_BYTES:
                raise _archive_size_limit_error(uri)
    if buffer.tell() > _DIRECTORY_ARCHIVE_MAX_BYTES:
        raise _archive_size_limit_error(uri)
    return buffer.getvalue(), f"{root_name}.zip"
