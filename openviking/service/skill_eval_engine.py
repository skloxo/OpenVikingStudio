# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Evaluation Retina — TriJudge Engine & EvalRunner.

三级判定器评测引擎:
  ExactJudge:   精确字符串 / 正则匹配断言 (Level 0)
  CommandJudge: Shell 命令退出码断言 (Level 1)
  AgentJudge:   LLM 语义判官骨架 (Level 2, 本版本预留 skip)

EvalCaseLoader: 从 evals/cases/<skill>/*.yaml 加载声明式用例
EvalRunner:     调度 TriJudge 执行所有用例，返回 EvalRunResult
"""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from openviking.service.skill_eval_types import (
    EvalCase,
    EvalRunResult,
    EvalSummary,
    JudgeResult,
    JudgeType,
    JudgeVerdict,
)

# ---------------------------------------------------------------------------
# 抽象判定器基类
# ---------------------------------------------------------------------------

class BaseJudge(ABC):
    """抽象判定器基类 — 深模块窄接口。"""

    @abstractmethod
    def judge(self, case: EvalCase, skill_path: Optional[str] = None) -> JudgeResult:
        """对单个用例执行判定，返回 JudgeResult。"""


# ---------------------------------------------------------------------------
# Level 0: ExactJudge (精确 / 正则匹配)
# ---------------------------------------------------------------------------

class ExactJudge(BaseJudge):
    """精确字符串或正则匹配断言。

    case.judge_type == 'exact' → 字符串 in 检查
    case.judge_type == 'regex' → re.search 检查
    """

    def judge(self, case: EvalCase, skill_path: Optional[str] = None) -> JudgeResult:
        t0 = time.monotonic()
        try:
            if case.input is None or case.expect is None:
                return self._result(case, JudgeVerdict.FAIL, error="Missing input or expect field")

            if case.judge_type == JudgeType.REGEX:
                matched = bool(re.search(case.expect, case.input, re.DOTALL | re.IGNORECASE))
            else:  # exact
                matched = case.expect in case.input

            verdict = JudgeVerdict.PASS if matched else JudgeVerdict.FAIL
            error = None if matched else f"Pattern not found: {case.expect!r}"
            return self._result(
                case, verdict,
                actual=case.input[:200] if case.input else None,
                expected=case.expect,
                error=error,
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except re.error as exc:
            return self._result(case, JudgeVerdict.FAIL, error=f"Regex error: {exc}")

    @staticmethod
    def _result(case: EvalCase, verdict: JudgeVerdict, **kwargs) -> JudgeResult:
        return JudgeResult(
            case_id=case.case_id,
            skill_name=case.skill_name,
            judge_type=case.judge_type,
            verdict=verdict,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Level 1: CommandJudge (Shell 命令退出码)
# ---------------------------------------------------------------------------

class CommandJudge(BaseJudge):
    """Shell 命令退出码断言。

    case.command 支持 {skill_path} 变量替换。
    exit_code == case.expected_exit_code (默认 0) → PASS。
    超时 10s → FAIL。
    """

    _TIMEOUT_SECONDS = 10

    def judge(self, case: EvalCase, skill_path: Optional[str] = None) -> JudgeResult:
        t0 = time.monotonic()
        if not case.command:
            return JudgeResult(
                case_id=case.case_id, skill_name=case.skill_name,
                judge_type=case.judge_type, verdict=JudgeVerdict.FAIL,
                error="CommandJudge: case.command is empty",
            )

        # 变量替换
        cmd = case.command
        if skill_path:
            cmd = cmd.replace("{skill_path}", skill_path)

        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=self._TIMEOUT_SECONDS,
            )
            passed = proc.returncode == case.expected_exit_code
            verdict = JudgeVerdict.PASS if passed else JudgeVerdict.FAIL
            actual_out = (proc.stdout + proc.stderr)[:300]
            return JudgeResult(
                case_id=case.case_id, skill_name=case.skill_name,
                judge_type=case.judge_type, verdict=verdict,
                actual=f"exit={proc.returncode}\n{actual_out}",
                expected=f"exit={case.expected_exit_code}",
                error=None if passed else f"exit code {proc.returncode} != {case.expected_exit_code}",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except subprocess.TimeoutExpired:
            return JudgeResult(
                case_id=case.case_id, skill_name=case.skill_name,
                judge_type=case.judge_type, verdict=JudgeVerdict.FAIL,
                error=f"Command timed out after {self._TIMEOUT_SECONDS}s",
                duration_ms=(time.monotonic() - t0) * 1000,
            )


# ---------------------------------------------------------------------------
# Level 2: AgentJudge (LLM 语义判官骨架，本版预留 skip)
# ---------------------------------------------------------------------------

class AgentJudge(BaseJudge):
    """LLM 语义判官 — 本版本预留骨架，无 LLM 配置时自动 skip。"""

    def judge(self, case: EvalCase, skill_path: Optional[str] = None) -> JudgeResult:
        return JudgeResult(
            case_id=case.case_id, skill_name=case.skill_name,
            judge_type=case.judge_type, verdict=JudgeVerdict.SKIP,
            error="AgentJudge: LLM not configured in this build (reserved for future)",
        )


# ---------------------------------------------------------------------------
# EvalCaseLoader — 从 YAML 文件加载用例
# ---------------------------------------------------------------------------

class EvalCaseLoader:
    """从 evals/cases/<skill>/<case-id>.yaml 加载声明式评测用例。

    支持 `input_from_fixture: <filename>` 字段，自动从 evals/fixtures/ 加载内容
    注入到 case.input 中，实现夹具解耦。
    """

    def __init__(self, evals_root: Path):
        self._root = evals_root / "cases"
        self._fixtures_root = evals_root / "fixtures"

    def load_all(self) -> List[EvalCase]:
        """加载所有技能的全部用例。"""
        cases: List[EvalCase] = []
        if not self._root.exists():
            return cases
        for yaml_file in sorted(self._root.rglob("case-*.yaml")):
            case = self._load_file(yaml_file)
            if case and case.enabled:
                cases.append(case)
        return cases

    def load_for_skill(self, skill_name: str) -> List[EvalCase]:
        """加载指定技能的所有用例。"""
        skill_dir = self._root / skill_name
        cases: List[EvalCase] = []
        if not skill_dir.exists():
            return cases
        for yaml_file in sorted(skill_dir.glob("case-*.yaml")):
            case = self._load_file(yaml_file)
            if case and case.enabled:
                cases.append(case)
        return cases

    def _load_file(self, path: Path) -> Optional[EvalCase]:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None

            # 支持 input_from_fixture: <filename> 自动注入 input
            fixture_name = raw.pop("input_from_fixture", None)
            if fixture_name and raw.get("input") is None:
                fixture_path = self._fixtures_root / fixture_name
                if fixture_path.exists():
                    raw["input"] = fixture_path.read_text(encoding="utf-8")

            return EvalCase(**raw)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# EvalRunner — 调度 TriJudge 执行
# ---------------------------------------------------------------------------

_JUDGES: Dict[JudgeType, BaseJudge] = {
    JudgeType.EXACT: ExactJudge(),
    JudgeType.REGEX: ExactJudge(),   # ExactJudge handles both exact & regex
    JudgeType.COMMAND: CommandJudge(),
    JudgeType.AGENT: AgentJudge(),
}


class EvalRunner:
    """调度 TriJudge 执行所有评测用例，维护历史 RunResult。

    单例外部状态：结果列表。生产模式下由服务层托管。
    """

    def __init__(self, evals_root: Path):
        self._loader = EvalCaseLoader(evals_root)
        self._history: List[EvalRunResult] = []

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run(self, skill_name: str = "*") -> EvalRunResult:
        """运行评测并返回结果。skill_name='*' 时评测所有技能。"""
        run_id = str(uuid.uuid4())[:8]
        run = EvalRunResult(run_id=run_id, skill_name=skill_name)

        cases = (
            self._loader.load_all()
            if skill_name == "*"
            else self._loader.load_for_skill(skill_name)
        )

        for case in cases:
            judge = _JUDGES.get(case.judge_type, AgentJudge())
            result = judge.judge(case)
            run.results.append(result)
            run.total += 1
            if result.verdict == JudgeVerdict.PASS:
                run.passed += 1
            elif result.verdict == JudgeVerdict.SKIP:
                run.skipped += 1
            else:
                run.failed += 1

        run.finished_at = datetime.now(timezone.utc)
        run.pass_rate = run.passed / run.total if run.total > 0 else 0.0
        run.status = "done"
        self._history.append(run)
        return run

    def get_history(self, limit: int = 20) -> List[EvalRunResult]:
        """返回最近 limit 条历史评测结果。"""
        return self._history[-limit:]

    def get_summary(self) -> EvalSummary:
        """返回全局汇总指标。"""
        all_cases = self._loader.load_all()
        skills = list({c.skill_name for c in all_cases})
        last = self._history[-1] if self._history else None

        if not self._history:
            global_pass_rate = 0.0
        else:
            total_passed = sum(r.passed for r in self._history)
            total_judged = sum(r.total - r.skipped for r in self._history)
            global_pass_rate = total_passed / total_judged if total_judged > 0 else 0.0

        return EvalSummary(
            total_cases=len(all_cases),
            total_runs=len(self._history),
            global_pass_rate=global_pass_rate,
            last_run_at=last.finished_at if last else None,
            skills_evaluated=skills,
            recent_runs=self._history[-5:],
        )
