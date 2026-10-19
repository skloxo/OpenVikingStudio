#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Scan recent changes and all Antigravity IDE skills."""

import os
import time
from pathlib import Path

print("=== 1. SCANNING RECENT MODIFIED FILES (PAST 60 MINS) ===")
now = time.time()
recent_threshold = now - 3600

scan_roots = [
    Path("/mnt/c/Users/Skl/.gemini"),
    Path("/mnt/c/Users/Skl/Desktop/Work/.agents"),
    Path("/mnt/c/Users/Skl/Desktop/One/.agents"),
    Path("/mnt/c/Users/Skl/Desktop/coding"),
    Path("/home/skloxo/.openviking"),
]

for r in scan_roots:
    if not r.exists():
        continue
    recent_files = []
    try:
        for p in r.rglob("*"):
            if p.is_file() and not any(part.startswith(".") for part in p.parts if part not in [".gemini", ".agents"]):
                try:
                    if p.stat().st_mtime > recent_threshold:
                        recent_files.append((p, p.stat().st_mtime))
                except Exception:
                    pass
    except Exception as e:
        print(f"Error scanning {r}: {e}")
        
    if recent_files:
        print(f"[{r}] {len(recent_files)} files modified in past hour:")
        for rf, mt in sorted(recent_files, key=lambda x: x[1], reverse=True)[:15]:
            print(f"  - {rf} ({time.strftime('%H:%M:%S', time.localtime(mt))})")

print("\n=== 2. TOTAL SKILLS IN ANTIGRAVITY IDE ECOSYSTEM ===")
total_skills = []
# A: .gemini/config/skills
p_skills = Path("/mnt/c/Users/Skl/.gemini/config/skills")
if p_skills.exists():
    for d in p_skills.iterdir():
        if d.is_dir() and (d / "SKILL.md").exists():
            total_skills.append(("config/skills", d.name))

# B: .gemini/config/plugins/*/skills/*
p_plugins = Path("/mnt/c/Users/Skl/.gemini/config/plugins")
if p_plugins.exists():
    for plug in p_plugins.iterdir():
        sk_dir = plug / "skills"
        if sk_dir.exists():
            for d in sk_dir.iterdir():
                if d.is_dir() and (d / "SKILL.md").exists():
                    total_skills.append((f"plugins/{plug.name}", d.name))

# C: Workspaces .agents/skills
for ws in ["Work", "One", "coding/OpenVikingStudio"]:
    ws_sk = Path(f"/mnt/c/Users/Skl/Desktop/{ws}/.agents/skills")
    if ws_sk.exists():
        for d in ws_sk.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                total_skills.append((f"ws:{ws}", d.name))

# D: Builtin skills
p_builtin = Path("/mnt/c/Users/Skl/.gemini/antigravity-ide/builtin/skills")
if p_builtin.exists():
    for d in p_builtin.iterdir():
        if d.is_dir() and (d / "SKILL.md").exists():
            total_skills.append(("builtin", d.name))

print(f"Total Antigravity IDE Skills found: {len(total_skills)}")
from collections import defaultdict
by_loc = defaultdict(list)
for loc, name in total_skills:
    by_loc[loc].append(name)

for loc, names in by_loc.items():
    print(f"  [{loc}] ({len(names)}): {', '.join(names[:6])}{' ...' if len(names) > 6 else ''}")
