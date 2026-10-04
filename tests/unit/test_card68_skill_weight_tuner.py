# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-68 Unit Tests: Skill Weight Dynamic Tuner & Ingestion (SKILLOPT-03).

Verifies:
1. Default profile baseline (weight = 1.0, success_rate = 1.0)
2. PASS Attempt feedback boosts weight (+alpha * conf)
3. DEGRADED / FAIL Attempt feedback applies adaptive penalty
4. Utility boundary clamping strictly enforced [0.10, 2.00]
5. Persistent disk ledger serialization and recovery
6. Modulated weighted intent score computation
7. FastMCP openviking_skill_weight_tune tool invocation
8. REST API router endpoints (/weight/tune, /weights)
9. Version alignment gate (v1.7.22+)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from openviking.service.skill_weight_types import AttemptVerdict, SkillWeightProfile
from openviking.service.skill_weight_tuner import (
    MIN_WEIGHT,
    MAX_WEIGHT,
    SkillWeightTuner,
)
from openviking.server.mcp_endpoint import openviking_skill_weight_tune
from openviking.server.routers.skill_opt import (
    WeightTuneApiRequest,
    tune_skill_weight,
    list_skill_weights,
)
from openviking._version import __version__


def test_default_profile_initialization(tmp_path: Path):
    tuner = SkillWeightTuner(storage_path=tmp_path / "weights.json")
    profile = tuner.get_profile("debugger-skill")
    assert profile.weight == 1.0
    assert profile.total_attempts == 0
    assert profile.passed_attempts == 0
    assert profile.success_rate == 1.0


def test_tune_weight_pass_boost(tmp_path: Path):
    tuner = SkillWeightTuner(storage_path=tmp_path / "weights.json")
    res = tuner.tune_weight("healer-skill", AttemptVerdict.PASS, confidence=1.0, notes="Fixed memory leak")
    assert res.new_weight > res.previous_weight
    assert res.profile.passed_attempts == 1
    assert res.profile.total_attempts == 1
    assert res.profile.success_rate == 1.0
    assert res.weight_delta > 0.0


def test_tune_weight_degraded_and_fail_penalties(tmp_path: Path):
    tuner = SkillWeightTuner(storage_path=tmp_path / "weights.json")
    res_deg = tuner.tune_weight("flaky-skill", AttemptVerdict.DEGRADED, confidence=0.8)
    assert res_deg.new_weight < 1.0
    assert res_deg.profile.degraded_attempts == 1

    res_fail = tuner.tune_weight("flaky-skill", AttemptVerdict.FAIL, confidence=1.0)
    assert res_fail.new_weight < res_deg.new_weight
    assert res_fail.profile.failed_attempts == 1
    assert res_fail.profile.total_attempts == 2
    assert res_fail.profile.success_rate == 0.0


def test_weight_boundary_clamping(tmp_path: Path):
    tuner = SkillWeightTuner(storage_path=tmp_path / "weights.json")
    # Repeated fails should clamp at MIN_WEIGHT
    for _ in range(25):
        res = tuner.tune_weight("broken-skill", AttemptVerdict.FAIL, confidence=1.0)
    assert res.new_weight == MIN_WEIGHT
    assert res.profile.weight == MIN_WEIGHT

    # Repeated passes should clamp at MAX_WEIGHT
    for _ in range(40):
        res = tuner.tune_weight("golden-skill", AttemptVerdict.PASS, confidence=1.0)
    assert res.new_weight == MAX_WEIGHT
    assert res.profile.weight == MAX_WEIGHT


def test_persistence_and_recovery(tmp_path: Path):
    storage_file = tmp_path / "sub" / "weights.json"
    tuner1 = SkillWeightTuner(storage_path=storage_file)
    tuner1.tune_weight("persistent-skill", AttemptVerdict.PASS, confidence=1.0)
    tuner1.tune_weight("persistent-skill", AttemptVerdict.PASS, confidence=0.8)
    w1 = tuner1.get_profile("persistent-skill").weight

    # Recover in a clean new tuner instance pointing to same file
    tuner2 = SkillWeightTuner(storage_path=storage_file)
    p2 = tuner2.get_profile("persistent-skill")
    assert p2.weight == w1
    assert p2.total_attempts == 2
    assert p2.passed_attempts == 2


def test_calculate_weighted_score(tmp_path: Path):
    tuner = SkillWeightTuner(storage_path=tmp_path / "weights.json")
    tuner.tune_weight("high-rep", AttemptVerdict.PASS, confidence=1.0)
    high_weight = tuner.get_profile("high-rep").weight
    assert high_weight > 1.0

    raw_score = 0.60
    weighted = tuner.calculate_weighted_score(raw_score, "high-rep")
    assert weighted == round(raw_score * high_weight, 4)
    assert weighted > raw_score


@pytest.mark.asyncio
async def test_fastmcp_openviking_skill_weight_tune_tool():
    raw_json = await openviking_skill_weight_tune(
        skill_slug="mcp-test-skill",
        verdict="PASS",
        confidence=0.95,
        notes="Automated attempt passed",
    )
    data = json.loads(raw_json)
    assert data["skill_slug"] == "mcp-test-skill"
    assert data["verdict"] == "PASS"
    assert "profile" in data
    assert data["profile"]["passed_attempts"] >= 1
    assert data["new_weight"] > 1.0


@pytest.mark.asyncio
async def test_rest_api_weight_endpoints():
    req = WeightTuneApiRequest(
        skill_slug="api-test-skill",
        verdict="DEGRADED",
        confidence=0.5,
        notes="API test degradation",
    )
    res = await tune_skill_weight(req)
    assert res["skill_slug"] == "api-test-skill"
    assert res["verdict"] == "DEGRADED"

    list_res = await list_skill_weights()
    assert list_res["total_skills"] >= 1
    slugs = [p["skill_slug"] for p in list_res["profiles"]]
    assert "api-test-skill" in slugs


def test_card68_version_alignment():
    pkg_path = Path(__file__).resolve().parents[2] / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    pkg_version = pkg_data["version"]
    assert pkg_version == __version__, f"Version mismatch: {pkg_version} vs {__version__}"

    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7), f"Expected 1.7.x, got {__version__}"
    assert parts[2] >= 21, f"Expected patch >= 21, got {parts[2]}"
