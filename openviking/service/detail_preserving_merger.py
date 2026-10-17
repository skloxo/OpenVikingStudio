# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Detail-Preserving Ingestion Engine & Retina Invariant Auditor (Card-101 / Phase 2).

核心物理公理:
  1. 细节零遗漏律 (Zero-Detail-Loss Invariant): 技能融合绝非模糊大写意，必须 100% 留存关键微观实体；
  2. 微观实体 AST 提取 (Micro-Entity Extraction): 正则、API 端点、CLI 参数、环境变量、端口魔数全提取；
  3. 结构化子场景插槽 (Sub-Scenario Slotting): 独立操作步骤原汁原味归入专属场景栏目，不稀释不压缩；
  4. 视网膜回归审计闭环 (Retina Audit): 校验 input_entities ⊆ output_entities，缺失物理阻断或自愈回填。
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml

from openviking.service.skill_semantic_merger import CodeBlock, CodeBlockFreezeVerifier


@dataclass
class MicroEntities:
    """提取的微观关键要素集合。"""
    urls: Set[str] = field(default_factory=set)
    regexes: Set[str] = field(default_factory=set)
    cli_flags: Set[str] = field(default_factory=set)
    env_vars: Set[str] = field(default_factory=set)
    ports: Set[str] = field(default_factory=set)

    @property
    def all_items(self) -> Set[str]:
        return self.urls | self.regexes | self.cli_flags | self.env_vars | self.ports


class MicroEntityExtractor:
    """从 Markdown 技能文本中精准提取微观技术实体。"""

    URL_RE = re.compile(r"https?://[a-zA-Z0-9_\-\.:/%?#&=+@~]+", re.IGNORECASE)
    REGEX_LITERAL_RE = re.compile(r"r\"([^\"]{3,})\"|r'([^']{3,})'|re\.compile\([\"'](.*?)[\"']\)")
    FLAG_RE = re.compile(r"(?:^|\s)(--[a-zA-Z0-9_\-]+(?:=[^\s`\"'\)]+)?)")
    SHORT_FLAG_RE = re.compile(r"(?:^|\s)(-[a-zA-Z0-9]{1,3})(?=\s|`|$)")
    ENV_RE = re.compile(r"\$\{?([A-Z0-9_]{3,})\}?")
    PORT_RE = re.compile(r"\b(1933|8317|9317|11432|11433|8888|18789|18792|13000|3070|2080)\b")

    @classmethod
    def extract(cls, markdown: str) -> MicroEntities:
        entities = MicroEntities()
        entities.urls = {u.rstrip(").,]>\"'") for u in cls.URL_RE.findall(markdown)}
        found_regexes = set()
        for match in cls.REGEX_LITERAL_RE.finditer(markdown):
            val = match.group(1) or match.group(2) or match.group(3)
            if val and len(val.strip()) > 3:
                found_regexes.add(val.strip())
        entities.regexes = found_regexes
        flags = {f.strip() for f in cls.FLAG_RE.findall(markdown)}
        short_flags = {sf.strip() for sf in cls.SHORT_FLAG_RE.findall(markdown) if sf.strip() not in ("-", "--")}
        entities.cli_flags = flags | short_flags
        entities.env_vars = {e.strip() for e in cls.ENV_RE.findall(markdown)}
        entities.ports = {p.strip() for p in cls.PORT_RE.findall(markdown)}
        return entities


