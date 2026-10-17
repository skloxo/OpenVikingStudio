# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Automated Harness Evolution (AHE) Engine.

测试套件:
  test_ahe_assumption            AHE 可证伪假设结构与字段
  test_file_snapshot             文件快照哈希计算与秒级漂移检测
  test_ahe_manifest_and_store    Manifest 生命周期与 ManifestStore 增删查
  test_cluster_catalog           根因机制聚类与冻结面补丁冲突排他检测
  test_polar_judge               Polar 真实沙箱判官 (exit code 真理判定)
  test_ahe_engine_e2e            AHE 统一调度引擎端到端验证闭环
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# 确保项目根在 sys.path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.ahe_manifest import (
    AHEAssumption,
    AHEManifest,
    AHEStatus,
    FileSnapshot,
    ManifestStore,
    MechanismKind,
)
from openviking.core.ahe_cluster_catalog import (
    ClusterCatalog,
    ClusterEntry,
)
from openviking.core.polar_judge import (
    PolarJudge,
    PolarProbeResult,
    PolarVerdict,
)
from openviking.core.ahe_engine import AHEEngine


# ---------------------------------------------------------------------------
# 1. 可证伪假设测试
# ---------------------------------------------------------------------------

def test_ahe_assumption():
    """测试 AHE 可证伪假设结构与字段。"""
    asm = AHEAssumption(
        description="P99 latency under 200ms",
        validation_command="python3 -c 'exit(0)'",
        frozen_surface="openviking/core/ahe_engine.py:10-50",
    )
    assert asm.assumption_id.startswith("asm-")
    assert asm.description == "P99 latency under 200ms"
    assert asm.validation_command == "python3 -c 'exit(0)'"
    assert asm.frozen_surface == "openviking/core/ahe_engine.py:10-50"
    assert asm.verified_at is None


# ---------------------------------------------------------------------------
# 2. 文件快照哈希与漂移检测
# ---------------------------------------------------------------------------

