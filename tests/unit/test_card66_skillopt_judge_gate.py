"""Card-66 Unit Tests: SkillOpt Attempt Simulation & Judge Gate Evaluator.

Verifies:
1. Multi-dimensional quality scoring (SOP, Tool Contract, I/O, Fault Tolerance)
2. Passing gate threshold validation (>= 70.0)
3. Actionable remediation advice generation for low-quality drafts
4. Attempt trajectory execution simulation
5. FastMCP openviking_skill_judge tool invocation
6. Version alignment gate (v1.7.20+)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from openviking.service.skill_opt_judge import SkillOptJudge
from openviking.server.mcp_endpoint import openviking_skill_judge
from openviking._version import __version__


HIGH_QUALITY_SKILL_SAMPLE = """---
name: high-fidelity-debugger
description: Comprehensive SOP for diagnosing and healing runtime memory exceptions.
allowed-tools:
  - openviking_history_search
  - find
triggers:
  - 内存异常排查
---
# High-Fidelity Debugging SOP

## Inputs & Preconditions
Input parameters: session ID and target error stack.

## Step-by-Step Execution Plan
Step 1: Locate relevant past exceptions via `openviking_history_search`.
Step 2: Inspect active memory allocations via `find`.
Step 3: Verify the output artifacts match expected schema.

## Fault Tolerance & Self-Healing
If error occurs during history search, retry with fallback keyword.
Handle unexpected exception gracefully by logging diagnosis.
"""

POOR_SKILL_SAMPLE = """---
name: poor-quality-skill
description: Just some rough notes without formal structure.
---
# Some Notes
Just try to do something vaguely without clear steps or error handling.
"""


def test_skill_opt_judge_high_quality_skill():
    report = SkillOptJudge.evaluate_skill(HIGH_QUALITY_SKILL_SAMPLE, passing_score=70.0)
    assert report.passed is True
    assert report.total_score >= 80.0
    assert report.scores["sop_structure"] == 30.0
    assert report.scores["tool_contract"] == 25.0
    assert report.scores["io_contract"] >= 15.0
    assert report.scores["fault_tolerance"] == 20.0
    assert len(report.diagnostics) > 0


def test_skill_opt_judge_poor_skill_rejection():
    report = SkillOptJudge.evaluate_skill(POOR_SKILL_SAMPLE, passing_score=70.0)
    assert report.passed is False
    assert report.total_score < 70.0
    assert len(report.recommendations) > 0
    assert any("numbered steps" in rec.lower() for rec in report.recommendations)


def test_skill_opt_judge_empty_input():
    report = SkillOptJudge.evaluate_skill("", passing_score=70.0)
    assert report.passed is False
    assert report.total_score == 0.0
    assert any("empty" in d.lower() for d in report.diagnostics)


def test_evaluate_attempt_trajectory():
    success_log = [
        "Step 1: Init sensor",
        "Step 2: Invoking tool openviking_history_search",
        "Step 3: Verification passed and done",
    ]
    res_success = SkillOptJudge.evaluate_attempt_trajectory("test-skill", success_log)
    assert res_success["attempt_success"] is True
    assert res_success["verdict"] == "PASS"
    assert res_success["completion_rate"] == 1.0

    fail_log = [
        "Step 1: Init sensor",
        "Error: Connection refused during tool call",
        "Failed to continue",
    ]
    res_fail = SkillOptJudge.evaluate_attempt_trajectory("test-skill", fail_log)
    assert res_fail["attempt_success"] is False
    assert res_fail["has_error"] is True


@pytest.mark.asyncio
async def test_openviking_skill_judge_mcp_tool():
    raw_json = await openviking_skill_judge(HIGH_QUALITY_SKILL_SAMPLE, passing_score=70.0)
    data = json.loads(raw_json)
    assert data["passed"] is True
    assert data["total_score"] >= 80.0
    assert "scores" in data
    assert "sop_structure" in data["scores"]


def test_card66_version_alignment():
    pkg_path = Path(__file__).resolve().parents[2] / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    pkg_version = pkg_data["version"]
    assert pkg_version == __version__, f"Version mismatch: {pkg_version} vs {__version__}"

    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7), f"Expected 1.7.x, got {__version__}"
    assert parts[2] >= 20, f"Expected patch >= 20, got {parts[2]}"
