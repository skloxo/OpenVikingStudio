# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST router for Knowledge Deficit Capture, Stage-1 Scaffolding & Dual-Track Fulfillment."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.server.models import Response
from openviking.service.knowledge_deficit import BlindspotLedger

router = APIRouter(prefix="/api/v1/knowledge-deficits", tags=["knowledge-deficits"])


class RecordMissPayload(BaseModel):
    query: str = Field(description="触发零命中或低分检索的 Query")
    top_score: float = Field(default=0.0, ge=0.0, le=1.0)
    operation: str = Field(default="search")
    force_promote: bool = Field(default=False, description="是否跳过冷观察阈值直接铸造骨架卡")


class FulfillDeficitPayload(BaseModel):
    content: str = Field(default="", description="补充知识 Markdown 正文")
    fields: Optional[Dict[str, str]] = Field(default=None, description="结构化槽位键值对")
    track: str = Field(default="", description="human_assistance | autonomous_researcher")


class DismissDeficitPayload(BaseModel):
    reason: str = Field(default="", description="忽略原因说明")


@router.get("/summary")
async def get_deficits_summary(_ctx: RequestContext = Depends(get_request_context)):
    ledger = BlindspotLedger.get_instance()
    return Response(status="ok", result=ledger.get_summary()).model_dump(exclude_none=True)


@router.get("")
async def list_deficits(
    status: Optional[str] = Query(default="all", description="observing|pending_fulfillment|fulfilled|dismissed|all"),
    limit: int = Query(default=100, ge=1, le=500),
    _ctx: RequestContext = Depends(get_request_context),
):
    ledger = BlindspotLedger.get_instance()
    items = ledger.list_deficits(status=status, limit=limit)
    return Response(status="ok", result={"total": len(items), "items": items}).model_dump(exclude_none=True)


@router.post("/record-miss")
async def record_miss(
    payload: RecordMissPayload,
    ctx: RequestContext = Depends(get_request_context),
):
    ledger = BlindspotLedger.get_instance()
    account_id = getattr(ctx, "account_id", None) or "default"
    user_id = getattr(getattr(ctx, "user", None), "user_id", None) or "default"
    item = ledger.record_miss(
        payload.query,
        top_score=payload.top_score,
        operation=payload.operation,
        account_id=account_id,
        user_id=user_id,
        force_promote=payload.force_promote,
    )
    if item is None:
        raise HTTPException(status_code=400, detail="Query ignored by deficit filter")
    return Response(status="ok", result=item).model_dump(exclude_none=True)


@router.post("/{deficit_id}/scaffold")
async def cast_scaffold(deficit_id: str, _ctx: RequestContext = Depends(get_request_context)):
    ledger = BlindspotLedger.get_instance()
    try:
        item = ledger.cast_scaffold(deficit_id)
        return Response(status="ok", result=item).model_dump(exclude_none=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{deficit_id}/fulfill")
async def fulfill_deficit(
    deficit_id: str,
    payload: FulfillDeficitPayload,
    _ctx: RequestContext = Depends(get_request_context),
):
    ledger = BlindspotLedger.get_instance()
    try:
        item = ledger.fulfill_deficit(
            deficit_id,
            content=payload.content,
            fields=payload.fields,
            track=payload.track,
        )
        return Response(status="ok", result=item).model_dump(exclude_none=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{deficit_id}/dismiss")
async def dismiss_deficit(
    deficit_id: str,
    payload: Optional[DismissDeficitPayload] = None,
    _ctx: RequestContext = Depends(get_request_context),
):
    ledger = BlindspotLedger.get_instance()
    try:
        item = ledger.dismiss_deficit(deficit_id, reason=(payload.reason if payload else ""))
        return Response(status="ok", result=item).model_dump(exclude_none=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
