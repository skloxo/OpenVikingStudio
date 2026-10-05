# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
SkillOpt 物理落盘与快照备份原子服务 (SkillOpt Physical Apply & Snapshot Service)
专用于将工作台优化的技能补丁安全物理写回 VikingFS / 本地存储，严格闭环：
1. 校验 YAML 标头与 Python AST 静态语法；
2. 写入前物理备份至 quarantine 快照区；
3. 原子化落盘物理覆盖；
4. 记录全生命周期 Provenance 演变证据链。
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from openviking.service.skill_provenance_tracker import ProvenanceAction, SkillProvenanceTracker

logger = logging.getLogger(__name__)


class SkillOptApplyService:
    """SkillOpt 物理回写与快照安全服务。"""

    def __init__(
        self,
        backup_root: Optional[Path | str] = None,
        candidate_dirs: Optional[List[Path]] = None,
    ) -> None:
        home = Path.home()
        self.backup_root = Path(backup_root) if backup_root else home / ".openviking" / "data" / "quarantine" / "skill_opt_pre_apply"
        self.backup_root.mkdir(parents=True, exist_ok=True)

        if candidate_dirs:
            self.candidate_dirs = candidate_dirs
        else:
            self.candidate_dirs = [
                home / ".openviking" / "data" / "viking" / "default" / "user" / "default" / "skills",
                home / ".openviking" / "data" / "viking" / "default" / "agent" / "skills",
                home / ".openviking" / "skills",
                home / ".openclaw" / "skills",
                home / ".gemini" / "config" / "skills",
            ]
        self.tracker = SkillProvenanceTracker()

    def find_skill_file(self, skill_slug: str) -> Optional[Path]:
        """按 slug 查找技能对应的实际 SKILL.md 文件绝对路径。"""
        clean_slug = skill_slug.strip()
        for c_dir in self.candidate_dirs:
            if not c_dir.exists():
                continue
            direct_p = c_dir / clean_slug / "SKILL.md"
            if direct_p.exists() and direct_p.is_file():
                return direct_p
        return None

    def validate_content_integrity(self, content: str) -> tuple[bool, Optional[str]]:
        """检查待写回内容是否具备合规 Frontmatter 及 AST 语法。"""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return False, "缺少合规的 YAML Frontmatter (--- ... ---)"
        
        fm_text, body = match.group(1), match.group(2)
        try:
            fm = yaml.safe_load(fm_text)
            if not isinstance(fm, dict):
                return False, "YAML Frontmatter 解析结果不是有效字典"
            if not fm.get("name"):
                return False, "Frontmatter 缺少必填字段 'name'"
            if not fm.get("description"):
                return False, "Frontmatter 缺少必填字段 'description'"
        except Exception as exc:
            return False, f"YAML Frontmatter 语法错误: {exc}"

        # 检查 Python 代码块语法
        code_blocks = re.findall(r"```python\s*\n(.*?)\n```", body, re.DOTALL)
        for idx, block in enumerate(code_blocks, 1):
            if block.strip() and not block.strip().startswith("#"):
                try:
                    ast.parse(block)
                except SyntaxError as e:
                    return False, f"Python 代码块 #{idx} 语法解析错误: {e.msg} (line {e.lineno})"

        return True, None

    def apply_patch(
        self,
        skill_slug: str,
        optimized_content: str,
        target_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """将优化补丁原子化写入真实技能文件，带快照保护与证据链记录。"""
        # 1. 语法完整性静态门禁
        is_valid, err_msg = self.validate_content_integrity(optimized_content)
        if not is_valid:
            raise ValueError(f"优化补丁质量门禁未通过: {err_msg}")

        # 2. 定位物理文件路径
        resolved_path: Optional[Path] = None
        if target_path:
            p = Path(target_path)
            if p.exists() and p.is_file():
                resolved_path = p
        
        if not resolved_path:
            resolved_path = self.find_skill_file(skill_slug)

        if not resolved_path:
            raise FileNotFoundError(f"未能在系统中找到技能 '{skill_slug}' 的物理 SKILL.md 文件")

        # 3. 物理快照备份
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_root / f"{timestamp}_{skill_slug}.bak.md"
        shutil.copy2(resolved_path, backup_file)

        # 4. 原子安全写入
        temp_file = resolved_path.with_suffix(".tmp")
        temp_file.write_text(optimized_content, encoding="utf-8")
        temp_file.replace(resolved_path)

        # 5. 记录证据链事件
        rec = self.tracker.record_event(
            action=ProvenanceAction.OPTIMIZE,
            skill_name=skill_slug,
            operator="skill_opt_workbench",
            snapshot_path=str(backup_file),
            details={
                "target_file": str(resolved_path),
                "bytes_written": len(optimized_content),
                "timestamp": timestamp,
                "delta_summary": "Applied SkillOpt automated optimization patch to production SKILL.md",
            },
        )
        event_id = rec.event_id

        logger.info(
            "Successfully applied SkillOpt patch to %s (backup: %s, event: %s)",
            resolved_path,
            backup_file,
            event_id,
        )

        return {
            "status": "ok",
            "skill_slug": skill_slug,
            "target_path": str(resolved_path),
            "backup_path": str(backup_file),
            "event_id": event_id,
            "bytes_written": len(optimized_content),
            "message": f"技能 '{skill_slug}' 物理补丁已安全落盘，快照已建立",
        }
