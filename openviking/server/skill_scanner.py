# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Automated, configuration-driven Skill Scanner and Synchronizer for OpenViking."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

_DATE_ARCHIVE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}", re.IGNORECASE)

# Default SSOT Source Paths if not specified in ov.conf
DEFAULT_SKILL_SOURCES: List[Dict[str, str]] = [
    {
        "path": "/home/skloxo/.gemini/config/skills",
        "category": "Engineering / Core",
        "source": "Antigravity",
        "scope": "system",
    },
    {
        "path": "/home/skloxo/.gemini/antigravity-ide/builtin/skills",
        "category": "Engineering / Builtin",
        "source": "Antigravity",
        "scope": "system",
    },
    {
        "path": "/home/skloxo/aho/openclaw/project/.agents/skills",
        "category": "Workspace / Project",
        "source": "OpenViking",
        "scope": "system",
    },
    {
        "path": "/home/skloxo/aho/openclaw/skills",
        "category": "OpenClaw / Skills",
        "source": "OpenClaw",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/.openclaw/skills",
        "category": "OpenClaw / User Skills",
        "source": "OpenClaw",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/a/SenseNova-Skills/skills",
        "category": "SenseNova / Office",
        "source": "SenseNova",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/.hermes/hermes-agent/skills",
        "category": "Hermes / Core",
        "source": "Hermes",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/.hermes/hermes-agent/optional-skills",
        "category": "Hermes / Optional",
        "source": "Hermes",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/aho/openclaw/agent-center/skills",
        "category": "Agent Center",
        "source": "OpenClaw",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/aho/tide-trading/agent/src/skills",
        "category": "Financial / Trading",
        "source": "TideTrading",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/aho/tide-trading/daily_stock_analysis/.claude/skills",
        "category": "Financial / Stock Analysis",
        "source": "TideTrading",
        "scope": "user",
    },
    {
        "path": "/home/skloxo/aho/openclaw/project",
        "category": "Project Submodules",
        "source": "Project",
        "scope": "user",
    },
]

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_TARGETS: List[str] = [
    os.path.expanduser("~/.openviking/all_skills.json"),
    str(_REPO_ROOT / "public" / "all_skills.json"),
    str(_REPO_ROOT / "dist" / "all_skills.json"),
]


def parse_skill_file(filepath: str, category: str, source: str, scope: str = "user") -> Optional[Dict[str, Any]]:
    """Parse a single SKILL.md file and return standardized skill metadata."""
    skill_dir = os.path.dirname(filepath)
    dirname = os.path.basename(skill_dir)
    if not dirname or dirname.startswith(".") or dirname == "__pycache__":
        return None
    if _DATE_ARCHIVE_REGEX.match(dirname) or "backup" in dirname.lower() or "curator" in dirname.lower():
        return None

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.debug("Failed reading skill at %s: %s", filepath, e)
        return None

    name = dirname
    description = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            try:
                fm = yaml.safe_load(fm_text)
                if isinstance(fm, dict):
                    name = str(fm.get("name", dirname)).strip()
                    description = str(fm.get("description", "")).strip()
            except Exception:
                pass

    if not name or name.startswith(".") or _DATE_ARCHIVE_REGEX.match(name) or "backup" in name.lower() or "curator" in name.lower():
        return None

    if not description:
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("---")]
        if lines:
            description = lines[0].lstrip("#").strip()

    subfiles = []
    try:
        for root, _, files in os.walk(skill_dir):
            for file in files:
                rel = os.path.relpath(os.path.join(root, file), skill_dir)
                subfiles.append(rel)
    except Exception:
        subfiles = ["SKILL.md"]

    return {
        "name": name,
        "description": description or "自然语言智能体意图感应与执行规范",
        "source": source,
        "category": category,
        "path": filepath,
        "uri": f"viking://resources/skills/{name}",
        "scope": scope,
        "files": subfiles,
        "content": content[:40000],
    }


def scan_configured_skills(
    sources: Optional[List[Dict[str, str]]] = None,
    output_targets: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Scan all configured skill directories, deduplicate by canonical name, and persist to targets."""
    actual_sources = sources if sources is not None else DEFAULT_SKILL_SOURCES
    actual_targets = output_targets if output_targets is not None else DEFAULT_OUTPUT_TARGETS

    skills: List[Dict[str, Any]] = []
    seen_names: set = set()
    breakdown_by_source: Dict[str, int] = {}
    breakdown_by_category: Dict[str, int] = {}

    for src_cfg in actual_sources:
        root_path = src_cfg.get("path", "")
        category = src_cfg.get("category", "General")
        source = src_cfg.get("source", "System")
        scope = src_cfg.get("scope", "user")

        if not os.path.exists(root_path):
            continue

        for dirpath, dirnames, filenames in os.walk(root_path):
            # Prune hidden directories (dot-dirs like .clawhub, .git, __pycache__) and backup archives in-place
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".")
                and d != "__pycache__"
                and not _DATE_ARCHIVE_REGEX.match(d)
                and "backup" not in d.lower()
                and "curator" not in d.lower()
            ]
            if "SKILL.md" in filenames:
                skill_file = os.path.join(dirpath, "SKILL.md")
                parsed = parse_skill_file(skill_file, category, source, scope)
                if parsed and parsed["name"] not in seen_names:
                    seen_names.add(parsed["name"])
                    skills.append(parsed)
                    breakdown_by_source[source] = breakdown_by_source.get(source, 0) + 1
                    breakdown_by_category[category] = breakdown_by_category.get(category, 0) + 1

    skills.sort(key=lambda s: s["name"].lower())

    # Persist to output targets
    if actual_targets:
        data = json.dumps(skills, indent=2, ensure_ascii=False)
        for target in actual_targets:
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(data)
            except Exception as e:
                logger.warning("Failed writing skills index to target %s: %s", target, e)

    stats = {
        "total_unique_skills": len(skills),
        "breakdown_by_source": breakdown_by_source,
        "breakdown_by_category": breakdown_by_category,
        "scanned_source_paths": [s.get("path") for s in actual_sources if os.path.exists(s.get("path", ""))],
    }
    logger.info("Skill scan completed: indexed %d unique skills across %d sources", len(skills), len(actual_sources))
    return skills, stats


def get_skill_by_name(skill_name: str) -> Optional[Dict[str, Any]]:
    """Look up a skill across all configured sources by name and return its full details."""
    skills, _ = scan_configured_skills()
    for s in skills:
        if s.get("name") == skill_name:
            return s
    return None
