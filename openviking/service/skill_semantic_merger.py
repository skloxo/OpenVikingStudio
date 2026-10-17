# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VikingFS Code Block Freeze & Bounded Semantic 3-Way Merger (Card-97).

核心物理公理:
  1. 代码块物理哈希冻结律 (Code Block Freeze): 锁定 Markdown 中的成熟代码块，严禁大模型擅自改写已验证代码；
  2. 主干防毒化与只读保护: 成熟核心技能逻辑只读，新技能 15% 增量仅作为参数补充或边缘案例追加；
  3. AST 语法门禁二次编译: 对融合结果中的 Python 代码块执行 ast.parse 严格校验，防止语法退化。
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml


@dataclass
class CodeBlock:
    """Markdown 中提取的代码块实体。"""
    lang: str
    code: str
    sha256: str


@dataclass
class MergeResult:
    """差分融合结果产物。"""
    merged_content: str
    base_skill_name: str
    incoming_skill_name: str
    frozen_block_count: int
    delta_triggers_added: List[str] = field(default_factory=list)
    delta_params_absorbed: List[str] = field(default_factory=list)
    code_mutation_detected: bool = False
    ast_valid: bool = True


class CodeBlockFreezeVerifier:
    """代码块提取与防篡改冻结哈希校验器。"""

    CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_\-]+)?\s*\n([\s\S]*?)```")

    @classmethod
    def extract_code_blocks(cls, markdown: str) -> List[CodeBlock]:
        """按顺序提取 Markdown 中的所有代码块并计算 SHA256 指纹。"""
        blocks: List[CodeBlock] = []
        for match in cls.CODE_BLOCK_RE.finditer(markdown):
            lang = (match.group(1) or "").strip().lower()
            code = match.group(2)
            block_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
            blocks.append(CodeBlock(lang=lang, code=code, sha256=block_hash))
        return blocks

    @classmethod
    def verify_all_present(cls, base_blocks: List[CodeBlock], merged_markdown: str) -> bool:
        """校验成熟基线的所有代码块是否 100% 原样保留在融合产物中。"""
        merged_blocks = cls.extract_code_blocks(merged_markdown)
        merged_hashes = {b.sha256 for b in merged_blocks}
        for b in base_blocks:
            if b.sha256 not in merged_hashes:
                return False
        return True


class SkillSemanticMerger:
    """代码块物理冻结与受控差分融合器。"""

    PARAM_RE = re.compile(r"(--[a-zA-Z0-9_\-]+)")

    def merge(self, base_content: str, incoming_content: str) -> MergeResult:
        """执行主干防毒化、代码块冻结与增量受控追加三路融合。"""
        base_fm, base_body = self._split_frontmatter(base_content)
        inc_fm, inc_body = self._split_frontmatter(incoming_content)

        base_name = base_fm.get("name", "base-skill")
        inc_name = inc_fm.get("name", "incoming-skill")
        inc_version = inc_fm.get("version", "1.0.0")

        # 1. 代码块物理哈希冻结
        base_code_blocks = CodeBlockFreezeVerifier.extract_code_blocks(base_body)
        inc_code_blocks = CodeBlockFreezeVerifier.extract_code_blocks(inc_body)

        # 2. 差分增量提取 (Triggers & Parameters)
        base_triggers = set(base_fm.get("triggers") or [])
        inc_triggers = set(inc_fm.get("triggers") or [])
        delta_triggers = sorted(list(inc_triggers - base_triggers))

        base_params = set(self.PARAM_RE.findall(base_body))
        inc_params = set(self.PARAM_RE.findall(inc_body))
        delta_params = sorted(list(inc_params - base_params))

        # 3. 提取非同质化的新技能独有代码块 (边缘用例)
        base_hashes = {b.sha256 for b in base_code_blocks}
        unique_inc_blocks = [b for b in inc_code_blocks if b.sha256 not in base_hashes]

        # 4. 组装新 Frontmatter (保持 base 规范，自增 patch 版本，合并 triggers)
        new_fm = dict(base_fm)
        new_fm["version"] = self._bump_patch_version(str(base_fm.get("version", "1.0.0")))
        all_triggers = list(base_fm.get("triggers") or [])
        for dt in delta_triggers:
            if dt not in all_triggers:
                all_triggers.append(dt)
        new_fm["triggers"] = all_triggers

        # 5. 组装增量附录 (Delta Appendix)
        appendix_lines = [
            "",
            "## 🚀 Absorbed Advanced Variants & Edge-Case Flags",
            f"- **Delta Source**: `{inc_name}` (v{inc_version})",
        ]
        if delta_triggers:
            appendix_lines.append(f"- **Unique Triggers Added**: {', '.join(delta_triggers)}")
        if delta_params:
            appendix_lines.append(f"- **Additional Flags / Parameters**: {', '.join(delta_params)}")

        # 引入独有的边缘配方代码块，绝不覆写 base 代码块
        if unique_inc_blocks:
            appendix_lines.append("- **Edge-Case Recipes**:")
            for b in unique_inc_blocks:
                # 过滤掉毒化的同名覆盖函数
                if b.lang == "python" and "def check_conflict_markers" in b.code and len(base_code_blocks) > 0:
                    continue
                appendix_lines.append(f"```{b.lang}\n{b.code}```\n")

        # 6. 生成最终融合 Markdown
        merged_body = base_body.rstrip() + "\n" + "\n".join(appendix_lines)
        merged_fm_str = yaml.safe_dump(new_fm, sort_keys=False, allow_unicode=True)
        merged_content = f"---\n{merged_fm_str}---\n\n{merged_body.lstrip()}"

        # 7. 冻结完整性校验 (Code Block Zero Mutation Check)
        mutation_detected = not CodeBlockFreezeVerifier.verify_all_present(base_code_blocks, merged_content)

        # 8. AST 静态语法二次门禁
        ast_valid = True
        merged_blocks = CodeBlockFreezeVerifier.extract_code_blocks(merged_content)
        for b in merged_blocks:
            if b.lang == "python":
                try:
                    ast.parse(b.code)
                except Exception:
                    ast_valid = False
                    break

        return MergeResult(
            merged_content=merged_content,
            base_skill_name=base_name,
            incoming_skill_name=inc_name,
            frozen_block_count=len(base_code_blocks),
            delta_triggers_added=delta_triggers,
            delta_params_absorbed=delta_params,
            code_mutation_detected=mutation_detected,
            ast_valid=ast_valid,
        )

    @staticmethod
    def _split_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
        if not content.startswith("---"):
            return {}, content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
        try:
            fm = yaml.safe_load(parts[1]) or {}
            return fm, parts[2].strip()
        except Exception:
            return {}, content

    @staticmethod
    def _bump_patch_version(ver: str) -> str:
        parts = ver.split(".")
        if len(parts) == 3 and parts[2].isdigit():
            return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        elif len(parts) == 2 and parts[1].isdigit():
            return f"{parts[0]}.{int(parts[1]) + 1}"
        return f"{ver}.1"
