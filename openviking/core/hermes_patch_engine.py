# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Patch 优先技能微手术引擎 (Patch-First Skill Micro-Surgery Engine).

核心物理公理:
  1. 强制局部微手术 (≤30行):
     - 拒绝全量重写 (Edit 模式) 带来的严重幻觉覆盖与无脑抹除已验证逻辑；
     - 替换行数严格受限在 ≤30 行内，确保保留 90% 既有逻辑；
  2. 原子化应用与秒级可回滚:
     - 应用前自动备份原始代码快照，支持无损一键回滚 (revert)；
     - 上下文指纹精确锚定，避免匹配漂移。

(Card-Evolve-HermesEvolveLoop-Patch v1.5.39)
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

MAX_PATCH_LINES = 30  # 硬性物理门禁：单次微手术不超过 30 行


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class SkillPatch(BaseModel):
    """单条技能微手术补丁。"""
    patch_id: str = Field(default_factory=lambda: f"pch-{uuid.uuid4().hex[:8]}")
    skill_name: str
    file_path: str
    target_content: str
    replacement_content: str
    reason: str
    status: str = "proposed"  # "proposed" | "applied" | "reverted"
    created_at: float = Field(default_factory=time.time)
    applied_at: Optional[float] = None
    reverted_at: Optional[float] = None
    backup_content: Optional[str] = None
    target_line_count: int = 0
    replacement_line_count: int = 0


# ---------------------------------------------------------------------------
# 补丁引擎 (单例)
# ---------------------------------------------------------------------------

class HermesPatchEngine:
    """技能微手术补丁引擎。全服务单例。"""

    _instance: Optional["HermesPatchEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._patches: Dict[str, SkillPatch] = {}
        self._engine_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "HermesPatchEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def propose_patch(
        self,
        skill_name: str,
        file_path: str,
        target_content: str,
        replacement_content: str,
        reason: str,
    ) -> SkillPatch:
        """提议一个微手术补丁，强制执行 ≤30 行门禁。"""
        target_lines = len(target_content.strip().splitlines()) if target_content.strip() else 0
        rep_lines = len(replacement_content.strip().splitlines()) if replacement_content.strip() else 0

        # 物理硬性门禁：替换行数或目标行数不能超过 30 行
        if target_lines > MAX_PATCH_LINES or rep_lines > MAX_PATCH_LINES:
            raise ValueError(
                f"Patch exceeds micro-surgery limit ({MAX_PATCH_LINES} lines). "
                f"Target: {target_lines} lines, Replacement: {rep_lines} lines. "
                f"Refusing full-file rewrite to prevent hallucination regression."
            )

        patch = SkillPatch(
            skill_name=skill_name,
            file_path=file_path,
            target_content=target_content,
            replacement_content=replacement_content,
            reason=reason,
            target_line_count=target_lines,
            replacement_line_count=rep_lines,
        )

        with self._engine_lock:
            self._patches[patch.patch_id] = patch

        return patch

    def apply_patch(self, patch_id: str) -> SkillPatch:
        """原子化应用微补丁并备份快照。"""
        with self._engine_lock:
            patch = self._patches.get(patch_id)
            if not patch:
                raise KeyError(f"Patch not found: {patch_id}")
            if patch.status == "applied":
                return patch

            p = Path(patch.file_path)
            if not p.exists():
                raise FileNotFoundError(f"Target file does not exist: {patch.file_path}")

            original_text = p.read_text(encoding="utf-8")
            if patch.target_content not in original_text:
                raise ValueError("Target content anchor not found in target file (fingerprint mismatch)")

            # 保存备份快照
            patch.backup_content = original_text

            # 执行精准局部替换
            updated_text = original_text.replace(patch.target_content, patch.replacement_content, 1)
            p.write_text(updated_text, encoding="utf-8")

            patch.status = "applied"
            patch.applied_at = time.time()
            return patch

    def revert_patch(self, patch_id: str) -> SkillPatch:
        """秒级一键回滚微补丁。"""
        with self._engine_lock:
            patch = self._patches.get(patch_id)
            if not patch:
                raise KeyError(f"Patch not found: {patch_id}")
            if patch.status != "applied":
                raise ValueError(f"Cannot revert patch in '{patch.status}' status")
            if patch.backup_content is None:
                raise ValueError("No backup content found for rollback")

            p = Path(patch.file_path)
            p.write_text(patch.backup_content, encoding="utf-8")

            patch.status = "reverted"
            patch.reverted_at = time.time()
            return patch

    def get_patch(self, patch_id: str) -> Optional[SkillPatch]:
        with self._engine_lock:
            return self._patches.get(patch_id)

    def list_patches(
        self,
        skill_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[SkillPatch]:
        with self._engine_lock:
            patches = list(self._patches.values())
            if skill_name:
                patches = [p for p in patches if p.skill_name == skill_name]
            if status:
                patches = [p for p in patches if p.status == status]
            return patches

    def summary(self) -> Dict[str, Any]:
        with self._engine_lock:
            patches = list(self._patches.values())
            return {
                "total_patches": len(patches),
                "proposed": sum(1 for p in patches if p.status == "proposed"),
                "applied": sum(1 for p in patches if p.status == "applied"),
                "reverted": sum(1 for p in patches if p.status == "reverted"),
                "max_allowed_lines": MAX_PATCH_LINES,
            }
