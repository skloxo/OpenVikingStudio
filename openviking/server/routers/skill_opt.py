# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""SkillOpt Attempt / Judge 质量门禁与自动优化 REST API 路由。

端点:
  POST /api/v1/skill-opt/audit        ← 对技能文本执行四维体检
  POST /api/v1/skill-opt/attempt      ← 执行测试用例 Attempt 与 Judge 判定
  POST /api/v1/skill-opt/optimize     ← 自动优化并生成修复版 Draft Patch
  GET  /api/v1/skill-opt/batch-audit  ← 批量扫描已安装技能体检概览
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.service.skill_opt_service import SkillOptService
from openviking.service.skill_opt_types import (
    BatchAuditSummary,
    SkillOptAttemptRequest,
    SkillOptAttemptResult,
    SkillOptAuditResult,
    SkillOptOptimizeRequest,
    SkillOptOptimizeResult,
)

router = APIRouter(prefix="/api/v1/skill-opt", tags=["skill-opt"])
_service = SkillOptService()


class AuditContentRequest(BaseModel):
    """技能体检请求。"""
    model_config = ConfigDict(strict=False)

    skill_content: str = Field(..., description="技能完整 Markdown 文本")
    skill_name: Optional[str] = Field(None, description="技能可选名称")


@router.post("/audit", response_model=SkillOptAuditResult)
async def audit_skill_content(
    req: AuditContentRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillOptAuditResult:
    """执行四维技能规范与质量体检，输出各项维度评分与改进建议。"""
    return _service.audit_content(skill_content=req.skill_content, skill_name=req.skill_name)


@router.post("/attempt", response_model=SkillOptAttemptResult)
async def attempt_skill_execution(
    req: SkillOptAttemptRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillOptAttemptResult:
    """模拟测试用例 Attempt 执行，由 Judge Gate 进行意图与调用判定。"""
    return _service.attempt_execution(req)


@router.post("/optimize", response_model=SkillOptOptimizeResult)
async def optimize_skill_content(
    req: SkillOptOptimizeRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> SkillOptOptimizeResult:
    """根据体检扣分项生成自动修复补丁与优化版 Draft。"""
    return _service.optimize_content(req)


@router.get("/batch-audit", response_model=BatchAuditSummary)
async def batch_audit_skills(
    skills_dir: Optional[str] = Query(default=None, description="可选指定扫描技能目录"),
    ctx: RequestContext = Depends(get_request_context),
) -> BatchAuditSummary:
    """批量扫描已安装技能并汇总体检质量概览与等级分布。"""
    return _service.batch_audit_skills(skills_dir=skills_dir)
