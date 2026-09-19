# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST Endpoints for Valet Ingestion Engine & Anti-Entropy Gate.

(Card-Memory-ValetIngestion-AntiEntropyGate / v1.5.36)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.valet_ingestion import ValetIngestionEngine, ValetTicket
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/valet", tags=["valet-ingestion"])


class HandoverRequest(BaseModel):
    uri: str = Field(..., description="Target canonical viking:// URI")
    content: str = Field(..., description="Payload markdown or text content")
    source: str = Field("api", description="Source channel (api, webdav, mcp, worker)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata key-value map")
    caller: str = Field("Agent", description="Caller identifier or agent name")


class HandoverItem(BaseModel):
    uri: str = Field(..., description="Target canonical viking:// URI")
    content: str = Field(..., description="Payload content")
    source: str = Field("batch", description="Source channel")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    caller: str = Field("BatchAgent")


class BatchHandoverRequest(BaseModel):
    items: List[HandoverItem] = Field(..., description="List of items for high-throughput batch handover")


@router.post("/handover", status_code=status.HTTP_202_ACCEPTED)
async def valet_handover(
    req: HandoverRequest,
    response: Response,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Driver hands over payload, instantly returns HTTP 202 Ticket (<2ms)."""
    engine = ValetIngestionEngine.get_instance()
    ticket = engine.handover(
        uri=req.uri,
        content=req.content,
        source=req.source,
        metadata=req.metadata,
        caller=req.caller or (ctx.user.user_id if ctx.user else "Agent"),
    )
    response.status_code = status.HTTP_202_ACCEPTED
    return ticket.to_dict()


@router.get("/ticket/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve ticket status from the Valet Ingestion Engine."""
    engine = ValetIngestionEngine.get_instance()
    ticket = engine.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Valet ticket not found: {ticket_id}")
    return ticket.to_dict()


@router.get("/tickets")
async def list_tickets(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of recent tickets to return"),
    ctx: RequestContext = Depends(get_request_context),
) -> List[Dict[str, Any]]:
    """List recent tickets processed by Valet Ingestion Engine."""
    engine = ValetIngestionEngine.get_instance()
    tickets = engine.list_tickets(limit=limit)
    return [t.to_dict() for t in tickets]


@router.get("/stats")
async def get_valet_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve real-time metrics (throughput, handover latency, queue depth, dedup ratio)."""
    engine = ValetIngestionEngine.get_instance()
    return engine.get_valet_stats()


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def batch_valet_handover(
    req: BatchHandoverRequest,
    response: Response,
    ctx: RequestContext = Depends(get_request_context),
) -> List[Dict[str, Any]]:
    """Batch handover of multiple knowledge nodes with non-blocking 202 tickets."""
    engine = ValetIngestionEngine.get_instance()
    tickets: List[Dict[str, Any]] = []
    for item in req.items:
        t = engine.handover(
            uri=item.uri,
            content=item.content,
            source=item.source,
            metadata=item.metadata,
            caller=item.caller or (ctx.user.user_id if ctx.user else "BatchAgent"),
        )
        tickets.append(t.to_dict())
    response.status_code = status.HTTP_202_ACCEPTED
    return tickets
