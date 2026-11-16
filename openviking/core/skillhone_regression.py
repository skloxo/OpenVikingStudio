# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""SkillHone Isolated Regression & Optimizer/Evaluator Decoupling Engine.

Implements three core safeguards for Card-254:
1. Optimizer vs Evaluator separation: optimizer receives sanitized failure signals
   and historical rejected decisions only, never holdout internals or write access.
2. Full-bundle integrity validation across SKILL.md, scripts/, references/, and assets/.
3. Isolated temporary sandbox execution for targeted regression commands without
   mutating the source skill directory.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import yaml

MAX_BUNDLE_FILE_LINES = 500
_SECRET_RE = re.compile(
    r"(?i)\b(?:vk-sk-[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{12,}|"
    r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{8,}['\"]?)"
)
_HOLDOUT_SECTION_RE = re.compile(r"(?is)#\s*HOLDOUT-PRIVATE.*?(?=\n#|\Z)")
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_ASSET_PATH_RE = re.compile(r"(?<![A-Za-z0-9_./-])((?:scripts|references|assets)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)")


def sanitize_failure_text(text: str) -> str:
    """Strip credentials and holdout-private test internals before optimizer sees them."""
    cleaned = _HOLDOUT_SECTION_RE.sub("[REDACTED_HOLDOUT_DETAILS]", str(text or ""))
    return _SECRET_RE.sub("[REDACTED_SECRET]", cleaned).strip()


def compute_bundle_fingerprint(
    diff_patch: str = "",
    package_files: Optional[Dict[str, str]] = None,
) -> str:
    """Compute a stable SHA-256 fingerprint over diff patch and candidate bundle files."""
    hasher = hashlib.sha256()
    hasher.update((diff_patch or "").strip().encode("utf-8"))
    if package_files:
        for rel_path in sorted(package_files):
            hasher.update(b"\x00")
            hasher.update(rel_path.replace("\\", "/").encode("utf-8"))
            hasher.update(b"\x01")
            hasher.update(str(package_files[rel_path]).encode("utf-8"))
    return hasher.hexdigest()[:24]


@dataclass(frozen=True)
class OptimizerFailureContext:
    """Read-only, sanitized diagnostic input exposed to the patch optimizer."""

    skill_name: str
    sanitized_signal: str
    avoided_fingerprints: frozenset[str]
    avoided_rationales: tuple[Dict[str, str], ...]


def build_optimizer_context(
    skill_name: str,
    raw_failure_signal: str,
    rejected_history: Sequence[Dict[str, Any]],
) -> OptimizerFailureContext:
    """Construct an isolated optimizer context from sanitized failure and past rejections."""
    avoided_fps = {
        str(item.get("patch_fingerprint") or "").strip()
        for item in rejected_history
        if item.get("patch_fingerprint")
    }
    avoided_details = tuple(
        {
            "patch_fingerprint": str(item.get("patch_fingerprint") or ""),
            "diagnosis": sanitize_failure_text(str(item.get("diagnosis") or "")),
            "rationale": sanitize_failure_text(str(item.get("rationale") or "")),
        }
        for item in rejected_history
    )
    return OptimizerFailureContext(
        skill_name=skill_name,
        sanitized_signal=sanitize_failure_text(raw_failure_signal),
        avoided_fingerprints=frozenset(avoided_fps),
        avoided_rationales=avoided_details,
    )


def _extract_frontmatter(text: str) -> Optional[Dict[str, Any]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None
    raw_yaml = "\n".join(lines[1:end_idx])
    try:
        parsed = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _collect_local_references(doc_text: str) -> List[str]:
    refs: List[str] = []
    for match in _MD_LINK_RE.findall(doc_text):
        target = match.strip().split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "viking://", "mailto:")):
            continue
        refs.append(target)
    for match in _ASSET_PATH_RE.findall(doc_text):
        if match not in refs:
            refs.append(match)
    return refs


def validate_skill_bundle(bundle_dir: Path) -> Dict[str, Any]:
    """Validate full Skill bundle directory (SKILL.md frontmatter, links, line caps)."""
    errors: List[str] = []
    skill_md = bundle_dir / "SKILL.md"
    if not skill_md.is_file():
        errors.append("Missing required SKILL.md in skill bundle.")
        return {"passed": False, "errors": errors, "checked_files": 0, "checked_links": 0}

    skill_text = skill_md.read_text(encoding="utf-8", errors="replace")
    meta = _extract_frontmatter(skill_text)
    if not meta or not str(meta.get("name") or "").strip() or not str(meta.get("description") or "").strip():
        errors.append("SKILL.md missing valid YAML frontmatter with non-empty 'name' and 'description'.")

    checked_files = 0
    checked_links = 0
    bundle_root = bundle_dir.resolve()
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        checked_files += 1
        rel = path.relative_to(bundle_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"Unreadable bundle file {rel}: {exc}")
            continue
        line_count = len(content.splitlines())
        if line_count > MAX_BUNDLE_FILE_LINES:
            errors.append(f"Bundle file {rel} has {line_count} lines (> {MAX_BUNDLE_FILE_LINES} line limit).")

        if path.name == "SKILL.md" or rel.startswith("references/"):
            for ref in _collect_local_references(content):
                checked_links += 1
                candidate = (path.parent / ref).resolve() if not ref.startswith(("scripts/", "references/", "assets/")) else (bundle_root / ref).resolve()
                try:
                    candidate.relative_to(bundle_root)
                except ValueError:
                    errors.append(f"Unsafe relative reference '{ref}' in {rel} escapes bundle root.")
                    continue
                if not candidate.exists():
                    errors.append(f"Broken reference '{ref}' in {rel}: target does not exist.")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "checked_files": checked_files,
        "checked_links": checked_links,
    }


