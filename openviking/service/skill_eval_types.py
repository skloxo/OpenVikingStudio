# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Pydantic DTOs for Skill Evaluation Retina (EvaluationRetina / SkillQuality).

TriJudge 三级判定器数据模型:
  Level 0 - ExactJudge:   精确字符串 / 正则匹配断言
  Level 1 - CommandJudge: Shell 命令退出码断言
  Level 2 - AgentJudge:   LLM 语义判官 (骨架预留)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 判定器类型枚举
# ---------------------------------------------------------------------------

class JudgeType(str, Enum):
    EXACT = "exact"          # 精确字符串匹配
    REGEX = "regex"          # 正则匹配
    COMMAND = "command"      # Shell 命令退出码
    AGENT = "agent"          # LLM 语义判官 (预留骨架)


class JudgeVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"            # 用于 AgentJudge 未配置 LLM 时


# ---------------------------------------------------------------------------
# 评测用例 (声明式 YAML 映射)
# ---------------------------------------------------------------------------

class EvalCase(BaseModel):
    """单个声明式评测用例 — 对应 evals/cases/<skill>/<case-id>.yaml。"""

    model_config = ConfigDict(strict=False)

    skill_name: str = Field(..., description="对应技能名称，如 cockpit-ui")
    case_id: str = Field(..., description="用例 ID，如 case-001-no-green")
    description: str = Field(..., description="人类可读的用例描述")
    judge_type: JudgeType = Field(..., description="判定器类型")

    # Level 0 / 1: 输入内容 (字符串，通常是 SKILL.md 正文片段或命令模板)
    input: Optional[str] = Field(None, description="送入判定器的输入文本")

    # Level 0 (exact/regex) — 期望值
    expect: Optional[str] = Field(None, description="期望匹配的字符串或正则表达式")

    # Level 1 (command) — Shell 命令模板
    command: Optional[str] = Field(
        None,
        description="Shell 命令，exit code 0 = pass；支持 {skill_path} 变量",
    )
    expected_exit_code: int = Field(0, description="期望退出码，默认 0 = 成功")

    # Level 2 (agent) — LLM prompt 骨架
    agent_prompt: Optional[str] = Field(None, description="LLM 语义判官 prompt (预留)")

    # 元信息
    tags: List[str] = Field(default_factory=list, description="用例标签，如 [p0, visual]")
    enabled: bool = Field(True, description="是否启用该用例")


# ---------------------------------------------------------------------------
# 判定结果
# ---------------------------------------------------------------------------

class JudgeResult(BaseModel):
    """单次判定结果。"""

    model_config = ConfigDict(strict=False)

    case_id: str
    skill_name: str
    judge_type: JudgeType
    verdict: JudgeVerdict
    actual: Optional[str] = None        # 实际值（用于调试）
    expected: Optional[str] = None      # 期望值快照
    error: Optional[str] = None         # 失败原因
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# 评测运行结果 (汇总)
# ---------------------------------------------------------------------------

class EvalRunResult(BaseModel):
    """一次完整评测运行的结果。"""

    model_config = ConfigDict(strict=False)

    run_id: str
    skill_name: str                     # 评测目标技能 ("*" = 全部)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    pass_rate: float = 0.0              # 0.0 ~ 1.0
    results: List[JudgeResult] = Field(default_factory=list)
    status: str = "running"             # running | done | error


# ---------------------------------------------------------------------------
# 评测汇总指标 (API 响应)
# ---------------------------------------------------------------------------

class EvalSummary(BaseModel):
    """面向前端座舱的汇总指标。"""

    model_config = ConfigDict(strict=False)

    total_cases: int = 0
    total_runs: int = 0
    global_pass_rate: float = 0.0
    last_run_at: Optional[datetime] = None
    skills_evaluated: List[str] = Field(default_factory=list)
    recent_runs: List[EvalRunResult] = Field(default_factory=list)
