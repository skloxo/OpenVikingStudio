# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Watch store kept in ``viking://resources/.watch_tasks.json``.

The task snapshot is read once at startup and reads are answered from memory.
Run occupancy belongs to this process and never writes to disk. Task changes
and settlement publish a full snapshot with tmp/backup rotation before updating
the cache. Every operation runs under one in-process lock.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from heapq import nlargest
from typing import Any, Iterable, Mapping, Optional, Sequence

from openviking.concurrency import AsyncSemaphore
from openviking.resource.watch_pagination import WatchPageQuery
from openviking.resource.watch_storage import (
    WATCH_TASK_STORAGE_BAK_URI,
    WATCH_TASK_STORAGE_TMP_URI,
    WATCH_TASK_STORAGE_URI,
)
from openviking.resource.watch_store import (
    WatchListPage,
    WatchMoveResult,
    WatchStore,
    is_connector,
    parent_uri,
    target_conflict_message,
)
from openviking.resource.watch_types import (
    PAYLOAD_FIELDS,
    PRIVATE_PATCH_FIELDS,
    PermissionDeniedError,
    WatchAuthority,
    WatchCandidate,
    WatchPatch,
    WatchRun,
    WatchRunning,
    WatchRunResult,
    WatchState,
    WatchTask,
    uri_matches_prefix,
)
from openviking_cli.exceptions import ConflictError, NotFoundError
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class _Row:
    task: WatchTask
    current_run_id: Optional[str] = None
    run_started_at: Optional[float] = None
    deleted: bool = False

    def to_storage_dict(self) -> dict[str, Any]:
        data = self.task.to_storage_dict()
        data.pop("run_source_checkpoint_version", None)
        return data

    @classmethod
    def from_storage_dict(cls, data: dict[str, Any]) -> "_Row":
        return cls(task=WatchTask.from_dict({**data, "run_source_checkpoint_version": None}))


def _changed(task: WatchTask, **values: Any) -> WatchTask:
    return WatchTask.from_dict({**task.to_storage_dict(), **values})


def _due(task: WatchTask, now: datetime) -> bool:
    return task.next_execution_time is not None and task.next_execution_time <= now


