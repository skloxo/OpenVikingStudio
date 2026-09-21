# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""REST Endpoints for Skill LiveGen — Interactive Skill Creation & Sandbox Validation.

(Epic-LIVE-GEN / Card 14: Card-Skill-LiveGen-Editor-And-Sandbox-Validation / v1.5.71)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.skill_livegen_service import (
    QuerySimulationItem,
    SkillLiveGenService,
    SkillPublishResult,
    SkillScaffoldRequest,
    SkillSimulationResult,
    SkillValidationResult,
)
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/skills/livegen", tags=["skill-livegen"])


class ScaffoldResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str
    template_type: str


class ValidateDraftRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str = Field(..., description="SKILL.md 内容")
    strict: bool = Field(default=True, description="严格模式")


class SimulateTriggerRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str = Field(..., description="SKILL.md 内容")
    queries: List[str] = Field(..., description="测试 query 列表")


class PublishSkillRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill_name: str = Field(..., description="技能唯一标识")
    content: str = Field(..., description="校验通过的 SKILL.md 内容")
    base_dir: Optional[str] = Field(None, description="自定义存储基础目录")


@router.post("/scaffold", response_model=ScaffoldResponse)
async def generate_skill_scaffold(
    req: SkillScaffoldRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> ScaffoldResponse:
    """生成符合规范的初始 SKILL.md 脚手架骨架。"""
    svc = SkillLiveGenService.get_instance()
    content = svc.generate_scaffold(req)
    logger.info(f"LiveGen generated scaffold for skill '{req.name}' ({req.template_type})")
    return ScaffoldResponse(content=content, template_type=req.template_type)


@router.post("/validate", response_model=SkillValidationResult)
async def validate_skill_draft(
    req: ValidateDraftRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillValidationResult:
    """对 SKILL.md 草稿执行全量静态与格式门禁校验。"""
    svc = SkillLiveGenService.get_instance()
    result = svc.validate_draft(req.content, strict=req.strict)
    return result


@router.post("/simulate", response_model=SkillSimulationResult)
async def simulate_trigger(
    req: SimulateTriggerRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillSimulationResult:
    """沙盒环境模拟 Agent 自然语言触发测试。"""
    svc = SkillLiveGenService.get_instance()
    result = svc.simulate_trigger(req.content, req.queries)
    return result


@router.post("/publish", response_model=SkillPublishResult)
async def publish_skill(
    req: PublishSkillRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillPublishResult:
    """校验并一键持久化发布技能至 Viking 中枢。"""
    svc = SkillLiveGenService.get_instance()
    result = svc.publish_skill(req.skill_name, req.content, base_dir=req.base_dir)
    logger.info(f"LiveGen published skill '{req.skill_name}': success={result.success}")
    return result


@router.get("/stats")
async def get_livegen_stats(
    ctx: RequestContext = Depends(get_request_context),
) -> Dict[str, Any]:
    """获取 LiveGen 实时统计数据。"""
    svc = SkillLiveGenService.get_instance()
    return svc.get_stats()
