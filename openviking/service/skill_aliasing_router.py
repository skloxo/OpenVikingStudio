# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Aliasing & Virtual Projection Router (Card-1).

Provides zero-breaking, seamless backward compatibility for multi-agent fleets
(Hermes, OpenClaw, mobile/edge nodes) to invoke granular skills that have been
absorbed and crystallized into higher-level capability bundles.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml

DEFAULT_SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

# 明确的重定向与归一化别名映射
EXPLICIT_ALIASES: Dict[str, str] = {
    "cpa_squad": "cpa-squad",
    "credential-vault": "keepass-vault",
    "web-search-pro": "web-harvest-pro",
    "network-search-ops": "web-harvest-pro",
    "wechat-article-reader": "web-harvest-pro",
}


class SkillAliasingRouter:
    """Manages alias resolution and virtual projection for capability bundle scenarios."""

    def __init__(self, skills_root: Optional[Path | str] = None) -> None:
        self.skills_root = Path(skills_root) if skills_root else DEFAULT_SKILLS_DIR
        self._scenario_map: Optional[Dict[str, Tuple[str, Path]]] = None

    def get_alias_map(self, force_refresh: bool = False) -> Dict[str, Tuple[str, Path]]:
        """Discover and cache granular scenarios across all capability bundles."""
        if self._scenario_map is not None and not force_refresh:
            return self._scenario_map

        mapping: Dict[str, Tuple[str, Path]] = {}
        if not self.skills_root.exists():
            self._scenario_map = mapping
            return mapping

        for bundle_dir in self.skills_root.iterdir():
            if not bundle_dir.is_dir():
                continue
            scenarios_dir = bundle_dir / "scenarios"
            if scenarios_dir.exists() and scenarios_dir.is_dir():
                for sc_file in scenarios_dir.glob("*.md"):
                    sc_name = sc_file.stem
                    mapping[sc_name] = (bundle_dir.name, sc_file)

            # Check provenance if exists
            prov_file = bundle_dir / "ABSORPTION_PROVENANCE.json"
            if prov_file.exists():
                try:
                    data = json.loads(prov_file.read_text(encoding="utf-8"))
                    absorbed = data.get("absorbed_skills", [])
                    for item in absorbed:
                        name = item if isinstance(item, str) else item.get("name")
                        if name and name not in mapping:
                            mapping[name] = (bundle_dir.name, bundle_dir / "SKILL.md")
                except Exception:
                    pass

        self._scenario_map = mapping
        return mapping

    def resolve(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Resolve a requested skill name to a bundle or scenario projection."""
        # 1. 显式归一化别名
        norm_name = EXPLICIT_ALIASES.get(skill_name, skill_name)

        # 2. 检查是否直接是顶级目录
        direct_path = self.skills_root / norm_name
        if direct_path.exists() and direct_path.is_dir():
            return {
                "type": "bundle",
                "target_name": norm_name,
                "bundle_name": norm_name,
                "file_path": direct_path / "SKILL.md",
                "is_virtual": False,
            }

        # 3. 检查是否是某大包下的子 scenario
        sc_map = self.get_alias_map()
        if norm_name in sc_map:
            bundle_name, file_path = sc_map[norm_name]
            return {
                "type": "scenario_projection",
                "target_name": norm_name,
                "bundle_name": bundle_name,
                "file_path": file_path,
                "is_virtual": True,
            }

        return None

    def get_virtual_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Construct an OpenAPI-compliant skill response dict for virtual scenarios."""
        res = self.resolve(skill_name)
        if not res:
            return None

        bundle_name = res["bundle_name"]
        file_path: Path = res["file_path"]

        if not file_path.exists():
            return None

        content = file_path.read_text(encoding="utf-8")
        description = f"Virtual scenario projection from capability bundle [{bundle_name}]."
        tags = [bundle_name, "virtual-projection", skill_name]
        tools: List[str] = []

        # Parse frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                    if isinstance(fm, dict):
                        description = fm.get("description", description)
                        tags.extend(fm.get("tags") or fm.get("triggers") or [])
                        tools.extend(fm.get("allowed-tools") or fm.get("tools") or [])
                except Exception:
                    pass

        # Construct URI conforming to VikingFS standard
        rel_uri = f"viking://agent/skills/{bundle_name}/scenarios/{file_path.name}"

        return {
            "name": skill_name,
            "type": "skill",
            "uri": rel_uri,
            "root_uri": rel_uri,
            "skill_md_uri": rel_uri,
            "description": description,
            "tags": list(dict.fromkeys(tags)),
            "allowed_tools": tools,
            "parent_bundle": bundle_name,
            "is_virtual": True,
            "content": content,
            "files": [
                {
                    "path": file_path.name,
                    "kind": "definition",
                    "uri": rel_uri,
                }
            ],
        }
