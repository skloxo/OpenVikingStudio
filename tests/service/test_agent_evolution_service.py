# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

from unittest.mock import AsyncMock, Mock

import pytest

from openviking.server.identity import RequestContext, Role
from openviking.service.agent_evolution_service import AgentEvolutionService
from openviking.session.memory.experience_lineage import (
    TRAJECTORY_OUTCOMES,
    experience_source_tag,
    trajectory_outcome_tag,
)
from openviking.storage.expr import And, Eq, PathScope, TimeRange
from openviking_cli.exceptions import InvalidArgumentError
from openviking_cli.session.user_id import UserIdentifier


def _ctx() -> RequestContext:
    return RequestContext(user=UserIdentifier("account", "alice"), role=Role.USER)


@pytest.mark.asyncio
async def test_list_trajectories_by_experience_uses_exact_scalar_filter_and_pagination():
    experience_uri = "viking://user/alice/memories/experiences/exchange.md"
    viking_fs = Mock()
    viking_fs.stat = AsyncMock(return_value={"isDir": False})
    vikingdb = Mock()
    vikingdb.filter = AsyncMock(
        return_value=[
            {
                "uri": "viking://user/alice/memories/trajectories/exchange-2.md",
                "name": "exchange-2.md",
                "updated_at": "2026-08-03T12:00:00Z",
                "_score": 1,
            }
        ]
    )
    vikingdb.count = AsyncMock(return_value=3)
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    result = await service.list_trajectories_by_experience(
        experience_uri=experience_uri,
        ctx=_ctx(),
        limit=1,
        offset=1,
    )

    assert result == {
        "experience_uri": experience_uri,
        "items": [
            {
                "uri": "viking://user/alice/memories/trajectories/exchange-2.md",
                "name": "exchange-2.md",
                "updated_at": "2026-08-03T12:00:00Z",
            }
        ],
        "total": 3,
        "limit": 1,
        "offset": 1,
        "has_more": True,
    }
    expected_filter = And(
        [
            PathScope(
                "uri",
                "viking://user/alice/memories/trajectories",
                depth=1,
            ),
            Eq("context_type", "memory"),
            Eq("level", 2),
            Eq("search_tags", experience_source_tag(experience_uri)),
        ]
    )
    assert vikingdb.filter.await_args.kwargs["filter"] == expected_filter
    assert vikingdb.filter.await_args.kwargs["limit"] == 1
    assert vikingdb.filter.await_args.kwargs["offset"] == 1
    assert vikingdb.filter.await_args.kwargs["order_by"] == "updated_at"
    assert vikingdb.filter.await_args.kwargs["order_desc"] is True
    assert vikingdb.count.await_args.kwargs["filter"] == expected_filter


@pytest.mark.asyncio
async def test_list_trajectories_by_experience_rejects_other_user_uri():
    service = AgentEvolutionService(viking_fs=Mock(), vikingdb=Mock())

    with pytest.raises(InvalidArgumentError):
        await service.list_trajectories_by_experience(
            experience_uri="viking://user/bob/memories/experiences/exchange.md",
            ctx=_ctx(),
        )


@pytest.mark.asyncio
async def test_list_trajectories_by_experience_filters_created_at_by_utc_date():
    experience_uri = "viking://user/alice/memories/experiences/exchange.md"
    viking_fs = Mock()
    viking_fs.stat = AsyncMock(return_value={"isDir": False})
    vikingdb = Mock()
    vikingdb.filter = AsyncMock(return_value=[])
    vikingdb.count = AsyncMock(return_value=0)
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    await service.list_trajectories_by_experience(
        experience_uri=experience_uri,
        ctx=_ctx(),
        start_date="2026-08-01",
        end_date="2026-08-10",
    )

    expected_filter = And(
        [
            PathScope("uri", "viking://user/alice/memories/trajectories", depth=1),
            Eq("context_type", "memory"),
            Eq("level", 2),
            Eq("search_tags", experience_source_tag(experience_uri)),
            TimeRange(
                "created_at",
                start="2026-08-01T00:00:00+00:00",
                end="2026-08-11T00:00:00+00:00",
            ),
        ]
    )
    assert vikingdb.filter.await_args.kwargs["filter"] == expected_filter
    assert vikingdb.count.await_args.kwargs["filter"] == expected_filter


