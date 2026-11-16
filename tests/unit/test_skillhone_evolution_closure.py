# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""SkillHone evolution regression & decision history closure tests (Card-254)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.evolution_cicd import (
    AutonomousLevel,
    EvolutionCICDPipeline,
    PipelineStage,
    SecondOrderMetrics,
)
from openviking.core.rsi_trajectory_store import RSITrajectoryStore
from openviking.server.routers.evolution_cicd import router


@pytest.fixture
def isolated_cicd(tmp_path: Path):
    RSITrajectoryStore.reset_instance()
    store = RSITrajectoryStore.get_instance(tmp_path / "skillhone.db")
    pipeline = EvolutionCICDPipeline.get_instance()
    pipeline.set_store(store)
    pipeline.packages.clear()
    pipeline.autonomous_level = AutonomousLevel.LEVEL_2_BOUNDED_AUTO
    pipeline.emergency_kill_switch_tripped = False
    pipeline.auto_downgrade_count = 0
    pipeline.metrics = SecondOrderMetrics()
    yield pipeline, store, tmp_path
    pipeline.packages.clear()
    pipeline.set_store(None)
    RSITrajectoryStore.reset_instance()


def _create_base_skill_dir(root: Path, name: str = "demo-skill") -> Path:
    sdir = root / name
    (sdir / "scripts").mkdir(parents=True)
    (sdir / "references").mkdir(parents=True)
    (sdir / "scripts" / "check.py").write_text("VALUE = 1\n", encoding="utf-8")
    (sdir / "references" / "guide.md").write_text("# Guide\nRun [check](../scripts/check.py)\n", encoding="utf-8")
    (sdir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: SkillHone test skill\n---\n\nSee scripts/check.py and references/guide.md.\n",
        encoding="utf-8",
    )
    return sdir


def test_optimizer_context_sanitizes_secrets_and_holdout_details(isolated_cicd):
    pipeline, store, _ = isolated_cicd
    store.record_skill_decision(
        package_id="pkg_prev",
        skill_name="demo-skill",
        diagnosis="Broken script ref sk-1234567890abcdef",
        candidate_patches={"diff_patch": "bad"},
        eval_evidence={"passed": False},
        patch_fingerprint="fp_rejected_001",
        decision="rejected",
        rationale="Broken reference scripts/missing.py",
    )
    raw_signal = (
        "Failure token=vk-sk-secret9988776655\n"
        "# HOLDOUT-PRIVATE\nassert secret_case == 42\n"
        "# Public\nMissing script check.py exit code 1"
    )
    ctx = pipeline.prepare_optimizer_context("demo-skill", raw_signal)
    assert "vk-sk-secret9988776655" not in ctx.sanitized_signal
    assert "secret_case" not in ctx.sanitized_signal
    assert "[REDACTED_SECRET]" in ctx.sanitized_signal
    assert "[REDACTED_HOLDOUT_DETAILS]" in ctx.sanitized_signal
    assert "fp_rejected_001" in ctx.avoided_fingerprints
    assert "sk-1234567890abcdef" not in ctx.avoided_rationales[0]["diagnosis"]


