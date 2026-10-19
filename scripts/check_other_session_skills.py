#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Check for 60+ skills submitted by other session."""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("/home/skloxo/.openviking/data/viking/default/skill_ingestion_inbox.db")
SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
GLOBAL_CONFIG_SKILLS = Path("/mnt/c/Users/Skl/.gemini/config/skills")
ANTIGRAVITY_IDE_SKILLS = Path("/mnt/c/Users/Skl/.gemini/antigravity-ide/builtin/skills")
ANTIGRAVITY_PLUGINS = Path("/mnt/c/Users/Skl/.gemini/config/plugins")

print("=== 1. CHECK INBOX DB (ALL STATUSES) ===")
if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM skill_ingestion_inbox;")
    print(f"Total inbox records: {c.fetchone()[0]}")
    
    # Check all distinct statuses
    c.execute("SELECT status, count(*) FROM skill_ingestion_inbox GROUP BY status;")
    print("Status counts:", c.fetchall())
    
    # Check distinct authors
    c.execute("SELECT DISTINCT author FROM skill_ingestion_inbox;")
    authors = [r[0] for r in c.fetchall()]
    print("Distinct authors:", authors)
    
    # Check all records in DB
    c.execute("SELECT skill_name, status, author, datetime(created_at, 'unixepoch', 'localtime'), datetime(updated_at, 'unixepoch', 'localtime') FROM skill_ingestion_inbox ORDER BY updated_at DESC;")
    all_recs = c.fetchall()
    print(f"\nAll Records in DB ({len(all_recs)}):")
    for r in all_recs:
        print(f"  {r[0]:35s} | {r[1]:10s} | {r[2]:15s} | {r[3]} -> {r[4]}")
    conn.close()
else:
    print("DB_PATH does not exist:", DB_PATH)

print("\n=== 2. CHECK LOCAL ANTIGRAVITY / GEMINI SKILLS DIRECTORIES ===")
for p, desc in [
    (GLOBAL_CONFIG_SKILLS, "Windows Global Config Skills"),
    (ANTIGRAVITY_IDE_SKILLS, "Windows Builtin Skills"),
    (ANTIGRAVITY_PLUGINS, "Windows Plugins"),
]:
    if p.exists():
        dirs = [d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")]
        print(f"[{desc}] Path: {p} (Total: {len(dirs)})")
        for d in sorted(dirs)[:10]:
            print(f"  - {d}")
        if len(dirs) > 10:
            print(f"  ... and {len(dirs) - 10} more")
    else:
        print(f"[{desc}] Path does not exist: {p}")

print("\n=== 3. CHECK ANY NEW SKILLS DIRECTORIES IN /home/skloxo ===")
try:
    import subprocess
    cmd = "find /home/skloxo -maxdepth 5 -type d -name 'skills*' 2>/dev/null"
    out = subprocess.check_output(cmd, shell=True, text=True)
    print("Found skills directories:\n" + out.strip())
except Exception as e:
    print("Error scanning directories:", e)
