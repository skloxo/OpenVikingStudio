# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VikingFS Skill Package Router & Dynamic KNN Deduplication (Card-96).

核心物理公理:
  1. 动态近邻裕度 (Margin-based KNN): 废黜死阈值，采用 Top-1 vs Top-2 Margin 智能判别同质化与领域归属；
  2. 领域技能包规范落盘: PACKAGE.yaml + INDEX.md + subskills/ 树状架构收敛顶级目录；
  3. 资产相对路径重写 (Path Rewriter Hook): 统一重写 `${PACKAGE_ROOT}/subskills/.../scripts` 杜绝 404。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml


class RouteAction(str, Enum):
    """路由决策动作枚举。"""
    MERGE = "MERGE"                  # 高置信度同质化重复，送入 Card-97 差分融合
    PACKAGE_ADD = "PACKAGE_ADD"      # 同领域已有包，追加为该领域子技能
    NEW_PACKAGE = "NEW_PACKAGE"      # 全新或无近邻领域，创建独立领域包


@dataclass
class RouteDecision:
    """路由分析决策产物。"""
    action: RouteAction
    target_package: str
    top1_candidate: Optional[str] = None
    top1_score: float = 0.0
    top2_candidate: Optional[str] = None
    top2_score: float = 0.0
    margin: float = 0.0
    rationale: str = ""


class PathRewriterHook:
    """技能资产相对路径改写钩子，防止归包后 scripts 路径断裂。"""

    SCRIPT_PATH_RE = re.compile(r"(?:\./)?(scripts/[a-zA-Z0-9_\-\./]+)")

    @classmethod
    def rewrite_paths(cls, content: str, package_name: str, skill_name: str) -> str:
        """将内部脚本引用重写为绝对/环境锚定的包内路径。"""
        replacement = rf"${{PACKAGE_ROOT}}/subskills/{skill_name}/\1"
        return cls.SCRIPT_PATH_RE.sub(replacement, content)


