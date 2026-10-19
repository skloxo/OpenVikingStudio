#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Fix broken scenario links in all Master SKILL.md files."""

import re
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

def fix_broken_links():
    bundles = [d for d in SKILLS_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")]
    fixed_count = 0
    
    for b in bundles:
        skill_md = b / "SKILL.md"
        if not skill_md.exists():
            continue
            
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        new_lines = []
        modified = False
        
        for line in lines:
            links = re.findall(r"\[.*?\]\((scenarios/.*?\.md)\)", line)
            is_broken = False
            for rel in links:
                target = b / rel
                if not target.exists():
                    is_broken = True
                    print(f"  [FIXED] Removed broken link in {b.name}/SKILL.md: {rel}")
                    fixed_count += 1
                    modified = True
                    break
            if not is_broken:
                new_lines.append(line)
                
        if modified:
            skill_md.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            
    print(f"Total broken link lines pruned: {fixed_count}")

if __name__ == "__main__":
    fix_broken_links()
