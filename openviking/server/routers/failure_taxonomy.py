# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Failure Taxonomy & Whitelist Sensor Endpoints (Card-Observability-FailureTaxonomy-WhitelistSensor / v1.5.11)."""

from dataclasses import asdict
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openviking.core.failure_taxonomy_telemetry import get_failure_taxonomy_telemetry
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext

router = APIRouter(tags=["failure_taxonomy"])


class FailureTaxonomyProbeRequest(BaseModel):
    action: str
    tool_name: Optional[str] = "example_tool"
    error_msg: Optional[str] = None
    whitelist_type: Optional[str] = "TaskPlan"


@router.get("/api/v1/system/failure_taxonomy_metrics")
async def get_failure_taxonomy_metrics(
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Get live telemetry snapshot for three-tier failure taxonomy,
    anti-loop barrier interceptions, and compression whitelist preservation.
    """
    telemetry = get_failure_taxonomy_telemetry()
    snapshot = telemetry.get_snapshot()
    return JSONResponse(status_code=200, content=asdict(snapshot))


@router.post("/api/v1/system/failure_taxonomy_probe")
async def execute_failure_taxonomy_probe(
    req: FailureTaxonomyProbeRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Execute live interactive verification probe for failure classification,
    anti-loop barrier defense, or compression whitelist payload protection.
    """
    telemetry = get_failure_taxonomy_telemetry()
    result = telemetry.execute_probe(
        action=req.action,
        tool_name=req.tool_name or "example_tool",
        error_msg=req.error_msg,
        whitelist_type=req.whitelist_type,
    )
    return JSONResponse(status_code=200, content=result)
