#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Deep Munger scan on current 18 bundles."""

import re
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

def scan():
    print("=== Munger Inversion Scan on 18 Current Bundles ===")
    bundles = sorted([d for d in SKILLS_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")])
    print(f"Total Bundles: {len(bundles)}")
    
    total_broken_links = 0
    bloat_bundles = []
    
    for b in bundles:
        name = b.name
        sc_dir = b / "scenarios"
        mod_dir = b / "modules"
        skill_md = b / "SKILL.md"
        
        sc_count = len(list(sc_dir.glob("*.md"))) if sc_dir.exists() else 0
        if sc_count >= 100:
            bloat_bundles.append((name, sc_count))
            
        # Check broken links in SKILL.md and modules/*.md
        checked_texts = []
        if skill_md.exists():
            checked_texts.append(("SKILL.md", skill_md.read_text(encoding="utf-8"), b))
        if mod_dir.exists():
            for mf in mod_dir.glob("*.md"):
                checked_texts.append((mf.name, mf.read_text(encoding="utf-8"), mod_dir))
                
        b_broken = 0
        for src_name, txt, base_p in checked_texts:
            # find markdown links [text](path)
            links = re.findall(r"\[.*?\]\((.*?)\)", txt)
            for link in links:
                if link.startswith("http") or link.startswith("#") or link.startswith("viking://"):
                    continue
                # resolve relative path
                target = (base_p / link).resolve()
                if not target.exists():
                    print(f"  [BROKEN LINK] in {b.name}/{src_name} -> {link}")
                    b_broken += 1
                    total_broken_links += 1
                    
    print(f"\n1. Broken Links Count: {total_broken_links}")
    print("\n2. Bloat Warning Bundles (>=100 scenarios):")
    for name, cnt in bloat_bundles:
        print(f"  - {name}: {cnt} scenarios (Potential Cognitive Overload)")
        
    print("\n3. Naming Convention Audit:")
    for b in bundles:
        if "_" in b.name:
            print(f"  [NAMING INCONSISTENT] {b.name} contains underscore '_' (expected kebab-case '-')")

if __name__ == "__main__":
    scan()
