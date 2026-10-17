# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Test Retina Runner: Sandbox execution and False-Exit-0 rejection guard.
(Card-Verify-MultiMetricGate - v1.5.06)

Derived from ByteDance Aspire (2026.06):
Guarantees that test suites are actually executed and passed.
Rejects False-Exit-0 scams:
1. Swallowing errors with exit code 0;
2. Marking all tests as @pytest.mark.skip;
3. Running empty test suites (collected 0 items);
4. Premature test runner exits.
"""

from dataclasses import dataclass
import os
import re
import subprocess
import time
from typing import Optional, Tuple


@dataclass(frozen=True)
class TestRetinaResult:
    """Immutable outcome of test retina execution."""
    is_valid: bool
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_sec: float
    exit_code: int
    command: str
    rejection_reason: Optional[str] = None
    output_snippet: str = ""


class TestRetinaRunner:
    """
    Executes unit/integration tests in a sandboxed subprocess and validates real test metrics.
    Blocks any test run where passed == 0 or where tests were skipped/swallowed.
    """

    __test__ = False  # Prevent pytest from miscollecting this runner class as test suite

    RE_PASSED = re.compile(r"(\d+)\s+passed", re.IGNORECASE)
    RE_FAILED = re.compile(r"(\d+)\s+failed", re.IGNORECASE)
    RE_SKIPPED = re.compile(r"(\d+)\s+skipped", re.IGNORECASE)
    RE_ERRORS = re.compile(r"(\d+)\s+error(?:s)?", re.IGNORECASE)
    RE_DURATION = re.compile(r"in\s+([\d\.]+)s", re.IGNORECASE)
    RE_GENERIC_TESTS = re.compile(r"(?:Tests|Passes|Completed):\s+(\d+)\s+passed", re.IGNORECASE)

    def __init__(self, timeout_sec: float = 60.0) -> None:
        self.timeout_sec = max(5.0, timeout_sec)

    @classmethod
    def parse_test_output(cls, output: str) -> Tuple[int, int, int, int, float]:
        """
        Parses test output to extract (passed, failed, skipped, errors, duration_sec).
        Uses modular pattern matching over summary lines for maximum format tolerance.
        """
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        duration = 0.0

        for line in reversed(output.splitlines()):
            lower = line.lower()
            # Check for pytest or standard summary line
            if any(k in lower for k in ("passed", "failed", "skipped", "error")):
                found_metric = False
                m_pass = cls.RE_PASSED.search(line)
                if m_pass:
                    passed = int(m_pass.group(1))
                    found_metric = True

                m_fail = cls.RE_FAILED.search(line)
                if m_fail:
                    failed = int(m_fail.group(1))
                    found_metric = True

                m_skip = cls.RE_SKIPPED.search(line)
                if m_skip:
                    skipped = int(m_skip.group(1))
                    found_metric = True

                m_err = cls.RE_ERRORS.search(line)
                if m_err:
                    errors = int(m_err.group(1))
                    found_metric = True

                m_dur = cls.RE_DURATION.search(line)
                if m_dur:
                    duration = float(m_dur.group(1))

                if found_metric:
                    return passed, failed, skipped, errors, duration

            gm = cls.RE_GENERIC_TESTS.search(line)
            if gm:
                passed = int(gm.group(1))
                return passed, 0, 0, 0, 0.0

        # Check for individual test dots/markers if no summary found
        # (fallback: counts "tests/... PASSED" or "... ok")
        pytest_passed_lines = len(re.findall(r"\bPASSED\b|\.\.\.\s*ok\b", output))
        if pytest_passed_lines > 0:
            passed = pytest_passed_lines

        return passed, failed, skipped, errors, duration

    def run_tests(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> TestRetinaResult:
        """
        Executes the test command synchronously within timeout, parsing true metrics.
        """
        effective_timeout = timeout or self.timeout_sec
        start_time = time.monotonic()
        work_dir = cwd or os.getcwd()

        try:
            proc = subprocess.run(
                command,
                cwd=work_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
            )
            elapsed = time.monotonic() - start_time
            combined_output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            return TestRetinaResult(
                is_valid=False,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                duration_sec=effective_timeout,
                exit_code=-1,
                command=command,
                rejection_reason=f"Test execution timed out after {effective_timeout:.1f}s",
                output_snippet="[TimeoutExpired]",
            )
        except Exception as e:
            return TestRetinaResult(
                is_valid=False,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                duration_sec=time.monotonic() - start_time,
                exit_code=-1,
                command=command,
                rejection_reason=f"Subprocess launch error: {e}",
                output_snippet=str(e),
            )

        passed, failed, skipped, errors, parsed_duration = self.parse_test_output(combined_output)
        actual_duration = parsed_duration if parsed_duration > 0 else elapsed

        # Extract last 8 lines as snippet
        lines = [ln for ln in combined_output.splitlines() if ln.strip()]
        snippet = "\n".join(lines[-8:]) if lines else ""

        # False Exit 0 & Goodhart Law defense assertions
        if exit_code != 0:
            return TestRetinaResult(
                is_valid=False,
                passed=passed,
                failed=max(1, failed),
                skipped=skipped,
                errors=errors,
                duration_sec=actual_duration,
                exit_code=exit_code,
                command=command,
                rejection_reason=f"Test suite failed with non-zero exit code ({exit_code}).",
                output_snippet=snippet,
            )

        if failed > 0 or errors > 0:
            return TestRetinaResult(
                is_valid=False,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration_sec=actual_duration,
                exit_code=exit_code,
                command=command,
                rejection_reason=f"Test failures detected: {failed} failed, {errors} errors.",
                output_snippet=snippet,
            )

        if passed == 0:
            return TestRetinaResult(
                is_valid=False,
                passed=0,
                failed=0,
                skipped=skipped,
                errors=0,
                duration_sec=actual_duration,
                exit_code=exit_code,
                command=command,
                rejection_reason=(
                    f"False Exit 0 rejected: 0 passed tests detected "
                    f"(all skipped={skipped} or empty test suite). Genuine assertion required."
                ),
                output_snippet=snippet,
            )

        return TestRetinaResult(
            is_valid=True,
            passed=passed,
            failed=0,
            skipped=skipped,
            errors=0,
            duration_sec=actual_duration,
            exit_code=0,
            command=command,
            output_snippet=snippet,
        )
