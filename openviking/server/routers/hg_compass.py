# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for HG-RAG Hierarchical Compass Topology & Navigation.
(Card-Knowledge-HG-RAG-HierarchicalCompass / v1.5.19)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.retrieve.compass_topology import CompassDirection, CompassNode, NavigationResult
from openviking.retrieve.read_write_decoupling import KnowledgeDeskManager, KnowledgeDeskStats

router = APIRouter(tags=["hg_compass"])


class NavigateRequest(BaseModel):
    anchor_id: str
    direction: CompassDirection
    child_index: int = Field(default=0, ge=0)


class LineageRequest(BaseModel):
    node_id: str


@router.get("/api/v1/rag/compass/stats")
async def get_compass_stats(_ctx: RequestContext = Depends(get_request_context)):
    """Get operational statistics for the read/write decoupled knowledge desk."""
    manager = KnowledgeDeskManager.get_instance()
    stats = manager.get_stats()
    return JSONResponse(status_code=200, content=stats.model_dump())


@router.get("/api/v1/rag/compass/node/{node_id}")
async def get_compass_node(
    node_id: str,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Retrieve node details and available compass directions."""
    manager = KnowledgeDeskManager.get_instance()
    nav = manager.get_serving_navigator()
    node = nav.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    available = nav.get_available_directions(node_id)
    return JSONResponse(
        status_code=200,
        content={
            "node": node.model_dump(),
            "available_directions": [d.value for d in available],
        },
    )


@router.post("/api/v1/rag/compass/navigate")
async def navigate_compass(
    req: NavigateRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Navigate one step in the specified compass direction (north, south, east, west)."""
    manager = KnowledgeDeskManager.get_instance()
    nav = manager.get_serving_navigator()
    res = nav.navigate(
        anchor_id=req.anchor_id,
        direction=req.direction,
        child_index=req.child_index,
    )
    return JSONResponse(status_code=200, content=res.model_dump())


@router.post("/api/v1/rag/compass/lineage")
async def get_node_lineage(
    req: LineageRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get self-contained breadcrumb ancestor lineage from root down to this node."""
    manager = KnowledgeDeskManager.get_instance()
    nav = manager.get_serving_navigator()
    chain = nav.get_full_lineage(req.node_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Node '{req.node_id}' not found")

    return JSONResponse(
        status_code=200,
        content={
            "node_id": req.node_id,
            "depth": chain[-1].depth,
            "breadcrumbs": chain[-1].breadcrumbs,
            "lineage_chain": [n.model_dump() for n in chain],
        },
    )
