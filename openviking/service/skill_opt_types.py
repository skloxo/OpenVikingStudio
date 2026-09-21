# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Pydantic DTOs for SkillOpt Quality Gate & Optimization Engine."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DimensionScore(BaseModel):
    """单个维度的评分详情。"""
    model_config = ConfigDict(strict=False)

    name: str = Field(..., description="维度英文名")
    label: str = Field(..., description="维度中文标签")
    score: int = Field(..., ge=0, le=25, description="得分 (0~25)")
    max_score: int = Field(25, description="满分")
    status: str = Field("good", description="状态: good | warning | critical")
    details: List[str] = Field(default_factory=list, description="评分说明或扣分项")


class SkillOptAuditResult(BaseModel):
    """技能体检综合报告。"""
    model_config = ConfigDict(strict=False)

    skill_name: str
    total_score: int = Field(..., ge=0, le=100, description="综合总分 (0~100)")
    grade: str = Field(..., description="等级评级: S | A | B | C | D")
    line_count: int = 0
    dimensions: List[DimensionScore] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    passed_gate: bool = True


class SkillOptAttemptRequest(BaseModel):
    """Attempt 执行测试请求。"""
    model_config = ConfigDict(strict=False)

    skill_content: str
    test_query: str
    expected_action: Optional[str] = None


class SkillOptAttemptResult(BaseModel):
    """Attempt 执行与 Judge 判据结果。"""
    model_config = ConfigDict(strict=False)

    verdict: str = Field(..., description="判据结果: PASS | FAIL | PARTIAL")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    matched_intent: bool = False
    judge_reason: str = ""
    triggered_tools: List[str] = Field(default_factory=list)


class SkillOptOptimizeRequest(BaseModel):
    """自动优化补丁请求。"""
    model_config = ConfigDict(strict=False)

    skill_content: str
    target_improvements: Optional[List[str]] = None


class SkillOptOptimizeResult(BaseModel):
    """自动优化结果与 Draft 补丁。"""
    model_config = ConfigDict(strict=False)

    original_score: int
    optimized_score: int
    applied_fixes: List[str] = Field(default_factory=list)
    optimized_content: str
    diff_summary: str = ""


class BatchAuditSummary(BaseModel):
    """全库技能批量体检概览。"""
    model_config = ConfigDict(strict=False)

    total_audited: int = 0
    avg_score: float = 0.0
    grade_counts: Dict[str, int] = Field(default_factory=lambda: {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0})
    results: List[SkillOptAuditResult] = Field(default_factory=list)
