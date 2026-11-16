# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Context derivation, entry sorting, and PathLock mixin helpers for AsyncAGFSClient."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from openviking.service.task_tracker_concurrency import run_to_completion
from openviking.storage.errors import InvalidPathLockRequestError

_SYSTEM_ACCOUNT_ID = "_system"
_DISABLE_PATH_LOCKS_ENV = "OPENVIKING_DISABLE_PATH_LOCKS"
_DISABLED_PATH_LOCK_OWNER_ID = "path-locks-disabled"
_PATH_LOCK_RESTORE_VALUES = {"0", "false", "no", "off"}


def _path_locks_disabled() -> bool:
    """Return whether this process should bypass every Path Lock operation."""
    value = os.environ.get(_DISABLE_PATH_LOCKS_ENV)
    return value is None or value.strip().lower() not in _PATH_LOCK_RESTORE_VALUES


def _disabled_pathlock_lease(lock_paths: list[str] | None = None) -> Dict[str, Any]:
    """Return an owned lease shape accepted by existing Path Lock call sites."""
    return {
        "lease_ref": _DISABLED_PATH_LOCK_OWNER_ID,
        "owner_id": _DISABLED_PATH_LOCK_OWNER_ID,
        "ownership_ref": _DISABLED_PATH_LOCK_OWNER_ID,
        "lock_paths": lock_paths or [],
        "covered_paths": [],
        "owned": True,
    }


def fs_ctx_from_agfs_path(path: str) -> Dict[str, str]:
    """Derive a stable FsContext from an absolute AGFS path."""
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "local" and parts[1]:
        return {"account_id": parts[1]}
    return {"account_id": _SYSTEM_ACCOUNT_ID}


def _fs_ctx_or_default(path: str, fs_ctx: Dict[str, str] | None) -> Dict[str, str]:
    """Return explicit FsContext when present, otherwise derive it from path."""
    return fs_ctx if fs_ctx is not None else fs_ctx_from_agfs_path(path)


def _fs_ctx_with_auto_pathlock(
    path: str,
    fs_ctx: Dict[str, str] | None,
    auto_pathlock: bool,
) -> Dict[str, str]:
    """Return FsContext with optional auto PathLock bypass for unlocked calls."""
    ctx = dict(_fs_ctx_or_default(path, fs_ctx))
    if _path_locks_disabled() or not auto_pathlock:
        ctx.pop("lease_ref", None)
        ctx["disable_auto_pathlock"] = "true"
    elif ctx.get("lease_ref"):
        ctx.pop("disable_auto_pathlock", None)
    return ctx


def local_account_id_from_agfs_path(path: str) -> str | None:
    """Extract the account_id from `/local/{account_id}/...`, or None for non-local paths."""
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "local" and parts[1]:
        return parts[1]
    return None


def encryption_account_id_from_agfs_path(path: str) -> str:
    """Return the account_id used by the encryption layer for this AGFS path."""
    return fs_ctx_from_agfs_path(path)["account_id"]


def ensure_same_encryption_account(src_path: str, dst_path: str) -> None:
    """Reject AGFS moves/copies across encryption-account domains."""
    src_account = encryption_account_id_from_agfs_path(src_path)
    dst_account = encryption_account_id_from_agfs_path(dst_path)
    if src_account != dst_account:
        raise ValueError(
            f"cross-account AGFS move/copy is not supported: {src_account!r} -> {dst_account!r}"
        )


def sort_raw_entries(
    entries: List[Dict[str, Any]],
    sort_by: str | None,
    sort_order: str = "asc",
) -> List[Dict[str, Any]]:
    """Sort AGFS entries when falling back to precompiled bindings without native sort."""
    if not sort_by:
        return entries
    descending = sort_order == "desc"
    directories = [
        e for e in entries if e.get("isDir", False) or e.get("info", {}).get("isDir", False)
    ]
    files = [
        e
        for e in entries
        if not (e.get("isDir", False) or e.get("info", {}).get("isDir", False))
    ]
    if sort_by == "name":

        def name_key(e: Dict[str, Any]) -> tuple[str, str]:
            name = str(e.get("name") or e.get("info", {}).get("name") or "")
            return name.lower(), name

        directories.sort(key=name_key, reverse=descending)
        files.sort(key=name_key, reverse=descending)
        return directories + files
    if sort_by == "mtime":

        def mtime_key(e: Dict[str, Any]) -> float:
            mtime = e.get("mtime") or e.get("modTime") or e.get("info", {}).get("mtime") or 0
            if isinstance(mtime, (int, float)):
                return float(mtime)
            return 0.0

        directories.sort(key=mtime_key, reverse=descending)
        files.sort(key=mtime_key, reverse=descending)
        return directories + files
    return entries


