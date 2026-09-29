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

# Ensure project root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.core.ahe_engine import AHEEngine
from openviking.core.ahe_manifest import AHEStatus


def run_ahe_check(run_polar: bool = False) -> int:
    engine = AHEEngine.get_instance()
    manifests = engine.list_manifests()

    if not manifests:
        print("🛡️ [AHE Gate] No registered manifests to check. (PASS)")
        return 0

    drift_violations = []
    polar_violations = []

    for m in manifests:
        # 仅针对 ACTIVE 与 VERIFIED 状态的契约执行强防护
        if m.status in (AHEStatus.ACTIVE, AHEStatus.VERIFIED):
            drift_res = engine.check_snapshot_drift(m.manifest_id)
            if not drift_res.get("snapshot_clean", True):
                for f in drift_res.get("drifted_files", []):
                    drift_violations.append(
                        f"Manifest [{m.manifest_id}] Skill [{m.skill_name}]: Drift in {f['path']}"
                    )

            if run_polar:
                verify_res = engine.verify_manifest(m.manifest_id)
                for r in verify_res.get("results", []):
                    if r.get("verdict") not in ("pass", "skip"):
                        polar_violations.append(
                            f"Manifest [{m.manifest_id}] Assumption [{r.get('assumption_id')}]: "
                            f"Command '{r.get('command')}' failed with exit {r.get('exit_code')}"
                        )

    exit_code = 0
    if drift_violations:
        print(f"🚨 [AHE Gate BLOCKED] Detected {len(drift_violations)} unrecorded snapshot drift(s):")
        for v in drift_violations:
            print(f"   - {v}")
        exit_code = 1

    if polar_violations:
        print(f"🚨 [AHE Gate BLOCKED] Detected {len(polar_violations)} PolarJudge assertion failure(s):")
        for v in polar_violations:
            print(f"   - {v}")
        exit_code = 1

    if exit_code == 0:
        print(f"✅ [AHE Gate PASS] All {len(manifests)} manifest(s) clean and verified.")

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="AHE Contract & Snapshot Drift Pre-Commit/CI Gate Checker")
    parser.add_argument("--run-polar", action="store_true", help="Execute PolarJudge validation commands")
    args = parser.parse_args()

    sys.exit(run_ahe_check(run_polar=args.run_polar))


if __name__ == "__main__":
    main()
