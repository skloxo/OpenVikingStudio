#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Step 3 & Step 4: Populate park-grid-governance, property-cadre-ops, and document-governance."""

import os
import re
import yaml
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
WORK_SKILLS = Path("/mnt/c/Users/Skl/Desktop/Work/.agents/skills")

def sanitize_and_normalize(content: str, target_domain: str) -> str:
    """Normalize frontmatter and strip naked Windows paths."""
    # Replace Windows paths with generic/relative or viking URI
    content = content.replace("c:\\Users\\Skl\\Desktop\\Work\\", "viking://work/")
    content = content.replace("C:\\Users\\Skl\\Desktop\\Work\\", "viking://work/")
    content = content.replace("file:///c:/Users/Skl/Desktop/Work/", "viking://work/")
    
    parts = re.split(r"^---\s*$", content, flags=re.MULTILINE)
    if len(parts) >= 3:
        fm_raw = parts[1]
        body = "---".join(parts[2:])
        try:
            fm = yaml.safe_load(fm_raw) or {}
        except Exception:
            fm = {}
    else:
        fm = {}
        body = content
        
    fm["domain"] = target_domain
    if "triggers" not in fm or not fm["triggers"]:
        fm["triggers"] = [target_domain, fm.get("name", target_domain)]
        
    new_fm_str = yaml.dump(fm, allow_unicode=True, sort_keys=False)
    return f"---\n{new_fm_str}---\n{body.strip()}\n"

def execute():
    print("=== Step 3: Populate park-grid-governance ===")
    p_grid = SKILLS_ROOT / "park-grid-governance"
    p_scenarios = p_grid / "scenarios"
    p_modules = p_grid / "modules"
    p_scenarios.mkdir(parents=True, exist_ok=True)
    p_modules.mkdir(parents=True, exist_ok=True)
    
    # 移出遗留的 antigravity-host-ops.md 错配文件
    leftover = p_scenarios / "antigravity-host-ops.md"
    if leftover.exists():
        leftover.unlink()
        print("  [CLEANED] Removed misplaced antigravity-host-ops.md from park-grid-governance")
        
    # 从 Work 萃取真正的网格化技能
    grid_source_files = {
        "grid_management": "grid-management.md",
        "ai_monitor_ops": "ai-monitor-ops.md",
        "komari_ops": "komari-ops.md",
    }
    
    for src_dir, target_fname in grid_source_files.items():
        sk_md = WORK_SKILLS / src_dir / "SKILL.md"
        if sk_md.exists():
            clean_text = sanitize_and_normalize(sk_md.read_text(encoding="utf-8"), "park-grid-governance")
            (p_scenarios / target_fname).write_text(clean_text, encoding="utf-8")
            print(f"  [POPULATED] {src_dir} -> park-grid-governance/scenarios/{target_fname}")

    # 重构 park-grid-governance 的 Master SKILL.md
    p_master = """---
name: park-grid-governance
version: 1.0.0
domain: park-grid-governance
description: 直管园区网格化管理平台全景知识库与开发规范，涵盖网格划分、AI安防监控割接与边缘网关探针。
triggers:
  - 网格化管理平台
  - 迭代网格化管理平台
  - 美丽园区网格化
  - AI监控割接
  - 海康NVR运维
---

# 🌳 Park Grid Governance Capability Bundle

直管园区网格化规划与安防基础设施核心业务母包。

## 核心工序清单 (Scenarios)
- [`grid-management`](scenarios/grid-management.md): 美丽园区网格化管理平台专案全景知识库与开发规范
- [`ai-monitor-ops`](scenarios/ai-monitor-ops.md): AI 监控与基础设施技术运维全景知识库（央厨/华庭安防与割接）
- [`komari-ops`](scenarios/komari-ops.md): Komari 统一监控驾驶舱与边缘网关接入
"""
    (p_grid / "SKILL.md").write_text(p_master, encoding="utf-8")
    
    print("\n=== Step 4: Populate property-cadre-ops & document-governance ===")
    # A: property-cadre-ops
    prop_grid = SKILLS_ROOT / "property-cadre-ops" / "scenarios"
    prop_grid.mkdir(parents=True, exist_ok=True)
    prop_sources = {
        "cadre_apartment": "cadre-apartment.md",
        "smart_lock": "smart-lock.md",
    }
    for src_dir, target_fname in prop_sources.items():
        sk_md = WORK_SKILLS / src_dir / "SKILL.md"
        if sk_md.exists():
            clean_text = sanitize_and_normalize(sk_md.read_text(encoding="utf-8"), "property-cadre-ops")
            (prop_grid / target_fname).write_text(clean_text, encoding="utf-8")
            print(f"  [POPULATED] {src_dir} -> property-cadre-ops/scenarios/{target_fname}")

    # B: document-governance
    doc_grid = SKILLS_ROOT / "document-governance" / "scenarios"
    doc_grid.mkdir(parents=True, exist_ok=True)
    doc_sources = {
        "doc_naming_norm": "doc-naming-norm.md",
        "weekly_report": "weekly-report.md",
        "monthly_report": "monthly-report.md",
        "pdca": "pdca.md",
        "reporting": "reporting.md",
        "daily_report": "daily-report.md",
    }
    for src_dir, target_fname in doc_sources.items():
        sk_md = WORK_SKILLS / src_dir / "SKILL.md"
        if sk_md.exists():
            clean_text = sanitize_and_normalize(sk_md.read_text(encoding="utf-8"), "document-governance")
            (doc_grid / target_fname).write_text(clean_text, encoding="utf-8")
            print(f"  [POPULATED] {src_dir} -> document-governance/scenarios/{target_fname}")

    print("\n✅ Step 3 & Step 4 completed successfully.")

if __name__ == "__main__":
    execute()
