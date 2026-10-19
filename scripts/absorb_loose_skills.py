#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Utility script to consolidate loose spawned skills into the 20 Canonical Capability Bundles
as granular scenarios under `scenarios/`, enforcing Rule 12 macro-convergence.
"""

import json
from pathlib import Path
import shutil
import sys

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

SKILL_TO_BUNDLE_MAP = {
    "accidental-data-loss-prevention": "security-audit-compliance",
    "antigravity-plugin-crafting": "antigravity-host-ops",
    "bigquery-data-transfer-service": "cloud-infra-ops",
    "building-data-apps": "codebase-engineering",
    "circuit-breaker-ops": "ai-harness-ops",
    "data-autocleaning": "codebase-engineering",
    "dataform-bigquery": "codebase-engineering",
    "dbt-bigquery": "codebase-engineering",
    "discovering-gcp-data-assets": "cloud-infra-ops",
    "gcp-dataflow": "cloud-infra-ops",
    "gcp-spark": "cloud-infra-ops",
    "google-cloud-auth-verification": "cloud-infra-ops",
    "ml-best-practices": "codebase-engineering",
    "notebook-guidance": "developer-productivity",
    "schema-mapping": "codebase-engineering",
    "skill-repair": "codebase-engineering",
}


def consolidate():
    if not SKILLS_ROOT.exists():
        print(f"Skills root {SKILLS_ROOT} does not exist. Nothing to do.")
        return 0

    absorbed_count = 0
    for skill_name, bundle_name in SKILL_TO_BUNDLE_MAP.items():
        skill_dir = SKILLS_ROOT / skill_name
        bundle_dir = SKILLS_ROOT / bundle_name

        if not skill_dir.exists():
            continue

        if not bundle_dir.exists():
            print(f"Target bundle {bundle_name} not found! Skipping {skill_name}")
            continue

        scenarios_dir = bundle_dir / "scenarios"
        scenarios_dir.mkdir(parents=True, exist_ok=True)
        target_scenario_file = scenarios_dir / f"{skill_name}.md"

        # Locate best content
        candidate_sc = skill_dir / "scenarios" / f"{skill_name}.md"
        candidate_skill = skill_dir / "SKILL.md"

        content = ""
        if candidate_sc.exists():
            content = candidate_sc.read_text(encoding="utf-8")
        elif candidate_skill.exists():
            content = candidate_skill.read_text(encoding="utf-8")

        if content:
            target_scenario_file.write_text(content, encoding="utf-8")
            print(f"✅ Absorbed {skill_name} -> {bundle_name}/scenarios/{skill_name}.md")

        # Update absorption provenance
        prov_file = bundle_dir / "ABSORPTION_PROVENANCE.json"
        if prov_file.exists():
            try:
                data = json.loads(prov_file.read_text(encoding="utf-8"))
                absorbed = data.get("absorbed_skills", [])
                if skill_name not in absorbed:
                    absorbed.append(skill_name)
                    data["absorbed_skills"] = absorbed
                    prov_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                print(f"Warning: could not update provenance for {bundle_name}: {e}")

        # Remove the loose directory
        shutil.rmtree(skill_dir)
        absorbed_count += 1

    # Also clean any mock-* test directories if lingering
    for item in SKILLS_ROOT.glob("mock-*"):
        if item.is_dir():
            shutil.rmtree(item)
            print(f"🧹 Cleaned mock directory: {item.name}")

    print(f"\n🎉 Successfully consolidated {absorbed_count} loose skill(s) into Canonical Bundles.")
    return 0


if __name__ == "__main__":
    sys.exit(consolidate())
