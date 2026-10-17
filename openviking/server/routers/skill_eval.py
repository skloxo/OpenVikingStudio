# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Evaluation Retina REST API 路由。

端点:
  POST /api/v1/skill-eval/run          ← 运行技能评测
  GET  /api/v1/skill-eval/results      ← 历史评测结果
  GET  /api/v1/skill-eval/summary      ← 全局汇总指标
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query

from openviking.service.skill_eval_engine import EvalRunner
from openviking.service.skill_eval_types import EvalRunResult, EvalSummary

router = APIRouter(prefix="/api/v1/skill-eval", tags=["skill-eval"])

# ---------------------------------------------------------------------------
# 全局单例 EvalRunner（与服务同生命周期）
# ---------------------------------------------------------------------------

def _get_evals_root() -> Path:
    """解析 evals/ 目录路径：相对项目根（向上遍历查找含 evals/ 目录的父路径）。"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "evals"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "evals"


_runner = EvalRunner(evals_root=_get_evals_root())


# ---------------------------------------------------------------------------
# 端点实现 (直接返回 Pydantic model，不使用 Response[T] 泛型)
# ---------------------------------------------------------------------------

@router.post("/run", response_model=EvalRunResult)
async def run_skill_eval(
    skill_name: Optional[str] = Query(
        default="*",
        description="技能名称，'*' 表示评测所有已注册技能",
    )
) -> EvalRunResult:
    """运行指定技能（或全部技能）的评测用例，返回本次运行结果。"""
    return _runner.run(skill_name=skill_name or "*")


@router.get("/results", response_model=List[EvalRunResult])
async def list_eval_results(
    limit: int = Query(default=20, ge=1, le=100, description="返回最近 N 条历史"),
) -> List[EvalRunResult]:
    """返回最近 N 条历史评测结果列表。"""
    return _runner.get_history(limit=limit)


@router.get("/summary", response_model=EvalSummary)
async def get_eval_summary() -> EvalSummary:
    """返回全局汇总指标：总用例数、总运行数、全局通过率、最近运行时间。"""
    return _runner.get_summary()
