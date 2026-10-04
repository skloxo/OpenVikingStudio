"""SkillOpt Attempt Simulation & Judge Gate Evaluator (SSOT).

Implements the multi-dimensional Judge Gate architecture inspired by Microsoft SkillOpt:
1. Multi-factor Skill Quality Scoring (SOP Structure, Tool Contract, I/O Clarity, Fault Tolerance)
2. Passing gate threshold validation (default >= 70.0 / 100.0)
3. Actionable remediation recommendations generation
4. Attempt trajectory simulation evaluation
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from openviking.service.skill_validator import SkillValidator


_STEP_PATTERN = re.compile(
    r"(?m)^\s*(?:(?:\d+\.)|(?:Step\s*\d+:?)|(?:第[一二三四五六七八九十0-9]+步))",
    re.IGNORECASE,
)
_TOOL_MENTION_PATTERN = re.compile(
    r"\b(?:openviking_[a-z0-9_]+|find|search|read|write|replace_file_content|run_command)\b"
)
_IO_KEYWORDS = ("input", "output", "参数", "返回值", "交付物", "assert", "断言", "result", "schema")
_FAULT_KEYWORDS = ("error", "fail", "retry", "exception", "fallback", "报错", "失败", "重试", "自愈", "兜底")


@dataclass
class SkillJudgeReport:
    """Evaluation verdict and detailed scores produced by the SkillOpt Judge Gate."""

    passed: bool
    total_score: float
    threshold: float
    scores: dict[str, float] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total_score": round(self.total_score, 2),
            "threshold": self.threshold,
            "scores": self.scores,
            "diagnostics": self.diagnostics,
            "recommendations": self.recommendations,
        }


class SkillOptJudge:
    """Zero-side-effect static Judge Gate and trajectory evaluator."""

    @classmethod
    def evaluate_skill(
        cls,
        raw_content: str,
        passing_score: float = 70.0,
    ) -> SkillJudgeReport:
        """Evaluate a skill specification across 4 orthogonal quality dimensions."""
        if not raw_content or not raw_content.strip():
            return SkillJudgeReport(
                passed=False,
                total_score=0.0,
                threshold=passing_score,
                diagnostics=["Raw skill content is empty."],
                recommendations=["Provide full SKILL.md content with YAML frontmatter and SOP body."],
            )

        validation = SkillValidator.validate_content(raw_content)
        diagnostics: list[str] = []
        recommendations: list[str] = []

        # 1. SOP Structure (0 ~ 30)
        sop_score = 0.0
        step_matches = _STEP_PATTERN.findall(raw_content)
        step_count = len(step_matches)
        if step_count >= 3:
            sop_score = 30.0
            diagnostics.append(f"SOP Structure: High (detected {step_count} numbered steps).")
        elif step_count >= 1:
            sop_score = 15.0
            diagnostics.append(f"SOP Structure: Moderate (detected {step_count} steps).")
            recommendations.append("Expand SOP into at least 3 structured sequential steps.")
        else:
            sop_score = 5.0 if len(raw_content.splitlines()) > 5 else 0.0
            diagnostics.append("SOP Structure: Low (no clear step numbering detected).")
            recommendations.append("Adopt numbered steps (e.g. '1.', 'Step 1:', '第一步') for clear agent execution.")

        # 2. Tool Contract (0 ~ 25)
        tool_score = 0.0
        allowed_tools = validation.parsed_metadata.get("allowed-tools") or []
        if isinstance(allowed_tools, list) and len(allowed_tools) > 0:
            tool_score += 10.0

        tool_mentions = _TOOL_MENTION_PATTERN.findall(raw_content)
        if tool_mentions:
            tool_score += 15.0
            diagnostics.append(f"Tool Contract: Explicit tools referenced ({len(tool_mentions)} mentions).")
        else:
            diagnostics.append("Tool Contract: No explicit tool names referenced in SOP body.")
            recommendations.append("Explicitly reference tools to invoke (e.g. `find`, `openviking_history_search`).")

        # 3. I/O Contract (0 ~ 25)
        io_score = 0.0
        lower_content = raw_content.lower()
        matched_io = [kw for kw in _IO_KEYWORDS if kw in lower_content]
        if len(matched_io) >= 2:
            io_score = 25.0
            diagnostics.append(f"I/O Contract: Strong input/output contracts specified ({', '.join(matched_io)}).")
        elif len(matched_io) == 1:
            io_score = 15.0
            diagnostics.append("I/O Contract: Partial input/output definitions.")
            recommendations.append("Define explicit output artifacts, schema, or assertions.")
        else:
            diagnostics.append("I/O Contract: Missing explicit input/output deliverables.")
            recommendations.append("Define expected inputs and measurable delivery criteria.")

        # 4. Fault Tolerance (0 ~ 20)
        fault_score = 0.0
        matched_fault = [kw for kw in _FAULT_KEYWORDS if kw in lower_content]
        if len(matched_fault) >= 2:
            fault_score = 20.0
            diagnostics.append("Fault Tolerance: Comprehensive error handling and retry instructions present.")
        elif len(matched_fault) == 1:
            fault_score = 10.0
            diagnostics.append("Fault Tolerance: Basic error awareness detected.")
            recommendations.append("Add explicit fallback and recovery instructions for potential tool errors.")
        else:
            diagnostics.append("Fault Tolerance: No error handling or retry SOP defined.")
            recommendations.append("Include failure recovery SOP (e.g. fallback tools, retry thresholds).")

        total = round(sop_score + tool_score + io_score + fault_score, 2)
        passed = total >= passing_score and validation.is_valid

        if not validation.is_valid:
            diagnostics.extend(validation.errors)
            recommendations.append("Fix YAML Frontmatter syntax errors before proceeding.")

        scores = {
            "sop_structure": sop_score,
            "tool_contract": tool_score,
            "io_contract": io_score,
            "fault_tolerance": fault_score,
        }

        return SkillJudgeReport(
            passed=passed,
            total_score=total,
            threshold=passing_score,
            scores=scores,
            diagnostics=diagnostics,
            recommendations=recommendations,
        )

    @classmethod
    def evaluate_attempt_trajectory(
        cls,
        skill_slug: str,
        execution_log: list[str],
    ) -> dict[str, Any]:
        """Simulate and grade an execution attempt log against a target skill."""
        if not execution_log:
            return {
                "skill_slug": skill_slug,
                "attempt_success": False,
                "completion_rate": 0.0,
                "verdict": "FAIL_EMPTY_LOG",
            }

        total_lines = len(execution_log)
        tool_invocations = sum(1 for line in execution_log if "tool" in line.lower() or "call" in line.lower())
        has_error = any("error" in line.lower() or "exception" in line.lower() for line in execution_log)
        has_success = any("success" in line.lower() or "done" in line.lower() or "passed" in line.lower() for line in execution_log)

        completion_rate = 1.0 if (has_success and not has_error) else (0.5 if has_success else 0.0)
        verdict = "PASS" if completion_rate >= 0.8 else ("DEGRADED" if completion_rate >= 0.5 else "FAIL")

        return {
            "skill_slug": skill_slug,
            "attempt_success": completion_rate >= 0.8,
            "completion_rate": completion_rate,
            "total_steps": total_lines,
            "tool_invocations": tool_invocations,
            "has_error": has_error,
            "verdict": verdict,
        }