class PathLockMixin:
    """Async PathLock methods supporting native Rust SQLite locks, bypass flag, and mocks."""

    async def pathlock_acquire_exact(
        self,
        path: str,
        timeout_secs: float = 0.0,
        owner_lease_ref: Dict[str, Any] | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire an exact lock on a single path."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease([path])
        if callable(getattr(self._client, "pathlock_acquire_batch_async", None)):
            return await self.pathlock_acquire_batch(
                [{"path": path, "kind": "exact"}],
                timeout_secs,
                owner_lease_ref,
                fs_ctx=fs_ctx,
            )
        return await self.run(
            "pathlock_acquire_exact",
            _fs_ctx_or_default(path, fs_ctx),
            path,
            timeout_secs,
            owner_lease_ref,
        )

    async def pathlock_acquire_exact_batch(
        self,
        paths: list[str],
        timeout_secs: float = 0.0,
        owner_lease_ref: Dict[str, Any] | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire exact locks on multiple paths."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease(paths)
        if callable(getattr(self._client, "pathlock_acquire_batch_async", None)):
            return await self.pathlock_acquire_batch(
                [{"path": path, "kind": "exact"} for path in paths],
                timeout_secs,
                owner_lease_ref,
                fs_ctx=fs_ctx,
            )
        if not paths:
            raise ValueError("pathlock paths must not be empty")
        return await self.run(
            "pathlock_acquire_exact_batch",
            _fs_ctx_or_default(paths[0], fs_ctx),
            paths,
            timeout_secs,
            owner_lease_ref,
        )

    async def pathlock_acquire_tree(
        self,
        path: str,
        timeout_secs: float = 0.0,
        owner_lease_ref: Dict[str, Any] | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire a tree lock on a single path."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease([path])
        if callable(getattr(self._client, "pathlock_acquire_batch_async", None)):
            return await self.pathlock_acquire_batch(
                [{"path": path, "kind": "tree"}],
                timeout_secs,
                owner_lease_ref,
                fs_ctx=fs_ctx,
            )
        return await self.run(
            "pathlock_acquire_tree",
            _fs_ctx_or_default(path, fs_ctx),
            path,
            timeout_secs,
            owner_lease_ref,
        )

    async def pathlock_acquire_tree_batch(
        self,
        paths: list[str],
        timeout_secs: float = 0.0,
        owner_lease_ref: Dict[str, Any] | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire tree locks on multiple paths."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease(paths)
        if callable(getattr(self._client, "pathlock_acquire_batch_async", None)):
            return await self.pathlock_acquire_batch(
                [{"path": path, "kind": "tree"} for path in paths],
                timeout_secs,
                owner_lease_ref,
                fs_ctx=fs_ctx,
            )
        if not paths:
            raise ValueError("pathlock paths must not be empty")
        return await self.run(
            "pathlock_acquire_tree_batch",
            _fs_ctx_or_default(paths[0], fs_ctx),
            paths,
            timeout_secs,
            owner_lease_ref,
        )

    async def pathlock_acquire_exact_tree_batch(
        self,
        exact_paths: list[str],
        tree_paths: list[str],
        timeout_secs: float = 0.0,
        owner_lease_ref: Dict[str, Any] | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire a mixed batch of exact and tree locks."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease([*exact_paths, *tree_paths])
        if callable(getattr(self._client, "pathlock_acquire_batch_async", None)):
            requests = [{"path": path, "kind": "exact"} for path in exact_paths]
            requests.extend({"path": path, "kind": "tree"} for path in tree_paths)
            return await self.pathlock_acquire_batch(
                requests,
                timeout_secs,
                owner_lease_ref,
                fs_ctx=fs_ctx,
            )
        if not exact_paths and not tree_paths:
            raise ValueError("pathlock batch must not be empty")
        first = exact_paths[0] if exact_paths else tree_paths[0]
        return await self.run(
            "pathlock_acquire_exact_tree_batch",
            _fs_ctx_or_default(first, fs_ctx),
            exact_paths,
            tree_paths,
            timeout_secs,
            owner_lease_ref,
        )

    async def pathlock_acquire_batch(
        self,
        requests: list[Dict[str, str]],
        timeout_secs: float = 0.0,
        owner_lease_ref: Dict[str, Any] | None = None,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire a batch of locks from a list of request dicts."""
        if not requests:
            raise ValueError("pathlock request batch must not be empty")
        for request in requests:
            path = request.get("path")
            if not path or not path.startswith("/"):
                raise ValueError("pathlock request.path must be an absolute path")
            if request.get("kind") not in {"exact", "tree"}:
                raise ValueError("pathlock request.kind must be 'exact' or 'tree'")
        if _path_locks_disabled():
            return _disabled_pathlock_lease([request["path"] for request in requests])
        resolved_ctx = _fs_ctx_or_default(requests[0]["path"], fs_ctx)
        acquire_async = getattr(self._client, "pathlock_acquire_batch_async", None)
        if callable(acquire_async):
            future = asyncio.ensure_future(
                acquire_async(resolved_ctx, requests, timeout_secs, owner_lease_ref)
            )
            return await self._settle_pathlock_acquisition(future, resolved_ctx)
        return await self.run(
            "pathlock_acquire_batch",
            resolved_ctx,
            requests,
            timeout_secs,
            owner_lease_ref,
        )

    async def pathlock_reacquire_batch(
        self,
        requests: list[Dict[str, str]],
        owner_id: str,
        timeout_secs: float = 0.0,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Acquire fresh holders under the durable owner validated by the recovery helper."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease([r["path"] for r in requests])
        resolved_ctx = _fs_ctx_or_default(requests[0]["path"] if requests else "/", fs_ctx)
        future = asyncio.ensure_future(
            self._client.pathlock_reacquire_batch_async(
                resolved_ctx, requests, owner_id, timeout_secs
            )
        )
        return await self._settle_pathlock_acquisition(future, resolved_ctx)

    async def _settle_pathlock_acquisition(
        self, future: asyncio.Future[Dict[str, Any]], fs_ctx: Dict[str, str]
    ) -> Dict[str, Any]:
        """Release a lease that finishes acquisition after Python cancellation."""
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError as cancelled:

            async def release_acquired() -> None:
                await self.pathlock_release(await future, fs_ctx=fs_ctx)

            try:
                await run_to_completion(release_acquired)
            finally:
                raise cancelled

    async def pathlock_as_borrowed(
        self,
        owned_lease_ref: Dict[str, Any],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Create a borrowed view of an owned lease."""
        if _path_locks_disabled():
            return owned_lease_ref
        return await self.run(
            "pathlock_as_borrowed",
            _fs_ctx_or_default("/", fs_ctx),
            owned_lease_ref,
        )

    async def pathlock_refresh(
        self,
        owned_lease_ref: Dict[str, Any],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> str:
        """Refresh an owned lease. Returns 'refreshed', 'lost', or 'failed'."""
        if _path_locks_disabled():
            return "refreshed"
        return await self.run(
            "pathlock_refresh",
            _fs_ctx_or_default("/", fs_ctx),
            owned_lease_ref,
        )

    async def pathlock_release(
        self,
        owned_lease_ref: Dict[str, Any],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> None:
        """Release an owned lease."""
        if _path_locks_disabled():
            return
        await self.run(
            "pathlock_release",
            _fs_ctx_or_default("/", fs_ctx),
            owned_lease_ref,
        )

    async def pathlock_release_selected(
        self,
        owned_lease_ref: Dict[str, Any],
        lock_paths: list[str],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> None:
        """Release selected lock paths from an owned lease."""
        if _path_locks_disabled():
            return
        await self.run(
            "pathlock_release_selected",
            _fs_ctx_or_default("/", fs_ctx),
            owned_lease_ref,
            lock_paths,
        )

    async def pathlock_to_handoff(
        self,
        owned_lease_ref: Dict[str, Any],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Export a handoff ref from an owned lease."""
        if _path_locks_disabled():
            return owned_lease_ref
        return await self.run(
            "pathlock_to_handoff",
            _fs_ctx_or_default("/", fs_ctx),
            owned_lease_ref,
        )

    async def pathlock_handoff(
        self,
        owned_lease_ref: Dict[str, Any],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> None:
        """Mark an owned lease as handed off."""
        if _path_locks_disabled():
            return
        method = (
            "pathlock_handoff"
            if hasattr(self._client, "pathlock_handoff")
            else "pathlock_to_handoff"
        )
        await self.run(
            method,
            _fs_ctx_or_default("/", fs_ctx),
            owned_lease_ref,
        )

    async def pathlock_adopt(
        self,
        handoff_ref: Dict[str, Any],
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Adopt a handoff ref, returning a new owned lease."""
        if _path_locks_disabled():
            return _disabled_pathlock_lease(handoff_ref.get("lock_paths"))
        try:
            return await self.run(
                "pathlock_adopt",
                _fs_ctx_or_default("/", fs_ctx),
                handoff_ref,
            )
        except ValueError as exc:
            if str(exc).startswith("invalid lock request:"):
                raise InvalidPathLockRequestError(str(exc)) from exc
            raise

    async def pathlock_is_locked(
        self,
        path: str,
        ignore_stale: bool = True,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> bool:
        """Check if a path is locked."""
        if _path_locks_disabled():
            return False
        return await self.run(
            "pathlock_is_locked",
            _fs_ctx_or_default(path, fs_ctx),
            path,
            ignore_stale,
        )

    async def pathlock_observe(
        self,
        *,
        fs_ctx: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Return an observability snapshot of current lock state."""
        if _path_locks_disabled():
            return {
                "active_locks": 0,
                "waiting_locks": 0,
                "stale_locks_removed": 0,
                "conflicts": [],
            }
        return await self.run(
            "pathlock_observe",
            _fs_ctx_or_default("/", fs_ctx),
        )
