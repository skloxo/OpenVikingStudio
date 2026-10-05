# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Deterministic Ingestion Gatekeeper & Static Environment Verifier (Card-94).

Provides 100% deterministic physical static verification before skills enter the vault:
1. YAML Frontmatter v2.0 schema and contract validation
2. Single-file line count physical limits (sweet spot <= 300, hard cap <= 500)
3. AST Python security scanning for dangerous syscalls (os.system, subprocess, eval)
4. Local CLI and environment reachability checks
5. FastMCP ghost tool interception
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from enum import Enum
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional
import yaml


class ValidationSeverity(str, Enum):
    FATAL = "FATAL"
    SECURITY = "SECURITY"
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class ValidationViolation:
    severity: ValidationSeverity
    field: str
    message: str
    remediation: str


@dataclass
class ValidationReceipt:
    is_valid: bool
    status: str  # "APPROVED" | "REJECTED"
    skill_name: str
    version: str
    domain: str
    violations: List[ValidationViolation] = field(default_factory=list)
    line_count: int = 0
    latency_ms: float = 0.0

    @property
    def critical_violations(self) -> List[ValidationViolation]:
        return [
            v for v in self.violations
            if v.severity in (ValidationSeverity.FATAL, ValidationSeverity.SECURITY, ValidationSeverity.ERROR)
        ]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["violations"] = [
            {
                "severity": v.severity.value if isinstance(v.severity, ValidationSeverity) else str(v.severity),
                "field": v.field,
                "message": v.message,
                "remediation": v.remediation,
            }
            for v in self.violations
        ]
        return data


# Whitelist of standard builtin tools and OpenViking MCP tools
STANDARD_ALLOWED_TOOLS = {
    "openviking_find", "openviking_search", "openviking_read", "openviking_write",
    "openviking_store", "openviking_commit", "openviking_skills", "openviking_code_search",
    "openviking_code_outline", "openviking_grep", "openviking_glob", "openviking_ls",
    "openviking_tree", "openviking_mv", "openviking_rename", "openviking_tag",
    "openviking_diff", "openviking_health", "openviking_metrics", "openviking_valet_handover",
    "find", "search", "read", "write", "run_command", "view_file", "write_to_file",
    "replace_file_content", "grep_search", "list_dir", "read_url_content", "web_search",
}


