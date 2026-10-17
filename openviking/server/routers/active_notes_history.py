# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
REST Endpoints for Codex-grade Active Notes and History Context Governance.
(Card-Context-ActiveNotesAndHistory / v1.5.34)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.active_notes_history import (
    ActiveNotes,
    ActiveNotesHistoryManager,
    HistoryMessage,
    HistorySearchResult,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/context", tags=["context-governance"])


class UpdateNotesRequest(BaseModel):
    session_id: str = Field(..., description="Target session ID")
    active_goal: str = Field(..., description="Active goal of current session")
    working_constraints: List[str] = Field(default_factory=list, description="Strict operational constraints")
    current_state: str = Field("", description="Current operational milestone or phase")
    discovered_facts: List[str] = Field(default_factory=list, description="Verified immutable facts")


class AppendHistoryRequest(BaseModel):
    session_id: str = Field(..., description="Target session ID")
    role: str = Field(..., description="Role of message sender (user/assistant/tool/system)")
    content: str = Field(..., description="Uncompressed original message content")
    tool_calls: Optional[str] = Field(None, description="Optional raw tool calls JSON string")


class SearchHistoryRequest(BaseModel):
    session_id: str = Field(..., description="Target session ID")
    query: str = Field(..., description="Search query string (symbol, error, path, keyword)")
    top_k: int = Field(5, description="Maximum number of hits to return")


@router.get("/notes")
async def get_active_notes(
    session_id: str = Query("default", description="Session identifier"),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    manager = ActiveNotesHistoryManager.get_instance()
    try:
        notes = manager.get_or_create_notes(session_id)
        return {
            "session_id": notes.session_id,
            "active_goal": notes.active_goal,
            "working_constraints": notes.working_constraints,
            "current_state": notes.current_state,
            "discovered_facts": notes.discovered_facts,
            "version": notes.version,
            "updated_at": notes.updated_at,
        }
    except Exception as e:
        logger.error(f"Failed to fetch active notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notes")
async def update_active_notes(
    req: UpdateNotesRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    manager = ActiveNotesHistoryManager.get_instance()
    try:
        notes = manager.update_notes(
            session_id=req.session_id,
            active_goal=req.active_goal,
            working_constraints=req.working_constraints,
            current_state=req.current_state,
            discovered_facts=req.discovered_facts,
        )
        return {
            "session_id": notes.session_id,
            "active_goal": notes.active_goal,
            "working_constraints": notes.working_constraints,
            "current_state": notes.current_state,
            "discovered_facts": notes.discovered_facts,
            "version": notes.version,
            "updated_at": notes.updated_at,
        }
    except Exception as e:
        logger.error(f"Failed to update active notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/append")
async def append_history_message(
    req: AppendHistoryRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    manager = ActiveNotesHistoryManager.get_instance()
    try:
        msg = manager.append_history(
            session_id=req.session_id,
            role=req.role,
            content=req.content,
            tool_calls=req.tool_calls,
        )
        return {
            "message_id": msg.message_id,
            "session_id": msg.session_id,
            "turn_index": msg.turn_index,
            "role": msg.role,
            "content": msg.content,
            "token_count": msg.token_count,
            "created_at": msg.created_at,
        }
    except Exception as e:
        logger.error(f"Failed to append history message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/windows")
async def list_history_windows(
    session_id: str = Query("default", description="Session identifier"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    order: str = Query("asc", description="Sort order by turn_index: asc or desc"),
    ctx: RequestContext = Depends(get_request_context),
) -> List[Dict[str, Any]]:
    manager = ActiveNotesHistoryManager.get_instance()
    try:
        messages = manager.list_history_windows(
            session_id=session_id,
            offset=offset,
            limit=limit,
            order=order,
        )
        return [
            {
                "message_id": m.message_id,
                "session_id": m.session_id,
                "turn_index": m.turn_index,
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "token_count": m.token_count,
                "created_at": m.created_at,
            }
            for m in messages
        ]
    except Exception as e:
        logger.error(f"Failed to list history windows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/search")
async def search_history(
    req: SearchHistoryRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> List[Dict[str, Any]]:
    manager = ActiveNotesHistoryManager.get_instance()
    try:
        hits = manager.search_history(
            session_id=req.session_id,
            query=req.query,
            top_k=req.top_k,
        )
        return [
            {
                "message_id": h.message_id,
                "turn_index": h.turn_index,
                "role": h.role,
                "content": h.content,
                "score": h.score,
                "created_at": h.created_at,
            }
            for h in hits
        ]
    except Exception as e:
        logger.error(f"Failed to search history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_context_stats(
    session_id: str = Query("default", description="Session identifier"),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    manager = ActiveNotesHistoryManager.get_instance()
    try:
        return manager.get_stats(session_id)
    except Exception as e:
        logger.error(f"Failed to get context stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
