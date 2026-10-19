# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Mutation Engine & Retina Micro-Patch Gate (Card-193 SSOT).

核心公理:
  1. 致命微手术律: 存量技能的更新往往仅变动关键 1~2 行 (重叠率 99%)，绝对禁止当成重复废话拒之门外；
  2. 微观实体 Delta 审计: 严格提取 API 端点、CLI 标志、环境变量与代码块 SHA256 变动；
  3. 视网膜防洗劫守卫: 若新提交恶意或异常截断清空原有核心代码块，物理熔断阻断覆盖；
  4. 原地自增升轨: 原地微手术替换对应场景文件并自动自增 patch 版本号。
"""

from __future__ import annotations

from enum import Enum
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml

from openviking.service.detail_preserving_merger import MicroEntityExtractor
from openviking.service.skill_semantic_merger import CodeBlockFreezeVerifier
from openviking.service.skill_provenance_tracker import (
    ProvenanceAction,
    SkillProvenanceTracker,
)
from openviking.service.skill_path_resolver import resolve_skills_root

logger = logging.getLogger(__name__)


class MutationVerdict(str, Enum):
    """微手术突变审计结论。"""
    APPLY_PATCH = "APPLY_PATCH"
    NO_CHANGE = "NO_CHANGE"
    REJECTED_VANDALISM = "REJECTED_VANDALISM"


class SkillMutationEngine:
    """存量技能微手术热更新与微观技术实体 Diff 审计引擎。"""

    def __init__(self, skills_root: Optional[Path | str] = None) -> None:
        self.skills_root = Path(skills_root) if skills_root else resolve_skills_root()
        self.tracker = SkillProvenanceTracker.get_instance()

    def find_existing_target(self, skill_name: str) -> Tuple[bool, Optional[str], Optional[Path]]:
        """血缘寻源：精准定位 skill_name 是否为已有大包根或大包子场景。"""
        if not self.skills_root.exists():
            return False, None, None

        clean_name = skill_name.strip().lower().replace("_", "-")

        # 1. 检查是否为大包主定义
        bundle_master = self.skills_root / clean_name / "SKILL.md"
        if bundle_master.exists():
            return True, clean_name, bundle_master

        # 2. 检查各大包下的 scenarios/ 子场景
        for bundle_dir in self.skills_root.iterdir():
            if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
                continue
            scenario_file = bundle_dir / "scenarios" / f"{clean_name}.md"
            if scenario_file.exists():
                return True, bundle_dir.name, scenario_file

        return False, None, None

    def audit_mutation(
        self,
        skill_name: str,
        incoming_content: str,
        target_path: Optional[Path] = None,
    ) -> Tuple[MutationVerdict, str, str]:
        """对存量技能变更执行微观实体 Diff 审计与防洗劫检测。"""
        if target_path is None:
            found, _, found_path = self.find_existing_target(skill_name)
            if not found or found_path is None:
                return MutationVerdict.NO_CHANGE, f"No existing target found for {skill_name}", incoming_content
            target_path = found_path

        base_content = target_path.read_text(encoding="utf-8")

        # 1. 幂等内容防抖
        if base_content.strip() == incoming_content.strip():
            return MutationVerdict.NO_CHANGE, "Content identical, NOOP", base_content

        # 2. 视网膜防洗劫守卫 (Anti-Vandalism Gate)
        base_blocks = CodeBlockFreezeVerifier.extract_code_blocks(base_content)
        inc_blocks = CodeBlockFreezeVerifier.extract_code_blocks(incoming_content)
        if (len(base_blocks) >= 1 and len(inc_blocks) == 0) or (len(base_blocks) >= 2 and len(inc_blocks) < len(base_blocks) * 0.5):
            msg = f"检测到新版本异常清空原有核心代码块（原 {len(base_blocks)} 个，现 {len(inc_blocks)} 个），触发防洗劫安全阻断"
            logger.warning("[MutationEngine] %s on %s", msg, skill_name)
            return MutationVerdict.REJECTED_VANDALISM, msg, base_content

        # 3. 微观技术实体 Delta 提取
        base_entities = MicroEntityExtractor.extract(base_content)
        inc_entities = MicroEntityExtractor.extract(incoming_content)

        added_urls = inc_entities.urls - base_entities.urls
        added_flags = inc_entities.cli_flags - base_entities.cli_flags
        added_envs = inc_entities.env_vars - base_entities.env_vars
        added_ports = inc_entities.ports - base_entities.ports

        diff_details: List[str] = []
        if added_urls:
            diff_details.append(f"URLs: {sorted(list(added_urls))}")
        if added_flags:
            diff_details.append(f"Flags: {sorted(list(added_flags))}")
        if added_envs:
            diff_details.append(f"Envs: {sorted(list(added_envs))}")
        if added_ports:
            diff_details.append(f"Ports: {sorted(list(added_ports))}")

        inc_hashes = {b.sha256 for b in inc_blocks}
        base_hashes = {b.sha256 for b in base_blocks}
        if inc_hashes != base_hashes:
            diff_details.append("Code blocks updated")

        diff_summary = "; ".join(diff_details) if diff_details else "Micro text adjustments"

        # 4. 原子自增 Frontmatter SemVer 版本号 (e.g. 1.0.0 -> 1.0.1)
        patched_content = self._bump_version(incoming_content)

        return MutationVerdict.APPLY_PATCH, f"Detected Gold Patch ({diff_summary})", patched_content

    def apply_mutation(
        self,
        skill_name: str,
        patched_content: str,
        target_path: Path,
        operator: str = "mutation-engine",
    ) -> Dict[str, Any]:
        """原地微手术物理写盘，记录 Provenance 演进证据链并刷新别名网关。"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(patched_content, encoding="utf-8")

        self.tracker.record_event(
            action=ProvenanceAction.MUTATE,
            skill_name=skill_name,
            operator=operator,
            details={
                "stage": "MICRO_PATCH_APPLIED",
                "target_path": str(target_path),
                "message": f"原地微手术成功落盘: {target_path.name}",
            },
        )

        return {
            "status": "MUTATED",
            "skill_name": skill_name,
            "target_path": str(target_path),
        }

    def _bump_version(self, content: str) -> str:
        """解析 Frontmatter 并自增 patch 版本号。"""
        if not content.startswith("---"):
            return content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return content

        raw_fm = parts[1]
        body = parts[2]

        try:
            fm = yaml.safe_load(raw_fm) or {}
            ver = str(fm.get("version", "1.0.0")).strip()
            # 兼容 v1, v2 或 semver 1.0.0
            semver_match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", ver)
            if semver_match:
                major, minor, patch = semver_match.groups()
                new_ver = f"{major}.{minor}.{int(patch) + 1}"
            elif ver.startswith("v") and ver[1:].isdigit():
                new_ver = f"v{int(ver[1:]) + 1}"
            else:
                new_ver = "1.0.1"

            fm["version"] = new_ver
            new_fm_str = yaml.dump(fm, sort_keys=False, allow_unicode=True).strip()
            return f"---\n{new_fm_str}\n---{body}"
        except Exception:
            return content
