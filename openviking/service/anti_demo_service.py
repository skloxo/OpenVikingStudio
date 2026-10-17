# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Anti-Demo & Anti-Dangling Automated Retina Gate Service (Card-103 / v1.7.57).

Provides runtime telemetry, on-demand codebase audits, and monotonic-clock snapshot caching
for anti-demo and anti-dangling compliance.
"""

from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from scripts.anti_demo_gate import run_anti_demo_gate


class AntiDemoViolation(BaseModel):
    """Detailed violation found during anti-demo audit."""
    file: str
    rule: str
    line: int
    message: str


class AntiDemoAuditReport(BaseModel):
    """Overall audit report for anti-demo and anti-dangling compliance."""
    status: str
    scanned_components: int
    total_dangling_features_count: int
    anti_demo_gate_pass_rate: float
    violations: List[AntiDemoViolation] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
    cached: bool = False


class AntiDemoGateService:
    """Orchestrates on-demand audits with monotonic-clock快照 (15s TTL) to protect CPU."""

    _instance: Optional[AntiDemoGateService] = None
    _singleton_lock = threading.Lock()

    def __init__(self, repo_root: Optional[Path] = None, ttl_seconds: float = 15.0) -> None:
        self.repo_root = (
            repo_root.resolve()
            if repo_root
            else Path(__file__).resolve().parents[2]
        )
        self.ttl_seconds = ttl_seconds
        self._cached_report: Optional[AntiDemoAuditReport] = None
        self._last_audit_time: float = 0.0
        self._audit_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> AntiDemoGateService:
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def audit(self, force_refresh: bool = False) -> AntiDemoAuditReport:
        """Run audit or return cached snapshot if within TTL."""
        now = time.monotonic()
        with self._audit_lock:
            if not force_refresh and self._cached_report and (now - self._last_audit_time < self.ttl_seconds):
                cached_copy = self._cached_report.model_copy()
                cached_copy.cached = True
                return cached_copy

            raw_res = run_anti_demo_gate(repo_root=self.repo_root)
            violations = [
                AntiDemoViolation(
                    file=v["file"],
                    rule=v["rule"],
                    line=v["line"],
                    message=v["message"],
                )
                for v in raw_res.get("violations", [])
            ]

            report = AntiDemoAuditReport(
                status=raw_res.get("status", "PASS"),
                scanned_components=raw_res.get("scanned_components", 0),
                total_dangling_features_count=raw_res.get("total_dangling_features_count", 0),
                anti_demo_gate_pass_rate=raw_res.get("anti_demo_gate_pass_rate", 100.0),
                violations=violations,
                timestamp=time.time(),
                cached=False,
            )
            self._cached_report = report
            self._last_audit_time = now
            return report
