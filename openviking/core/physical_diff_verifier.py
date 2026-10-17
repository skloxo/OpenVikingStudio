# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Physical Diff Verifier: Defends against zero-diff or comment-only delivery cheats.
(Card-Verify-MultiMetricGate - v1.5.06)

Derived from ByteDance Aspire (2026.06) & Goodhart's Law defense:
Agent delivery must produce real physical code changes. Blank lines, whitespace shifts,
and pure comments (#, //, /* */, <!-- -->, etc.) are filtered out.
Effective diff lines must strictly exceed the minimum threshold.
"""

from dataclasses import dataclass, field
import hashlib
import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DiffVerificationResult:
    """Immutable outcome of physical diff verification."""
    is_valid: bool
    effective_diff_lines: int
    added_lines: int
    deleted_lines: int
    comment_lines_filtered: int
    whitespace_lines_filtered: int
    changed_files: List[str] = field(default_factory=list)
    file_hashes: Dict[str, str] = field(default_factory=dict)
    rejection_reason: Optional[str] = None


class PhysicalDiffVerifier:
    """
    Analyzes unified diffs or working tree changes to assert genuine code modifications.
    Filters out synthetic diff noise: comments, docstrings, blank lines, and whitespace.
    """

    SINGLE_LINE_COMMENT_PREFIXES = ("#", "//", "--", ";", "rem ", "REM ")
    BLOCK_COMMENT_MARKERS = ("/*", "*/", "*", '"""', "'''", "<!--", "-->")

    def __init__(self, min_effective_lines: int = 1) -> None:
        self.min_effective_lines = max(1, min_effective_lines)

    @classmethod
    def is_comment_or_whitespace(cls, text: str) -> Tuple[bool, str]:
        """
        Determines if a diff payload line is pure whitespace or comment.
        Returns (is_filtered, filter_type: 'whitespace' | 'comment' | 'none').
        """
        stripped = text.strip()
        if not stripped:
            return True, "whitespace"

        for prefix in cls.SINGLE_LINE_COMMENT_PREFIXES:
            if stripped.startswith(prefix):
                return True, "comment"

        # Check for block comment markers or inline continuation
        if any(stripped.startswith(m) or stripped.endswith(m) for m in cls.BLOCK_COMMENT_MARKERS):
            return True, "comment"

        return False, "none"

    def verify_diff_text(
        self,
        diff_text: str,
        changed_files: Optional[List[str]] = None,
        file_hashes: Optional[Dict[str, str]] = None,
    ) -> DiffVerificationResult:
        """
        Verifies unified diff text by filtering comment-only and whitespace-only lines.
        """
        if not diff_text or not diff_text.strip():
            return DiffVerificationResult(
                is_valid=False,
                effective_diff_lines=0,
                added_lines=0,
                deleted_lines=0,
                comment_lines_filtered=0,
                whitespace_lines_filtered=0,
                changed_files=changed_files or [],
                file_hashes=file_hashes or {},
                rejection_reason="Empty diff: No code changes were submitted.",
            )

        effective_count = 0
        added_count = 0
        deleted_count = 0
        comment_filtered = 0
        whitespace_filtered = 0

        files_detected: List[str] = list(changed_files) if changed_files else []

        for line in diff_text.splitlines():
            # Parse changed file headers: +++ b/path/to/file or diff --git a/... b/...
            if line.startswith("+++ b/"):
                filepath = line[6:].strip()
                if filepath not in files_detected and filepath != "/dev/null":
                    files_detected.append(filepath)
                continue
            if line.startswith("--- ") or line.startswith("@@ ") or line.startswith("diff --git"):
                continue

            # Modified lines
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                is_noise, kind = self.is_comment_or_whitespace(content)
                if is_noise:
                    if kind == "comment":
                        comment_filtered += 1
                    else:
                        whitespace_filtered += 1
                else:
                    effective_count += 1
                    added_count += 1
            elif line.startswith("-") and not line.startswith("---"):
                content = line[1:]
                is_noise, kind = self.is_comment_or_whitespace(content)
                if is_noise:
                    if kind == "comment":
                        comment_filtered += 1
                    else:
                        whitespace_filtered += 1
                else:
                    effective_count += 1
                    deleted_count += 1

        is_valid = effective_count >= self.min_effective_lines
        reason = None
        if not is_valid:
            reason = (
                f"Diff validation failed: effective code changes ({effective_count}) "
                f"< required minimum ({self.min_effective_lines}). "
                f"Filtered {comment_filtered} comments and {whitespace_filtered} blank lines."
            )

        return DiffVerificationResult(
            is_valid=is_valid,
            effective_diff_lines=effective_count,
            added_lines=added_count,
            deleted_lines=deleted_count,
            comment_lines_filtered=comment_filtered,
            whitespace_lines_filtered=whitespace_filtered,
            changed_files=files_detected,
            file_hashes=file_hashes or {},
            rejection_reason=reason,
        )

    def verify_git_working_tree(
        self,
        repo_path: str,
        paths: Optional[List[str]] = None,
    ) -> DiffVerificationResult:
        """
        Extracts git working tree and staged diffs, computes SHA-256 hashes, and asserts validity.
        """
        if not os.path.isdir(repo_path):
            return DiffVerificationResult(
                is_valid=False,
                effective_diff_lines=0,
                added_lines=0,
                deleted_lines=0,
                comment_lines_filtered=0,
                whitespace_lines_filtered=0,
                rejection_reason=f"Repository directory does not exist: {repo_path}",
            )

        cmd = ["git", "diff", "HEAD"]
        if paths:
            cmd.append("--")
            cmd.extend(paths)

        try:
            res = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=15.0,
                check=False,
            )
            diff_text = res.stdout or ""
        except Exception as e:
            return DiffVerificationResult(
                is_valid=False,
                effective_diff_lines=0,
                added_lines=0,
                deleted_lines=0,
                comment_lines_filtered=0,
                whitespace_lines_filtered=0,
                rejection_reason=f"Git command failed: {e}",
            )

        # Compute sha256 for tracked/changed files
        file_hashes: Dict[str, str] = {}
        changed_files: List[str] = []
        try:
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10.0,
                check=False,
            )
            for line in status_res.stdout.splitlines():
                if len(line) > 3:
                    fp = line[3:].strip()
                    changed_files.append(fp)
                    full_fp = os.path.join(repo_path, fp)
                    if os.path.isfile(full_fp):
                        try:
                            with open(full_fp, "rb") as f:
                                file_hashes[fp] = hashlib.sha256(f.read()).hexdigest()[:16]
                        except Exception:
                            pass
        except Exception:
            pass

        return self.verify_diff_text(
            diff_text=diff_text,
            changed_files=changed_files,
            file_hashes=file_hashes,
        )
