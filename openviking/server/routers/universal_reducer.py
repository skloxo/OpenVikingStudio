# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Universal Atomic Engines REST API Router (Card-190 SSOT).

Exposes:
1. POST /api/v1/content/reduce - Unified code, skill, and text dehydration.
2. GET /api/v1/audit/timeline - Multi-axis immutable audit ledger timeline.
3. GET /api/v1/lifecycle/state - Query FSM lifecycle state and transition history.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.universal_reducer import (
    UniversalContentReducer,
    UniversalReduceRequest,
    UniversalReduceResult,
)
from openviking.service.universal_audit_ledger import (
    AuditEvent,
    UniversalAuditLedger,
)
from openviking.service.unified_lifecycle import (
    LifecycleState,
    LifecycleTransitionEvent,
    UnifiedLifecycleEngine,
)

router = APIRouter(prefix="/api/v1/universal", tags=["universal-engines"])


@router.post("/reduce", response_model=UniversalReduceResult)
async def reduce_content(
    request: UniversalReduceRequest,
    _ctx: RequestContext = Depends(get_request_context),
) -> UniversalReduceResult:
    """Unified Content Reduction API (auto-sniffs code, skill, and text)."""
    reducer = UniversalContentReducer.get_instance()
    try:
        return reducer.reduce(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reduction failed: {str(exc)}")


@router.get("/audit/timeline", response_model=List[AuditEvent])
async def get_audit_timeline(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (skill, doc, session)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action (INGEST, REDUCE, COMMIT)"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Query offset"),
    _ctx: RequestContext = Depends(get_request_context),
) -> List[AuditEvent]:
    """Retrieve multi-axis immutable audit ledger timeline."""
    ledger = UniversalAuditLedger.get_instance()
    return ledger.get_timeline(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
        offset=offset,
    )


@router.get("/lifecycle/state")
async def get_lifecycle_state(
    entity_type: str = Query(..., description="Entity type (e.g. skill, session)"),
    entity_id: str = Query(..., description="Entity ID"),
    _ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Fetch current 5-stage lifecycle state and transition history."""
    engine = UnifiedLifecycleEngine.get_instance()
    state = engine.get_state(entity_type, entity_id)
    history = engine.get_history(entity_type, entity_id)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "current_state": state.value if state else None,
        "history": [h.model_dump() for h in history],
    }