def build_reviewable_change_summary(
    *,
    skill_dir: Optional[Path] = None,
    package_files: Optional[Dict[str, str]] = None,
    diff_patch: str = "",
) -> Dict[str, Any]:
    """Generate a reviewable manifest comparing changed/added files against base skill_dir."""
    added: List[str] = []
    modified: List[str] = []
    unchanged: List[str] = []
    if package_files:
        for rel, new_text in sorted(package_files.items()):
            norm_rel = rel.replace("\\", "/")
            if skill_dir and (skill_dir / norm_rel).is_file():
                old_text = (skill_dir / norm_rel).read_text(encoding="utf-8", errors="replace")
                if old_text == new_text:
                    unchanged.append(norm_rel)
                else:
                    modified.append(norm_rel)
            else:
                added.append(norm_rel)
    return {
        "added_files": added,
        "modified_files": modified,
        "unchanged_files": unchanged,
        "has_diff_patch": bool((diff_patch or "").strip()),
        "total_overlay_files": len(package_files or {}),
    }


def _safe_write_overlay(sandbox_dir: Path, package_files: Dict[str, str]) -> List[str]:
    errors: List[str] = []
    sandbox_root = sandbox_dir.resolve()
    for rel_path, content in package_files.items():
        norm = Path(rel_path)
        if norm.is_absolute() or ".." in norm.parts:
            errors.append(f"Rejected unsafe package file path: {rel_path}")
            continue
        dest = (sandbox_root / norm).resolve()
        try:
            dest.relative_to(sandbox_root)
        except ValueError:
            errors.append(f"Rejected escaping package path: {rel_path}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(str(content), encoding="utf-8")
    return errors


class IsolatedSkillEvaluator:
    """Read-isolated evaluator executing bundle checks and regression commands in temp sandbox."""

    @staticmethod
    def evaluate(
        *,
        skill_dir: Optional[str | Path] = None,
        package_files: Optional[Dict[str, str]] = None,
        regression_commands: Optional[Sequence[Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """Run full-bundle integrity check + isolated sandbox regression without mutating source."""
        source_path = Path(skill_dir).resolve() if skill_dir else None
        if source_path is not None and not source_path.is_dir():
            return {
                "passed": False,
                "rationale": f"Target skill_dir does not exist: {source_path}",
                "bundle_validation": {"passed": False, "errors": [f"Missing directory {source_path}"]},
                "command_results": [],
            }

        with tempfile.TemporaryDirectory(prefix="skillhone_eval_") as tmp_root:
            sandbox = Path(tmp_root) / "skill_bundle"
            if source_path is not None:
                shutil.copytree(source_path, sandbox)
            else:
                sandbox.mkdir(parents=True, exist_ok=True)

            if package_files:
                overlay_errors = _safe_write_overlay(sandbox, package_files)
                if overlay_errors:
                    return {
                        "passed": False,
                        "rationale": "; ".join(overlay_errors),
                        "bundle_validation": {"passed": False, "errors": overlay_errors},
                        "command_results": [],
                    }

            bundle_check = validate_skill_bundle(sandbox)
            command_results: List[Dict[str, Any]] = []
            cmd_failed = False

            for cmd in regression_commands or ():
                is_shell = isinstance(cmd, str)
                env = os.environ.copy()
                env["SKILLHONE_SANDBOX_DIR"] = str(sandbox)
                env["SKILLHONE_READONLY_EVAL"] = "1"
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(sandbox),
                        shell=is_shell,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=timeout_seconds,
                        env=env,
                    )
                    passed_cmd = proc.returncode == 0
                    command_results.append(
                        {
                            "command": cmd if is_shell else " ".join(str(x) for x in cmd),
                            "returncode": proc.returncode,
                            "passed": passed_cmd,
                            "stdout_tail": sanitize_failure_text((proc.stdout or "")[-800:]),
                            "stderr_tail": sanitize_failure_text((proc.stderr or "")[-800:]),
                        }
                    )
                    if not passed_cmd:
                        cmd_failed = True
                except (subprocess.TimeoutExpired, OSError) as exc:
                    cmd_failed = True
                    command_results.append(
                        {
                            "command": str(cmd),
                            "returncode": -1,
                            "passed": False,
                            "stdout_tail": "",
                            "stderr_tail": sanitize_failure_text(str(exc)),
                        }
                    )

            passed = bool(bundle_check["passed"]) and not cmd_failed
            reasons: List[str] = []
            if not bundle_check["passed"]:
                reasons.extend(bundle_check["errors"])
            if cmd_failed:
                failed_cmds = [c["command"] for c in command_results if not c["passed"]]
                reasons.append(f"Regression command(s) failed: {', '.join(failed_cmds)}")

            return {
                "passed": passed,
                "rationale": "; ".join(reasons) if reasons else "Bundle integrity and isolated regression passed.",
                "bundle_validation": bundle_check,
                "command_results": command_results,
            }
