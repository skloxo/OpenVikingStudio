# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""可训练外部技能文档 (Trainable Skill Document) 与有界可编辑 Surface 机制。

核心物理公理:
  1. Skill-MDP 外部策略状态:
     - 流程文档本身就是可训练的外部策略状态；
  2. # EVOLVE-BLOCK 有界可编辑 Surface 机制:
     - 只有在 `# EVOLVE-BLOCK-START` 与 `# EVOLVE-BLOCK-END` 之间的区域允许自演进；
     - 外部的核心框架、接口签名、YAML Frontmatter 完全物理冻结；
     - 彻底杜绝“为了局部提分搞乱全局架构”的灾难性漂移。

(Card-Skill-TrainablePolicy-RSI v1.5.40)
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

EVOLVE_BLOCK_START_TAG = "# EVOLVE-BLOCK-START"
EVOLVE_BLOCK_END_TAG = "# EVOLVE-BLOCK-END"

_BLOCK_PATTERN = re.compile(
    r"(^[ \t]*#[ \t]*EVOLVE-BLOCK-START[ \t]*\n)(.*?)(^[ \t]*#[ \t]*EVOLVE-BLOCK-END[ \t]*)",
    re.MULTILINE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class EvolveBlock(BaseModel):
    """单段有界可编辑区块。"""
    block_index: int
    content: str
    sha256: str
    line_count: int


class SurfaceInspectionResult(BaseModel):
    """技能文档 Surface 审查结果。"""
    has_evolve_blocks: bool
    block_count: int
    frozen_surface_sha256: str
    blocks: List[EvolveBlock] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 可训练技能文档类
# ---------------------------------------------------------------------------

class TrainableSkillDocument:
    """可训练外部技能策略文档，负责有界 Surface 的解析、验证与安全更新。"""

    def __init__(self, raw_text: str, skill_name: str = "unnamed") -> None:
        self.skill_name = skill_name
        self._raw_text = raw_text

    @classmethod
    def from_file(cls, path: str | Path, skill_name: Optional[str] = None) -> "TrainableSkillDocument":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Skill document not found: {path}")
        text = p.read_text(encoding="utf-8")
        name = skill_name or p.parent.name or p.stem
        return cls(text, skill_name=name)

    @property
    def raw_text(self) -> str:
        return self._raw_text

    def inspect(self) -> SurfaceInspectionResult:
        """分析文档中的有界可编辑区块与冻结面指纹。"""
        matches = list(_BLOCK_PATTERN.finditer(self._raw_text))
        blocks: List[EvolveBlock] = []

        for idx, m in enumerate(matches):
            body = m.group(2)
            sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
            line_count = len(body.splitlines())
            blocks.append(
                EvolveBlock(
                    block_index=idx,
                    content=body,
                    sha256=sha,
                    line_count=line_count,
                )
            )

        # 将所有可编辑区块用占位符剥离，计算外部冻结面哈希
        frozen_text = _BLOCK_PATTERN.sub(r"\1__EVOLVE_SLOT__\n\3", self._raw_text)
        frozen_sha = hashlib.sha256(frozen_text.encode("utf-8")).hexdigest()

        return SurfaceInspectionResult(
            has_evolve_blocks=len(blocks) > 0,
            block_count=len(blocks),
            frozen_surface_sha256=frozen_sha,
            blocks=blocks,
        )

    def update_block(self, block_index: int, new_content: str) -> "TrainableSkillDocument":
        """安全更新指定 index 的有界区块，确保外部冻结面绝对零篡改。"""
        matches = list(_BLOCK_PATTERN.finditer(self._raw_text))
        if block_index < 0 or block_index >= len(matches):
            raise IndexError(f"Evolve block index {block_index} out of range (total {len(matches)} blocks)")

        target_match = matches[block_index]
        start_pos = target_match.start(2)
        end_pos = target_match.end(2)

        # 确保新内容以换行结尾
        normalized_content = new_content if new_content.endswith("\n") else new_content + "\n"

        # 拼接更新后的文档
        updated_text = self._raw_text[:start_pos] + normalized_content + self._raw_text[end_pos:]

        new_doc = TrainableSkillDocument(updated_text, skill_name=self.skill_name)

        # 验证冻结面不变公理
        orig_inspection = self.inspect()
        new_inspection = new_doc.inspect()
        if orig_inspection.frozen_surface_sha256 != new_inspection.frozen_surface_sha256:
            raise ValueError(
                "Violation: Update breached the bounded evolve block! Frozen surface SHA256 mismatch."
            )

        return new_doc

    def save(self, path: str | Path) -> None:
        """持久化更新后的技能文档。"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self._raw_text, encoding="utf-8")