class SkillPackageRouter:
    """动态 KNN 查重与领域包自动路由编排器。"""

    def __init__(self, vault_root: Optional[Path] = None):
        self._vault_root = vault_root or (Path.home() / ".openviking" / "data" / "viking" / "default" / "skills")

    def analyze_routing(
        self,
        skill_name: str,
        content: str,
        existing_skills: List[Dict[str, Any]],
    ) -> RouteDecision:
        """基于动态 KNN 近邻与 Margin 分析进行确定性路由决策。"""
        incoming_domain = self._extract_domain(content) or skill_name
        if not existing_skills:
            return RouteDecision(
                action=RouteAction.NEW_PACKAGE,
                target_package=incoming_domain,
                top1_candidate=None,
                top1_score=0.0,
                rationale="Empty library: initiating new domain package.",
            )

        incoming_tokens = self._tokenize(content)
        scored_candidates: List[Tuple[str, str, float]] = []

        for item in existing_skills:
            cand_name = item.get("name", "unknown")
            cand_content = item.get("content", "")
            cand_domain = item.get("domain", "")
            cand_tokens = self._tokenize(cand_content)

            score = self._compute_hybrid_similarity(
                incoming_tokens=incoming_tokens,
                candidate_tokens=cand_tokens,
                incoming_domain=incoming_domain,
                candidate_domain=cand_domain,
            )
            scored_candidates.append((cand_name, cand_domain, score))

        scored_candidates.sort(key=lambda x: x[2], reverse=True)
        top1_name, top1_domain, top1_score = scored_candidates[0]
        top2_name, _, top2_score = scored_candidates[1] if len(scored_candidates) > 1 else (None, "", 0.0)
        margin = max(0.0, top1_score - top2_score)

        # 规则1: 高度相似 (Score >= 0.85 且 Margin >= 0.08, 或 Score >= 0.95) -> MERGE
        if (top1_score >= 0.85 and margin >= 0.08) or top1_score >= 0.95:
            target_pkg = top1_domain or incoming_domain
            return RouteDecision(
                action=RouteAction.MERGE,
                target_package=target_pkg,
                top1_candidate=top1_name,
                top1_score=round(top1_score, 4),
                top2_candidate=top2_name,
                top2_score=round(top2_score, 4),
                margin=round(margin, 4),
                rationale=f"High semantic overlap ({top1_score:.2f}) with distinct top-1 margin ({margin:.2f}).",
            )

        # 规则2: 中高相似或同领域 (Score >= 0.60 或 同 domain) -> PACKAGE_ADD
        if top1_score >= 0.60 or (top1_domain and top1_domain.lower() == incoming_domain.lower()):
            target_pkg = top1_domain or incoming_domain
            return RouteDecision(
                action=RouteAction.PACKAGE_ADD,
                target_package=target_pkg,
                top1_candidate=top1_name,
                top1_score=round(top1_score, 4),
                top2_candidate=top2_name,
                top2_score=round(top2_score, 4),
                margin=round(margin, 4),
                rationale=f"Domain match ({target_pkg}) with moderate novelty. Grouping into domain package.",
            )

        # 规则3: 低相似度且不同领域 -> NEW_PACKAGE
        return RouteDecision(
            action=RouteAction.NEW_PACKAGE,
            target_package=incoming_domain,
            top1_candidate=top1_name,
            top1_score=round(top1_score, 4),
            top2_candidate=top2_name,
            top2_score=round(top2_score, 4),
            margin=round(margin, 4),
            rationale=f"Novel domain pattern detected (top score: {top1_score:.2f}). Establishing new domain package.",
        )

    def materialize_package(
        self,
        package_name: str,
        subskills: List[Tuple[str, str]],
    ) -> Path:
        """结构化将技能整编入 PACKAGE.yaml + INDEX.md + subskills/ 树状架构。"""
        pkg_dir = self._vault_root / "packages" / package_name
        subskills_dir = pkg_dir / "subskills"
        subskills_dir.mkdir(parents=True, exist_ok=True)

        subskill_names: List[str] = []
        for s_name, s_content in subskills:
            s_dir = subskills_dir / s_name
            s_dir.mkdir(parents=True, exist_ok=True)
            rewritten_content = PathRewriterHook.rewrite_paths(
                content=s_content,
                package_name=package_name,
                skill_name=s_name,
            )
            (s_dir / "SKILL.md").write_text(rewritten_content, encoding="utf-8")
            subskill_names.append(s_name)

        # 1. Write PACKAGE.yaml
        pkg_meta = {
            "name": package_name,
            "version": "1.0.0",
            "domain": package_name,
            "description": f"Domain package grouping {len(subskills)} unified skills for {package_name}.",
            "subskills": subskill_names,
        }
        with open(pkg_dir / "PACKAGE.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(pkg_meta, f, sort_keys=False)

        # 2. Write INDEX.md
        index_lines = [
            f"# Domain Package: {package_name}",
            "",
            f"This package organizes {len(subskills)} subskills under domain `{package_name}`.",
            "",
            "## Available Subskills",
            "",
        ]
        for name in subskill_names:
            index_lines.append(f"- [{name}](./subskills/{name}/SKILL.md)")
        index_lines.append("")
        (pkg_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

        return pkg_dir

    def _compute_hybrid_similarity(
        self,
        incoming_tokens: Set[str],
        candidate_tokens: Set[str],
        incoming_domain: str,
        candidate_domain: str,
    ) -> float:
        """计算词元 Jaccard 与领域亲和度的混合相似度分值。"""
        if not incoming_tokens or not candidate_tokens:
            return 0.0

        intersection = len(incoming_tokens & candidate_tokens)
        union = len(incoming_tokens | candidate_tokens)
        jaccard = intersection / union if union > 0 else 0.0

        domain_bonus = 0.25 if (incoming_domain and candidate_domain and incoming_domain.lower() == candidate_domain.lower()) else 0.0
        return min(1.0, jaccard * 0.75 + domain_bonus)

    @staticmethod
    def _tokenize(content: str) -> Set[str]:
        words = re.findall(r"[a-zA-Z0-9_\-]+", content.lower())
        return {w for w in words if len(w) > 2}

    @staticmethod
    def _extract_domain(content: str) -> Optional[str]:
        match = re.search(r"domain:\s*([a-zA-Z0-9_\-]+)", content)
        return match.group(1).strip() if match else None
