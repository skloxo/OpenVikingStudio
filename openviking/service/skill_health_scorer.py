# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Health Scorer & Auto-Remediation Generator (SSOT).

Comprehensive health scoring and deterministic patch generator for agent skills:
1. Multi-factor holistic health scoring (Specification, Actionability, Security Hygiene, Attention & Boundary)
2. Defect diagnosis and prioritized issues taxonomy (CRITICAL, WARNING, INFO)
3. Zero-side-effect auto-remediation patch and draft generation
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml

from openviking.service.skill_health_types import (
    HealthCategoryScore,
    HealthIssue,
    HealthStatus,
    IssueSeverity,
    SkillHealthReport,
    SkillRemediationResult,
)


_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_STEP_PATTERN = re.compile(r"(?m)^\s*(?:(?:\d+\.)|(?:Step\s*\d+:?)|(?:第[一二三四五六七八九十0-9]+步))", re.IGNORECASE)
_TOOL_MENTION_PATTERN = re.compile(r"\b(?:openviking_[a-z0-9_]+|find|search|read|write|replace_file_content|run_command)\b")
_SECRET_PATTERN = re.compile(r"\b(?:sk-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{20,}|eyJ[a-zA-Z0-9_-]{30,})\b")
_DESTRUCTIVE_CMD_PATTERN = re.compile(r"\b(?:rm\s+-(?:rf|fr)\s+/(?:\s|$|\*)|mkfs\.[a-z0-9]+\b|dd\s+if=/dev/(?:zero|urandom)\s+of=/dev/[a-z]+)")
_BOUNDARY_PATTERNS = ["when not to use", "do not", "边界约束", "负向判定", "严禁", "禁止"]
_IO_KEYWORDS = ("input", "output", "参数", "返回值", "交付物", "assert", "断言", "result", "schema")


