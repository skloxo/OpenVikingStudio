# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-20H: AHE Contract Triad & PolarJudge Mount in Skill Pipeline.
(Card-AHE-PolarJudge-SkillPipeline-Mount / v1.5.84)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.core.ahe_engine import AHEEngine
from openviking.core.ahe_manifest import ManifestStore, MechanismKind
from openviking.core.ahe_cluster_catalog import ClusterCatalog
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.ahe import router as ahe_router
from openviking.service.skill_opt_service import SkillOptService
from openviking.service.skill_opt_types import SkillOptOptimizeRequest
from openviking_cli.session.user_id import UserIdentifier

SAMPLE_SKILL = """---
name: sample-agent-skill
description: 基础测试技能，用于验证 AHE 契约门禁。
tools:
  - openviking_find
---

# Sample Skill

## 1. 触发意图与场景
- 触发关键词：测试、排查、验证。

## 2. 边界约束与负向判定
- 何时严禁使用：当未指定测试目标时严禁运行。

## 3. 标准操作清单
1. 步骤一；
2. 步骤二。

## 4. 调用示例
```bash
python3 -c 'print("ok")'
```
"""


@pytest.fixture(autouse=True)
def reset_ahe():
    ManifestStore.get_instance().reset_for_test()
    ClusterCatalog.get_instance().reset_for_test()
    yield
    ManifestStore.get_instance().reset_for_test()
    ClusterCatalog.get_instance().reset_for_test()


def test_skill_opt_with_ahe_gate_pass():
    """Verify that SkillOpt with enable_ahe_gate passes when PolarJudge succeeds."""
    service = SkillOptService()
    req = SkillOptOptimizeRequest(
        skill_content=SAMPLE_SKILL,
        skill_name="sample-agent-skill",
        enable_ahe_gate=True,
        validation_command="python3 -c 'print(\"POLAR_PASS\"); exit(0)'",
    )

    res = service.optimize_content(req)
    assert res.ahe_gate_passed is True
    assert res.ahe_blocked_reason is None
    assert res.manifest_id is not None
    assert res.polar_verdict == "pass"

    # Verify manifest state in store
    manifest = AHEEngine.get_instance().get_manifest(res.manifest_id)
    assert manifest is not None
    assert manifest.status.value == "verified"


def test_skill_opt_with_ahe_gate_block_on_polar_fail():
    """Verify that SkillOpt with enable_ahe_gate BLOCKS when PolarJudge fails."""
    service = SkillOptService()
    req = SkillOptOptimizeRequest(
        skill_content=SAMPLE_SKILL,
        skill_name="sample-agent-skill",
        enable_ahe_gate=True,
        validation_command="python3 -c 'import sys; sys.exit(7)'",
    )

    res = service.optimize_content(req)
    assert res.ahe_gate_passed is False
    assert res.ahe_blocked_reason is not None
    assert "exit=7" in res.ahe_blocked_reason
    assert res.polar_verdict == "fail"

    # Verify manifest was recorded as violated
    manifest = AHEEngine.get_instance().get_manifest(res.manifest_id)
    assert manifest is not None
    assert manifest.status.value == "violated"

    # Verify cluster catalog recorded the failure
    catalog = ClusterCatalog.get_instance()
    clusters = catalog.get_all()
    assert any(c.mechanism == MechanismKind.QUALITY_DEGRADATION for c in clusters)


def test_ahe_physical_snapshot_and_rollback():
    """Verify that file snapshot capture, drift detection, and physical rollback work on disk."""
    engine = AHEEngine.get_instance()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        f.write("# Original Pristine Content\nVersion 1.0\n")
        skill_file = f.name

    try:
        # 1. Create manifest capturing file snapshot
        manifest = engine.create_manifest(
            skill_name="rollback-skill",
            snapshot_paths=[skill_file],
            assumptions=[{"description": "Base test", "validation_command": "true"}],
        )

        assert len(manifest.snapshots) == 1
        assert manifest.snapshots[0].content_backup is not None
        assert "Original Pristine Content" in manifest.snapshots[0].content_backup

        # 2. Modify file to simulate an external or corrupting edit
        Path(skill_file).write_text("# Corrupted Content\nBad edit!\n", encoding="utf-8")

        # 3. Drift check detects deviation
        drift_res = engine.check_snapshot_drift(manifest.manifest_id)
        assert drift_res["snapshot_clean"] is False
        assert len(drift_res["drifted_files"]) == 1

        # 4. Trigger physical rollback
        rb_res = engine.rollback_manifest(manifest.manifest_id)
        assert rb_res["rolled_back"] is True

        # 5. File content on disk is restored
        restored_text = Path(skill_file).read_text(encoding="utf-8")
        assert "Original Pristine Content" in restored_text
        assert "Corrupted Content" not in restored_text

        # 6. Drift check is now clean
        drift_clean = engine.check_snapshot_drift(manifest.manifest_id)
        assert drift_clean["snapshot_clean"] is True

    finally:
        Path(skill_file).unlink(missing_ok=True)


def test_ahe_rollback_rest_api():
    """Verify POST /api/v1/ahe/manifest/{id}/rollback endpoint."""
    app = FastAPI()
    app.include_router(ahe_router)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    client = TestClient(app)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        f.write("# Safe Initial Content\n")
        temp_path = f.name

    try:
        # Create manifest via API
        resp = client.post(
            "/api/v1/ahe/manifest",
            json={
                "skill_name": "api-rb-skill",
                "snapshot_paths": [temp_path],
                "assumptions": [],
            },
        )
        assert resp.status_code == 200
        mid = resp.json()["manifest_id"]

        # Corrupt file
        Path(temp_path).write_text("# Unintended Write\n", encoding="utf-8")

        # Call rollback API
        rb_resp = client.post(f"/api/v1/ahe/manifest/{mid}/rollback")
        assert rb_resp.status_code == 200
        data = rb_resp.json()
        assert data["rolled_back"] is True

        # File restored
        content = Path(temp_path).read_text(encoding="utf-8")
        assert "# Safe Initial Content\n" == content

    finally:
        Path(temp_path).unlink(missing_ok=True)
