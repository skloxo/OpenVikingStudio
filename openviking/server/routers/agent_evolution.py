# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Agent Evolution endpoints."""

from fastapi import APIRouter, Depends, Query

from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.auth import get_request_context
from openviking.server.dependencies import get_service
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.service.agent_evolution_service import (
    DEFAULT_TRAJECTORY_PAGE_LIMIT,
    MAX_TRAJECTORY_PAGE_LIMIT,
)

router = APIRouter(prefix="/api/v1/agent-evolution", tags=["agent-evolution"])


@router.get("/overview")
async def get_agent_evolution_overview(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Aggregate high-level evolution metrics (trajectories, experiences, outcomes, 24h activity)."""
    service = get_service()
    result = await service.agent_evolution.get_evolution_overview(ctx=_ctx)
    return Response(status="ok", result=result)


@router.get("/experiences")
async def list_user_experiences(
    limit: int = Query(
        DEFAULT_TRAJECTORY_PAGE_LIMIT,
        ge=1,
        le=MAX_TRAJECTORY_PAGE_LIMIT,
    ),
    offset: int = Query(0, ge=0),
    _ctx: RequestContext = Depends(get_request_context),
):
    """List all Experience files owned by the current user with associated trajectory stats."""
    service = get_service()
    result = await service.agent_evolution.list_user_experiences(
        ctx=_ctx,
        limit=limit,
        offset=offset,
    )
    return Response(status="ok", result=result)


@router.get("/experiences/trajectories")
async def list_experience_trajectories(
    experience_uri: str | None = Query(None, description="Experience file URI (optional, lists all trajectories if omitted)"),
    limit: int = Query(
        DEFAULT_TRAJECTORY_PAGE_LIMIT,
        ge=1,
        le=MAX_TRAJECTORY_PAGE_LIMIT,
    ),
    offset: int = Query(0, ge=0),
    start_date: str | None = Query(None, description="UTC start date, inclusive (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="UTC end date, inclusive (YYYY-MM-DD)"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """List trajectories produced by commits, optionally filtered by an Experience."""
    service = get_service()
    validated_uri = validate_request_viking_uri(experience_uri, _ctx) if experience_uri else None
    result = await service.agent_evolution.list_trajectories_by_experience(
        experience_uri=validated_uri,
        ctx=_ctx,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )
    return Response(status="ok", result=result)


@router.get("/experiences/outcomes")
async def get_experience_outcome_distribution(
    experience_uri: str | None = Query(None, description="Experience file URI (optional, aggregates all trajectories if omitted)"),
    start_date: str | None = Query(None, description="UTC start date, inclusive (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="UTC end date, inclusive (YYYY-MM-DD)"),
    _ctx: RequestContext = Depends(get_request_context),
):
    """Count application trajectories by outcome, optionally for an Experience."""
    service = get_service()
    validated_uri = validate_request_viking_uri(experience_uri, _ctx) if experience_uri else None
    result = await service.agent_evolution.get_experience_outcome_distribution(
        experience_uri=validated_uri,
        ctx=_ctx,
        start_date=start_date,
        end_date=end_date,
    )
    return Response(status="ok", result=result)
