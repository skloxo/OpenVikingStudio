# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Agent Evolution product queries."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

from openviking.server.identity import RequestContext
from openviking.session.memory.experience_lineage import (
    _EXPERIENCE_SIDECAR_FILENAMES,
    TRAJECTORY_OUTCOMES,
    canonical_experience_uri,
    experience_source_tag,
    trajectory_outcome_tag,
)
from openviking.storage.expr import And, Eq, PathScope, TimeRange
from openviking.storage.viking_fs import VikingFS
from openviking_cli.exceptions import InvalidArgumentError, NotInitializedError

if TYPE_CHECKING:
    from openviking.storage.vikingdb_manager import VikingDBManager

DEFAULT_TRAJECTORY_PAGE_LIMIT = 50
MAX_TRAJECTORY_PAGE_LIMIT = 1000

_TRAJECTORY_OUTPUT_FIELDS = [
    "uri",
    "name",
    "description",
    "created_at",
    "updated_at",
]


def _trajectory_created_at_range(
    start_date: Optional[str],
    end_date: Optional[str],
) -> Optional[TimeRange]:
    """Build a UTC, end-date-inclusive filter over trajectory creation time."""
    normalized_start = (start_date or "").strip()
    normalized_end = (end_date or "").strip()
    if not normalized_start and not normalized_end:
        return None

    def parse_date(value: str, field: str) -> date:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise InvalidArgumentError(f"{field} must be a valid YYYY-MM-DD date") from exc
        if parsed.isoformat() != value:
            raise InvalidArgumentError(f"{field} must use YYYY-MM-DD format")
        return parsed

    start = parse_date(normalized_start, "start_date") if normalized_start else None
    end = parse_date(normalized_end, "end_date") if normalized_end else None
    if start is not None and end is not None and start > end:
        raise InvalidArgumentError("start_date must be earlier than or equal to end_date")

    start_time = (
        datetime.combine(start, time.min, tzinfo=timezone.utc).isoformat()
        if start is not None
        else None
    )
    # TimeRange uses an exclusive upper bound. Advancing one day keeps end_date inclusive.
    end_time = (
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc).isoformat()
        if end is not None
        else None
    )
    return TimeRange("created_at", start=start_time, end=end_time)


def _experience_trajectory_conditions(
    *,
    trajectory_root: str,
    experience_uri: str,
    created_at_range: Optional[TimeRange],
) -> list[Any]:
    conditions: list[Any] = [
        PathScope("uri", trajectory_root, depth=1),
        Eq("context_type", "memory"),
        Eq("level", 2),
        Eq("search_tags", experience_source_tag(experience_uri)),
    ]
    if created_at_range is not None:
        conditions.append(created_at_range)
    return conditions


