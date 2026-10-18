# -*- coding: utf-8 -*-
"""Unit tests for SeamDecisionGateB5 (Stage 0 Ante-Gate with 4 Ratified Grill-Me Decisions)."""

import pytest
from pathlib import Path
from openviking.service.auto_crystallizer_b5 import SeamDecisionGateB5


def test_capacity_ceiling_and_cell_division(tmp_path: Path):
    """Q1: When target bundle reaches capacity limit (100 scenarios), trigger CELL_DIVISION_REQUIRED."""
    bundle_dir = tmp_path / "system-fleet-ops"
    scenarios_dir = bundle_dir / "scenarios"
    modules_dir = bundle_dir / "modules"
    scenarios_dir.mkdir(parents=True)
    modules_dir.mkdir(parents=True)

    # Create 100 mock scenarios
    for i in range(100):
        (scenarios_dir / f"scenario_{i:03d}.md").write_text("Mock scenario", encoding="utf-8")

    (bundle_dir / "SKILL.md").write_text(
        "---\nname: system-fleet-ops\ntriggers:\n  - 节点巡检\n  - 集群同步\n---\n# Master",
        encoding="utf-8",
    )
    (modules_dir / "01_fleet.md").write_text(
        "# Fleet Module\nRuntime: linux\nTools: ssh, docker\nAction: 节点巡检\nLib: paramiko",
        encoding="utf-8",
    )

    decision = SeamDecisionGateB5.audit_candidate(
        candidate_name="edge-satellite-ops",
        scenario_count=15,
        keywords=["节点巡检", "集群同步"],
        toolchain=["ssh", "docker"],
        existing_bundles_dir=tmp_path,
        runtime="linux",
        action_verb_noun=["节点巡检"],
        dedicated_libs=["paramiko"],
    )

    assert decision["decision"] == "CELL_DIVISION_REQUIRED"
    assert "细胞分裂" in decision["reason"]
    assert decision["current_scenarios"] == 100


def test_slot_hot_plugging(tmp_path: Path):
    """Q2: Slot hot-plugging appends scenario to module without modifying master SKILL.md."""
    bundle_dir = tmp_path / "network-tunnel-ops"
    modules_dir = bundle_dir / "modules"
    scenarios_dir = bundle_dir / "scenarios"
    modules_dir.mkdir(parents=True)
    scenarios_dir.mkdir(parents=True)

    master_skill = bundle_dir / "SKILL.md"
    master_content = "---\nname: network-tunnel-ops\n---\n# Network Master\n"
    master_skill.write_text(master_content, encoding="utf-8")

    mod_file = modules_dir / "01_cellular_cpe_routing.md"
    mod_file.write_text("# Cellular CPE Routing\n\n### 专精场景清单\n", encoding="utf-8")

    new_scenario = scenarios_dir / "cpe_cj888c_luci_flow.md"
    new_scenario.write_text("# New CPE Flow", encoding="utf-8")

    res = SeamDecisionGateB5.hot_plug_slot(
        bundle_dir=bundle_dir,
        scenario_file=new_scenario,
        target_module_file=mod_file,
        scenario_title="创景 CJ888C 表单自动化",
        scenario_summary="自动配置网络重定向",
    )

    assert res["status"] == "SUCCESS_HOT_PLUGGED"
    # Verify module has the link with backticks
    mod_txt = mod_file.read_text(encoding="utf-8")
    assert "[`cpe_cj888c_luci_flow`](../scenarios/cpe_cj888c_luci_flow.md)" in mod_txt
    # Master SKILL.md must remain completely untouched!
    assert master_skill.read_text(encoding="utf-8") == master_content


def test_triad_fingerprint_high_confidence_merge(tmp_path: Path):
    """Q3: High triad affinity (>=75) triggers MERGE_INTO_EXISTING."""
    bundle_dir = tmp_path / "network-tunnel-ops"
    modules_dir = bundle_dir / "modules"
    modules_dir.mkdir(parents=True)

    (bundle_dir / "SKILL.md").write_text(
        "---\nname: network-tunnel-ops\ntriggers:\n  - 路由器\n  - ttl伪装\n---\n# Master",
        encoding="utf-8",
    )
    (modules_dir / "01_cpe.md").write_text(
        "# CPE\nRuntime: openwrt\nAction: ttl伪装\nLib: requests_luci\nTool: luci",
        encoding="utf-8",
    )

    decision = SeamDecisionGateB5.audit_candidate(
        candidate_name="cellular-cpe-ops",
        scenario_count=12,
        keywords=["路由器", "ttl伪装"],
        toolchain=["luci"],
        existing_bundles_dir=tmp_path,
        runtime="openwrt",
        action_verb_noun=["ttl伪装"],
        dedicated_libs=["requests_luci"],
    )

    assert decision["decision"] == "MERGE_INTO_EXISTING"
    assert decision["target"] == "network-tunnel-ops"
    assert decision["affinity_score"] >= 75.0


def test_triad_fingerprint_gray_zone_confirm(tmp_path: Path):
    """Q3: Gray zone affinity (25 < score < 75) triggers CONFIRM_WITH_HUMAN."""
    bundle_dir = tmp_path / "system-fleet-ops"
    modules_dir = bundle_dir / "modules"
    modules_dir.mkdir(parents=True)

    (bundle_dir / "SKILL.md").write_text(
        "---\nname: system-fleet-ops\ntriggers:\n  - 运维脚本\n---\n# Master",
        encoding="utf-8",
    )
    (modules_dir / "01_ops.md").write_text("# Ops\nRuntime: linux", encoding="utf-8")

    decision = SeamDecisionGateB5.audit_candidate(
        candidate_name="ambiguous-tool",
        scenario_count=10,
        keywords=["运维脚本"],
        toolchain=["bash"],
        existing_bundles_dir=tmp_path,
        runtime="linux",
    )

    assert decision["decision"] == "CONFIRM_WITH_HUMAN"
    assert "灰色争议区" in decision["reason"]


def test_triad_fingerprint_low_affinity_spawn(tmp_path: Path):
    """Q3: Low triad affinity (<=25) triggers SPAWN_NEW_BUNDLE."""
    decision = SeamDecisionGateB5.audit_candidate(
        candidate_name="quantum-computing",
        scenario_count=20,
        keywords=["量子线路", "超导比特"],
        toolchain=["qiskit"],
        existing_bundles_dir=tmp_path,
        runtime="qasm",
        action_verb_noun=["量子纠缠态测量"],
        dedicated_libs=["qiskit-aer"],
    )

    assert decision["decision"] == "SPAWN_NEW_BUNDLE"
    assert decision["affinity_score"] <= 25.0
