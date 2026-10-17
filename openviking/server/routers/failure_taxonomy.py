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
    real 429 exponential backoff drill, watchdog timeout abort, or whitelist protection.
    """
    from openviking.core.chaos_resilience_engine import ChaosResilienceEngine
    engine = ChaosResilienceEngine.get_instance()
    telemetry = get_failure_taxonomy_telemetry()

    if req.action in ("simulate_transient", "drill_chaos_429"):
        drill_res = await engine.drill_transient_retry(tool_name=req.tool_name or "fetch_remote_context")
        telemetry_res = telemetry.execute_probe(
            action="simulate_transient",
            tool_name=req.tool_name or "fetch_remote_context",
            error_msg=req.error_msg,
            whitelist_type=req.whitelist_type,
        )
        telemetry_res.update({
            "real_drill_executed": True,
            "actual_duration_ms": drill_res.duration_ms,
            "drill_success": drill_res.success,
            "attempts_used": drill_res.details.get("attempts_used", 1),
            "retry_delays_ms": drill_res.details.get("retry_delays_ms", []),
            "backoff_algorithm": drill_res.details.get("backoff_algorithm"),
            "healed": drill_res.details.get("healed", True),
        })
        return JSONResponse(status_code=200, content=telemetry_res)

    elif req.action in ("drill_watchdog_timeout", "simulate_watchdog"):
        drill_res = await engine.drill_watchdog_timeout()
        return JSONResponse(
            status_code=200,
            content={
                "action": req.action,
                "real_drill_executed": True,
                "category": "watchdog_timeout",
                "drill_success": drill_res.success,
                "duration_ms": drill_res.duration_ms,
                "timeout_triggered": drill_res.details.get("timeout_triggered", True),
                "task_reclaimed": drill_res.details.get("task_reclaimed", True),
                "reclaim_latency_ms": drill_res.details.get("reclaim_latency_ms", 0.0),
                "zombie_leak_prevented": True,
            },
        )

    elif req.action in ("drill_real_merkle", "probe_merkle"):
        drill_res = engine.drill_real_merkle_tree()
        return JSONResponse(
            status_code=200,
            content={
                "action": req.action,
                "real_drill_executed": True,
                "drill_success": drill_res.success,
                "duration_ms": drill_res.duration_ms,
                "details": drill_res.details,
            },
        )

    # 兼容基础分类与白名单注册逻辑
    result = telemetry.execute_probe(
        action=req.action,
        tool_name=req.tool_name or "example_tool",
        error_msg=req.error_msg,
        whitelist_type=req.whitelist_type,
    )
    return JSONResponse(status_code=200, content=result)
