# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
SkillZip 契约压缩原子落盘与快照备份服务 (SkillZip Physical Apply & Snapshot Service - Card-100)
专用于将 SkillZip 压缩后的六元组规约写回 VikingFS / 本地存储，杜绝半拉子 DEMO：
1. 校验 YAML 标头与代码块语法完整性；
2. 写入前物理备份至 quarantine 快照区；
3. 支持原地覆盖 (in_place) 与紧凑衍生版 (compact_variant) 双模态落盘；
4. 记录全生命周期 Provenance 演变证据链。
"""

from __future__ import annotations

import ast
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


class SkillZipApplyService:
    """SkillZip 压缩规约安全落盘服务。单例/多实例安全。"""

    def __init__(
        self,
        backup_root: Optional[Path] = None,
        candidate_dirs: Optional[List[Path]] = None,
        provenance_tracker: Optional[SkillProvenanceTracker] = None,
    ):
        self.backup_root = backup_root or (
            Path.home() / ".openviking" / "data" / "quarantine" / "skill_zip_pre_apply"
        )
        self.backup_root.mkdir(parents=True, exist_ok=True)

        self.candidate_dirs = candidate_dirs or [
            Path.home() / ".openviking" / "data" / "viking" / "default" / "user" / "default" / "skills",
            Path.home() / ".openviking" / "data" / "viking" / "default" / "agent" / "skills",
            Path.home() / ".openviking" / "skills",
            Path.cwd() / "skills",
        ]
        self.tracker = provenance_tracker or SkillProvenanceTracker.get_instance()

    def find_skill_file(self, skill_slug: str) -> Optional[Path]:
        """根据技能唯一 slug 定位生产物理文件。"""
        clean_slug = skill_slug.strip().rstrip("/")
        if "/" in clean_slug:
            clean_slug = clean_slug.split("/")[-1]

        for base_dir in self.candidate_dirs:
            if not base_dir.exists():
                continue

            direct_candidate = base_dir / clean_slug / "SKILL.md"
            if direct_candidate.exists() and direct_candidate.is_file():
                return direct_candidate

            flat_candidate = base_dir / f"{clean_slug}.md"
            if flat_candidate.exists() and flat_candidate.is_file():
                return flat_candidate

            try:
                for match in base_dir.glob(f"**/{clean_slug}/SKILL.md"):
                    if match.is_file():
                        return match
            except Exception:
                pass

        return None

    def validate_content_integrity(self, content: str) -> tuple[bool, str]:
        """静态门禁：校验 YAML 标头与代码块语法，严禁毒化破损规约入库。"""
        if not content.strip():
            return False, "压缩内容不可为空"

        # 1. YAML 标头校验
        header_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not header_match:
            return False, "缺少合规的 YAML Frontmatter 标头 (--- ... ---)"

        header_yaml = header_match.group(1)
        try:
            parsed_meta = yaml.safe_load(header_yaml)
            if not isinstance(parsed_meta, dict) or "name" not in parsed_meta:
                return False, "YAML 标头必须包含有效字典且含有 'name' 字段"
        except Exception as exc:
            return False, f"YAML 标头解析失败: {exc}"

        # 2. Python 代码块静态 AST 语法树门禁
        python_blocks = re.findall(r"```python\s*\n(.*?)\n```", content, re.DOTALL)
        for idx, block in enumerate(python_blocks):
            if block.strip():
                try:
                    ast.parse(block)
                except SyntaxError as syn_err:
                    return False, f"代码块 #{idx+1} 存在 Python 语法错误: {syn_err}"

        return True, "OK"

    def apply_compressed_skill(
        self,
        skill_slug: str,
        compressed_content: str,
        mode: str = "in_place",
        target_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """将压缩补丁原子化写入真实技能文件，带快照保护与证据链记录。"""
        is_valid, err_msg = self.validate_content_integrity(compressed_content)
        if not is_valid:
            raise ValueError(f"SkillZip 压缩规约门禁未通过: {err_msg}")

        resolved_path: Optional[Path] = None
        if target_path:
            p = Path(target_path)
            if p.exists() and p.is_file():
                resolved_path = p

        if not resolved_path:
            resolved_path = self.find_skill_file(skill_slug)

        if not resolved_path:
            raise FileNotFoundError(f"未能在系统中找到技能 '{skill_slug}' 的物理 SKILL.md 文件")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_root / f"{timestamp}_{skill_slug}.bak.md"
        shutil.copy2(resolved_path, backup_file)

        if mode == "compact_variant":
            dest_file = resolved_path.parent / "SKILL.compact.md"
        else:
            dest_file = resolved_path

        temp_file = dest_file.with_suffix(".tmp")
        temp_file.write_text(compressed_content, encoding="utf-8")
        temp_file.replace(dest_file)

        orig_len = backup_file.stat().st_size
        comp_len = dest_file.stat().st_size
        ratio = 1.0 - (comp_len / orig_len) if orig_len > 0 else 0.0

        rec = self.tracker.record_event(
            action=ProvenanceAction.OPTIMIZE,
            skill_name=skill_slug,
            operator="skill_zip_cockpit",
            snapshot_path=str(backup_file),
            details={
                "target_file": str(dest_file),
                "mode": mode,
                "bytes_written": comp_len,
                "original_bytes": orig_len,
                "compression_ratio": round(ratio, 4),
                "timestamp": timestamp,
                "delta_summary": f"Applied SkillZip 0-rollout compression in mode={mode}",
            },
        )

        logger.info(
            "Successfully applied SkillZip to %s (mode=%s, backup=%s, event=%s)",
            dest_file,
            mode,
            backup_file,
            rec.event_id,
        )

        return {
            "status": "ok",
            "skill_slug": skill_slug,
            "mode": mode,
            "target_path": str(dest_file),
            "backup_path": str(backup_file),
            "event_id": rec.event_id,
            "bytes_written": comp_len,
            "original_bytes": orig_len,
            "compression_ratio": round(ratio, 4),
            "message": f"技能 '{skill_slug}' 压缩规约已安全落盘 ({mode})，快照已建立",
        }
