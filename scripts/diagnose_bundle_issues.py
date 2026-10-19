#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Detailed diagnosis of cross-bundle duplicates and displaced scenarios."""

from pathlib import Path
from collections import Counter

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

def diagnose():
    bundles = [d for d in SKILLS_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    file_to_bundles = {}
    for b in bundles:
        sc_dir = b / "scenarios"
        if not sc_dir.exists():
            continue
        for f in sc_dir.glob("*.md"):
            file_to_bundles.setdefault(f.name, []).append(b.name)
            
    print("=== 24 DUPLICATED SCENARIOS DETAIL ===")
    for fname, blist in file_to_bundles.items():
        if len(blist) > 1:
            print(f"{fname:35s}: {blist}")
            
    print("\n=== PARK GRID GOVERNANCE SCENARIOS ===")
    p_sc = SKILLS_ROOT / "park-grid-governance" / "scenarios"
    if p_sc.exists():
        for f in p_sc.glob("*.md"):
            print(" ", f.name, f.stat().st_size, "bytes")
            
    print("\n=== API TEST SKILL SCENARIOS ===")
    a_sc = SKILLS_ROOT / "api-test-skill" / "scenarios"
    if a_sc.exists():
        for f in a_sc.glob("*.md"):
            print(" ", f.name, f.stat().st_size, "bytes")

if __name__ == "__main__":
    diagnose()
