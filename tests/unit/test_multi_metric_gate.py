# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Multi-Metric Gate, Physical Diff Verifier, and Test Retina Runner.
(Card-Verify-MultiMetricGate - v1.5.06)
"""

import pytest

from openviking.core.physical_diff_verifier import PhysicalDiffVerifier
from openviking.core.test_retina_runner import TestRetinaRunner
from openviking.core.multi_metric_gate import MultiMetricGate


class TestPhysicalDiffVerifier:
    """Tests noise filtering and assertion of genuine code modifications."""

    def test_filters_pure_comments_and_whitespace(self):
        verifier = PhysicalDiffVerifier(min_effective_lines=1)
        diff_noise = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,6 @@
+# This is a python comment
+// This is a ts comment
+/* block comment start
+ * inside block comment
+ */
+   
"""
        res = verifier.verify_diff_text(diff_noise)
        assert res.is_valid is False
        assert res.effective_diff_lines == 0
        assert res.comment_lines_filtered >= 5
        assert res.whitespace_lines_filtered >= 1
        assert "Diff validation failed" in (res.rejection_reason or "")

    def test_accepts_genuine_code_modifications(self):
        verifier = PhysicalDiffVerifier(min_effective_lines=1)
        diff_genuine = """diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@ -10,3 +10,6 @@
+# Note on logic
+def compute_velocity(distance: float, time_sec: float) -> float:
+    if time_sec <= 0:
+        raise ValueError("time must be positive")
+    return distance / time_sec
"""
        res = verifier.verify_diff_text(diff_genuine)
        assert res.is_valid is True
        assert res.effective_diff_lines == 4
        assert res.comment_lines_filtered == 1
        assert res.added_lines == 4
        assert "service.py" in res.changed_files
        assert res.rejection_reason is None

    def test_rejects_empty_diff(self):
        verifier = PhysicalDiffVerifier(min_effective_lines=1)
        res = verifier.verify_diff_text("")
        assert res.is_valid is False
        assert res.effective_diff_lines == 0
        assert "Empty diff" in (res.rejection_reason or "")


class TestTestRetinaRunner:
    """Tests parsing and rejection of False Exit 0 (all skipped or swallowed)."""

    def test_parses_successful_pytest_output(self):
        sample_output = """
============================= test session starts ==============================
rootdir: /workspace
collected 5 items

tests/test_demo.py .....                                                 [100%]

============================== 5 passed in 0.12s ===============================
"""
        passed, failed, skipped, errors, duration = TestRetinaRunner.parse_test_output(sample_output)
        assert passed == 5
        assert failed == 0
        assert skipped == 0
        assert errors == 0
        assert duration == 0.12

    def test_parses_mixed_failure_pytest_output(self):
        sample_output = """
============================== 1 failed, 2 passed, 1 skipped in 1.25s ===============================
"""
        passed, failed, skipped, errors, duration = TestRetinaRunner.parse_test_output(sample_output)
        assert passed == 2
        assert failed == 1
        assert skipped == 1
        assert errors == 0
        assert duration == 1.25

    def test_rejects_false_exit_zero_all_skipped(self):
        runner = TestRetinaRunner()
        sample_output = """
============================= test session starts ==============================
collected 3 items

tests/test_demo.py sss                                                   [100%]

============================== 3 skipped in 0.05s ===============================
"""
        # Mocking parse output against runner assertion
        passed, failed, skipped, errors, duration = runner.parse_test_output(sample_output)
        assert passed == 0
        assert skipped == 3

        # Simulate runner result evaluation for Exit 0 with 0 passed
        # Direct check on run_tests with echo
        res = runner.run_tests(command='echo "=== 3 skipped in 0.05s ==="')
        assert res.is_valid is False
        assert res.passed == 0
        assert res.skipped == 3
        assert "False Exit 0 rejected" in (res.rejection_reason or "")

    def test_rejects_empty_suite_exit_zero(self):
        runner = TestRetinaRunner()
        res = runner.run_tests(command='echo "collected 0 items / no tests ran"')
        assert res.is_valid is False
        assert res.passed == 0
        assert "False Exit 0 rejected" in (res.rejection_reason or "")

    def test_executes_real_passing_test(self):
        runner = TestRetinaRunner(timeout_sec=15.0)
        res = runner.run_tests(
            command='python3 -c "import sys; print(\'== 1 passed in 0.01s ==\'); sys.exit(0)"'
        )
        assert res.is_valid is True
        assert res.passed == 1
        assert res.failed == 0
        assert res.exit_code == 0
        assert res.rejection_reason is None


class TestMultiMetricGate:
    """Tests full gate pipeline combining diff validation and test retina."""

    def test_gate_rejects_when_diff_is_noise_only(self):
        gate = MultiMetricGate()
        diff_noise = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
+# Just a comment
"""
        report = gate.verify_delivery(
            diff_text=diff_noise,
            test_command='python3 -c "import sys; print(\'== 1 passed in 0.01s ==\'); sys.exit(0)"',
        )
        assert report.passed is False
        assert any("Diff validation failed" in r for r in report.rejection_reasons)

    def test_gate_rejects_when_test_is_false_exit_zero(self):
        gate = MultiMetricGate()
        diff_code = """diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,1 +1,3 @@
+def add(a, b):
+    return a + b
"""
        report = gate.verify_delivery(
            diff_text=diff_code,
            test_command='python3 -c "import sys; print(\'== 2 skipped in 0.02s ==\'); sys.exit(0)"',
        )
        assert report.passed is False
        assert any("False Exit 0 rejected" in r for r in report.rejection_reasons)

    def test_gate_passes_with_real_diff_and_real_tests(self):
        gate = MultiMetricGate()
        diff_code = """diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,1 +1,3 @@
+def multiply(a, b):
+    return a * b
"""
        report = gate.verify_delivery(
            diff_text=diff_code,
            test_command='python3 -c "import sys; print(\'== 2 passed in 0.04s ==\'); sys.exit(0)"',
        )
        assert report.passed is True
        assert len(report.rejection_reasons) == 0
        assert report.diff_result.effective_diff_lines == 2
        assert report.test_result is not None
        assert report.test_result.passed == 2
        assert "Diff Verified: 2 effective lines" in report.summary
        assert "Test Retina Verified: 2 passed" in report.summary
