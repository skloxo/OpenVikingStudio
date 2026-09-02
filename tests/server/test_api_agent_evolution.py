# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import httpx


async def test_list_experience_trajectories_uses_default_pagination(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    captured = {}

    async def fake_list(*, experience_uri, ctx, limit, offset, start_date, end_date):
        captured.update(
            experience_uri=experience_uri,
            ctx=ctx,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )
        return {
            "experience_uri": experience_uri,
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "has_more": False,
        }

    monkeypatch.setattr(
        service.agent_evolution,
        "list_trajectories_by_experience",
        fake_list,
    )
    uri = "viking://user/default/memories/experiences/exchange.md"

    response = await client.get(
        "/api/v1/agent-evolution/experiences/trajectories",
        params={"experience_uri": uri},
    )

    assert response.status_code == 200
    assert response.json()["result"]["limit"] == 50
    assert captured["experience_uri"] == uri
    assert captured["limit"] == 50
    assert captured["offset"] == 0
    assert captured["start_date"] is None
    assert captured["end_date"] is None


async def test_list_experience_trajectories_passes_date_range(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    captured = {}

    async def fake_list(**kwargs):
        captured.update(kwargs)
        return {
            "experience_uri": kwargs["experience_uri"],
            "items": [],
            "total": 0,
            "limit": kwargs["limit"],
            "offset": kwargs["offset"],
            "has_more": False,
        }

    monkeypatch.setattr(service.agent_evolution, "list_trajectories_by_experience", fake_list)
    response = await client.get(
        "/api/v1/agent-evolution/experiences/trajectories",
        params={
            "experience_uri": "viking://user/default/memories/experiences/exchange.md",
            "start_date": "2026-08-01",
            "end_date": "2026-08-10",
        },
    )

    assert response.status_code == 200
    assert captured["start_date"] == "2026-08-01"
    assert captured["end_date"] == "2026-08-10"


async def test_list_experience_trajectories_rejects_limit_above_1000(
    client: httpx.AsyncClient,
):
    response = await client.get(
        "/api/v1/agent-evolution/experiences/trajectories",
        params={
            "experience_uri": "viking://user/default/memories/experiences/exchange.md",
            "limit": 1001,
        },
    )

    assert response.status_code == 400


async def test_get_experience_outcome_distribution(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    captured = {}

    async def fake_get(*, experience_uri, ctx, start_date, end_date):
        captured.update(
            experience_uri=experience_uri,
            ctx=ctx,
            start_date=start_date,
            end_date=end_date,
        )
        return {
            "experience_uri": experience_uri,
            "outcome_distribution": [{"outcome": "success", "count": 2}],
        }

    monkeypatch.setattr(
        service.agent_evolution,
        "get_experience_outcome_distribution",
        fake_get,
    )
    uri = "viking://user/default/memories/experiences/exchange.md"

    response = await client.get(
        "/api/v1/agent-evolution/experiences/outcomes",
        params={"experience_uri": uri},
    )

    assert response.status_code == 200
    assert response.json()["result"] == {
        "experience_uri": uri,
        "outcome_distribution": [{"outcome": "success", "count": 2}],
    }
    assert captured["experience_uri"] == uri
    assert captured["start_date"] is None
    assert captured["end_date"] is None


async def test_get_experience_outcome_distribution_passes_date_range(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    captured = {}

    async def fake_get(**kwargs):
        captured.update(kwargs)
        return {
            "experience_uri": kwargs["experience_uri"],
            "outcome_distribution": [],
        }

    monkeypatch.setattr(
        service.agent_evolution,
        "get_experience_outcome_distribution",
        fake_get,
    )
    response = await client.get(
        "/api/v1/agent-evolution/experiences/outcomes",
        params={
            "experience_uri": "viking://user/default/memories/experiences/exchange.md",
            "start_date": "2026-08-01",
            "end_date": "2026-08-10",
        },
    )

    assert response.status_code == 200
    assert captured["start_date"] == "2026-08-01"
    assert captured["end_date"] == "2026-08-10"


async def test_get_agent_evolution_overview(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    fake_overview = {
        "total_trajectories": 18,
        "total_experiences": 3,
        "outcomes_summary": {
            "success": 15,
            "failure": 2,
            "partial": 1,
            "unknown": 0,
            "unfinished": 0,
        },
        "success_rate": 88.2,
        "recent_24h_active_count": 5,
    }

    async def fake_get(*, ctx):
        return fake_overview

    monkeypatch.setattr(service.agent_evolution, "get_evolution_overview", fake_get)
    response = await client.get("/api/v1/agent-evolution/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["total_trajectories"] == 18
    assert data["result"]["success_rate"] == 88.2


async def test_list_user_experiences(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    fake_experiences = {
        "items": [
            {
                "uri": "viking://user/default/memories/experiences/exchange.md",
                "name": "exchange.md",
                "trajectory_count": 12,
                "updated_at": "2026-08-24T10:00:00Z",
                "size": 1024,
            }
        ],
        "total": 1,
        "limit": 50,
        "offset": 0,
        "has_more": False,
    }

    async def fake_list(*, ctx, limit, offset):
        return fake_experiences

    monkeypatch.setattr(service.agent_evolution, "list_user_experiences", fake_list)
    response = await client.get("/api/v1/agent-evolution/experiences")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["result"]["items"]) == 1
    assert data["result"]["items"][0]["name"] == "exchange.md"
    assert data["result"]["items"][0]["trajectory_count"] == 12


async def test_list_experience_trajectories_optional_uri(
    client: httpx.AsyncClient,
    service,
    monkeypatch,
):
    captured = {}

    async def fake_list(*, experience_uri, ctx, limit, offset, start_date, end_date):
        captured.update(experience_uri=experience_uri)
        return {
            "experience_uri": experience_uri,
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "has_more": False,
        }

    monkeypatch.setattr(service.agent_evolution, "list_trajectories_by_experience", fake_list)
    response = await client.get("/api/v1/agent-evolution/experiences/trajectories")

    assert response.status_code == 200
    assert captured["experience_uri"] is None

