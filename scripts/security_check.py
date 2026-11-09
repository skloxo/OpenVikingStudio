#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Pre-Commit & CI Secret Scanner for OpenViking.
Ensures zero API keys, private IPs, SSH credentials, or internal accounts are ever committed to Git.
"""

import hashlib
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PREFIX_SK = "s" + "k-"
PREFIX_GHP = "g" + "hp_"
PREFIX_GHFP = "github_" + "pat_"
PREFIX_ZGV = "ZGVmYXVsdA" + r"\."

SECRET_PATTERNS = [
    (re.compile(PREFIX_SK + r"[a-zA-Z0-9_-]{24,}"), "API Key Pattern"),
    (re.compile(PREFIX_GHP + r"[a-zA-Z0-9_-]{24,}"), "GitHub Token Pattern"),
    (re.compile(PREFIX_GHFP + r"[a-zA-Z0-9_]{24,}"), "GitHub Fine-Grained PAT"),
    (re.compile(PREFIX_ZGV + r"[A-Za-z0-9_=-]+\.[A-Za-z0-9_=-]{16,}"), "OpenViking UserKey Pattern"),
    (re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"), "Private Key Header"),
]

# One-way SHA-256 fingerprints of forbidden private infrastructure literals (zero plaintext stored)
FORBIDDEN_SHA256 = {
    "78a55a34f3a52e9f74af20996fea3171f4f899d882f7a98be3cf7777c09fb02c": "Internal FRP IP",
    "3873364c490a00e2a021af12859ce9316786fe5d7e11a7d3cb159adfff373afa": "Tailscale Private IP",
    "5e028ddf3dd97025b23f0ca5f593e0f4f5ee24175193fd2ed25aaf99811f32ae": "Internal Azure Account",
    "2a844e3e7ac7d94a0afa710467fa20213b9d7d00c0818258915389874c761cfc": "Hardcoded SSH Password",
    "8e44c56b7b6f4573f8da1ab079d0535047d76aa1f637472b04d51ead7f4914d7": "Hardcoded VLM API Key",
}
_TOKEN_CANDIDATES = re.compile(r"(?:\b(?:\d{1,3}\.){3}\d{1,3}\b|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[A-Za-z0-9_-]{8,})")

WHITELIST_PATTERNS = [
    re.compile(r"sk-mock-token-sample"),
    re.compile(r"sk-ant-api03-DAqS"),
    re.compile(r"sk-proj-1234567890"),
    re.compile(r"sk-center-stats"),
    re.compile(r"sk-concurrency"),
    re.compile(r"sk-xxxxxxxx"),
    re.compile(r"\[REDACTED"),
    re.compile(r"ZGVmYXVsdA\.ZGVmYXVsdA"),
    re.compile(r"ZGVmYXVsdA\.dGVzdHVzZXI"),
    re.compile(r"0123456789abcdef0123456789abcdef"),
    re.compile(r"sk-lf-vikingbot"),
    re.compile(r"name: dotenv"),
    re.compile(r"displayName\":\"Emacs Lisp"),
    re.compile(r"sk-user-threat"),
]


def _check_tarball(file_path: Path) -> list[str]:
    violations = []
    try:
        with tarfile.open(file_path, "r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                bn = Path(member.name).name
                if bn not in ("config.json", "mcp_config.json"):
                    continue
                data = tf.extractfile(member).read().decode("utf-8", errors="ignore")
                if any(w.search(data) for w in WHITELIST_PATTERNS):
                    continue
                for pat, desc in SECRET_PATTERNS:
                    if pat.search(data):
                        violations.append(f"{file_path}!{member.name} - [{desc}] (packaged credential)")
    except Exception:
        pass
    return violations


def check_file(file_path: Path) -> list[str]:
    if file_path.suffix == ".tgz":
        return _check_tarball(file_path)

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
        for cand in _TOKEN_CANDIDATES.findall(line):
            digest = hashlib.sha256(cand.encode("utf-8")).hexdigest()
            if digest in FORBIDDEN_SHA256:
                violations.append(f"{file_path}:{line_idx} - [{FORBIDDEN_SHA256[digest]}] (sha256 match masked)")
    return violations


def main():
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    cmd = ["git", "ls-files"]
    cp = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if cp.returncode == 0 and cp.stdout.strip():
        tracked_files = [Path(f.strip()) for f in cp.stdout.splitlines() if f.strip()]
    else:
        tracked_files = []
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in ("node_modules", "dist", "build", ".git", "__pycache__", "scratch", "openviking.egg-info")
            ]
            for fn in files:
                if fn.startswith(".env") or fn.endswith((".snap.md", ".sqlite", ".db")):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), repo_root)
                if rel.startswith("scratch") or rel.startswith("scripts/check_api_skills") or rel.startswith("scripts/test_detail_api"):
                    continue
                tracked_files.append(Path(rel))

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
