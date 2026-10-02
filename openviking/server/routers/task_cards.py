# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Task card endpoints for autonomous agent issue filing and triage."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.service.task_card_manager import TaskCardManager

logger = logging.getLogger("openviking.server.routers.task_cards")

router = APIRouter(prefix="/api/v1", tags=["task-cards"])


class FileTaskCardPayload(BaseModel):
    title: str = Field(description="任务卡片简明标题")
    priority: str = Field(default="P1", description="优先级: P0 | P1 | P2 | P3")
    module: str = Field(description="受影响模块")
    symptom: str = Field(description="物理现象与脱水错误日志")
    root_cause_hypothesis: Optional[str] = Field(default="", description="根因推测")
    reproduce_steps: Optional[str] = Field(default="", description="复现路径与临时方案")
    suggested_action: Optional[str] = Field(default="", description="建议修复方向")


class ResolveTaskCardPayload(BaseModel):
    resolution_tag: str = Field(description="交付版本 Tag (如 v1.6.4)")
    commit_hash: Optional[str] = Field(default="", description="Git Commit Hash")
    summary: Optional[str] = Field(default="", description="解决概述")


@router.post("/task-cards/file")
async def file_task_card(
    payload: FileTaskCardPayload,
    _ctx: RequestContext = Depends(get_request_context),
):
    """File or aggregate an autonomous issue task card from any cluster agent."""
    mgr = TaskCardManager.get_instance()
    # Resolve initiator from context identity
    initiator = "agent"
    if _ctx and _ctx.user and _ctx.user.user_id:
        initiator = _ctx.user.user_id

    try:
        res = await mgr.file_issue_card(
            title=payload.title,
            priority=payload.priority,
            module=payload.module,
            symptom=payload.symptom,
            initiator=initiator,
            root_cause_hypothesis=payload.root_cause_hypothesis or "",
            reproduce_steps=payload.reproduce_steps or "",
            suggested_action=payload.suggested_action or "",
        )
        return Response(status="ok", result=res).model_dump(exclude_none=True)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error("Failed to file task card: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to file task card: {e}")


@router.get("/task-cards/pending")
async def list_pending_task_cards(
    _ctx: RequestContext = Depends(get_request_context),
):
    """List all active pending cards sorted by priority for master triage."""
    mgr = TaskCardManager.get_instance()
    cards = await mgr.list_pending_cards()
    return Response(status="ok", result={"total": len(cards), "cards": cards}).model_dump(exclude_none=True)


@router.post("/task-cards/{card_id}/resolve")
async def resolve_task_card(
    card_id: str,
    payload: ResolveTaskCardPayload,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Archive a task card as resolved with Git tag and commit traceability."""
    mgr = TaskCardManager.get_instance()
    try:
        res = await mgr.resolve_card(
            card_id=card_id,
            resolution_tag=payload.resolution_tag,
            commit_hash=payload.commit_hash or "",
            summary=payload.summary or "",
        )
        return Response(status="ok", result=res).model_dump(exclude_none=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task card {card_id} not found in pending inbox")
    except Exception as e:
        logger.error("Failed to resolve task card: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
