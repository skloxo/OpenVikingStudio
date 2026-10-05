# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Ingestion Gatekeeper & Staging REST Router (Card-94 & Card-95)."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.skill_ingestion_validator import SkillIngestionValidator
from openviking.service.skill_ingestion_worker import SkillIngestionWorker
from openviking.storage.skill_ingestion_store import SkillIngestionStore

router = APIRouter(prefix="/api/v1/skills/ingestion", tags=["Skill Ingestion"])
_validator = SkillIngestionValidator()
_store = SkillIngestionStore.get_instance()
_worker = SkillIngestionWorker(store=_store, validator=_validator)


class ValidateRequest(BaseModel):
    content: str = Field(..., description="Raw markdown content of the skill including YAML frontmatter")
    filename: str = Field(default="SKILL.md", description="Original filename")


class SubmitSkillRequest(BaseModel):
    skill_name: str = Field(..., description="Skill name in kebab-case")
    content: str = Field(..., description="Raw markdown content of the skill including YAML frontmatter")
    author: str = Field(default="anonymous", description="Submitting author or agent")


@router.post("/validate")
async def validate_skill_content(
    payload: ValidateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Run deterministic static and security gates on submitted skill content."""
    receipt = _validator.validate(payload.content, filename=payload.filename)
    return receipt.to_dict()


@router.post("/submit")
async def submit_skill_to_inbox(
    payload: SubmitSkillRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Asynchronously enqueue raw skill into SQLite staging inbox (< 50ms latency)."""
    record = _store.enqueue_skill(
        skill_name=payload.skill_name,
        raw_content=payload.content,
        author=payload.author,
    )
    return {
        "status": "ok",
        "receipt_id": record.receipt_id,
        "skill_name": record.skill_name,
        "ingestion_status": record.status.value,
        "created_at": record.created_at,
        "message": "Skill enqueued in staging inbox. Awaiting asynchronous worker validation.",
    }


@router.get("/receipt/{receipt_id}")
async def get_ingestion_receipt(
    receipt_id: str,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Query ingestion progress, gatekeeper report, and current status."""
    record = _store.get_record(receipt_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Ingestion receipt '{receipt_id}' not found.")
    return {
        "status": "ok",
        "record": record.model_dump(),
    }


@router.get("/queue")
async def get_ingestion_queue_metrics(
    limit: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Inspect inbox queue depth and recent submissions."""
    return {
        "status": "ok",
        "queue_depth": _store.get_queue_depth(),
        "recent_records": [r.model_dump() for r in _store.list_records(limit=limit)],
    }


@router.post("/process-batch")
async def trigger_worker_batch(
    batch_size: int = Query(default=5, ge=1, le=50),
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Manually trigger background worker tick to drain pending inbox items."""
    summary = _worker.run_worker_tick(batch_size=batch_size)
    return {
        "status": "ok",
        "worker_summary": summary,
    }


@router.get("/rules")
async def get_ingestion_rules(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Return deterministic static gate limits and Frontmatter v2.0 schema contract."""
    return {
        "status": "ok",
        "schema_version": "v2.0",
        "max_line_limit": 500,
        "sweet_spot_line_limit": 300,
        "min_triggers_count": 3,
        "required_fields": ["name", "version", "domain", "description", "triggers", "allowed-tools"],
        "disallowed_syscalls": ["os.system", "subprocess", "eval", "exec"],
    }
