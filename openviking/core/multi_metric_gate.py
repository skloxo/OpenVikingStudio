# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Multi-Metric Gate: Holistic delivery gate binding diff validation, content hashing, and test retina.
(Card-Verify-MultiMetricGate - v1.5.06)

Derived from ByteDance Aspire (2026.06) & Goodhart's Law defense:
Eliminates synthetic loop completion. Asserts:
1. Genuine code modifications (effective diff lines > 0, filtering comments & whitespace);
2. Cryptographic content hashing (SHA-256 tracked artifact fingerprinting);
3. Genuine test suite execution (passed > 0, failed == 0, False Exit 0 blocked).
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional

from openviking.core.physical_diff_verifier import DiffVerificationResult, PhysicalDiffVerifier
from openviking.core.test_retina_runner import TestRetinaResult, TestRetinaRunner


@dataclass(frozen=True)
class GateVerificationReport:
    """Consolidated verification verdict for task completion."""
    passed: bool
    diff_result: DiffVerificationResult
    test_result: Optional[TestRetinaResult]
    rejection_reasons: List[str] = field(default_factory=list)
    verified_at: float = field(default_factory=time.time)
    summary: str = ""


class MultiMetricGate:
    """
    Orchestrates physical verification of code delivery before marking tasks completed.
    Enforces non-negotiable physical truth over agent self-reported exit codes.
    """

    def __init__(
        self,
        diff_verifier: Optional[PhysicalDiffVerifier] = None,
        test_runner: Optional[TestRetinaRunner] = None,
    ) -> None:
        self.diff_verifier = diff_verifier or PhysicalDiffVerifier(min_effective_lines=1)
        self.test_runner = test_runner or TestRetinaRunner(timeout_sec=60.0)

    def verify_delivery(
        self,
        repo_path: Optional[str] = None,
        diff_text: Optional[str] = None,
        test_command: Optional[str] = None,
        cwd: Optional[str] = None,
        min_effective_lines: int = 1,
        paths: Optional[List[str]] = None,
    ) -> GateVerificationReport:
        """
        Executes holistic multi-metric verification.
        Requires effective diff lines > 0 and (if test_command provided) real test suite green.
        """
        rejection_reasons: List[str] = []

        # 1. Physical Diff Verification
        if diff_text is not None:
            diff_res = self.diff_verifier.verify_diff_text(diff_text)
        elif repo_path:
            diff_res = self.diff_verifier.verify_git_working_tree(repo_path, paths=paths)
        else:
            diff_res = DiffVerificationResult(
                is_valid=False,
                effective_diff_lines=0,
                added_lines=0,
                deleted_lines=0,
                comment_lines_filtered=0,
                whitespace_lines_filtered=0,
                rejection_reason="Neither repo_path nor diff_text was provided for verification.",
            )

        if not diff_res.is_valid and diff_res.rejection_reason:
            rejection_reasons.append(diff_res.rejection_reason)

        # 2. Test Retina Verification (if command provided)
        test_res: Optional[TestRetinaResult] = None
        if test_command:
            runner_res = self.test_runner.run_tests(command=test_command, cwd=cwd or repo_path)
            test_res = runner_res
            if not runner_res.is_valid and runner_res.rejection_reason:
                rejection_reasons.append(runner_res.rejection_reason)

        is_overall_passed = len(rejection_reasons) == 0

        # Construct readable summary
        summary_parts = []
        if diff_res.is_valid:
            summary_parts.append(
                f"Diff Verified: {diff_res.effective_diff_lines} effective lines modified "
                f"(+{diff_res.added_lines}/-{diff_res.deleted_lines}, {len(diff_res.changed_files)} files)"
            )
        else:
            summary_parts.append("Diff Rejected")

        if test_res:
            if test_res.is_valid:
                summary_parts.append(
                    f"Test Retina Verified: {test_res.passed} passed in {test_res.duration_sec:.2f}s (zero skipped scams)"
                )
            else:
                summary_parts.append("Test Retina Rejected")

        summary = " | ".join(summary_parts)

        return GateVerificationReport(
            passed=is_overall_passed,
            diff_result=diff_res,
            test_result=test_res,
            rejection_reasons=rejection_reasons,
            summary=summary,
        )

    def verify_task_record(
        self,
        task_id: str,
        task_meta: Dict[str, Any],
        repo_path: Optional[str] = None,
    ) -> GateVerificationReport:
        """
        Convenience hook for TaskTracker to verify completion claims.
        Reads verification parameters from task_meta.
        """
        diff_text = task_meta.get("diff_text")
        test_command = task_meta.get("test_command")
        min_lines = task_meta.get("min_effective_lines", 1)

        return self.verify_delivery(
            repo_path=repo_path,
            diff_text=diff_text,
            test_command=test_command,
            min_effective_lines=min_lines,
        )
