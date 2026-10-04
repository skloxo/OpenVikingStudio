"""Skill Specification & YAML Frontmatter Validator (SSOT).

Provides strict static validation of SKILL.md documents:
1. Validates YAML Frontmatter boundaries (^--- ... ---)
2. Enforces mandatory fields: name (slug-compliant) and description
3. Verifies trigger definitions and structure
4. Inspects allowed-tools against registered FastMCP / native tool catalogs
5. Produces strongly-typed SkillValidationResult diagnostics
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
import yaml

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class SkillValidationResult:
    """Strongly-typed validation report for a SKILL.md draft."""

    is_valid: bool
    name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed_metadata: dict[str, Any] = field(default_factory=dict)
    body_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "name": self.name,
            "errors": self.errors,
            "warnings": self.warnings,
            "parsed_metadata": self.parsed_metadata,
            "body_length": self.body_length,
        }


class SkillValidator:
    """Zero-side-effect static validator for Skill-as-Code specifications."""

    # Default recognized tool set for ghost tool detection
    KNOWN_SYSTEM_TOOLS: frozenset[str] = frozenset({
        "find", "search", "read", "list", "tree", "remember", "write", "edit",
        "add_resource", "list_watches", "cancel_watch", "grep", "glob", "forget",
        "health", "zg_search", "openviking_task_cards_summary", "openviking_dlq_status",
        "openviking_resolve_task_card", "openviking_code_impact", "openviking_vector_sync_metrics",
        "openviking_generate_contract_test", "openviking_list_pending_cards", "openviking_file_task_card",
        "openviking_valet_handover", "openviking_valet_ticket_status", "openviking_dspy_compile",
        "openviking_skill_zip", "openviking_tokenshift_compress", "openviking_memory_purity_report",
        "openviking_retry_dead_letter", "openviking_context_route", "openviking_agent_sensors",
        "openviking_active_notes_get", "openviking_active_notes_update", "openviking_history_search",
        "openviking_privacy_mask", "openviking_skill_validate",
    })

    @classmethod
    def validate_content(cls, raw_text: str) -> SkillValidationResult:
        """Validates raw SKILL.md text content."""
        if not raw_text or not raw_text.strip():
            return SkillValidationResult(
                is_valid=False,
                name="",
                errors=["Content is empty. SKILL.md must contain YAML frontmatter and body."],
            )

        match = FRONTMATTER_PATTERN.match(raw_text.strip())
        if not match:
            return SkillValidationResult(
                is_valid=False,
                name="",
                errors=["Missing valid YAML frontmatter delimiters. Must start and enclose with '---'."],
            )

        frontmatter_str, body = match.groups()
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Parse YAML Frontmatter
        try:
            metadata = yaml.safe_load(frontmatter_str) or {}
            if not isinstance(metadata, dict):
                return SkillValidationResult(
                    is_valid=False,
                    name="",
                    errors=["Frontmatter must be a valid YAML key-value mapping."],
                )
        except yaml.YAMLError as exc:
            return SkillValidationResult(
                is_valid=False,
                name="",
                errors=[f"YAML parsing error: {exc}"],
            )

        # 2. Check 'name'
        name = str(metadata.get("name") or "").strip()
        if not name:
            errors.append("Mandatory field 'name' is missing or empty in frontmatter.")
        elif not SLUG_PATTERN.match(name):
            errors.append(f"Field 'name' ('{name}') must be a kebab-case slug (e.g. 'diagnosing-bugs').")

        # 3. Check 'description'
        description = str(metadata.get("description") or "").strip()
        if not description:
            errors.append("Mandatory field 'description' is missing or empty in frontmatter.")
        elif len(description) < 10:
            warnings.append("Description is very short (< 10 chars). Recommended to provide clear intent.")

        # 4. Check 'allowed-tools'
        allowed_tools = metadata.get("allowed-tools") or metadata.get("allowed_tools")
        if allowed_tools is not None:
            if not isinstance(allowed_tools, (list, tuple)):
                errors.append("Field 'allowed-tools' must be a sequence of tool names.")
            else:
                for tool in allowed_tools:
                    tool_name = str(tool).strip()
                    if tool_name not in cls.KNOWN_SYSTEM_TOOLS:
                        warnings.append(
                            f"Tool '{tool_name}' is not in standard registered tools catalog (possible ghost tool)."
                        )

        # 5. Check 'triggers'
        triggers = metadata.get("triggers")
        if triggers is not None and not isinstance(triggers, (list, tuple, str)):
            warnings.append("Field 'triggers' should be a list of natural language intent phrases.")

        # 6. Check body length
        body_len = len(body.strip())
        if body_len == 0:
            warnings.append("Skill body is empty. Recommended to include SOP instructions and guidelines.")

        is_valid = len(errors) == 0
        return SkillValidationResult(
            is_valid=is_valid,
            name=name,
            errors=errors,
            warnings=warnings,
            parsed_metadata=metadata,
            body_length=body_len,
        )


def validate_skill_content(raw_text: str) -> SkillValidationResult:
    """Convenience functional wrapper for SkillValidator.validate_content."""
    return SkillValidator.validate_content(raw_text)
