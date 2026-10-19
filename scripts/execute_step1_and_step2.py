#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Step 1 & Step 2: Clean 24 cross-bundle duplicate scenarios and archive api-test-skill."""

import os
import shutil
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
ARCHIVE_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills_archive_transition")
ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)

# 24 重复场景的法定唯一正统归宿 (Canonical SSOT Ownership)
CANONICAL_MAPPING = {
    "cluster-network-ops.md": "network-tunnel-ops",
    "web-search-pro.md": "web-harvest-pro",
    "cellular-cpe-ops.md": "network-tunnel-ops",
    "mac-studio-remote-ops.md": "network-tunnel-ops",
    "network-search-ops.md": "network-tunnel-ops",
    "openviking-plugin-ops.md": "openviking",
    "n8n-ops.md": "cloud-infra-ops",
    "dify-ops.md": "cloud-infra-ops",
    "homepage-ops.md": "cockpit-ui",
    "living-asset-system.md": "codebase-engineering",
    "komari-ops.md": "cloud-infra-ops",
    "skill-state-fsm.md": "codebase-engineering",
    "auto-pr.md": "codebase-engineering",
    "master-dev.md": "openviking",
    "openviking-memory-benchmark.md": "openviking",
    "tide-trading-dev.md": "quant-trading",
    "openviking-studio-dev.md": "openviking",
    "openviking-model-evaluator.md": "openviking",
    "deepseek-harness-ops.md": "ai-harness-ops",
    "session-handover.md": "openviking",
    "global-agent-core.md": "codebase-engineering",
    "openviking-memory-plugin-architecture.md": "openviking",
    "openviking-ops.md": "openviking",
    "satellite-fleet-ops.md": "cloud-infra-ops",
}

def clean_duplicates():
    print("=== Step 1: Cleaning 24 Cross-Bundle Duplicates ===")
    removed_count = 0
    
    # 扫描所有包
    for b_dir in SKILLS_ROOT.iterdir():
        if not b_dir.is_dir() or b_dir.name.startswith("."):
            continue
            
        sc_dir = b_dir / "scenarios"
        if not sc_dir.exists():
            continue
            
        for sc_file in list(sc_dir.glob("*.md")):
            fname = sc_file.name
            if fname in CANONICAL_MAPPING:
                legal_bundle = CANONICAL_MAPPING[fname]
                if b_dir.name != legal_bundle:
                    # 发现多余的非法副本！
                    # 检查当前包 modules/*.md 中是否有引用它，若有则进行安全清理
                    mod_dir = b_dir / "modules"
                    if mod_dir.exists():
                        for mf in mod_dir.glob("*.md"):
                            try:
                                txt = mf.read_text(encoding="utf-8")
                                # 替换或者清理死链
                                if f"../scenarios/{fname}" in txt:
                                    lines = [l for l in txt.splitlines() if f"../scenarios/{fname}" not in l]
                                    mf.write_text("\n".join(lines) + "\n", encoding="utf-8")
                            except Exception:
                                pass
                                
                    # 物理删除非法副本
                    sc_file.unlink()
                    print(f"  [REMOVED DUPLICATE] {fname} removed from {b_dir.name} (Canonical: {legal_bundle})")
                    removed_count += 1
                    
    print(f"Total duplicate scenario files removed: {removed_count}")

def archive_test_skill():
    print("\n=== Step 2: Archiving api-test-skill ===")
    api_test_dir = SKILLS_ROOT / "api-test-skill"
    if api_test_dir.exists():
        target_dst = ARCHIVE_ROOT / "api-test-skill"
        if target_dst.exists():
            shutil.rmtree(target_dst)
        shutil.move(api_test_dir, target_dst)
        print("  [ARCHIVED] api-test-skill moved to skills_archive_transition/")
    else:
        print("  api-test-skill does not exist, skipping.")

if __name__ == "__main__":
    clean_duplicates()
    archive_test_skill()