class AgentEvolutionService:
    """Serve exact, non-semantic Agent Evolution lineage queries."""

    def __init__(
        self,
        viking_fs: Optional[VikingFS] = None,
        vikingdb: Optional[VikingDBManager] = None,
    ):
        self._viking_fs = viking_fs
        self._vikingdb = vikingdb

    def set_dependencies(self, *, viking_fs: VikingFS, vikingdb: VikingDBManager) -> None:
        self._viking_fs = viking_fs
        self._vikingdb = vikingdb

    def _ensure_initialized(self) -> VikingFS:
        if self._viking_fs is None:
            raise NotInitializedError("VikingFS")
        return self._viking_fs

    async def _prepare_experience_query(
        self,
        *,
        experience_uri: str,
        ctx: RequestContext,
    ) -> tuple[str, str, VikingDBManager]:
        canonical_uri = canonical_experience_uri(experience_uri, ctx)
        if canonical_uri is None:
            raise InvalidArgumentError(
                "experience_uri must identify an Experience owned by the current user"
            )

        viking_fs = self._ensure_initialized()
        stat = await viking_fs.stat(canonical_uri, ctx=ctx, skip_count=True)
        if stat.get("isDir", False):
            raise InvalidArgumentError("experience_uri must identify an Experience file")

        if self._vikingdb is None:
            raise NotInitializedError("VikingDB")

        trajectory_root = f"viking://user/{ctx.user.user_id}/memories/trajectories"
        return canonical_uri, trajectory_root, self._vikingdb

    async def list_trajectories_by_experience(
        self,
        *,
        experience_uri: Optional[str] = None,
        ctx: RequestContext,
        limit: int = DEFAULT_TRAJECTORY_PAGE_LIMIT,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """List trajectories produced by commits, optionally filtered by an Experience."""
        if limit < 1 or limit > MAX_TRAJECTORY_PAGE_LIMIT:
            raise InvalidArgumentError(f"limit must be between 1 and {MAX_TRAJECTORY_PAGE_LIMIT}")
        if offset < 0:
            raise InvalidArgumentError("offset must be greater than or equal to 0")
        created_at_range = _trajectory_created_at_range(start_date, end_date)

        trajectory_root = f"viking://user/{ctx.user.user_id}/memories/trajectories"
        if self._vikingdb is None:
            raise NotInitializedError("VikingDB")

        if experience_uri:
            canonical_uri, trajectory_root, vikingdb = await self._prepare_experience_query(
                experience_uri=experience_uri,
                ctx=ctx,
            )
            conditions = _experience_trajectory_conditions(
                trajectory_root=trajectory_root,
                experience_uri=canonical_uri,
                created_at_range=created_at_range,
            )
        else:
            canonical_uri = None
            vikingdb = self._vikingdb
            conditions = [
                PathScope("uri", trajectory_root, depth=1),
                Eq("context_type", "memory"),
                Eq("level", 2),
            ]
            if created_at_range is not None:
                conditions.append(created_at_range)

        lineage_filter = And(conditions)
        records, total = await asyncio.gather(
            vikingdb.filter(
                filter=lineage_filter,
                limit=limit,
                offset=offset,
                output_fields=_TRAJECTORY_OUTPUT_FIELDS,
                order_by="updated_at",
                order_desc=True,
                ctx=ctx,
            ),
            vikingdb.count(filter=lineage_filter, ctx=ctx),
        )
        items = [
            {field: record.get(field) for field in _TRAJECTORY_OUTPUT_FIELDS if field in record}
            for record in records
        ]
        return {
            "experience_uri": canonical_uri,
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        }

    async def get_experience_outcome_distribution(
        self,
        *,
        experience_uri: Optional[str] = None,
        ctx: RequestContext,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Count application trajectories by outcome, optionally for an Experience."""
        created_at_range = _trajectory_created_at_range(start_date, end_date)
        trajectory_root = f"viking://user/{ctx.user.user_id}/memories/trajectories"
        if self._vikingdb is None:
            raise NotInitializedError("VikingDB")

        if experience_uri:
            canonical_uri, trajectory_root, vikingdb = await self._prepare_experience_query(
                experience_uri=experience_uri,
                ctx=ctx,
            )
            base_conditions = _experience_trajectory_conditions(
                trajectory_root=trajectory_root,
                experience_uri=canonical_uri,
                created_at_range=created_at_range,
            )
        else:
            canonical_uri = None
            vikingdb = self._vikingdb
            base_conditions = [
                PathScope("uri", trajectory_root, depth=1),
                Eq("context_type", "memory"),
                Eq("level", 2),
            ]
            if created_at_range is not None:
                base_conditions.append(created_at_range)

        counts = await asyncio.gather(
            *[
                vikingdb.count(
                    filter=And(
                        [
                            *base_conditions,
                            Eq("search_tags", trajectory_outcome_tag(outcome)),
                        ]
                    ),
                    ctx=ctx,
                )
                for outcome in TRAJECTORY_OUTCOMES
            ]
        )
        return {
            "experience_uri": canonical_uri,
            "outcome_distribution": [
                {"outcome": outcome, "count": count}
                for outcome, count in zip(TRAJECTORY_OUTCOMES, counts, strict=True)
            ],
        }

    async def get_evolution_overview(
        self,
        *,
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Aggregate high-level evolution metrics (trajectories, experiences, outcomes, 24h activity)."""
        viking_fs = self._ensure_initialized()
        if self._vikingdb is None:
            raise NotInitializedError("VikingDB")

        trajectory_root = f"viking://user/{ctx.user.user_id}/memories/trajectories"
        experience_root = f"viking://user/{ctx.user.user_id}/memories/experiences"

        base_filter = And(
            [
                PathScope("uri", trajectory_root, depth=1),
                Eq("context_type", "memory"),
                Eq("level", 2),
            ]
        )

        # 24H time range
        now = datetime.now(timezone.utc)
        one_day_ago = (now - timedelta(days=1)).isoformat()
        active_24h_filter = And(
            [
                PathScope("uri", trajectory_root, depth=1),
                Eq("context_type", "memory"),
                Eq("level", 2),
                TimeRange("created_at", start=one_day_ago),
            ]
        )

        outcome_tasks = [
            self._vikingdb.count(
                filter=And([base_filter, Eq("search_tags", trajectory_outcome_tag(outcome))]),
                ctx=ctx,
            )
            for outcome in TRAJECTORY_OUTCOMES
        ]

        total_trajectories_task = self._vikingdb.count(filter=base_filter, ctx=ctx)
        active_24h_task = self._vikingdb.count(filter=active_24h_filter, ctx=ctx)

        async def count_experiences() -> int:
            try:
                entries = await viking_fs.ls(experience_root, ctx=ctx)
                return sum(
                    1
                    for entry in (entries if isinstance(entries, list) else [])
                    if isinstance(entry, dict)
                    and not entry.get("isDir", False)
                    and entry.get("name", "") not in _EXPERIENCE_SIDECAR_FILENAMES
                )
            except Exception:
                return 0

        total_trajectories, active_24h, total_experiences, *outcome_counts = await asyncio.gather(
            total_trajectories_task,
            active_24h_task,
            count_experiences(),
            *outcome_tasks,
        )

        outcomes_summary = {
            outcome: count
            for outcome, count in zip(TRAJECTORY_OUTCOMES, outcome_counts, strict=True)
        }

        success_count = outcomes_summary.get("success", 0)
        failure_count = outcomes_summary.get("failure", 0)
        resolved_count = success_count + failure_count
        success_rate = round((success_count / resolved_count) * 100, 1) if resolved_count > 0 else 0.0

        return {
            "total_trajectories": total_trajectories,
            "total_experiences": total_experiences,
            "outcomes_summary": outcomes_summary,
            "success_rate": success_rate,
            "recent_24h_active_count": active_24h,
        }

    async def list_user_experiences(
        self,
        *,
        ctx: RequestContext,
        limit: int = DEFAULT_TRAJECTORY_PAGE_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List all Experience files owned by the current user with associated trajectory stats."""
        viking_fs = self._ensure_initialized()
        experience_root = f"viking://user/{ctx.user.user_id}/memories/experiences"

        try:
            entries = await viking_fs.ls(experience_root, ctx=ctx)
        except Exception:
            entries = []

        valid_entries = [
            entry
            for entry in (entries if isinstance(entries, list) else [])
            if isinstance(entry, dict)
            and not entry.get("isDir", False)
            and entry.get("name", "") not in _EXPERIENCE_SIDECAR_FILENAMES
        ]

        total = len(valid_entries)
        paged_entries = valid_entries[offset : offset + limit]

        items = []
        for entry in paged_entries:
            uri = entry.get("uri") or f"{experience_root}/{entry.get('name')}"
            name = entry.get("name") or uri.split("/")[-1]

            traj_count = 0
            if self._vikingdb is not None:
                try:
                    trajectory_root = f"viking://user/{ctx.user.user_id}/memories/trajectories"
                    lineage_filter = And(
                        _experience_trajectory_conditions(
                            trajectory_root=trajectory_root,
                            experience_uri=uri,
                            created_at_range=None,
                        )
                    )
                    traj_count = await self._vikingdb.count(filter=lineage_filter, ctx=ctx)
                except Exception:
                    traj_count = 0

            items.append(
                {
                    "uri": uri,
                    "name": name,
                    "trajectory_count": traj_count,
                    "updated_at": entry.get("updated_at") or entry.get("mtime") or None,
                    "size": entry.get("size", 0),
                }
            )

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        }
