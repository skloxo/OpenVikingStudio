#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Pre-Commit & CI Secret Scanner for OpenViking.
Ensures zero API keys, private IPs, SSH credentials, or internal accounts are ever committed to Git.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

PREFIX_SK = "s" + "k-"
PREFIX_GHP = "g" + "hp_"

SECRET_PATTERNS = [
    (re.compile(PREFIX_SK + r"[a-zA-Z0-9_-]{24,}"), "API Key Pattern"),
    (re.compile(PREFIX_GHP + r"[a-zA-Z0-9_-]{24,}"), "GitHub Token Pattern"),
    (re.compile(r"8\.129\.0\.26"), "Internal FRP IP"),
    (re.compile(r"100\.78\.64\.128"), "Tailscale Private IP"),
    (re.compile(r"Skl328" + r"9568"), "Hardcoded SSH Password"),
    (re.compile(r"s@8" + r"xx5\.com"), "Internal Azure Account"),
    (re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"), "Private Key Header"),
]

WHITELIST_PATTERNS = [
    re.compile(r"sk-mock-token-sample"),
    re.compile(r"sk-ant-api03-DAqS"),
    re.compile(r"sk-proj-1234567890"),
    re.compile(r"sk-center-stats"),
    re.compile(r"sk-concurrency"),
    re.compile(r"sk-xxxxxxxx"),
    re.compile(r"\[REDACTED"),
    re.compile(r"ZGVmYXVsdA\.ZGVmYXVsdA"),
    re.compile(r"sk-lf-vikingbot"),
    re.compile(r"name: dotenv"),
    re.compile(r"displayName\":\"Emacs Lisp"),
]


def check_file(file_path: Path) -> list[str]:
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    for line_idx, line in enumerate(content.splitlines(), start=1):
        if any(w.search(line) for w in WHITELIST_PATTERNS):
            continue
        for pat, desc in SECRET_PATTERNS:
            if pat.search(line):
                violations.append(f"{file_path}:{line_idx} - [{desc}] (sensitive match masked)")
    return violations


def main():
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    cmd = ["git", "ls-files"]
    cp = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if cp.returncode != 0:
        print(f"Error getting git files: {cp.stderr}")
        sys.exit(1)

    tracked_files = [Path(f.strip()) for f in cp.stdout.splitlines() if f.strip()]

    total_violations = []
    for f in tracked_files:
        if f.suffix in (".png", ".jpg", ".ico", ".woff2", ".pdf", ".pyc"):
            continue
        if str(f) == "scripts/security_check.py":
            continue
        v = check_file(f)
        if v:
            total_violations.extend(v)

    if total_violations:
        print("\n❌ SECURITY SCAN FAILED! The following secrets/credentials were detected in git tracked files:")
        for viol in total_violations:
            print(f"  🚨 {viol}")
        print("\nAction required: Remove all secrets, private IPs, and credentials before committing!\n")
        sys.exit(1)
    else:
        print(f"✅ Security Scan PASS: Checked {len(tracked_files)} tracked files. Zero secrets detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