class SkillHealthScorer:
    """Zero-side-effect static Skill Health evaluation engine."""

    @classmethod
    def calculate_health(cls, raw_content: str, skill_slug: Optional[str] = None) -> SkillHealthReport:
        lines = raw_content.splitlines() if raw_content else []
        line_count = len(lines)
        slug = skill_slug or "unnamed-skill"

        if not raw_content or not raw_content.strip():
            crit_issue = HealthIssue(
                category="specification",
                severity=IssueSeverity.CRITICAL,
                message="Raw skill content is completely empty.",
                remediation_hint="Provide standard SKILL.md content with frontmatter and body.",
            )
            return SkillHealthReport(
                skill_slug=slug,
                health_score=0.0,
                status=HealthStatus.CRITICAL,
                categories={},
                issues=[crit_issue],
                passed_gate=False,
                line_count=0,
            )

        fm, body = cls._parse_frontmatter(raw_content)
        if fm.get("name") and isinstance(fm["name"], str):
            slug = fm["name"].strip()

        issues: List[HealthIssue] = []

        # 1. Specification (0 ~ 25)
        cat_spec = cls._eval_spec(fm, slug, issues)

        # 2. Actionability (0 ~ 25)
        cat_action = cls._eval_actionability(body, fm, issues)

        # 3. Security Hygiene (0 ~ 25)
        cat_sec = cls._eval_security(raw_content, issues)

        # 4. Attention & Boundary (0 ~ 25)
        cat_attn = cls._eval_attention_boundary(lines, body, issues)

        categories = {
            "specification": cat_spec,
            "actionability": cat_action,
            "security_hygiene": cat_sec,
            "attention_boundary": cat_attn,
        }

        total_score = round(cat_spec.score + cat_action.score + cat_sec.score + cat_attn.score, 2)
        has_critical = any(i.severity == IssueSeverity.CRITICAL for i in issues)

        if total_score >= 85.0 and not has_critical:
            status = HealthStatus.HEALTHY
        elif total_score >= 70.0 and not has_critical:
            status = HealthStatus.STABLE
        elif total_score >= 50.0 and not has_critical:
            status = HealthStatus.NEEDS_REMEDIATION
        else:
            status = HealthStatus.CRITICAL

        passed_gate = (total_score >= 70.0) and not has_critical

        return SkillHealthReport(
            skill_slug=slug,
            health_score=total_score,
            status=status,
            categories=categories,
            issues=issues,
            passed_gate=passed_gate,
            line_count=line_count,
        )

    @staticmethod
    def _parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return {}, content
        fm_text, body = match.group(1), match.group(2)
        try:
            parsed = yaml.safe_load(fm_text)
            return (parsed if isinstance(parsed, dict) else {}), body
        except Exception:
            return {}, body

    @classmethod
    def _eval_spec(cls, fm: Dict[str, Any], slug: str, issues: List[HealthIssue]) -> HealthCategoryScore:
        score = 0.0
        details: List[str] = []

        if fm:
            score += 10.0
            details.append("YAML frontmatter properly parsed (+10).")
        else:
            details.append("Missing or malformed YAML frontmatter (-10).")
            issues.append(HealthIssue(
                category="specification",
                severity=IssueSeverity.CRITICAL,
                message="Missing or unparseable YAML frontmatter.",
                remediation_hint="Enclose valid YAML metadata between '---' separators at top of file.",
            ))

        name = fm.get("name", "")
        if name and isinstance(name, str) and _SLUG_PATTERN.match(name.strip()):
            score += 5.0
            details.append(f"Skill name '{name}' adheres to kebab-case slug convention (+5).")
        else:
            details.append("Skill name missing or invalid format (-5).")
            issues.append(HealthIssue(
                category="specification",
                severity=IssueSeverity.WARNING,
                message=f"Skill name '{name}' is missing or does not match kebab-case format.",
                remediation_hint="Set 'name: skill-name-slug' using lowercase letters, numbers, and hyphens.",
            ))

        desc = fm.get("description", "")
        if desc and isinstance(desc, str) and len(desc.strip()) >= 15:
            score += 5.0
            details.append("Description is sufficiently detailed (+5).")
        else:
            details.append("Description is missing or too concise (< 15 chars) (-5).")
            issues.append(HealthIssue(
                category="specification",
                severity=IssueSeverity.WARNING,
                message="Skill description is missing or too brief.",
                remediation_hint="Provide a descriptive 'description' explaining primary use cases and keywords.",
            ))

        tools = fm.get("allowed-tools") or fm.get("tools")
        if isinstance(tools, list) and len(tools) > 0:
            score += 5.0
            details.append(f"Explicitly declared {len(tools)} allowed tools (+5).")
        else:
            details.append("No explicit tools declared in frontmatter.")
            issues.append(HealthIssue(
                category="specification",
                severity=IssueSeverity.INFO,
                message="Frontmatter does not declare allowed-tools or tools list.",
                remediation_hint="Specify 'allowed-tools: [...]' to define tool invocation boundaries.",
            ))

        status = "good" if score >= 20.0 else ("warning" if score >= 12.0 else "critical")
        return HealthCategoryScore(category="specification", label="规范与元数据", score=score, status=status, details=details)

    @classmethod
    def _eval_actionability(cls, body: str, fm: Dict[str, Any], issues: List[HealthIssue]) -> HealthCategoryScore:
        score = 0.0
        details: List[str] = []

        step_matches = _STEP_PATTERN.findall(body)
        step_count = len(step_matches)
        if step_count >= 3:
            score += 12.0
            details.append(f"High actionability with {step_count} numbered execution steps (+12).")
        elif step_count >= 1:
            score += 6.0
            details.append(f"Moderate actionability ({step_count} steps detected) (+6).")
            issues.append(HealthIssue(
                category="actionability",
                severity=IssueSeverity.INFO,
                message=f"Only {step_count} execution steps detected.",
                remediation_hint="Decompose workflow into at least 3 distinct sequential steps.",
            ))
        else:
            details.append("No structured numbered steps detected.")
            issues.append(HealthIssue(
                category="actionability",
                severity=IssueSeverity.WARNING,
                message="SOP body lacks structured numbered steps.",
                remediation_hint="Add numbered steps (e.g., '1.', 'Step 1:', '第一步') for unambiguous execution.",
            ))

        has_code = "```" in body
        tool_mentions = _TOOL_MENTION_PATTERN.findall(body)
        if has_code or tool_mentions:
            score += 7.0
            details.append("Explicit code blocks or tool invocation references present (+7).")
        else:
            details.append("Lacks code blocks or explicit tool invocation examples.")
            issues.append(HealthIssue(
                category="actionability",
                severity=IssueSeverity.WARNING,
                message="No executable code blocks or tool calls in body.",
                remediation_hint="Include executable examples inside fenced markdown code blocks.",
            ))

        lower_body = body.lower()
        matched_io = [kw for kw in _IO_KEYWORDS if kw in lower_body]
        if len(matched_io) >= 2:
            score += 6.0
            details.append(f"Strong I/O delivery assertions ({', '.join(matched_io[:3])}) (+6).")
        elif len(matched_io) == 1:
            score += 3.0
            details.append("Partial I/O deliverables specified (+3).")
        else:
            details.append("No explicit input/output or delivery criteria defined.")
            issues.append(HealthIssue(
                category="actionability",
                severity=IssueSeverity.INFO,
                message="Lacks explicit inputs, outputs, or test assertions.",
                remediation_hint="Define input preconditions and measurable delivery outcomes.",
            ))

        status = "good" if score >= 20.0 else ("warning" if score >= 12.0 else "critical")
        return HealthCategoryScore(category="actionability", label="执行步骤与工效", score=score, status=status, details=details)

    @classmethod
    def _eval_security(cls, raw_content: str, issues: List[HealthIssue]) -> HealthCategoryScore:
        score = 0.0
        details: List[str] = []

        secret_matches = _SECRET_PATTERN.findall(raw_content)
        if not secret_matches:
            score += 15.0
            details.append("No raw credentials or unmasked API keys detected (+15).")
        else:
            details.append(f"Detected {len(secret_matches)} raw unmasked credentials/tokens (-15).")
            issues.append(HealthIssue(
                category="security",
                severity=IssueSeverity.CRITICAL,
                message=f"Raw credential or sensitive token detected: {secret_matches[0][:8]}...",
                remediation_hint="Replace raw secrets with environment variables or redacted placeholders.",
            ))

        destructive_matches = _DESTRUCTIVE_CMD_PATTERN.findall(raw_content)
        if not destructive_matches:
            score += 10.0
            details.append("No un-scoped destructive shell commands found (+10).")
        else:
            details.append(f"Detected hazardous destructive command pattern: {destructive_matches[0]} (-10).")
            issues.append(HealthIssue(
                category="security",
                severity=IssueSeverity.CRITICAL,
                message=f"Un-scoped destructive command detected: '{destructive_matches[0]}'.",
                remediation_hint="Remove un-scoped destructive operations or wrap them with safety dry-run guards.",
            ))

        status = "good" if score == 25.0 else "critical"
        return HealthCategoryScore(category="security_hygiene", label="安全卫生与凭据防线", score=score, status=status, details=details)

    @classmethod
    def _eval_attention_boundary(cls, lines: List[str], body: str, issues: List[HealthIssue]) -> HealthCategoryScore:
        score = 0.0
        details: List[str] = []
        n = len(lines)

        if 100 <= n <= 300:
            score += 15.0
            details.append(f"Line count ({n}) is inside the 100~300 golden sweet spot (+15).")
        elif (50 <= n < 100) or (301 <= n <= 400):
            score += 10.0
            details.append(f"Line count ({n}) is in acceptable range (+10).")
        elif 401 <= n <= 500:
            score += 4.0
            details.append(f"Line count ({n}) is approaching the 500-line hard limit (+4).")
            issues.append(HealthIssue(
                category="attention_budget",
                severity=IssueSeverity.WARNING,
                message=f"Skill length ({n} lines) approaches the 500-line ceiling.",
                remediation_hint="Identify domain seams and split sub-skills to remain in 100~300 sweet spot.",
            ))
        elif n > 500:
            details.append(f"Line count ({n}) exceeds the 500-line physical hard ceiling (-15).")
            issues.append(HealthIssue(
                category="attention_budget",
                severity=IssueSeverity.CRITICAL,
                message=f"Skill size ({n} lines) violates the <= 500 lines physical hard limit.",
                remediation_hint="Mandatory modular decomposition: factor out sub-modules to comply with single-file limits.",
            ))
        else:
            score += 5.0
            details.append(f"Line count ({n}) is sparse (< 50 lines) (+5).")
            issues.append(HealthIssue(
                category="attention_budget",
                severity=IssueSeverity.INFO,
                message=f"Skill length ({n} lines) is brief.",
                remediation_hint="Expand operational guidance to at least 50~100 lines for agent autonomy.",
            ))

        has_boundary = any(re.search(pat, body, re.IGNORECASE) for pat in _BOUNDARY_PATTERNS)
        if has_boundary:
            score += 10.0
            details.append("Explicit negative boundary constraints present (+10).")
        else:
            details.append("Lacks explicit negative boundary rules (-10).")
            issues.append(HealthIssue(
                category="boundary",
                severity=IssueSeverity.WARNING,
                message="No negative boundary constraints (When NOT to use) specified.",
                remediation_hint="Add 'When NOT to use' constraints to avoid hallucinated tool calls.",
            ))

        status = "good" if score >= 20.0 else ("warning" if score >= 12.0 else "critical")
        return HealthCategoryScore(category="attention_boundary", label="注意力信噪比与边界约束", score=score, status=status, details=details)


