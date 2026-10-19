#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Probe live status of OpenViking Skills Center."""

import sqlite3
import os
import json
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
DB_PATH = Path("/home/skloxo/.openviking/data/viking/default/skill_ingestion_inbox.db")

print("=== 1. TOP-LEVEL BUNDLES PHYSICAL REALITY ===")
if SKILLS_ROOT.exists():
    bundles = sorted([d.name for d in SKILLS_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")])
    print(f"Total Top-level Bundles: {len(bundles)}")
    total_scenarios = 0
    for b in bundles:
        sc_dir = SKILLS_ROOT / b / "scenarios"
        sc_count = len(list(sc_dir.glob("*.md"))) if sc_dir.exists() else 0
        total_scenarios += sc_count
        print(f"  - {b:30s}: {sc_count} scenarios")
    print(f"Total Scenarios across all bundles: {total_scenarios}")
else:
    print("SKILLS_ROOT does not exist:", SKILLS_ROOT)

print("\n=== 2. INGESTION INBOX DB STATUS ===")
if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status, count(*) FROM skill_ingestion_inbox GROUP BY status;")
    rows = cursor.fetchall()
    print("Status Breakdown:")
    for status, count in rows:
        print(f"  {status:15s}: {count}")
    
    cursor.execute("SELECT count(*) FROM skill_ingestion_inbox;")
    total_records = cursor.fetchone()[0]
    print(f"Total Records in Inbox: {total_records}")

    cursor.execute("SELECT skill_name, status, datetime(updated_at, 'unixepoch', 'localtime') FROM skill_ingestion_inbox ORDER BY updated_at DESC LIMIT 15;")
    recent = cursor.fetchall()
    print("\nRecent 15 Ingested Records:")
    for r in recent:
        print(f"  {r[0]:35s} | {r[1]:12s} | {r[2]}")
    conn.close()
else:
    print("DB_PATH does not exist:", DB_PATH)

print("\n=== 3. ALIAS PROJECTION GATEWAY ===")
try:
    from openviking.service.skill_aliasing_router import SkillAliasingRouter
    router = SkillAliasingRouter(skills_root=SKILLS_ROOT)
    alias_map = router.get_alias_map(force_refresh=True)
    print(f"Total Virtual Projection Aliases: {len(alias_map)}")
    
    # Check sample critical skills
    samples = [
        "bigquery-sql", "gcp-spark", "managing-python-dependencies",
        "web-search-pro", "clash_verge_governance", "deepseek-harness-ops"
    ]
    print("Sample Skill Resolution:")
    for s in samples:
        res = router.resolve(s)
        if res:
            print(f"  {s:30s} -> {res.get('bundle_name')}/{res.get('scenario_name', '')} (is_virtual={res.get('is_virtual')})")
        else:
            print(f"  {s:30s} -> NOT FOUND")
except Exception as e:
    print("Error querying router:", e)

print("\n=== 4. LIVE SERVER API ENDPOINT CHECK ===")
try:
    import urllib.request
    key_paths = [
        Path.home() / ".openviking" / "data" / "root_key.txt",
        Path.home() / ".openviking" / "data" / "viking" / "default" / "root_key.txt",
    ]
    api_key = ""
    for kp in key_paths:
        if kp.exists():
            api_key = kp.read_text(encoding="utf-8").strip()
            if api_key:
                break
    
    req = urllib.request.Request("http://127.0.0.1:1933/api/v1/skills/summary")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
        print("API /api/v1/skills/summary output:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:800] + "...")
except Exception as e:
    print("API Query failed:", e)

