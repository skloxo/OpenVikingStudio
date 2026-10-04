# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Reverse Impact Topology Builder (Card-46).

Extracts and models reverse dependency relationships:
1. SQLite storage tables to their readers and writers (blast-radius analysis).
2. Tools to agent skills inverted mapping (which skills break if a tool changes).
3. Skill trigger collision detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from openviking.service.skill_fact_compiler import SkillFactRecord


_SQL_WRITE_PATTERNS = [
    re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
    re.compile(r"UPDATE\s+([a-zA-Z0-9_]+)\s+SET", re.IGNORECASE),
    re.compile(r"DELETE\s+FROM\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
]
_SQL_READ_PATTERNS = [
    re.compile(r"FROM\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
    re.compile(r"JOIN\s+([a-zA-Z0-9_]+)", re.IGNORECASE),
]
_SQL_KEYWORDS = {
    "select", "from", "where", "join", "inner", "left", "right", "outer",
    "on", "set", "values", "group", "by", "order", "limit", "and", "or",
    "table", "index", "exists", "not", "null", "as", "case", "when", "then",
}


@dataclass
class TableImpactRecord:
    """Blast radius descriptor for a persistent database table."""

    table_name: str
    writers: List[str] = field(default_factory=list)
    readers: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "writers": sorted(list(set(self.writers))),
            "readers": sorted(list(set(self.readers))),
            "description": self.description,
        }


@dataclass
class SkillConflictGroup:
    """Group of skills sharing overlapping triggers."""

    trigger: str
    conflicting_skills: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger": self.trigger,
            "conflicting_skills": self.conflicting_skills,
        }


class ImpactTopologyBuilder:
    """Builder for extracting reverse dependency views across code and skills."""

    def __init__(self) -> None:
        self._table_records: Dict[str, TableImpactRecord] = {}

    @classmethod
    def build_skills_topology(
        cls, skills: List[SkillFactRecord]
    ) -> Dict[str, Any]:
        """Build tool inverted index and trigger collision matrix from skills."""
        tools_to_skills: Dict[str, List[str]] = {}
        triggers_to_skills: Dict[str, List[str]] = {}

        for skill in skills:
            # 1. Tools mapping
            for tool in skill.allowed_tools:
                clean_tool = tool.strip()
                if clean_tool:
                    tools_to_skills.setdefault(clean_tool, []).append(skill.name)

            # 2. Triggers mapping
            for trig in skill.triggers:
                clean_trig = trig.strip().lower()
                if clean_trig and len(clean_trig) > 1:
                    triggers_to_skills.setdefault(clean_trig, []).append(skill.name)

        # 3. Detect collisions (shared by >= 2 skills)
        conflicts: List[SkillConflictGroup] = []
        for trig, skill_list in sorted(triggers_to_skills.items()):
            unique_skills = sorted(list(set(skill_list)))
            if len(unique_skills) >= 2:
                conflicts.append(SkillConflictGroup(trigger=trig, conflicting_skills=unique_skills))

        return {
            "tools_to_skills": tools_to_skills,
            "triggers_to_skills": triggers_to_skills,
            "trigger_conflicts": conflicts,
            "total_tools": len(tools_to_skills),
            "total_conflicts": len(conflicts),
        }

    def analyze_source_sql(self, source_path: str, source_code: str) -> None:
        """Scan source code for SQL operations and record table readers/writers."""
        clean_path = source_path.replace("\\", "/")

        for pattern in _SQL_WRITE_PATTERNS:
            for match in pattern.finditer(source_code):
                tbl = match.group(1).lower()
                if tbl not in _SQL_KEYWORDS and not tbl.startswith("sqlite_"):
                    rec = self._table_records.setdefault(
                        tbl, TableImpactRecord(table_name=tbl)
                    )
                    if clean_path not in rec.writers:
                        rec.writers.append(clean_path)

        for pattern in _SQL_READ_PATTERNS:
            for match in pattern.finditer(source_code):
                tbl = match.group(1).lower()
                if tbl not in _SQL_KEYWORDS and not tbl.startswith("sqlite_"):
                    rec = self._table_records.setdefault(
                        tbl, TableImpactRecord(table_name=tbl)
                    )
                    if clean_path not in rec.readers:
                        rec.readers.append(clean_path)

    def get_table_impact_map(self) -> Dict[str, TableImpactRecord]:
        """Return the collected table impact map."""
        return self._table_records

    def scan_directory_sql(self, root_dir: Path | str) -> Dict[str, TableImpactRecord]:
        """Scan all Python files in a directory to build storage table topology."""
        root = Path(root_dir)
        for py_file in root.glob("**/*.py"):
            rel_str = py_file.as_posix()
            if "tests/" in rel_str or ".venv" in rel_str or "node_modules" in rel_str:
                continue

            try:
                code = py_file.read_text(encoding="utf-8", errors="replace")
                self.analyze_source_sql(py_file.name, code)
            except Exception:
                continue

        return self._table_records

    @staticmethod
    def render_storage_views_markdown(
        records: Dict[str, TableImpactRecord]
    ) -> str:
        """Render standard OKF Markdown view for database table impact."""
        lines = [
            "# 🗄️ SQLite Storage Tables Impact Topology (`views/storage_tables.md`)",
            "",
            "> Blast-radius index: check this view BEFORE refactoring any table schema.",
            f"> Tracked Tables: **{len(records)}**",
            "",
            "| SQLite Table | Writers (Mutators) | Readers (Consumers) |",
            "|:---|:---|:---|",
        ]
        for tbl, rec in sorted(records.items()):
            w_str = "<br>".join([f"`{w}`" for w in sorted(set(rec.writers))]) if rec.writers else "`--`"
            r_str = "<br>".join([f"`{r}`" for r in sorted(set(rec.readers))]) if rec.readers else "`--`"
            lines.append(f"| **`{tbl}`** | {w_str} | {r_str} |")

        return "\n".join(lines)

    @staticmethod
    def render_skills_views_markdown(topology: Dict[str, Any]) -> str:
        """Render standard OKF Markdown view for skills and tools topology."""
        tool_map: Dict[str, List[str]] = topology.get("tools_to_skills", {})
        conflicts: List[SkillConflictGroup] = topology.get("trigger_conflicts", [])

        lines = [
            "# 🛠️ Agent Skills Tool & Trigger Topology (`views/skills_tools.md`)",
            "",
            "> Reverse index: check which skills break when an MCP tool interface changes.",
            "",
            "## 1. Tool to Skills Inverted Index",
            "| Tool Name | Dependent Skills |",
            "|:---|:---|",
        ]
        for tool, skills in sorted(tool_map.items()):
            skills_str = ", ".join([f"`{s}`" for s in sorted(set(skills))])
            lines.append(f"| **`{tool}`** | {skills_str} |")

        lines.extend([
            "",
            "## 2. Trigger Collision Risk Matrix",
            "| Shared Trigger | Overlapping Skills |",
            "|:---|:---|",
        ])
        for c in conflicts:
            conf_str = ", ".join([f"`{s}`" for s in c.conflicting_skills])
            lines.append(f"| **`{c.trigger}`** | {conf_str} |")

        return "\n".join(lines)