@pytest.mark.asyncio
async def test_list_trajectories_by_experience_rejects_invalid_date_range():
    service = AgentEvolutionService(viking_fs=Mock(), vikingdb=Mock())

    with pytest.raises(InvalidArgumentError, match="start_date must be earlier"):
        await service.list_trajectories_by_experience(
            experience_uri="viking://user/alice/memories/experiences/exchange.md",
            ctx=_ctx(),
            start_date="2026-08-11",
            end_date="2026-08-10",
        )


@pytest.mark.asyncio
async def test_list_trajectories_by_experience_rejects_limit_above_1000():
    service = AgentEvolutionService(viking_fs=Mock(), vikingdb=Mock())

    with pytest.raises(InvalidArgumentError):
        await service.list_trajectories_by_experience(
            experience_uri="viking://user/alice/memories/experiences/exchange.md",
            ctx=_ctx(),
            limit=1001,
        )


@pytest.mark.asyncio
async def test_list_trajectories_by_experience_accepts_1000_and_paginates_all_results():
    experience_uri = "viking://user/alice/memories/experiences/exchange.md"
    viking_fs = Mock()
    viking_fs.stat = AsyncMock(return_value={"isDir": False})
    vikingdb = Mock()
    vikingdb.filter = AsyncMock(
        side_effect=[
            [
                {"uri": f"viking://user/alice/memories/trajectories/{index}.md"}
                for index in range(1000)
            ],
            [{"uri": "viking://user/alice/memories/trajectories/1000.md"}],
        ]
    )
    vikingdb.count = AsyncMock(side_effect=[1001, 1001])
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    first_page = await service.list_trajectories_by_experience(
        experience_uri=experience_uri,
        ctx=_ctx(),
        limit=1000,
    )
    second_page = await service.list_trajectories_by_experience(
        experience_uri=experience_uri,
        ctx=_ctx(),
        limit=1000,
        offset=1000,
    )

    assert len(first_page["items"]) == 1000
    assert first_page["has_more"] is True
    assert second_page["items"] == [{"uri": "viking://user/alice/memories/trajectories/1000.md"}]
    assert second_page["has_more"] is False
    assert [call.kwargs["offset"] for call in vikingdb.filter.await_args_list] == [0, 1000]


@pytest.mark.asyncio
async def test_get_experience_outcome_distribution_counts_two_tags_on_same_list_field():
    experience_uri = "viking://user/alice/memories/experiences/exchange.md"
    viking_fs = Mock()
    viking_fs.stat = AsyncMock(return_value={"isDir": False})
    vikingdb = Mock()
    vikingdb.count = AsyncMock(side_effect=[4, 2, 1, 0, 3])
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    result = await service.get_experience_outcome_distribution(
        experience_uri=experience_uri,
        ctx=_ctx(),
    )

    assert result == {
        "experience_uri": experience_uri,
        "outcome_distribution": [
            {"outcome": "success", "count": 4},
            {"outcome": "failure", "count": 2},
            {"outcome": "partial", "count": 1},
            {"outcome": "unknown", "count": 0},
            {"outcome": "unfinished", "count": 3},
        ],
    }
    assert vikingdb.count.await_count == len(TRAJECTORY_OUTCOMES)
    for call, outcome in zip(vikingdb.count.await_args_list, TRAJECTORY_OUTCOMES, strict=True):
        assert call.kwargs["filter"] == And(
            [
                PathScope(
                    "uri",
                    "viking://user/alice/memories/trajectories",
                    depth=1,
                ),
                Eq("context_type", "memory"),
                Eq("level", 2),
                Eq("search_tags", experience_source_tag(experience_uri)),
                Eq("search_tags", trajectory_outcome_tag(outcome)),
            ]
        )


