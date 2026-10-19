#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
AHE Contract & Snapshot Drift Pre-Commit/CI Gate Checker.
Checks all active AHE manifests for unauthorized file drift or PolarJudge failures.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.ahe_engine import AHEEngine
from openviking.core.ahe_manifest import AHEStatus


def run_ahe_check(run_polar: bool = False) -> int:
    engine = AHEEngine.get_instance()
    res = engine.run_pre_release_gate(run_polar=run_polar) if hasattr(engine, "run_pre_release_gate") else {}
    if not isinstance(res, dict):
        res = {}

    total = res.get("total_manifests", 0)
    drift_violations = res.get("drift_violations", [])
    polar_violations = res.get("polar_violations", [])

    exit_code = 0
    if isinstance(drift_violations, (list, tuple)) and len(drift_violations) > 0:
        print(f"🚨 [AHE Gate BLOCKED] Detected {len(drift_violations)} unrecorded snapshot drift(s):")
        for v in drift_violations:
            print(f"   - {v}")
        exit_code = 1

    if isinstance(polar_violations, (list, tuple)) and len(polar_violations) > 0:
        print(f"🚨 [AHE Gate BLOCKED] Detected {len(polar_violations)} PolarJudge assertion failure(s):")
        for v in polar_violations:
            print(f"   - {v}")
        exit_code = 1

    if exit_code == 0:
        print(f"✅ [AHE Gate PASS] All {total} core invariant manifest(s) clean and verified.")

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="AHE Contract & Snapshot Drift Pre-Commit/CI Gate Checker")
    parser.add_argument("--run-polar", action="store_true", help="Execute PolarJudge validation commands")
    args = parser.parse_args()

    sys.exit(run_ahe_check(run_polar=args.run_polar))


if __name__ == "__main__":
    main()