def test_broken_bundle_and_failed_regression_block_promotion_without_mutating_source(isolated_cicd):
    pipeline, store, tmp_path = isolated_cicd
    skill_dir = _create_base_skill_dir(tmp_path)
    original_skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    # 1. Broken reference blocks ISOLATED_EVALUATION -> SAFETY_GATE
    pkg_broken = pipeline.create_package(
        "demo-skill",
        skill_dir=skill_dir,
        package_files={
            "SKILL.md": "---\nname: demo-skill\ndescription: Updated\n---\nUse scripts/missing_tool.py\n"
        },
        diagnosis="Attempted broken script ref",
    )
    assert pipeline.advance_package(pkg_broken.package_id)[0]
    assert pipeline.advance_package(pkg_broken.package_id)[0]
    ok, msg = pipeline.advance_package(pkg_broken.package_id)
    assert ok is False
    assert "Isolated Evaluation rejected" in msg
    assert "missing_tool.py" in msg
    assert pkg_broken.current_stage == PipelineStage.ISOLATED_EVALUATION
    assert pkg_broken.decision == "rejected"
    assert (skill_dir / "SKILL.md").read_text(encoding="utf-8") == original_skill_md

    # 2. Regression command failure inside sandbox blocks promotion & records history
    py = sys.executable
    pkg_fail_cmd = pipeline.create_package(
        "demo-skill",
        skill_dir=skill_dir,
        package_files={"scripts/check.py": "VALUE = 0\n"},
        diagnosis="Set VALUE=0 candidate",
        regression_commands=[[py, "-c", "import check; assert check.VALUE == 1"]],
    )
    # Run from scripts/ import path via python snippet checking scripts/check.py
    pkg_fail_cmd.regression_commands = [
        [py, "-c", "import sys; sys.path.insert(0, 'scripts'); import check; assert check.VALUE == 1"]
    ]
    pipeline.advance_package(pkg_fail_cmd.package_id)
    pipeline.advance_package(pkg_fail_cmd.package_id)
    ok2, msg2 = pipeline.advance_package(pkg_fail_cmd.package_id)
    assert ok2 is False
    assert "Regression command(s) failed" in msg2
    assert (skill_dir / "scripts" / "check.py").read_text(encoding="utf-8") == "VALUE = 1\n"

    # 3. Persisted rejected history avoids repeating identical failing candidate
    rejected = store.get_rejected_decisions("demo-skill")
    assert len(rejected) == 2
    pkg_repeat = pipeline.create_package(
        "demo-skill",
        skill_dir=skill_dir,
        package_files={"scripts/check.py": "VALUE = 0\n"},
        diagnosis="Accidentally repeated rejected fix",
    )
    assert len(pkg_repeat.rejected_history_refs) == 2
    pipeline.advance_package(pkg_repeat.package_id)
    pipeline.advance_package(pkg_repeat.package_id)
    ok3, msg3 = pipeline.advance_package(pkg_repeat.package_id)
    assert ok3 is False
    assert "previously rejected patch fingerprint" in msg3


def test_valid_full_bundle_passes_isolated_regression_and_persists_accepted_decision(isolated_cicd):
    pipeline, store, tmp_path = isolated_cicd
    skill_dir = _create_base_skill_dir(tmp_path)
    py = sys.executable

    pkg = pipeline.create_package(
        "demo-skill",
        diff_patch="+- Added scripts/helper.py and updated SKILL.md reference",
        skill_dir=skill_dir,
        package_files={
            "SKILL.md": (
                "---\nname: demo-skill\ndescription: SkillHone verified\n---\n\n"
                "See scripts/check.py, scripts/helper.py and references/guide.md.\n"
            ),
            "scripts/helper.py": "def ok():\n    return 42\n",
        },
        diagnosis="Add helper module with isolated regression check",
        regression_commands=[
            [py, "-c", "import sys; sys.path.insert(0, 'scripts'); import check, helper; assert check.VALUE == 1 and helper.ok() == 42"]
        ],
    )
    assert pkg.review_manifest["added_files"] == ["scripts/helper.py"]
    assert pkg.review_manifest["modified_files"] == ["SKILL.md"]

    # Advance through all stages to EXPERIENCE_CRYSTALLIZATION
    for _ in range(6):
        ok, msg = pipeline.advance_package(pkg.package_id)
        assert ok is True, msg

    assert pkg.current_stage == PipelineStage.EXPERIENCE_CRYSTALLIZATION
    assert pkg.decision == "accepted"
    assert pkg.eval_evidence["passed"] is True

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    res = client.get("/api/v1/evolution/decisions?skill_name=demo-skill&decision=accepted")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["package_id"] == pkg.package_id
    assert body["items"][0]["candidate_patches"]["review_manifest"]["added_files"] == ["scripts/helper.py"]
    assert store.count_summary()["skill_decisions_total"] >= 1
