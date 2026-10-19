#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Audit GCP skills ingestion quality: Original vs Crystallized."""

import os
import re
from pathlib import Path

ARCHIVE_DIR = Path("/mnt/c/Users/Skl/.gemini/config/skills_archive")
SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

def extract_code_blocks(text: str) -> list[str]:
    return re.findall(r"```[\s\S]*?```", text)

def audit():
    print("=== GCP Skills Ingestion Quality Audit (Original vs Ingested) ===")
    if not ARCHIVE_DIR.exists():
        print("Archive dir not found:", ARCHIVE_DIR)
        return
        
    gcp_skills = [d.name for d in ARCHIVE_DIR.iterdir() if d.is_dir()]
    print(f"Total archived GCP skills: {len(gcp_skills)}")
    
    reports = []
    
    for s_name in sorted(gcp_skills):
        orig_file = ARCHIVE_DIR / s_name / "SKILL.md"
        if not orig_file.exists():
            continue
            
        orig_text = orig_file.read_text(encoding="utf-8")
        orig_lines = len(orig_text.splitlines())
        orig_bytes = len(orig_text.encode("utf-8"))
        orig_code_blocks = len(extract_code_blocks(orig_text))
        
        # Locate ingested file across all bundles
        ingested_file = None
        found_bundle = None
        for b in SKILLS_ROOT.iterdir():
            if b.is_dir() and not b.name.startswith("."):
                sc_f = b / "scenarios" / f"{s_name}.md"
                if sc_f.exists():
                    ingested_file = sc_f
                    found_bundle = b.name
                    break
                    
        if not ingested_file:
            reports.append({
                "skill": s_name,
                "status": "MISSING_IN_STUDIO",
                "orig_lines": orig_lines,
                "ing_lines": 0,
                "orig_blocks": orig_code_blocks,
                "ing_blocks": 0,
                "bundle": "NONE",
                "loss": "100% LOST"
            })
            continue
            
        ing_text = ingested_file.read_text(encoding="utf-8")
        ing_lines = len(ing_text.splitlines())
        ing_bytes = len(ing_text.encode("utf-8"))
        ing_code_blocks = len(extract_code_blocks(ing_text))
        
        code_loss = orig_code_blocks - ing_code_blocks
        line_ratio = ing_lines / max(1, orig_lines)
        
        status = "HEALTHY"
        loss_desc = "None"
        if code_loss > 0:
            status = "CODE_TRUNCATED"
            loss_desc = f"Lost {code_loss} code blocks!"
        elif line_ratio < 0.6:
            status = "HEAVILY_COMPRESSED"
            loss_desc = f"Compressed to {line_ratio:.1%}"
            
        reports.append({
            "skill": s_name,
            "status": status,
            "orig_lines": orig_lines,
            "ing_lines": ing_lines,
            "orig_blocks": orig_code_blocks,
            "ing_blocks": ing_code_blocks,
            "bundle": found_bundle,
            "loss": loss_desc
        })
        
    print(f"\n{'Skill Name':35s} | {'Bundle':22s} | {'Lines (Orig->Ing)':18s} | {'CodeBlocks':12s} | {'Status':16s} | {'Notes'}")
    print("-" * 125)
    for r in reports:
        lines_str = f"{r['orig_lines']} -> {r['ing_lines']}"
        blocks_str = f"{r['orig_blocks']} -> {r['ing_blocks']}"
        print(f"{r['skill']:35s} | {r['bundle']:22s} | {lines_str:18s} | {blocks_str:12s} | {r['status']:16s} | {r['loss']}")

if __name__ == "__main__":
    audit()
