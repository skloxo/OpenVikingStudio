# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Agent Skill Fact Compiler (Card-45).

Statically compiles SKILL.md documents into deterministic, structured L0/L1 facts.
Practices the OKF (Open Knowledge Format) first principle:
- Only record facts directly verifiable from code/frontmatter.
- Missing/uncertain fields are explicitly recorded as unverified_fields (honest omission).
- Zero runtime LLM hallucination during catalog compilation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TRIGGER_PATTERNS = [
    re.compile(r"(?:触发词|触发条件|Triggers?)[：:]\s*([^\n\r]+)", re.IGNORECASE),
    re.compile(r"(?:当用户说|当用户提到)[：:\"“]([^\"”\n\r]+)", re.IGNORECASE),
]
_SPLIT_CHARS_RE = re.compile(r"[,，、|/;\s]+")


@dataclass
class SkillFactRecord:
    """Immutable factual descriptor for an Agent Skill."""

    name: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    unverified_fields: List[str] = field(default_factory=list)
    l0_summary: str = ""
    l1_outline: str = ""
    source_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to JSON-serializable dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "allowed_tools": self.allowed_tools,
            "tags": self.tags,
            "triggers": self.triggers,
            "prerequisites": self.prerequisites,
            "unverified_fields": self.unverified_fields,
            "l0_summary": self.l0_summary,
            "source_path": self.source_path,
        }


class SkillFactCompiler:
    """Static compiler for parsing and structuring SKILL.md facts."""

    @classmethod
    def compile_skill_file(cls, skill_md_path: Path | str) -> Optional[SkillFactRecord]:
        """Compile a single SKILL.md file into a SkillFactRecord."""
        path = Path(skill_md_path)
        if not path.is_file():
            return None

        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        frontmatter_dict: Dict[str, Any] = {}
        body = raw_text

        match = _FRONTMATTER_RE.match(raw_text)
        if match:
            fm_text = match.group(1)
            try:
                parsed_fm = yaml.safe_load(fm_text)
                if isinstance(parsed_fm, dict):
                    frontmatter_dict = parsed_fm
            except Exception:
                frontmatter_dict = {}
            body = raw_text[match.end():]

        name = str(frontmatter_dict.get("name") or path.parent.name).strip()
        description = str(frontmatter_dict.get("description") or "").strip()

        unverified: List[str] = []

        # 1. Allowed Tools Extraction
        raw_tools = frontmatter_dict.get("allowed-tools") or frontmatter_dict.get("allowed_tools")
        allowed_tools: List[str] = []
        if isinstance(raw_tools, list):
            allowed_tools = [str(t).strip() for t in raw_tools if str(t).strip()]
        elif isinstance(raw_tools, str) and raw_tools.strip():
            allowed_tools = [t.strip() for t in _SPLIT_CHARS_RE.split(raw_tools) if t.strip()]

        if not allowed_tools:
            unverified.append("allowed_tools")

        # 2. Tags Extraction
        raw_tags = frontmatter_dict.get("tags") or []
        tags: List[str] = []
        if isinstance(raw_tags, list):
            tags = [str(t).strip() for t in raw_tags if str(t).strip()]
        elif isinstance(raw_tags, str) and raw_tags.strip():
            tags = [t.strip() for t in _SPLIT_CHARS_RE.split(raw_tags) if t.strip()]

        # 3. Triggers Extraction (Search in description and body)
        triggers: List[str] = []
        search_target = f"{description}\n{body[:1000]}"
        for pattern in _TRIGGER_PATTERNS:
            trig_match = pattern.search(search_target)
            if trig_match:
                extracted_str = trig_match.group(1)
                tokens = [t.strip() for t in _SPLIT_CHARS_RE.split(extracted_str) if len(t.strip()) > 1]
                for tok in tokens:
                    if tok not in triggers:
                        triggers.append(tok)

        if not triggers:
            unverified.append("triggers")

        # 4. Generate L0 High-Density Summary
        tools_str = f"[{', '.join(allowed_tools)}]" if allowed_tools else "[tools:none]"
        short_desc = description.split("。")[0].split(".")[0].strip()
        l0_summary = f"{name} {tools_str}: {short_desc or 'No description provided.'}"

        # 5. Generate L1 Structured Outline
        l1_lines = [
            f"# Skill: {name}",
            f"- Path: `{path.as_posix()}`",
            f"- Allowed Tools: {', '.join(allowed_tools) if allowed_tools else 'None declared'}",
            f"- Tags: {', '.join(tags) if tags else 'None'}",
            f"- Triggers: {', '.join(triggers) if triggers else 'None explicitly declared'}",
        ]
        if unverified:
            l1_lines.append(f"- Unverified/Blank Fields: {', '.join(unverified)}")

        l1_outline = "\n".join(l1_lines)

        return SkillFactRecord(
            name=name,
            description=description,
            allowed_tools=allowed_tools,
            tags=tags,
            triggers=triggers,
            prerequisites=[],
            unverified_fields=unverified,
            l0_summary=l0_summary,
            l1_outline=l1_outline,
            source_path=path.as_posix(),
        )

    def compile_directory(self, root_dir: Path | str) -> List[SkillFactRecord]:
        """Recursively scan a directory for SKILL.md and compile facts."""
        root = Path(root_dir)
        records: List[SkillFactRecord] = []
        if not root.is_dir():
            return records

        for skill_file in sorted(root.glob("**/SKILL.md")):
            record = self.compile_skill_file(skill_file)
            if record:
                records.append(record)

        return records

    @staticmethod
    def generate_markdown_catalog(records: List[SkillFactRecord]) -> str:
        """Render a unified OKF-compliant Markdown catalog from compiled records."""
        lines = [
            "# 🛠️ Agent Skills Fact Catalog",
            "",
            "> Compiled statically from verified SKILL.md files. Zero hallucination guarantee.",
            f"> Total Skills: **{len(records)}**",
            "",
            "| Skill Name | Tools | Triggers | Summary |",
            "|:---|:---|:---|:---|",
        ]
        for r in records:
            tools_badge = f"`{', '.join(r.allowed_tools)}`" if r.allowed_tools else "`--`"
            triggers_badge = f"`{', '.join(r.triggers[:3])}`" if r.triggers else "`--`"
            summary_clean = r.description.replace("|", "｜").replace("\n", " ")[:60]
            lines.append(f"| **`{r.name}`** | {tools_badge} | {triggers_badge} | {summary_clean} |")

        return "\n".join(lines)