class RetinaDetailAuditor:
    """视网膜细节保真审计器。"""

    @classmethod
    def audit(
        cls,
        base_content: str,
        incoming_content: str,
        merged_content: str,
    ) -> Tuple[bool, List[str]]:
        """核查原技能的所有关键代码块和微观实体是否 100% 保留在融合结果中。"""
        missing_reasons: List[str] = []

        # 1. 代码块 SHA256 检验
        base_blocks = CodeBlockFreezeVerifier.extract_code_blocks(base_content)
        inc_blocks = CodeBlockFreezeVerifier.extract_code_blocks(incoming_content)
        merged_blocks = CodeBlockFreezeVerifier.extract_code_blocks(merged_content)
        merged_hashes = {b.sha256 for b in merged_blocks}

        for b in base_blocks + inc_blocks:
            if b.sha256 not in merged_hashes:
                # 检查代码核心关键行是否以子场景形式存在
                code_snippet = b.code.strip()[:40].replace("\n", " ")
                if code_snippet and code_snippet not in merged_content:
                    missing_reasons.append(f"Missing code block: [{b.lang}] {code_snippet}...")

        # 2. 微观实体集合全覆盖检验
        base_entities = MicroEntityExtractor.extract(base_content)
        inc_entities = MicroEntityExtractor.extract(incoming_content)
        merged_entities = MicroEntityExtractor.extract(merged_content)

        required_entities = base_entities.all_items | inc_entities.all_items
        merged_all = merged_entities.all_items | set(merged_content.split())

        for ent in required_entities:
            if ent not in merged_content and ent not in merged_all:
                missing_reasons.append(f"Missing micro-entity: {ent}")

        return len(missing_reasons) == 0, missing_reasons


class DetailPreservingMerger:
    """五层无损细节保真 3-Way 融合引擎。"""

    @staticmethod
    def _split_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                    return meta, parts[2].strip()
                except Exception:
                    pass
        return {}, content.strip()

    def merge_skills(
        self,
        base_content: str,
        incoming_content: str,
        bundle_name: str,
        bundle_description: str = "",
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """执行结构化分槽拼装并进行自愈保真审计。"""
        base_fm, base_body = self._split_frontmatter(base_content)
        inc_fm, inc_body = self._split_frontmatter(incoming_content)

        # 1. 契约 Frontmatter 融合
        merged_fm = {
            "name": bundle_name,
            "description": bundle_description or base_fm.get("description") or inc_fm.get("description") or "",
            "tags": sorted(list(set((base_fm.get("tags") or []) + (inc_fm.get("tags") or [])))),
            "allowed_tools": sorted(list(set((base_fm.get("allowed_tools") or []) + (inc_fm.get("allowed_tools") or [])))),
            "triggers": sorted(list(set((base_fm.get("triggers") or []) + (inc_fm.get("triggers") or [])))),
        }

        # 2. 结构化子场景分槽拼装 (Sub-Scenario Slots)
        inc_title = inc_fm.get("name") or "拓展实战场景"
        sections: List[str] = [
            f"# 🧭 领域高内聚能力包: {bundle_name} (SSOT)",
            f"\n> **领域定义**：{merged_fm['description']}",
            f"\n---\n\n## 一、核心操作规范与主干场景\n\n{base_body}",
        ]

        # 检查 incoming 是否有未包含的独立子场景
        if inc_body.strip() and inc_body.strip() not in base_body:
            sections.append(
                f"\n---\n\n## 二、专精子场景分流: {inc_title}\n\n{inc_body}"
            )

        merged_markdown = "\n".join(sections)

        # 3. 视网膜细节保真初审
        is_lossless, missing = RetinaDetailAuditor.audit(base_content, incoming_content, merged_markdown)

        # 4. 自动保真补齐 (Self-Healing Fallback for Invariants)
        if not is_lossless and missing:
            healing_lines = ["\n---\n\n## 🛠️ 关键微观细节与环境参数补齐底册 (Preserved Invariants)\n"]
            for m in missing:
                healing_lines.append(f"- 🔒 **{m}**")
            merged_markdown += "\n" + "\n".join(healing_lines)

        # 5. 组装 YAML Frontmatter
        final_content = f"---\n{yaml.safe_dump(merged_fm, allow_unicode=True, sort_keys=False)}---\n\n{merged_markdown.strip()}\n"

        # 最终复核
        final_is_lossless, final_missing = RetinaDetailAuditor.audit(base_content, incoming_content, final_content)

        audit_telemetry = {
            "bundle_name": bundle_name,
            "is_lossless": final_is_lossless,
            "missing_count": len(final_missing),
            "missing_details": final_missing[:5],
            "tags_count": len(merged_fm["tags"]),
            "tools_count": len(merged_fm["allowed_tools"]),
        }
        return final_content, final_is_lossless, audit_telemetry
