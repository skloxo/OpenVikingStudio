# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Ingestion Gatekeeper REST Router (Card-94)."""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.skill_ingestion_validator import SkillIngestionValidator

router = APIRouter(prefix="/api/v1/skills/ingestion", tags=["Skill Ingestion"])
_validator = SkillIngestionValidator()


class ValidateRequest(BaseModel):
    content: str = Field(..., description="Raw markdown content of the skill including YAML frontmatter")
    filename: str = Field(default="SKILL.md", description="Original filename")


@router.post("/validate")
async def validate_skill_content(
    payload: ValidateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Run deterministic static and security gates on submitted skill content."""
    receipt = _validator.validate(payload.content, filename=payload.filename)
    return receipt.to_dict()


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
