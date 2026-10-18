#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Purge deprecated /evolution route and retire dangling links (Card-179)."""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def update_file(rel_path: str, old_str: str, new_str: str) -> bool:
    target = ROOT / rel_path
    if not target.exists():
        print(f"[-] File not found: {rel_path}")
        return False
    content = target.read_text(encoding="utf-8")
    if old_str not in content:
        print(f"[-] Target string not found in {rel_path}")
        return False
    updated = content.replace(old_str, new_str)
    target.write_text(updated, encoding="utf-8")
    print(f"[+] Successfully updated: {rel_path}")
    return True

def main():
    print("🚀 [Card-179] Starting deprecated /evolution purge...")

    # 1. Update app-shell-nav.tsx
    update_file(
        "src/components/app-shell-nav.tsx",
        "to: '/evolution'",
        "to: '/skills'",
    )

    # 2. Update retrieval/route.tsx
    update_file(
        "src/routes/retrieval/route.tsx",
        'to="/evolution"',
        'to="/skills"',
    )

    # 3. Update harness-guardrails-cockpit.tsx
    update_file(
        "src/routes/request-logs/-components/harness-guardrails-cockpit.tsx",
        'to="/evolution" search={{ tab: \'lessons\' }}',
        'to="/skills" search={{ mode: \'pipeline\' }}',
    )

    # 4. Remove src/routes/evolution directory
    evo_dir = ROOT / "src" / "routes" / "evolution"
    if evo_dir.exists():
        shutil.rmtree(evo_dir)
        print(f"[+] Physically purged: {evo_dir}")
    else:
        print(f"[-] Directory already purged: {evo_dir}")

    # 5. Ensure openviking/_version.py is 1.7.134
    version_file = ROOT / "openviking" / "_version.py"
    if version_file.exists():
        content = version_file.read_text(encoding="utf-8")
        content = content.replace('"1.7.133"', '"1.7.134"').replace('(1, 7, 133)', '(1, 7, 134)')
        version_file.write_text(content, encoding="utf-8")
        print("[+] Synchronized openviking/_version.py -> 1.7.134")

    print("🎉 [Card-179] Purge step completed successfully.")

if __name__ == "__main__":
    main()
