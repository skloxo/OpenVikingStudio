"""Card-64 Unit Tests: Skill Trigger Intent Matching & Simulation Sandbox.

Verifies:
1. Exact match and substring containment boosting
2. Multi-language character n-gram fuzzy matching
3. Threshold-based rejection and boundary robustness
4. Intent routing collision detection between multiple skills
5. FastMCP openviking_skill_intent_match tool invocation
6. Version alignment gate (v1.7.18+)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from openviking.service.skill_intent_matcher import SkillIntentMatcher
from openviking.server.mcp_endpoint import openviking_skill_intent_match
from openviking._version import __version__


def test_exact_and_containment_matching():
    triggers = ["压缩记忆", "清理上下文", "整理历史会话"]

    # 1. Exact match
    res_exact = SkillIntentMatcher.match_intent("压缩记忆", triggers)
    assert res_exact.matched is True
    assert res_exact.best_trigger == "压缩记忆"
    assert res_exact.score == 1.0

    # 2. Substring containment
    res_contain = SkillIntentMatcher.match_intent("请帮我压缩记忆，释放上下文", triggers)
    assert res_contain.matched is True
    assert res_contain.best_trigger == "压缩记忆"
    assert res_contain.score >= 0.85


def test_fuzzy_ngram_matching():
    triggers = ["diagnosing-bugs", "memory-compaction", "code-review"]

    # Fuzzy match with slight variations
    res_fuzzy = SkillIntentMatcher.match_intent("diagnose bugs in my code", triggers, threshold=0.4)
    assert res_fuzzy.matched is True
    assert res_fuzzy.best_trigger == "diagnosing-bugs"
    assert res_fuzzy.score > 0.4


def test_below_threshold_rejection():
    triggers = ["量化交易", "因子计算", "风控雷达"]
    res_irrelevant = SkillIntentMatcher.match_intent("今天天气真好，出去散步", triggers, threshold=0.6)
    assert res_irrelevant.matched is False
    assert res_irrelevant.score < 0.6
    assert "threshold" in res_irrelevant.reason


def test_empty_inputs_handling():
    res1 = SkillIntentMatcher.match_intent("", ["trigger"])
    assert res1.matched is False

    res2 = SkillIntentMatcher.match_intent("valid query", [])
    assert res2.matched is False

    res3 = SkillIntentMatcher.match_intent("valid query", ["   "])
    assert res3.matched is False


def test_intent_collision_detection():
    candidate_triggers = ["上下文压缩", "记忆整理"]
    existing_skills = {
        "memory-vault": ["上下文压缩", "历史会话归档"],
        "code-cleaner": ["重构代码", "死代码清理"],
    }

    report = SkillIntentMatcher.detect_collisions(candidate_triggers, existing_skills, threshold=0.8)
    assert report.has_collision is True
    assert len(report.collisions) == 1
    assert report.collisions[0]["conflicting_skill"] == "memory-vault"

    # No collision scenario
    report_safe = SkillIntentMatcher.detect_collisions(
        ["全新未见技能意图短语"], existing_skills, threshold=0.8
    )
    assert report_safe.has_collision is False
    assert len(report_safe.collisions) == 0


@pytest.mark.asyncio
async def test_openviking_skill_intent_match_mcp():
    raw_json = await openviking_skill_intent_match(
        query="帮我排查程序报错与异常",
        triggers=["排查程序报错", "代码调试", "性能分析"],
        threshold=0.6,
    )
    data = json.loads(raw_json)
    assert data["matched"] is True
    assert data["best_trigger"] == "排查程序报错"
    assert data["score"] >= 0.6


def test_card64_version_alignment():
    pkg_path = Path(__file__).resolve().parents[2] / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    pkg_version = pkg_data["version"]
    assert pkg_version == __version__, f"Version mismatch: {pkg_version} vs {__version__}"

    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7), f"Expected 1.7.x, got {__version__}"
    assert parts[2] >= 18, f"Expected patch >= 18, got {parts[2]}"
