# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
HITL Approval Center & Read-Side Offload Endpoints (Card-Observability-ReadOffload-HITLApprovalCenter / v1.5.12).
"""

from dataclasses import asdict
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openviking.core.hitl_offload_telemetry import HITLOffloadTelemetry
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext

router = APIRouter(tags=["hitl_offload"])


class HITLResolveRequest(BaseModel):
    action_id: str
    decision: str  # "approve" | "reject"
    comment: Optional[str] = None
    resolved_by: Optional[str] = "operator"


class HITLOffloadProbeRequest(BaseModel):
    probe_type: str  # "simulate_read_offload" | "simulate_hitl_intercept" | "reset"
    target_path: Optional[str] = None
    line_count: Optional[int] = 1200
    tool_name: Optional[str] = "deploy_production"
    command: Optional[str] = None
    danger_reason: Optional[str] = None


@router.get("/api/v1/system/hitl_offload_metrics")
async def get_hitl_offload_metrics(
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Get live telemetry snapshot for read-side offloaded tokens,
    active FileRefHandles, pending HITL dangerous actions, and approval audit logs.
    """
    telemetry = HITLOffloadTelemetry()
    data = telemetry.get_metrics_snapshot()
    return JSONResponse(status_code=200, content=data)


@router.post("/api/v1/hitl/resolve")
async def resolve_hitl_action(
    req: HITLResolveRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Approve or reject a pending Human-In-The-Loop dangerous action.
    If approved, generates and authorizes approval token in HITLGate.
    """
    telemetry = HITLOffloadTelemetry()
    item = telemetry.resolve_action(
        action_id=req.action_id,
        decision=req.decision,
        resolved_by=req.resolved_by or "operator",
        comment=req.comment,
    )
    if not item:
        raise HTTPException(status_code=404, detail=f"Pending action '{req.action_id}' not found.")

    return JSONResponse(status_code=200, content={"status": "ok", "action": asdict(item)})


@router.post("/api/v1/hitl/probe")
async def execute_hitl_offload_probe(
    req: HITLOffloadProbeRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """
    Execute live interactive verification probe for read-side offload simulation
    or HITL dangerous operation interception simulation.
    """
    telemetry = HITLOffloadTelemetry()

    if req.probe_type == "simulate_read_offload":
        path = req.target_path or "openviking/pipeline/orchestrator_large_dump.py"
        lines = req.line_count or 1500
        size_b = lines * 38
        content_hash = hashlib.sha256(f"{path}:{lines}:{size_b}".encode()).hexdigest()
        record = telemetry.record_read_offload(
            target_path=path,
            total_lines=lines,
            total_bytes=size_b,
            content_hash=content_hash,
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "probe_type": req.probe_type,
                "record": asdict(record),
                "message": f"成功模拟 Offload 文件 {path} ({lines}行)，节约 {record.tokens_saved} Tokens！",
            },
        )

    elif req.probe_type == "simulate_hitl_intercept":
        tool = req.tool_name or "run_command"
        args_summary = f"CommandLine='{req.command or 'rm -rf /var/data/models/*'}'"
        reason = req.danger_reason or "命令包含高危破坏性指令模式: 'rm -rf'"
        item = telemetry.record_dangerous_intercept(
            tool_name=tool,
            args_summary=args_summary,
            danger_reason=reason,
            phase="testing",
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "probe_type": req.probe_type,
                "action": asdict(item),
                "message": f"成功模拟拦截高危操作 '{tool}'，已注入待审队列 (ID: {item.action_id})！",
            },
        )

    elif req.probe_type == "reset":
        telemetry.reset_for_tests()
        return JSONResponse(status_code=200, content={"status": "ok", "message": "已重置遥测数据"})

    raise HTTPException(status_code=400, detail=f"Unknown probe_type: {req.probe_type}")