class _FileWatchStoreOpsMixin:

    @staticmethod
    def _candidate(row: _Row) -> WatchCandidate:
        task = row.task
        return WatchCandidate(
            task.task_id, task.account_id, task.user_id, task.to_uri, row.run_started_at
        )

    async def get_candidate(self, task_id: str) -> Optional[WatchCandidate]:
        self._require_initialized()
        async with self._lock:
            row = self._rows.get(task_id)
            return self._candidate(row) if row is not None and not row.deleted else None

    async def due_candidates(self, limit: int, *, offset: int = 0) -> list[WatchCandidate]:
        self._require_initialized()
        if limit <= 0:
            return []
        async with self._lock:
            now = datetime.now()
            candidates = []
            skipped = 0
            for row in self._rows.values():
                task = row.task
                next_run = task.next_execution_time
                if (
                    next_run is not None
                    and next_run <= now
                    and task.is_active
                    and not row.deleted
                    and row.run_started_at is None
                ):
                    if skipped < offset:
                        skipped += 1
                        continue
                    candidates.append(self._candidate(row))
                    if len(candidates) == limit:
                        break
            return candidates

    async def running(self, *, after: str = "", limit: int = 100) -> list[WatchRunning]:
        self._require_initialized()
        async with self._lock:
            now = time.time()
            ids = sorted(task_id for task_id in self._running if task_id > after)[:limit]
            result = []
            for task_id in ids:
                row = self._rows[task_id]
                assert row.run_started_at is not None
                result.append(
                    WatchRunning(
                        task_id=task_id,
                        account_id=row.task.account_id,
                        user_id=row.task.user_id,
                        current_run_id=row.current_run_id,
                        run_started_at=row.run_started_at,
                        now=now,
                        connector=is_connector(row.task.auth_state),
                        instruction=row.task.instruction,
                    )
                )
            return result

    async def begin_run(
        self,
        candidate: WatchCandidate,
        *,
        manual: bool = False,
    ) -> Optional[WatchRun]:
        self._require_initialized()
        async with self._lock:
            now = datetime.now()
            task_id = candidate.task_id
            row = self._rows.get(task_id)
            if (
                row is None
                or row.deleted
                or row.run_started_at is not None
                or row.task.to_uri != candidate.to_uri
                or row.task.account_id != candidate.account_id
                or row.task.user_id != candidate.user_id
                or (not manual and not (row.task.is_active and _due(row.task, now)))
            ):
                return None
            begun = replace(
                row,
                task=row.task.model_copy(
                    update={"run_source_checkpoint_version": row.task.source_checkpoint_version}
                ),
                run_started_at=now.timestamp(),
            )
            self._index({task_id: begun})
            return WatchRun(
                task_id=task_id,
                run_id=None,
                task=begun.task.model_copy(deep=True),
                started_at=begun.run_started_at,
            )

    async def attach_task(
        self,
        task_id: str,
        run_id: str,
        *,
        started_at: float,
    ) -> bool:
        self._require_initialized()
        async with self._lock:
            row = self._rows.get(task_id)
            if (
                row is None
                or row.deleted
                or row.current_run_id is not None
                or row.run_started_at != started_at
            ):
                return False
            self._index({task_id: replace(row, current_run_id=run_id)})
            return True

    async def finish_run(
        self,
        task_id: str,
        run_id: Optional[str],
        result: WatchRunResult,
        *,
        started_at: Optional[float] = None,
    ) -> bool:
        self._require_initialized()
        async with self._lock:
            row = self._rows.get(task_id)
            if (
                row is None
                or row.run_started_at is None
                or row.current_run_id != run_id
                or (started_at is not None and row.run_started_at != started_at)
            ):
                return False
            now = datetime.now()
            task = row.task
            enabled = task.is_active and not result.deactivate
            changes: dict[str, Any] = {
                "is_active": enabled,
                "next_execution_time": (
                    now + timedelta(minutes=task.watch_interval)
                    if enabled and not row.deleted
                    else None
                ),
                "last_execution_time": now,
                "last_task_id": result.execution_task_id,
                "last_status": result.status,
                "last_error": result.error,
            }
            if result.has_connector_states:
                changes["connector_states"] = result.connector_states
            if (
                result.source_checkpoint is not None
                and task.run_source_checkpoint_version == task.source_checkpoint_version
            ):
                changes["source_checkpoint"] = result.source_checkpoint
            changes["run_source_checkpoint_version"] = None
            settled = replace(
                row,
                task=_changed(task, **changes),
                current_run_id=None,
                run_started_at=None,
            )
            await self._commit({task_id: self._settled(settled)}, persist=not row.deleted)
            return True

    async def deactivate_idle(self, task_id: str, *, target_uri: Optional[str], error: str) -> bool:
        self._require_initialized()
        async with self._lock:
            row = self._rows.get(task_id)
            if (
                row is None
                or row.deleted
                or row.run_started_at is not None
                or row.task.to_uri != target_uri
            ):
                return False
            task = _changed(
                row.task,
                is_active=False,
                next_execution_time=None,
                last_execution_time=datetime.now(),
                last_task_id=None,
                last_status="failed",
                last_error=error,
            )
            await self._commit({task_id: replace(row, task=task)})
            return True

    async def has_running_overlap(self, account_id: str, uris: Sequence[str]) -> bool:
        uris = [uri for uri in uris if uri]
        self._require_initialized()
        async with self._lock:
            for task_id in self._running:
                task = self._rows[task_id].task
                if task.account_id != account_id or not task.to_uri:
                    continue
                if any(
                    uri_matches_prefix(task.to_uri, uri) or uri_matches_prefix(uri, task.to_uri)
                    for uri in uris
                ):
                    return True
            return False

    def _plan_move(
        self,
        account_id: str,
        from_uri: str,
        to_uri: str,
        task_ids: Optional[Sequence[str]],
    ) -> list[tuple[_Row, str]]:
        old_prefix, new_prefix = from_uri.rstrip("/"), to_uri.rstrip("/")
        selected_ids = None if task_ids is None else set(task_ids)
        plan = [
            (row, new_prefix + row.task.to_uri[len(old_prefix) :])
            for row in self._rows.values()
            if not row.deleted
            and row.task.account_id == account_id
            and row.task.to_uri is not None
            and uri_matches_prefix(row.task.to_uri, old_prefix)
            and (selected_ids is None or row.task.task_id in selected_ids)
        ]
        if selected_ids is not None and {row.task.task_id for row, _ in plan} != selected_ids:
            raise ConflictError(
                "Watch move source changed before the operation completed",
                resource=from_uri,
            )
        moving = {row.task.task_id for row, _ in plan}
        landing: dict[str, list[_Row]] = {}
        for row, target in plan:
            landing.setdefault(target, []).append(row)
        for target, occupants in landing.items():
            occupants.extend(
                row for row in self._on_target(account_id, target) if row.task.task_id not in moving
            )
            if len(occupants) > 1 and not all(is_connector(r.task.auth_state) for r in occupants):
                raise ConflictError(target_conflict_message(target), resource=target)
        return plan

    async def move(
        self,
        *,
        account_id: str,
        from_uri: str,
        to_uri: str,
        task_ids: Optional[Sequence[str]] = None,
    ) -> WatchMoveResult:
        self._require_initialized()
        requested_ids = None if task_ids is None else tuple(dict.fromkeys(task_ids))
        if requested_ids == ():
            return WatchMoveResult(account_id, from_uri.rstrip("/"), to_uri.rstrip("/"), ())
        async with self._lock:
            updates: dict[str, Optional[_Row]] = {}
            moved_ids: list[str] = []
            for row, target in self._plan_move(account_id, from_uri, to_uri, requested_ids):
                changes: dict[str, Any] = {"to_uri": target}
                task = row.task
                if (
                    task.to_uri is not None
                    and task.parent_uri is not None
                    and task.parent_uri == parent_uri(task.to_uri)
                ):
                    changes["parent_uri"] = parent_uri(target)
                task = _changed(task, **changes)
                if task != row.task:
                    updates[task.task_id] = replace(row, task=task)
                moved_ids.append(task.task_id)
            await self._commit(updates)
            return WatchMoveResult(
                account_id,
                from_uri.rstrip("/"),
                to_uri.rstrip("/"),
                tuple(moved_ids),
            )

    async def deactivate_under_uri(self, account_id: str, uri: str) -> list[WatchTask]:
        self._require_initialized()
        async with self._lock:
            updates: dict[str, Optional[_Row]] = {}
            matched: list[WatchTask] = []
            for task_id, row in self._rows.items():
                if (
                    row.deleted
                    or row.task.account_id != account_id
                    or not uri_matches_prefix(row.task.to_uri, uri)
                ):
                    continue
                task = row.task
                if task.is_active or task.next_execution_time is not None:
                    task = _changed(task, is_active=False, next_execution_time=None)
                    updates[task_id] = replace(row, task=task)
                matched.append(task)
            await self._commit(updates)
            return matched
