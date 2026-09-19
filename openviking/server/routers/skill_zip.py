# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST Endpoints for SkillZip 0-Rollout Contractual Compression Engine.

(Card-Skill-ZipOnWrite-ContractualCompression / v1.5.35)
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.skill_zip_engine import (
    SkillZipEngine,
    SkillZipResult,
    ZipGateResult,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/skills/zip", tags=["skill-zip"])


class CompressSkillRequest(BaseModel):
    skill_content: str = Field(..., description="Raw or evolved skill markdown content")
    seed_baseline: Optional[str] = Field(None, description="Optional seed baseline skill text")


class GateCheckRequest(BaseModel):
    skill_content: str = Field(..., description="Candidate skill content to verify against gate")
    seed_length: int = Field(400, description="Length of seed skill baseline")


@router.post("/compress", response_model=SkillZipResult)
async def compress_skill(
    req: CompressSkillRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillZipResult:
    """Execute 0-rollout deterministic contractual compression on a skill."""
    engine = SkillZipEngine.get_instance()
    result = engine.compress(req.skill_content)
    logger.info(
        f"SkillZip compressed {result.original_length} -> {result.compressed_length} "
        f"({result.compression_ratio:.1%}, fidelity={result.contract_fidelity})"
    )
    return result


@router.post("/gate-check", response_model=ZipGateResult)
async def check_zip_gate(
    req: GateCheckRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> ZipGateResult:
    """Evaluate skill candidate against the 1.6~1.9x seed multiplier gate."""
    engine = SkillZipEngine.get_instance()
    gate_result = engine.check_gate(req.skill_content, seed_length=req.seed_length)
    return gate_result


@router.get("/stats")
async def get_zip_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """Retrieve rolling metrics for the SkillZip compression engine."""
    engine = SkillZipEngine.get_instance()
    return engine.get_stats()