class SkillIngestionValidator:
    """Deterministic, pure-python static validator for new skills."""

    KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    SEMVER_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
    PYTHON_BLOCK_RE = re.compile(r"```python\s*([\s\S]*?)```", re.IGNORECASE)

    def validate(self, content: str, filename: str = "SKILL.md") -> ValidationReceipt:
        t0 = time.perf_counter()
        violations: List[ValidationViolation] = []
        lines = content.splitlines()
        line_count = len(lines)

        # 1. Physical file size check
        if line_count > 500:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.FATAL,
                    field="file_size",
                    message=f"Skill file length ({line_count} lines) exceeds 500 lines physical red line.",
                    remediation="Split this skill into a domain package with subskills or reduce redundancy.",
                )
            )
        elif line_count > 300:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.WARNING,
                    field="file_size",
                    message=f"Skill file length ({line_count} lines) exceeds 300 lines sweet spot.",
                    remediation="Refactor procedures into modular sub-files to improve agent attention.",
                )
            )

        # 2. YAML Frontmatter check
        if not content.startswith("---"):
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.FATAL,
                    field="frontmatter",
                    message="Missing opening YAML Frontmatter delimiter ('---').",
                    remediation="Ensure SKILL.md starts with '---' containing name, version, triggers, etc.",
                )
            )
            return self._build_receipt(False, "unknown", "", "", violations, line_count, t0)

        parts = content.split("---", 2)
        if len(parts) < 3:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.FATAL,
                    field="frontmatter",
                    message="Missing closing YAML Frontmatter delimiter ('---').",
                    remediation="Close the YAML Frontmatter header with '---'.",
                )
            )
            return self._build_receipt(False, "unknown", "", "", violations, line_count, t0)

        try:
            fm: Dict[str, Any] = yaml.safe_load(parts[1]) or {}
        except Exception as e:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.FATAL,
                    field="frontmatter_syntax",
                    message=f"YAML syntax parsing error: {e}",
                    remediation="Check indentation and syntax in YAML Frontmatter.",
                )
            )
            return self._build_receipt(False, "unknown", "", "", violations, line_count, t0)

        skill_name = str(fm.get("name") or "").strip()
        version = str(fm.get("version") or "1.0.0").strip()
        domain = str(fm.get("domain") or "").strip()
        description = str(fm.get("description") or "").strip()
        triggers = fm.get("triggers") or []
        allowed_tools = fm.get("allowed-tools") or fm.get("tools") or []

        # Name checks
        if not skill_name:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.ERROR,
                    field="name",
                    message="Field 'name' is required in Frontmatter.",
                    remediation="Specify a non-empty 'name' field.",
                )
            )
        elif not self.KEBAB_CASE_RE.match(skill_name):
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.ERROR,
                    field="name",
                    message=f"Skill name '{skill_name}' must strictly follow kebab-case (lowercase and hyphens only).",
                    remediation=f"Rename to '{skill_name.lower().replace('_', '-')}' without uppercase or spaces.",
                )
            )

        # Triggers checks
        if not isinstance(triggers, list) or len(triggers) < 3:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.ERROR,
                    field="triggers",
                    message=f"Field 'triggers' must be a list containing at least 3 intent phrases (found {len(triggers) if isinstance(triggers, list) else 0}).",
                    remediation="Provide at least 3 concrete natural language trigger phrases.",
                )
            )

        # Allowed tools & Ghost tools checks
        if not isinstance(allowed_tools, list) or len(allowed_tools) == 0:
            violations.append(
                ValidationViolation(
                    severity=ValidationSeverity.WARNING,
                    field="allowed-tools",
                    message="Field 'allowed-tools' is empty. Default read-only tools will be assigned.",
                    remediation="Explicitly specify which tools this skill needs to execute.",
                )
            )
        else:
            for t in allowed_tools:
                if isinstance(t, str):
                    is_valid_tool = (
                        t in STANDARD_ALLOWED_TOOLS
                        or t.startswith("openviking_")
                        or t.startswith("mcp_")
                    )
                    if not is_valid_tool:
                        violations.append(
                            ValidationViolation(
                                severity=ValidationSeverity.ERROR,
                                field="allowed-tools",
                                message=f"Unregistered ghost tool detected: '{t}'. Tool does not exist in registry.",
                                remediation=f"Remove '{t}' or register the corresponding FastMCP server first.",
                            )
                        )

        # 3. Prerequisites reachability checks
        prereqs = fm.get("prerequisites") or {}
        if isinstance(prereqs, dict):
            for cli_cmd in (prereqs.get("cli") or []):
                if isinstance(cli_cmd, str) and not shutil.which(cli_cmd):
                    violations.append(
                        ValidationViolation(
                            severity=ValidationSeverity.WARNING,
                            field="prerequisites.cli",
                            message=f"Required CLI binary '{cli_cmd}' not found on system PATH.",
                            remediation=f"Ensure '{cli_cmd}' is installed on the host or satellite node.",
                        )
                    )
            for env_var in (prereqs.get("env") or []):
                if isinstance(env_var, str) and env_var not in os.environ:
                    violations.append(
                        ValidationViolation(
                            severity=ValidationSeverity.WARNING,
                            field="prerequisites.env",
                            message=f"Required Environment variable '{env_var}' is currently unset.",
                            remediation=f"Export '{env_var}' in environment before executing this skill.",
                        )
                    )

        # 4. AST Python Code Security Scanning
        body = parts[2]
        self._scan_ast_security(body, violations)

        is_valid = len([v for v in violations if v.severity in (ValidationSeverity.FATAL, ValidationSeverity.SECURITY, ValidationSeverity.ERROR)]) == 0
        return self._build_receipt(is_valid, skill_name, version, domain, violations, line_count, t0)

    def _scan_ast_security(self, body: str, violations: List[ValidationViolation]) -> None:
        for match in self.PYTHON_BLOCK_RE.finditer(body):
            code_block = match.group(1)
            try:
                tree = ast.parse(code_block)
            except Exception:
                continue

            for node in ast.walk(tree):
                # Call checks: os.system, subprocess.*, eval, exec
                if isinstance(node, ast.Call):
                    func_name = self._resolve_call_name(node.func)
                    if func_name in ("os.system", "eval", "exec"):
                        violations.append(
                            ValidationViolation(
                                severity=ValidationSeverity.SECURITY,
                                field="code_security",
                                message=f"Dangerous system call detected in python block: '{func_name}'.",
                                remediation="Use controlled MCP tools or safe subprocess execution instead of raw os.system/eval.",
                            )
                        )
                    elif func_name and func_name.startswith("subprocess."):
                        violations.append(
                            ValidationViolation(
                                severity=ValidationSeverity.SECURITY,
                                field="code_security",
                                message=f"Direct subprocess invocation detected: '{func_name}'.",
                                remediation="Encapsulate shell operations within controlled run_command tools.",
                            )
                        )

    def _resolve_call_name(self, func_node: ast.AST) -> str:
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            val = self._resolve_call_name(func_node.value)
            return f"{val}.{func_node.attr}" if val else func_node.attr
        return ""

    def _build_receipt(
        self,
        is_valid: bool,
        name: str,
        version: str,
        domain: str,
        violations: List[ValidationViolation],
        line_count: int,
        t0: float,
    ) -> ValidationReceipt:
        status = "APPROVED" if is_valid else "REJECTED"
        latency = (time.perf_counter() - t0) * 1000
        return ValidationReceipt(
            is_valid=is_valid,
            status=status,
            skill_name=name or "unnamed",
            version=version or "1.0.0",
            domain=domain or "general",
            violations=violations,
            line_count=line_count,
            latency_ms=round(latency, 2),
        )
