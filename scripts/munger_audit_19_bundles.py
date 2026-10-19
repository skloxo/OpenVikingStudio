#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Munger Inversion Audit on the 19 Capability Bundles."""

import os
import json
import yaml
from pathlib import Path
from collections import Counter

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

def audit():
    bundles = sorted([d for d in SKILLS_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")])
    print(f"=== Munger Audit: 19 Bundles Deep Inversion ===\nTotal Bundles: {len(bundles)}")
    
    bundle_stats = []
    all_scenario_names = Counter()
    
    for b in bundles:
        name = b.name
        skill_md = b / "SKILL.md"
        modules_dir = b / "modules"
        scenarios_dir = b / "scenarios"
        
        has_skill_md = skill_md.exists()
        skill_md_size = skill_md.stat().st_size if has_skill_md else 0
        
        mod_count = len(list(modules_dir.glob("*.md"))) if modules_dir.exists() else 0
        sc_files = list(scenarios_dir.glob("*.md")) if scenarios_dir.exists() else []
        sc_count = len(sc_files)
        
        for sc in sc_files:
            all_scenario_names[sc.name] += 1
            
        bundle_stats.append({
            "name": name,
            "has_skill_md": has_skill_md,
            "skill_md_size": skill_md_size,
            "mod_count": mod_count,
            "sc_count": sc_count,
            "sc_files": [f.name for f in sc_files]
        })
    
    # 1. Size distribution & Bloat
    print("\n--- 1. BUNDLE SIZE & COMPLEXITY ---")
    for s in sorted(bundle_stats, key=lambda x: x["sc_count"], reverse=True):
        print(f"[{s['name']:30s}] Scenarios: {s['sc_count']:4d} | Modules: {s['mod_count']:2d} | SKILL.md: {s['skill_md_size']:5d} bytes")
        
    # 2. Check duplicate scenario files across bundles
    print("\n--- 2. CROSS-BUNDLE DUPLICATE SCENARIOS ---")
    duplicates = {name: cnt for name, cnt in all_scenario_names.items() if cnt > 1}
    if duplicates:
        print(f"Found {len(duplicates)} duplicated scenarios across multiple bundles!")
        for sc_name, cnt in list(duplicates.items())[:20]:
            containing_bundles = [b["name"] for b in bundle_stats if sc_name in b["sc_files"]]
            print(f"  - {sc_name} (in {cnt} bundles: {containing_bundles})")
    else:
        print("Zero cross-bundle duplicate scenarios detected.")
        
    # 3. Deep Dive into developer-productivity
    print("\n--- 3. PEEK INSIDE developer-productivity (262 scenarios) ---")
    dev_prod = next((b for b in bundle_stats if b["name"] == "developer-productivity"), None)
    if dev_prod:
        # Show sample 30 scenarios
        print(f"Total scenarios: {len(dev_prod['sc_files'])}")
        print("Sample 30 scenarios:")
        for sc in sorted(dev_prod['sc_files'])[:30]:
            print(f"  * {sc}")
            
    # 4. Deep Dive into api-test-skill and park-grid-governance
    print("\n--- 4. PEEK INSIDE SUSPICIOUS SMALL BUNDLES ---")
    for small_name in ["api-test-skill", "park-grid-governance", "security-audit-compliance"]:
        b_info = next((b for b in bundle_stats if b["name"] == small_name), None)
        if b_info:
            print(f"[{small_name}] Scenarios: {b_info['sc_files']}")

if __name__ == "__main__":
    audit()