@pytest.mark.asyncio
async def test_get_experience_outcome_distribution_filters_created_at_by_utc_date():
    experience_uri = "viking://user/alice/memories/experiences/exchange.md"
    viking_fs = Mock()
    viking_fs.stat = AsyncMock(return_value={"isDir": False})
    vikingdb = Mock()
    vikingdb.count = AsyncMock(return_value=0)
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    await service.get_experience_outcome_distribution(
        experience_uri=experience_uri,
        ctx=_ctx(),
        start_date="2026-08-10",
        end_date="2026-08-10",
    )

    for call, outcome in zip(vikingdb.count.await_args_list, TRAJECTORY_OUTCOMES, strict=True):
        assert call.kwargs["filter"] == And(
            [
                PathScope("uri", "viking://user/alice/memories/trajectories", depth=1),
                Eq("context_type", "memory"),
                Eq("level", 2),
                Eq("search_tags", experience_source_tag(experience_uri)),
                TimeRange(
                    "created_at",
                    start="2026-08-10T00:00:00+00:00",
                    end="2026-08-11T00:00:00+00:00",
                ),
                Eq("search_tags", trajectory_outcome_tag(outcome)),
            ]
        )


@pytest.mark.asyncio
async def test_get_experience_outcome_distribution_rejects_other_user_uri():
    service = AgentEvolutionService(viking_fs=Mock(), vikingdb=Mock())

    with pytest.raises(InvalidArgumentError):
        await service.get_experience_outcome_distribution(
            experience_uri="viking://user/bob/memories/experiences/exchange.md",
            ctx=_ctx(),
        )


@pytest.mark.asyncio
async def test_list_trajectories_accepts_master_memory_evolution_lesson_uri():
    lesson_uri = "viking://resources/master_memory/evolution_lessons/20261116_pitfall.md"
    viking_fs = Mock()
    viking_fs.stat = AsyncMock(return_value={"isDir": False})
    vikingdb = Mock()
    vikingdb.filter = AsyncMock(return_value=[])
    vikingdb.count = AsyncMock(return_value=0)
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    result = await service.list_trajectories_by_experience(
        experience_uri=lesson_uri,
        ctx=_ctx(),
    )

    assert result["experience_uri"] == lesson_uri
    assert vikingdb.filter.await_args.kwargs["filter"] == And(
        [
            PathScope("uri", "viking://user/alice/memories/trajectories", depth=1),
            Eq("context_type", "memory"),
            Eq("level", 2),
            Eq("search_tags", experience_source_tag(lesson_uri)),
        ]
    )


@pytest.mark.asyncio
async def test_list_user_experiences_merges_and_dedupes_evolution_lessons():
    viking_fs = Mock()

    async def fake_ls(root, ctx=None):
        if root == "viking://user/alice/memories/experiences":
            return [
                {"name": "shared.md", "uri": f"{root}/shared.md", "mtime": "2026-11-16T10:00:00Z", "size": 100},
                {"name": "user_only.md", "uri": f"{root}/user_only.md", "mtime": "2026-11-16T09:00:00Z", "size": 80},
                {"name": ".abstract.md", "uri": f"{root}/.abstract.md", "size": 10},
            ]
        return [
            {"name": "shared.md", "uri": f"{root}/shared.md", "mtime": "2026-11-16T08:00:00Z", "size": 100},
            {"name": "lesson_only.md", "uri": f"{root}/lesson_only.md", "mtime": "2026-11-16T11:00:00Z", "size": 220},
        ]

    viking_fs.ls = AsyncMock(side_effect=fake_ls)
    vikingdb = Mock()
    vikingdb.count = AsyncMock(side_effect=[3, 2, 1])
    service = AgentEvolutionService(viking_fs=viking_fs, vikingdb=vikingdb)

    result = await service.list_user_experiences(ctx=_ctx(), limit=10, offset=0)

    assert result["total"] == 3
    assert [item["name"] for item in result["items"]] == [
        "lesson_only.md",
        "shared.md",
        "user_only.md",
    ]
    assert [item["source"] for item in result["items"]] == [
        "evolution_lesson",
        "evolution_lesson",
        "experience",
    ]
    assert [item["trajectory_count"] for item in result["items"]] == [3, 2, 1]
