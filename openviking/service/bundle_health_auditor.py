# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""OpenViking Capability Bundle Health & Compliance Auditor.

Enforces:
1. Five Iron Invariants:
   - Master SKILL.md <= 100 lines
   - Modules <= 6 files, each <= 200 lines
   - Zero broken scenario links
   - Zero generic stop words in triggers
   - Zero cross-bundle trigger collisions
2. Grill-Me Ratified Ante-Gate Rules (Q1~Q4):
   - Capacity Ceiling: Scenarios <= 100 per bundle (otherwise CELL_DIVISION_REQUIRED)
   - Provenance Verification (ABSORPTION_PROVENANCE.json)
"""

import json
import yaml
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

from openviking.service.auto_crystallizer_b5 import (
    SeamDecisionGateB5,
    GENERIC_STOP_WORDS,
)

DEFAULT_SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")


class BundleHealthAuditor:
    """Audits one or more capability bundles for full compliance."""

    @classmethod
    def audit_single(cls, bundle_dir: Path) -> Dict[str, Any]:
        name = bundle_dir.name
        res = {
            "bundle": name,
            "exists": bundle_dir.exists(),
            "master_lines": 0,
            "master_ok": False,
            "modules_count": 0,
            "modules_ok": False,
            "max_module_lines": 0,
            "max_module_lines_ok": False,
            "scenarios_count": 0,
            "capacity_ok": False,
            "broken_links": 0,
            "total_links": 0,
            "has_provenance": False,
            "triggers_count": 0,
            "triggers_with_stopwords": [],
            "issues": [],
        }

        if not bundle_dir.exists():
            res["issues"].append("Bundle directory does not exist")
            return res

        # 1. Master SKILL.md
        skill_file = bundle_dir / "SKILL.md"
        if not skill_file.exists():
            res["issues"].append("Missing SKILL.md")
        else:
            content = skill_file.read_text(encoding="utf-8")
            lines = len(content.splitlines())
            res["master_lines"] = lines
            res["master_ok"] = lines <= 100
            if lines > 100:
                res["issues"].append(f"Master SKILL.md has {lines} lines (>100 lines limit)")

            try:
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    triggers = [str(t) for t in fm.get("triggers", [])]
                    res["triggers_count"] = len(triggers)
                    bad_trigs = [t for t in triggers if t.lower() in GENERIC_STOP_WORDS]
                    res["triggers_with_stopwords"] = bad_trigs
                    if bad_trigs:
                        res["issues"].append(f"Contains generic stopword triggers: {bad_trigs}")
            except Exception as e:
                res["issues"].append(f"Failed to parse triggers in SKILL.md: {e}")

        # 2. Modules
        modules_dir = bundle_dir / "modules"
        if not modules_dir.exists():
            res["issues"].append("Missing modules/ directory")
        else:
            mod_files = list(modules_dir.glob("*.md"))
            res["modules_count"] = len(mod_files)
            res["modules_ok"] = len(mod_files) <= SeamDecisionGateB5.MAX_MODULES_PER_BUNDLE
            if len(mod_files) > SeamDecisionGateB5.MAX_MODULES_PER_BUNDLE:
                res["issues"].append(
                    f"Modules count {len(mod_files)} > {SeamDecisionGateB5.MAX_MODULES_PER_BUNDLE} (violates Q1)"
                )

            max_lines = 0
            broken = 0
            total_links = 0
            for mf in mod_files:
                m_txt = mf.read_text(encoding="utf-8")
                m_lines = len(m_txt.splitlines())
                if m_lines > max_lines:
                    max_lines = m_lines
                if m_lines > 200:
                    res["issues"].append(f"Module {mf.name} has {m_lines} lines (>200 lines limit)")

                links = re.findall(r"\[.*?\]\(((\.\./scenarios/.*?\.md))\)", m_txt)
                for _, link in links:
                    total_links += 1
                    target = (modules_dir / link).resolve()
                    if not target.exists():
                        broken += 1

            res["max_module_lines"] = max_lines
            res["max_module_lines_ok"] = max_lines <= 200
            res["broken_links"] = broken
            res["total_links"] = total_links
            if broken > 0:
                res["issues"].append(f"Found {broken} broken scenario links")
            if total_links < 10 and res["scenarios_count"] >= 10:
                res["issues"].append(f"Total clickable links {total_links} < 10 (detail loss risk)")

        # 3. Scenarios (Q1 capacity ceiling)
        scenarios_dir = bundle_dir / "scenarios"
        if scenarios_dir.exists():
            scenarios = list(scenarios_dir.glob("*.md"))
            res["scenarios_count"] = len(scenarios)
            res["capacity_ok"] = len(scenarios) <= SeamDecisionGateB5.MAX_SCENARIOS_PER_BUNDLE
            if len(scenarios) > SeamDecisionGateB5.MAX_SCENARIOS_PER_BUNDLE:
                res["issues"].append(
                    f"Scenario count {len(scenarios)} > {SeamDecisionGateB5.MAX_SCENARIOS_PER_BUNDLE} (violates Q1, requires Cell Division)"
                )
        else:
            res["scenarios_count"] = 0
            res["capacity_ok"] = True

        # 4. Provenance
        prov_file = bundle_dir / "ABSORPTION_PROVENANCE.json"
        res["has_provenance"] = prov_file.exists()
        if not prov_file.exists():
            res["issues"].append("Missing ABSORPTION_PROVENANCE.json")

        return res

    @classmethod
    def audit_all(cls, skills_dir: Path = DEFAULT_SKILLS_DIR, bundle_names: List[str] = None) -> Dict[str, Any]:
        if bundle_names is None:
            bundle_names = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]

        results = []
        all_triggers = {}
        collisions = []

        for b_name in sorted(bundle_names):
            b_dir = skills_dir / b_name
            r = cls.audit_single(b_dir)
            results.append(r)

            # Check collisions
            skill_file = b_dir / "SKILL.md"
            if skill_file.exists():
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1])
                        trigs = {str(t).lower() for t in fm.get("triggers", []) if str(t).lower() not in GENERIC_STOP_WORDS}
                        for t in trigs:
                            if t in all_triggers:
                                collisions.append({"trigger": t, "bundle_a": all_triggers[t], "bundle_b": b_name})
                            else:
                                all_triggers[t] = b_name
                except Exception:
                    pass

        total_issues = sum(len(r["issues"]) for r in results)
        return {
            "total_bundles": len(results),
            "total_issues": total_issues,
            "collisions_count": len(collisions),
            "collisions": collisions,
            "bundle_results": results,
            "overall_status": "APPROVED" if (total_issues == 0 and len(collisions) == 0) else "NEEDS_ATTENTION",
        }


SYSTEM_META_SKILLS = {
    "agent-friendly-code-org",
    "agent-governance-guardrails",
    "antigravity-host-ops",
    "auto-pr",
    "capability-bundle-crystallizer",
    "clash_verge_governance",
    "cpa_squad",
    "cpa-squad",
    "dev-runtime-decoupling",
    "global-agent-core",
    "keepass-vault",
    "living-asset-system",
    "master-dev",
    "openviking",
    "openviking-model-evaluator",
    "skill-state-fsm",
    "xui_management",
}


def main():
    report = BundleHealthAuditor.audit_all()
    business_bundles = [r for r in report["bundle_results"] if r["bundle"] not in SYSTEM_META_SKILLS and r["bundle"] != "wechat-harvest"]
    meta_tools = [r for r in report["bundle_results"] if r["bundle"] in SYSTEM_META_SKILLS]
    legacy_skills = [r for r in report["bundle_results"] if r["bundle"] == "wechat-harvest"]

    pass_bundles = [r for r in business_bundles if len(r["issues"]) == 0]
    todo_bundles = [r for r in business_bundles if len(r["issues"]) > 0]

    print("=" * 78)
    print(f"📊 OpenViking Capability Bundle Health Audit (Decoupled SSOT)")
    print(f"Business Bundles: {len(pass_bundles)} Passed / {len(business_bundles)} Total | Meta Tools: {len(meta_tools)} | Collisions: {report['collisions_count']}")
    print("=" * 78)

    print("\n🏛️ [1. 业务能力大包战区 (Capability Bundles)]")
    for r in business_bundles:
        status = "✅ PASS" if len(r["issues"]) == 0 else f"⏳ PENDING ({len(r['issues'])} issues)"
        print(f"[{status}] {r['bundle']:<28} Master: {r['master_lines']:>2}L | Mods: {r['modules_count']} | Scenarios: {r['scenarios_count']:>3}")
        for iss in r["issues"]:
            print(f"   - {iss}")

    print("\n🛡️ [2. 宿主与集群系统基座元技能 (Host Infrastructure & Guardrails)]")
    for r in meta_tools:
        print(f"[META] {r['bundle']:<28} Master: {r['master_lines']:>3}L | (系统常驻规则/基础设施/治理律法)")

    if legacy_skills:
        print("\n🗑️ [3. 历史单技能冗余遗留 (待消杀归档)]")
        for r in legacy_skills:
            print(f"[LEGC] {r['bundle']:<28} Master: {r['master_lines']:>3}L | (已归拢入 web-harvest-pro，待清理)")

    if report["collisions"]:
        print("\n💥 Trigger Collisions:")
        for c in report["collisions"]:
            print(f"   - '{c['trigger']}' in [{c['bundle_a']}] vs [{c['bundle_b']}]")


if __name__ == "__main__":
    main()
