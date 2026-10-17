# -*- coding: utf-8 -*-
"""FastAPI Router for Context Router Pipeline.

Fulfills BLUEPRINT.md Topic 5 Section 4.2.
Exposes:
- POST /api/v1/context-router/route
- POST /api/v1/context-router/segment
- GET  /api/v1/context-router/stats
- POST /api/v1/context-router/reset-stats
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from openviking.service.context_router_engine import ContextRouterEngine
from openviking.service.context_router_types import (
    ContextRouteRequest,
    ContextRouteResult,
    ContextRouterStats,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/context-router", tags=["ContextRouter"])


@router.post("/route", response_model=ContextRouteResult)
async def route_and_compress(req: ContextRouteRequest) -> ContextRouteResult:
    """Segment, dispatch to specialized engines, and assemble high-purity context."""
    try:
        engine = ContextRouterEngine.get_instance()
        return engine.route_and_compress(req)
    except Exception as exc:
        logger.error("Context router execution failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Context routing error: {str(exc)}")


@router.post("/segment")
async def preview_segments(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dry-run preview of prompt segmentation without executing compression."""
    content = payload.get("content", "")
    preserve_static = payload.get("preserve_static_header", True)
    try:
        engine = ContextRouterEngine.get_instance()
        segments = engine.segment_preview(content, preserve_static=preserve_static)
        return {
            "status": "ok",
            "segments_count": len(segments),
            "segments": segments,
        }
    except Exception as exc:
        logger.error("Context router segmentation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Segmentation error: {str(exc)}")


@router.get("/stats", response_model=ContextRouterStats)
async def get_router_stats() -> ContextRouterStats:
    """Retrieve cumulative telemetry statistics of context routing."""
    return ContextRouterEngine.get_instance().get_stats()


@router.post("/reset-stats")
async def reset_router_stats() -> Dict[str, str]:
    """Reset cumulative context router statistics."""
    ContextRouterEngine.get_instance().reset_stats()
    return {"status": "ok", "message": "Context router statistics reset successfully"}
