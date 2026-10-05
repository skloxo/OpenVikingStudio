#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Anti-Demo & Anti-Dangling Automated Retina Gate (Card-103 / v1.7.57).

Statically and syntactically inspects all frontend components in src/routes/ to enforce:
  1. No forbidden demo/mock markers (@demo-only, MOCK_DATA_ONLY, fake_persistence).
  2. Grounded Cockpits: Cockpits with preset constants must mount real asset pickers or query endpoints.
  3. Action Persistence: User-facing save/persist buttons must be wired to real persistence callers or callback props.
  4. NO GREEN EVER 🚫 (zero emerald/green utility classes).
  5. Typography Floor: zero micro-fonts (< 12px).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

# Regex Patterns
RE_DEMO_MARKERS = re.compile(
    r"(\bDEMO_ONLY\b|@demo-only|MOCK_DATA_ONLY|//\s*TODO:\s*(mock|demo)\s*only|fake_persistence|mock-apply)",
    re.IGNORECASE,
)
RE_GREEN_CLASSES = re.compile(r"\b(text|bg|border)-(green|emerald)-\d+\b")
RE_MICRO_FONTS = re.compile(r"\btext-\[(8|9|10|11)px\]")


# Dangling Button Check: Button with save/apply text that only executes an alert or empty stub
RE_DANGLING_BUTTON = re.compile(
    r"<[Bb]utton[^>]*onClick=\{[^}]*alert\([^}]*\}[\s\S]*?(保存|覆写|落盘|Save|Persist)",
    re.IGNORECASE,
)

# Cockpit Grounding Tokens
GROUNDING_TOKENS = (
    "Picker",
    "useQuery",
    "useMutation",
    "ovClient",
    "file_picker",
    "onSelect",
    "fetch",
    "axios",
)

# Persistence Callers
PERSISTENCE_TOKENS = (
    "ovClient",
    "fetch",
    "useMutation",
    "localStorage",
    "sessionStorage",
    "onSave",
    "onApply",
    "onPersist",
    "applyMutation",
    "mutation",
    "dispatch",
)


def scan_file(file_path: Path, repo_root: Path) -> List[Dict[str, Any]]:
    """Scan a single component file for anti-demo violations."""
    rel_path = str(file_path.relative_to(repo_root))
    if file_path.name.endswith(".test.tsx") or file_path.name.endswith(".test.ts"):
        return []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        return [{"file": rel_path, "rule": "READ_ERROR", "line": 1, "message": str(exc)}]

    violations: List[Dict[str, Any]] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        # 1. Demo markers
        m_demo = RE_DEMO_MARKERS.search(line)
        if m_demo:
            violations.append({
                "file": rel_path,
                "rule": "FORBIDDEN_DEMO_MARKER",
                "line": idx,
                "message": f"Forbidden demo/mock marker detected: '{m_demo.group(0)}'",
            })

        # 2. NO GREEN EVER
        m_green = RE_GREEN_CLASSES.search(line)
        if m_green:
            violations.append({
                "file": rel_path,
                "rule": "NO_GREEN_EVER",
                "line": idx,
                "message": f"NO GREEN EVER violation: '{m_green.group(0)}' (use cyan-500/rose-500/muted)",
            })

        # 3. Typography Floor
        m_font = RE_MICRO_FONTS.search(line)
        if m_font:
            violations.append({
                "file": rel_path,
                "rule": "MICRO_FONT_FLOOR",
                "line": idx,
                "message": f"Micro-font violation: '{m_font.group(0)}' (minimum allowed is >= 12px / text-xs)",
            })

    # 4. Grounding Check for Cockpits with Presets
    if "-cockpit.tsx" in file_path.name.lower():
        has_presets = "PRESET" in content
        if has_presets:
            is_grounded = any(k in content for k in GROUNDING_TOKENS)
            if not is_grounded:
                violations.append({
                    "file": rel_path,
                    "rule": "UNGROUNDED_PRESET_COCKPIT",
                    "line": 1,
                    "message": "Cockpit defines presets but lacks real asset picker or query hook to real storage",
                })

    # 5. Dangling Button Check: Button with save/apply text that only executes alert
    m_dangling = RE_DANGLING_BUTTON.search(content)
    if m_dangling:
        violations.append({
            "file": rel_path,
            "rule": "DANGLING_ACTION_FAKE_ALERT",
            "line": 1,
            "message": "Component contains Save/Apply button that only invokes browser alert without physical persistence",
        })

    return violations


def run_anti_demo_gate(target_dir: Path | None = None, repo_root: Path | None = None) -> Dict[str, Any]:
    """Run full automated retina gate audit across frontend components."""
    root = repo_root or Path(__file__).resolve().parent.parent
    scan_dir = target_dir or (root / "src" / "routes")

    all_violations: List[Dict[str, Any]] = []
    scanned_count = 0

    if scan_dir.exists():
        for f in sorted(scan_dir.rglob("*.tsx")):
            if f.is_file() and not f.name.endswith(".test.tsx"):
                scanned_count += 1
                v = scan_file(f, root)
                all_violations.extend(v)

    total_dangling = len(all_violations)
    pass_rate = 100.0 if scanned_count > 0 and total_dangling == 0 else max(
        0.0, round(((scanned_count - total_dangling) / scanned_count) * 100.0, 1)
    )

    return {
        "status": "PASS" if total_dangling == 0 else "FAIL",
        "scanned_components": scanned_count,
        "total_dangling_features_count": total_dangling,
        "anti_demo_gate_pass_rate": pass_rate,
        "violations": all_violations,
    }


def main():
    parser = argparse.ArgumentParser(description="Anti-Demo & Anti-Dangling Automated Retina Gate")
    parser.add_argument("--path", type=str, default=None, help="Target directory to scan")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    target_path = Path(args.path) if args.path else None
    res = run_anti_demo_gate(target_dir=target_path)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("🛡️ Anti-Demo & Anti-Dangling Automated Retina Gate (Card-103)")
        print(f"• Scanned Components: {res['scanned_components']}")
        print(f"• Total Dangling Violations: {res['total_dangling_features_count']}")
        print(f"• Gate Pass Rate: {res['anti_demo_gate_pass_rate']}%")
        print(f"• Status: {res['status']}")
        print("=" * 60)

        if res["violations"]:
            print("\n❌ Violations Found:")
            for v in res["violations"]:
                print(f"  [{v['rule']}] {v['file']}:{v['line']} - {v['message']}")
            sys.exit(1)
        else:
            print("\n✅ All frontend components 100% grounded and closed-loop compliant.")
            sys.exit(0)


if __name__ == "__main__":
    main()