class SkillRemediationGenerator:
    """Deterministic auto-remediation synthesis generator."""

    @classmethod
    def remediate(cls, raw_content: str, skill_slug: Optional[str] = None) -> SkillRemediationResult:
        original_report = SkillHealthScorer.calculate_health(raw_content, skill_slug)
        fm, body = SkillHealthScorer._parse_frontmatter(raw_content)

        applied_remediations: List[str] = []
        new_fm = dict(fm)

        # 1. Frontmatter remediation
        slug = skill_slug or new_fm.get("name") or "remediated-skill"
        if not new_fm.get("name") or not _SLUG_PATTERN.match(str(new_fm.get("name"))):
            safe_slug = re.sub(r"[^a-z0-9]+", "-", str(slug).lower()).strip("-") or "remediated-skill"
            new_fm["name"] = safe_slug
            applied_remediations.append(f"Normalized skill slug name to '{safe_slug}'")

        if not new_fm.get("description") or len(str(new_fm.get("description")).strip()) < 15:
            new_fm["description"] = f"Standardized operational skill for {new_fm.get('name')}, including clear triggers and boundaries."
            applied_remediations.append("Injected comprehensive description metadata")

        if not new_fm.get("allowed-tools") and not new_fm.get("tools"):
            new_fm["allowed-tools"] = ["find", "search", "read"]
            applied_remediations.append("Populated default allowed-tools contract")

        # 2. Body remediation
        new_body = body

        # Sanitize credentials
        secret_matches = _SECRET_PATTERN.findall(new_body)
        if secret_matches:
            for s in secret_matches:
                new_body = new_body.replace(s, "<REDACTED_API_KEY>")
            applied_remediations.append(f"Masked {len(secret_matches)} exposed raw credentials")

        # Boundary constraints
        has_boundary = any(re.search(pat, new_body, re.IGNORECASE) for pat in _BOUNDARY_PATTERNS)
        if not has_boundary:
            new_body = (
                f"{new_body.strip()}\n\n"
                "## 边界约束与负向判定 (Boundary Constraints)\n"
                "- **何时严禁使用**：当任务仅涉及非本领域常规问答，或已有底层专有指令时严禁调用；\n"
                "- **职责隔离**：超出本技能声明范围的诉求，必须立即阻断并移交对应领域代理处理。\n"
            )
            applied_remediations.append("Injected standard negative boundary constraints section")

        # Execution examples / SOP steps
        step_matches = _STEP_PATTERN.findall(new_body)
        if len(step_matches) < 2:
            new_body = (
                f"{new_body.strip()}\n\n"
                "## 标准执行工序 (Execution SOP)\n"
                "1. **环境前置探针**：调用底层探针校验输入参数与前置依赖；\n"
                "2. **核心业务处理**：按照规范执行目标操作，记录中间产物；\n"
                "3. **门禁与结果验真**：断言交付物完整度，完成闭环汇报。\n"
            )
            applied_remediations.append("Injected standard 3-step numbered execution SOP")

        if "```" not in new_body:
            new_body = (
                f"{new_body.strip()}\n\n"
                "## 典型执行示例 (Execution Examples)\n"
                "```bash\n"
                "# 标准执行与门禁检验命令\n"
                "pytest -q\n"
                "```\n"
            )
            applied_remediations.append("Injected standard markdown code block example")

        fm_yaml = yaml.dump(new_fm, allow_unicode=True, sort_keys=False).strip()
        remediated_content = f"---\n{fm_yaml}\n---\n\n{new_body.strip()}\n"

        projected_report = SkillHealthScorer.calculate_health(remediated_content, new_fm.get("name"))

        diff_summary = (
            f"原始健康度: {original_report.health_score:.1f}分 ({original_report.status.value}) ➔ "
            f"修复后提升至: {projected_report.health_score:.1f}分 ({projected_report.status.value}) "
            f"[{len(applied_remediations)} 项自动修复]"
        )

        return SkillRemediationResult(
            original_report=original_report,
            remediated_content=remediated_content,
            applied_remediations=applied_remediations,
            projected_health_score=projected_report.health_score,
            projected_status=projected_report.status,
            diff_summary=diff_summary,
        )
