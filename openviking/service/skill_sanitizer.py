# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill ingestion sanitizer and scaffolding engine.

Ensures strict hygiene for Agent Skills:
1. Normalizes skill names to canonical kebab-case ASCII (1..64 chars).
2. Fixes or scaffolds missing SKILL.md and YAML frontmatter.
3. Prevents dirty directories or malformed entries from poisoning skill roots.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from openviking.utils.skill_processor import MAX_SKILL_NAME_LENGTH, validate_skill_name

# Regex for non-canonical characters in skill names (enforce canonical kebab-case)
_DISALLOWED_CHARS_RE = re.compile(r"[^a-zA-Z0-9\-]+")
_CONSECUTIVE_HYPHENS_RE = re.compile(r"-{2,}")
_DATE_ARCHIVE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}", re.IGNORECASE)


@dataclass
class SkillScaffoldResult:
    """Result of skill directory verification and auto-scaffolding."""

    skill_name: str
    is_valid: bool
    repaired: bool
    reason: str = ""
    skill_md_content: str = ""


class SkillSanitizer:
    """First-principles sanitizer for skill naming and directory scaffolding."""

    @staticmethod
    def sanitize_skill_name(raw_name: Any, default_prefix: str = "skill") -> str:
        """Sanitize an arbitrary skill name to canonical kebab-case ASCII.

        Guarantees:
        - Returned name 100% passes ``validate_skill_name``.
        - Replaces whitespace, dots, colons, slashes, and non-ASCII with hyphens.
        - Truncates to MAX_SKILL_NAME_LENGTH without trailing hyphens.
        """
        if raw_name is None:
            raw_str = ""
        else:
            raw_str = str(raw_name).strip()

        # Unicode normalization (NFKD decomposes characters with accents)
        normalized = unicodedata.normalize("NFKD", raw_str)
        # Encode to ascii ignoring unknown characters, or transliterate
        ascii_bytes = normalized.encode("ascii", "ignore")
        ascii_str = ascii_bytes.decode("ascii")

        # Replace invalid characters with hyphens
        sanitized = _DISALLOWED_CHARS_RE.sub("-", ascii_str)
        # Collapse multiple hyphens into one
        sanitized = _CONSECUTIVE_HYPHENS_RE.sub("-", sanitized)
        # Strip leading/trailing hyphens or underscores
        sanitized = sanitized.strip("-_").lower()

        # If empty (e.g. purely non-ASCII or whitespace), construct default
        if not sanitized:
            hash_suffix = (
                hex(abs(hash(raw_str)))[2:8] if raw_str else "000000"
            )
            sanitized = f"{default_prefix}-{hash_suffix}"

        # Enforce length constraints
        if len(sanitized) > MAX_SKILL_NAME_LENGTH:
            sanitized = sanitized[:MAX_SKILL_NAME_LENGTH].rstrip("-_")

        # Fallback safeguard in case truncation left it empty
        if not sanitized:
            sanitized = f"{default_prefix}-scaffold"

        # Verify against SSOT validator
        return validate_skill_name(sanitized)

    @staticmethod
    def is_anomalous_dir_name(dir_name: str) -> bool:
        """Check if a directory name is an internal or backup anomaly."""
        if not dir_name:
            return True
        clean = dir_name.strip()
        if clean.startswith(".") or clean.startswith("__"):
            return True
        if clean.endswith(".bak") or clean.endswith(".tmp"):
            return True
        if clean.startswith("backup-") or clean.startswith("curator-temp"):
            return True
        if _DATE_ARCHIVE_RE.match(clean):
            return True
        return False

    @staticmethod
    def parse_skill_markdown(content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter and body from a SKILL.md file."""
        if not content or not content.strip():
            return {}, ""

        stripped = content.strip()
        if not stripped.startswith("---"):
            return {}, stripped

        parts = stripped.split("---", 2)
        if len(parts) < 3:
            return {}, stripped

        yaml_text = parts[1].strip()
        body = parts[2].strip()

        try:
            parsed = yaml.safe_load(yaml_text)
            if isinstance(parsed, dict):
                return parsed, body
        except Exception:
            pass

        return {}, body

    @classmethod
    def generate_skill_scaffold(
        cls,
        skill_name: str,
        description: Optional[str] = None,
        existing_body: Optional[str] = None,
    ) -> str:
        """Generate a compliant SKILL.md string with YAML frontmatter."""
        canonical_name = cls.sanitize_skill_name(skill_name)
        desc = (
            description.strip()
            if description and description.strip()
            else f"Automated scaffold for {canonical_name}"
        )
        body = existing_body.strip() if existing_body else f"# {canonical_name}\n\n{desc}."

        frontmatter = {
            "name": canonical_name,
            "description": desc,
        }
        yaml_header = yaml.safe_dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).strip()

        return f"---\n{yaml_header}\n---\n\n{body}\n"

    @classmethod
    def verify_and_repair_skill_file(
        cls,
        skill_dir_name: str,
        skill_md_content: Optional[str],
    ) -> SkillScaffoldResult:
        """Verify SKILL.md content, repairing or scaffolding if incomplete."""
        canonical_name = cls.sanitize_skill_name(skill_dir_name)

        if not skill_md_content or not skill_md_content.strip():
            scaffold = cls.generate_skill_scaffold(canonical_name)
            return SkillScaffoldResult(
                skill_name=canonical_name,
                is_valid=True,
                repaired=True,
                reason="scaffolded_missing_skill_md",
                skill_md_content=scaffold,
            )

        meta, body = cls.parse_skill_markdown(skill_md_content)
        name_in_meta = meta.get("name") if isinstance(meta, dict) else None
        desc_in_meta = meta.get("description") if isinstance(meta, dict) else None

        needs_repair = False
        repaired_reason = []

        if not isinstance(name_in_meta, str) or not name_in_meta.strip():
            needs_repair = True
            repaired_reason.append("missing_name_in_frontmatter")
        else:
            try:
                validate_skill_name(name_in_meta.strip())
            except Exception:
                needs_repair = True
                repaired_reason.append("invalid_name_in_frontmatter")

        if not isinstance(desc_in_meta, str) or not desc_in_meta.strip():
            needs_repair = True
            repaired_reason.append("missing_description_in_frontmatter")

        if needs_repair:
            desc = desc_in_meta if isinstance(desc_in_meta, str) and desc_in_meta.strip() else None
            repaired_content = cls.generate_skill_scaffold(
                skill_name=canonical_name,
                description=desc,
                existing_body=body,
            )
            return SkillScaffoldResult(
                skill_name=canonical_name,
                is_valid=True,
                repaired=True,
                reason="; ".join(repaired_reason),
                skill_md_content=repaired_content,
            )

        return SkillScaffoldResult(
            skill_name=canonical_name,
            is_valid=True,
            repaired=False,
            reason="valid_skill_md",
            skill_md_content=skill_md_content,
        )
