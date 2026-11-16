# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Async adapter for the synchronous AGFS client."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any, BinaryIO, Dict, List, Union

from openviking.service.task_tracker_concurrency import run_to_completion

from .leader import _LOCAL_LEADER_BACKEND, LeaderCandidate, LeaderMode, leader_candidate
from .pathlock_helpers import (
    PathLockMixin,
    _disabled_pathlock_lease,
    _fs_ctx_or_default,
    _fs_ctx_with_auto_pathlock,
    _path_locks_disabled,
    encryption_account_id_from_agfs_path,
    ensure_same_encryption_account,
    fs_ctx_from_agfs_path,
    local_account_id_from_agfs_path,
    sort_raw_entries,
)
from .protocols import AGFSSyncClientProtocol


class AsyncAGFSClient(PathLockMixin):
    """Run blocking AGFS binding client operations off the event loop."""

    def __init__(self, client: AGFSSyncClientProtocol):
        self._client = client

    def leader_candidate(
        self,
        key: str,
        holder_id: str,
        *,
        ttl_secs: float,
        renew_interval_secs: float,
        retry_interval_secs: float,
        mode: LeaderMode = "distributed",
    ) -> LeaderCandidate:
        """Create a leader candidate whose terms expose only a stop event."""
        return leader_candidate(
            self._client,
            _LOCAL_LEADER_BACKEND,
            key=key,
            holder_id=holder_id,
            ttl_secs=ttl_secs,
            renew_interval_secs=renew_interval_secs,
            retry_interval_secs=retry_interval_secs,
            mode=mode,
        )

    async def run(self, method_name: str, /, *args: Any, **kwargs: Any) -> Any:
        """Run a sync method off-thread, settling I/O before propagating cancellation."""
        ctx = kwargs.get("ctx")
        if _path_locks_disabled() and isinstance(ctx, dict) and ctx.get("lease_ref"):
            ctx = dict(ctx)
            ctx.pop("lease_ref", None)
            ctx["disable_auto_pathlock"] = "true"
            kwargs["ctx"] = ctx
        method = getattr(self._client, method_name)
        try:
            return await run_to_completion(lambda: asyncio.to_thread(method, *args, **kwargs))
        except TypeError as exc:
            message = str(exc)
            if "ctx" not in kwargs or "unexpected keyword argument 'ctx'" not in message:
                raise
            legacy_kwargs = dict(kwargs)
            legacy_kwargs.pop("ctx", None)
            return await run_to_completion(
                lambda: asyncio.to_thread(method, *args, **legacy_kwargs)
            )

    @staticmethod
    def _sort_raw_entries(
        entries: List[Dict[str, Any]],
        sort_by: str | None,
        sort_order: str = "asc",
    ) -> List[Dict[str, Any]]:
        return sort_raw_entries(entries, sort_by=sort_by, sort_order=sort_order)

    async def ls(
        self,
        path: str = "/",
        *,
        offset: int = 0,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        fs_ctx: Dict[str, str] | None = None,
    ) -> List[Dict[str, Any]]:
        """Return a sorted directory range."""
        kwargs: Dict[str, Any] = {}
        if offset:
            kwargs["offset"] = offset
        if limit is not None:
            kwargs["limit"] = limit
        if sort_by is not None:
            kwargs["sort_by"] = sort_by
            kwargs["sort_order"] = sort_order
        try:
            return await self.run("ls", path, **kwargs, ctx=_fs_ctx_or_default(path, fs_ctx))
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            entries = await self.run("ls", path, ctx=_fs_ctx_or_default(path, fs_ctx))
            if sort_by:
                entries = self._sort_raw_entries(entries, sort_by=sort_by, sort_order=sort_order)
            if offset or limit is not None:
                start = offset
                end = None if limit is None else offset + limit
                entries = entries[start:end]
            return entries

    async def read(
        self,
        path: str,
        offset: int = 0,
        size: int = -1,
        stream: bool = False,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Any:
        kwargs: Dict[str, Any] = {}
        if offset != 0:
            kwargs["offset"] = offset
        if size != -1:
            kwargs["size"] = size
        if stream:
            kwargs["stream"] = stream
        return await self.run("read", path, **kwargs, ctx=_fs_ctx_or_default(path, fs_ctx))

    async def cat(
        self,
        path: str,
        offset: int = 0,
        size: int = -1,
        stream: bool = False,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Any:
        kwargs: Dict[str, Any] = {}
        if offset != 0:
            kwargs["offset"] = offset
        if size != -1:
            kwargs["size"] = size
        if stream:
            kwargs["stream"] = stream
        return await self.run("cat", path, **kwargs, ctx=_fs_ctx_or_default(path, fs_ctx))

    async def write(
        self,
        path: str,
        data: Union[bytes, Iterator[bytes], BinaryIO],
        max_retries: int = 3,
        *,
        fs_ctx: Dict[str, str] | None = None,
        auto_pathlock: bool = True,
    ) -> str:
        """Write file content to AGFS."""
        ctx = _fs_ctx_with_auto_pathlock(path, fs_ctx, auto_pathlock)
        if max_retries == 3:
            return await self.run("write", path, data, ctx=ctx)
        return await self.run("write", path, data, max_retries=max_retries, ctx=ctx)

    async def mkdir(
        self, path: str, mode: str = "755", *, fs_ctx: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
        if mode == "755":
            return await self.run("mkdir", path, ctx=_fs_ctx_or_default(path, fs_ctx))
        return await self.run("mkdir", path, mode=mode, ctx=_fs_ctx_or_default(path, fs_ctx))

    async def ensure_parent_dirs(
        self, path: str, mode: str = "755", *, fs_ctx: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
        if mode == "755":
            return await self.run("ensure_parent_dirs", path, ctx=_fs_ctx_or_default(path, fs_ctx))
        return await self.run(
            "ensure_parent_dirs", path, mode=mode, ctx=_fs_ctx_or_default(path, fs_ctx)
        )

    async def rm(
        self,
        path: str,
        recursive: bool = False,
        force: bool = True,
        *,
        fs_ctx: Dict[str, str] | None = None,
        auto_pathlock: bool = True,
    ) -> Dict[str, Any]:
        """Remove a file or directory from AGFS."""
        kwargs: Dict[str, Any] = {}
        if recursive:
            kwargs["recursive"] = recursive
        if not force:
            kwargs["force"] = force
        return await self.run(
            "rm",
            path,
            **kwargs,
            ctx=_fs_ctx_with_auto_pathlock(path, fs_ctx, auto_pathlock),
        )

    async def stat(
        self, path: str, *, fs_ctx: Dict[str, str] | None = None, bypass_cache: bool = False
    ) -> Dict[str, Any]:
        ctx = dict(_fs_ctx_or_default(path, fs_ctx))
        if bypass_cache:
            ctx["bypass_cache"] = "true"
        return await self.run("stat", path, ctx=ctx)

    async def mv(
        self,
        old_path: str,
        new_path: str,
        *,
        fs_ctx: Dict[str, str] | None = None,
        auto_pathlock: bool = True,
    ) -> Dict[str, Any]:
        """Move or rename a path inside AGFS."""
        ensure_same_encryption_account(old_path, new_path)
        return await self.run(
            "mv",
            old_path,
            new_path,
            ctx=_fs_ctx_with_auto_pathlock(old_path, fs_ctx, auto_pathlock),
        )

    async def cp(
        self,
        src_path: str,
        dst_path: str,
        recursive: bool = False,
        *,
        fs_ctx: Dict[str, str] | None = None,
        auto_pathlock: bool = True,
        allow_same_mount_fast_path: bool = False,
    ) -> Any:
        """Copy a path within AGFS while preserving the caller's FsContext."""
        from .helpers import cp

        return await run_to_completion(
            lambda: asyncio.to_thread(
                cp,
                self._client,
                src_path,
                dst_path,
                recursive=recursive,
                stream=True,
                fs_ctx=_fs_ctx_with_auto_pathlock(src_path, fs_ctx, auto_pathlock),
                allow_same_mount_fast_path=allow_same_mount_fast_path,
            )
        )

    async def grep(self, **kwargs: Any) -> Dict[str, Any]:
        if "ctx" not in kwargs or kwargs["ctx"] is None:
            path = kwargs.get("path")
            if isinstance(path, str):
                kwargs["ctx"] = fs_ctx_from_agfs_path(path)
        return await self.run("grep", **kwargs)

    async def tree_directory(
        self,
        path: str,
        show_hidden: bool = False,
        node_limit: int | None = None,
        level_limit: int | None = None,
        *,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str = "asc",
        directories_only: bool = False,
        fs_ctx: Dict[str, str] | None = None,
    ) -> list[Dict[str, Any]]:
        """Return a sorted range from a recursive directory traversal."""
        kwargs: Dict[str, Any] = {
            "show_hidden": show_hidden,
            "node_limit": node_limit,
            "level_limit": level_limit,
        }
        if directories_only:
            kwargs["directories_only"] = True
        if offset:
            kwargs["offset"] = offset
        if sort_by is not None:
            kwargs["sort_by"] = sort_by
            kwargs["sort_order"] = sort_order
        try:
            return await self.run(
                "tree_directory",
                path,
                **kwargs,
                ctx=_fs_ctx_or_default(path, fs_ctx),
            )
        except TypeError as exc:
            if "unexpected keyword argument" not in str(exc):
                raise
            legacy_kwargs = {
                "show_hidden": show_hidden,
                "node_limit": None if (offset or node_limit is not None or sort_by) else node_limit,
                "level_limit": level_limit,
            }
            entries = await self.run(
                "tree_directory",
                path,
                **legacy_kwargs,
                ctx=_fs_ctx_or_default(path, fs_ctx),
            )
            if sort_by:
                entries = self._sort_raw_entries(entries, sort_by=sort_by, sort_order=sort_order)
            if offset or node_limit is not None:
                start = offset
                end = None if node_limit is None else offset + node_limit
                entries = entries[start:end]
            return entries

    async def glob_directory(
        self,
        path: str,
        pattern: str,
        show_hidden: bool = False,
        page_size: int | None = None,
        level_limit: int | None = None,
        continuation_token: str | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        return await self.run(
            "glob_directory",
            path,
            pattern,
            show_hidden=show_hidden,
            page_size=page_size,
            level_limit=level_limit,
            continuation_token=continuation_token,
            ctx=_fs_ctx_or_default(path, fs_ctx),
        )

    async def system_sync_status(
        self, path: str, *, fs_ctx: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
        """Return multi-write sync status for a file or directory path."""
        return await self.run("system_sync_status", path, ctx=_fs_ctx_or_default(path, fs_ctx))

    async def system_sync_retry(
        self, path: str, *, fs_ctx: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
        """Retry pending multi-write sync work for a file or directory path."""
        return await self.run("system_sync_retry", path, ctx=_fs_ctx_or_default(path, fs_ctx))


__all__ = [
    "AsyncAGFSClient",
    "fs_ctx_from_agfs_path",
    "_fs_ctx_or_default",
    "_fs_ctx_with_auto_pathlock",
    "local_account_id_from_agfs_path",
    "encryption_account_id_from_agfs_path",
    "ensure_same_encryption_account",
    "_path_locks_disabled",
    "_disabled_pathlock_lease",
]
