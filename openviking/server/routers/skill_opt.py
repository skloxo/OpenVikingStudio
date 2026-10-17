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


class HealthScoreRequest(BaseModel):
    """技能健康体检请求。"""
    model_config = ConfigDict(strict=False)

    skill_content: str = Field(..., description="技能完整 Markdown 文本")
    skill_slug: Optional[str] = Field(None, description="可选技能标识")


class RemediateRequest(BaseModel):
    """技能自动修复建议与补丁生成请求。"""
    model_config = ConfigDict(strict=False)

    skill_content: str = Field(..., description="技能完整 Markdown 文本")
    skill_slug: Optional[str] = Field(None, description="可选技能标识")


@router.post("/health-score")
async def calculate_skill_health(
    req: HealthScoreRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """计算技能健康度评分与缺陷分类诊断报告 (SkillOpt SKILLOPT-02)。"""
    from openviking.service.skill_health_scorer import SkillHealthScorer
    report = SkillHealthScorer.calculate_health(raw_content=req.skill_content, skill_slug=req.skill_slug)
    return report.to_dict()


@router.post("/remediate")
async def remediate_skill_content(
    req: RemediateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """生成技能确定性自动修复补丁与重构草稿 (SkillOpt SKILLOPT-02)。"""
    from openviking.service.skill_health_scorer import SkillRemediationGenerator
    result = SkillRemediationGenerator.remediate(raw_content=req.skill_content, skill_slug=req.skill_slug)
    return result.to_dict()


class WeightTuneApiRequest(BaseModel):
    """技能权重动态微调请求。"""
    model_config = ConfigDict(strict=False)

    skill_slug: str = Field(..., description="目标技能唯一标识 slug")
    verdict: str = Field("PASS", description="Attempt 执行判据结果: PASS | DEGRADED | FAIL")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="置信度系数 (0.0~1.0)")
    notes: str = Field("", description="微调原因或执行摘要备注")


@router.post("/weight/tune")
async def tune_skill_weight(
    req: WeightTuneApiRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """动态微调技能调度权重并沉淀入账本 (SkillOpt SKILLOPT-03)。"""
    from openviking.service.skill_weight_tuner import SkillWeightTuner

    tuner = SkillWeightTuner.get_instance()
    result = tuner.tune_weight(
        skill_slug=req.skill_slug,
        verdict=req.verdict,
        confidence=req.confidence,
        notes=req.notes,
    )
    return result.to_dict()


@router.get("/weights")
async def list_skill_weights(
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """获取全量技能动态权重分布与执行履历概览 (SkillOpt SKILLOPT-03)。"""
    from openviking.service.skill_weight_tuner import SkillWeightTuner

    tuner = SkillWeightTuner.get_instance()
    profiles = tuner.list_profiles()
    return {
        "total_skills": len(profiles),
        "profiles": [p.to_dict() for p in profiles],
    }


class ApplySkillPatchRequest(BaseModel):
    """技能优化补丁物理落盘请求。"""
    model_config = ConfigDict(strict=False)

    skill_slug: str = Field(..., description="目标技能 slug")
    optimized_content: str = Field(..., description="优化后的完整 Markdown 文本")
    target_path: Optional[str] = Field(None, description="可选指定写入物理文件绝对路径")


@router.post("/apply")
async def apply_skill_patch(
    req: ApplySkillPatchRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> dict:
    """将工作台调优后的技能补丁安全物理写回文件，执行快照备份与 AST 校验。"""
    from openviking.service.skill_opt_apply import SkillOptApplyService
    service = SkillOptApplyService()
    try:
        result = service.apply_patch(
            skill_slug=req.skill_slug,
            optimized_content=req.optimized_content,
            target_path=req.target_path,
        )
        return result
    except (ValueError, FileNotFoundError) as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": f"Internal error: {exc}"}