def test_file_snapshot():
    """测试 FileSnapshot 捕获哈希与变更检测 (可回滚判定)。"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("initial snapshot content\n")
        temp_path = f.name

    try:
        snap = FileSnapshot.capture(temp_path)
        assert snap.sha256 != ""
        assert snap.still_matches() is True

        # 修改文件内容
        with open(temp_path, "w") as f:
            f.write("modified content\n")

        # 快照应检测到漂移
        assert snap.still_matches() is False
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. Manifest 与 ManifestStore 生命周期
# ---------------------------------------------------------------------------

def test_ahe_manifest_and_store():
    """测试 AHEManifest 状态流转与 ManifestStore 存储检索。"""
    store = ManifestStore.get_instance()

    manifest = AHEManifest(
        skill_name="test-skill",
        assumptions=[
            AHEAssumption(
                description="Command must succeed",
                validation_command="true",
            )
        ],
    )
    assert manifest.status == AHEStatus.ACTIVE
    assert manifest.manifest_id.startswith("ahe-")

    store.upsert(manifest)
    fetched = store.get(manifest.manifest_id)
    assert fetched is not None
    assert fetched.skill_name == "test-skill"

    # 标记已验证
    manifest.mark_verified()
    assert manifest.status == AHEStatus.VERIFIED

    # 标记违约与根因归因
    manifest.mark_violated(MechanismKind.STATE_RACE, "Detected concurrent lock acquisition")
    assert manifest.status == AHEStatus.VIOLATED
    assert manifest.violation_cause == MechanismKind.STATE_RACE
    assert "concurrent lock" in (manifest.violation_detail or "")


# ---------------------------------------------------------------------------
# 4. 根因机制聚类与冻结面补丁冲突检测
# ---------------------------------------------------------------------------

def test_cluster_catalog():
    """测试 RootCauseClusterCatalog 聚类聚合与已打补丁排他拦截。"""
    catalog = ClusterCatalog.get_instance()
    catalog.reset_for_test()

    # 首次归入
    entry1 = catalog.ingest(MechanismKind.TOOL_INTERFACE, "ahe-001", "Interface signature mismatch")
    assert entry1.occurrence_count == 1
    assert catalog.find_patch_conflict(MechanismKind.TOOL_INTERFACE) is None

    # 同机制再次出现 -> 频次 +1，聚合至同一 cluster
    entry2 = catalog.ingest(MechanismKind.TOOL_INTERFACE, "ahe-002", "Another tool signature change")
    assert entry2.cluster_id == entry1.cluster_id
    assert entry2.occurrence_count == 2

    # 标记已打补丁 (冻结面)
    assert catalog.mark_patched(MechanismKind.TOOL_INTERFACE, "commit-764af17cc") is True

    # 再次检测冲突 -> 触发冻结面冲突告警
    conflict = catalog.find_patch_conflict(MechanismKind.TOOL_INTERFACE)
    assert conflict is not None
    assert conflict.patch_commit == "commit-764af17cc"

    # 未打补丁的机制无冲突
    assert catalog.find_patch_conflict(MechanismKind.BUDGET_EXCEEDED) is None

    # 汇总统计
    summary = catalog.summary()
    assert summary["total_clusters"] == 1
    assert summary["patched_clusters"] == 1
    assert summary["total_occurrences"] == 2


# ---------------------------------------------------------------------------
# 5. Polar 不可伪造真实沙箱判官
# ---------------------------------------------------------------------------

def test_polar_judge():
    """测试 PolarJudge 真实执行命令，以物理 exit code 为真理。"""
    judge = PolarJudge(default_timeout_sec=5.0)

    # 成功用例 (exit 0)
    res_pass = judge.probe("python3 -c 'print(\"POLAR_TRUTH_PASS\")'")
    assert res_pass.verdict == PolarVerdict.PASS
    assert res_pass.exit_code == 0
    assert "POLAR_TRUTH_PASS" in res_pass.stdout_tail
    assert res_pass.duration_ms > 0

    # 失败用例 (exit 2)
    res_fail = judge.probe("python3 -c 'import sys; sys.exit(2)'")
    assert res_fail.verdict == PolarVerdict.FAIL
    assert res_fail.exit_code == 2

    # 空命令错误
    res_err = judge.probe("   ")
    assert res_err.verdict == PolarVerdict.ERROR


# ---------------------------------------------------------------------------
# 6. AHEEngine 端到端验证与生命周期闭环
# ---------------------------------------------------------------------------

def test_ahe_engine_e2e():
    """测试 AHEEngine 统一调度生命周期闭环。"""
    engine = AHEEngine.get_instance()

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("ahe e2e content\n")
        temp_path = f.name

    try:
        # 1. 创建契约 Manifest
        manifest = engine.create_manifest(
            skill_name="e2e-test-skill",
            assumptions=[
                {
                    "description": "Python expression evaluates to 42",
                    "validation_command": "python3 -c 'print(42)'",
                    "frozen_surface": "test:1-10",
                }
            ],
            snapshot_paths=[temp_path],
        )
        assert manifest.manifest_id.startswith("ahe-")
        assert len(manifest.assumptions) == 1
        assert len(manifest.snapshots) == 1

        # 2. Polar 判官物理验证
        verify_res = engine.verify_manifest(manifest.manifest_id)
        assert verify_res["status"] == "verified"
        assert len(verify_res["results"]) == 1
        assert verify_res["results"][0]["verdict"] == "pass"
        assert verify_res["results"][0]["exit_code"] == 0

        # 3. 检查文件快照一致性
        drift1 = engine.check_snapshot_drift(manifest.manifest_id)
        assert drift1["snapshot_clean"] is True
        assert len(drift1["drifted_files"]) == 0

        # 修改文件模拟外部漂移
        with open(temp_path, "w") as f:
            f.write("changed content\n")

        drift2 = engine.check_snapshot_drift(manifest.manifest_id)
        assert drift2["snapshot_clean"] is False
        assert len(drift2["drifted_files"]) == 1

        # 4. 模拟失败归因聚类
        violation = engine.ingest_violation(
            manifest_id=manifest.manifest_id,
            mechanism=MechanismKind.OUTPUT_CONTRACT,
            description="Output format does not conform to JSON contract",
        )
        assert violation["mechanism"] == "output_contract"
        assert violation["occurrence_count"] >= 1

        # 5. 全局汇总
        summary = engine.global_summary()
        assert summary["manifests"]["total"] >= 1
        assert summary["clusters"]["total_clusters"] >= 1
    finally:
        Path(temp_path).unlink(missing_ok=True)
