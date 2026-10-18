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

# 明确的重定向与归一化别名映射 (用于无独立 scenario 的泛化退化别名)
EXPLICIT_ALIASES: Dict[str, str] = {
    "cpa-squad": "cpa_squad",
    "keepass-vault": "credential-vault",
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
        """Resolve a requested skill name to a bundle or scenario projection.
        
        Priority order:
        1. Exact match top-level bundle directory
        2. Exact/normalized match scenario in any bundle (preserves granular precision)
        3. Explicit alias mapping fallback
        4. Hyphen/underscore normalized top-level bundle directory
        """
        clean_name = skill_name.strip()

        # 1. 优先检查是否直接是顶级目录 (真正的 bundle)
        direct_path = self.skills_root / clean_name
        if direct_path.exists() and direct_path.is_dir():
            return {
                "type": "bundle",
                "target_name": clean_name,
                "bundle_name": clean_name,
                "file_path": direct_path / "SKILL.md",
                "is_virtual": False,
            }

        # 2. 检查是否是某大包下的子 scenario (场景投影优先于泛化别名)
        sc_map = self.get_alias_map()
        candidates = [
            clean_name,
            clean_name.replace("_", "-"),
            clean_name.replace("-", "_"),
        ]
        for cand in candidates:
            if cand in sc_map:
                bundle_name, file_path = sc_map[cand]
                return {
                    "type": "scenario_projection",
                    "target_name": clean_name,
                    "bundle_name": bundle_name,
                    "file_path": file_path,
                    "is_virtual": True,
                }

        # 3. 检查显式别名重定向
        if clean_name in EXPLICIT_ALIASES:
            target_alias = EXPLICIT_ALIASES[clean_name]
            alias_path = self.skills_root / target_alias
            if alias_path.exists() and alias_path.is_dir():
                return {
                    "type": "bundle",
                    "target_name": clean_name,
                    "bundle_name": target_alias,
                    "file_path": alias_path / "SKILL.md",
                    "is_virtual": True,
                }
            if target_alias in sc_map:
                bundle_name, file_path = sc_map[target_alias]
                return {
                    "type": "scenario_projection",
                    "target_name": clean_name,
                    "bundle_name": bundle_name,
                    "file_path": file_path,
                    "is_virtual": True,
                }

        # 4. 检查连字符/下划线归一化后的顶层大包目录
        for cand in candidates[1:]:
            cand_path = self.skills_root / cand
            if cand_path.exists() and cand_path.is_dir():
                return {
                    "type": "bundle",
                    "target_name": clean_name,
                    "bundle_name": cand,
                    "file_path": cand_path / "SKILL.md",
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
