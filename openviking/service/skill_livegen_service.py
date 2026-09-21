# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill LiveGen Service — Interactive Skill Generator & Sandbox Evaluator (SSOT).

落实 BLUEPRINT.md Epic-LIVE-GEN (Milestone 3):
1. LIVEGEN-01: SKILL.md 规范脚手架生成与 YAML Frontmatter 语法强校验；
2. LIVEGEN-02: 沙盒隔离环境模拟 Agent 自然语言触发测试与置信度度量；
3. LIVEGEN-03: 一键校验与上架至 Viking 记忆中枢。
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field

from openviking.core.skill_loader import SkillLoader, validate_skill_format


class SkillScaffoldRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(description="技能名称 (kebab-case)")
    description: str = Field(description="技能说明与自然语言触发关键词")
    allowed_tools: List[str] = Field(default_factory=list, description="允许使用的工具列表")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    template_type: str = Field(default="standard", description="模板类型: standard, diagnosis, ui, workflow")


class SkillValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    valid: bool
    name: str
    description: str
    tags: List[str]
    allowed_tools: List[str]
    body_lines: int
    line_status: str
    errors: List[Dict[str, str]]
    warnings: List[Dict[str, str]]


class QuerySimulationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str
    matched: bool
    confidence: float
    matched_keywords: List[str]
    explanation: str


class SkillSimulationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill_name: str
    total_queries: int
    passed_queries: int
    pass_rate: float
    results: List[QuerySimulationItem]


class SkillPublishResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    success: bool
    skill_name: str
    target_path: str
    content_hash: str
    body_lines: int
    message: str


class SkillLiveGenService:
    """Skill Live Generator 在线技能创生核心引擎 (SSOT) — 严格单例。"""

    _instance: Optional[SkillLiveGenService] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._stats_lock = threading.Lock()
        self._total_scaffolds = 0
        self._total_validations = 0
        self._total_simulations = 0
        self._total_published = 0

    @classmethod
    def get_instance(cls) -> SkillLiveGenService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """测试隔离复位钩子。"""
        with cls._lock:
            cls._instance = None

    def generate_scaffold(self, req: SkillScaffoldRequest) -> str:
        """根据需求生成规范的 SKILL.md 初始骨架。"""
        with self._stats_lock:
            self._total_scaffolds += 1

        tools_str = " ".join(req.allowed_tools) if req.allowed_tools else ""
        tags_yaml = yaml.safe_dump(req.tags, default_flow_style=True).strip() if req.tags else "[]"

        body = self._render_template_body(req.template_type, req.name, req.description)
        return (
            f"---\n"
            f"name: {req.name}\n"
            f"description: {req.description}\n"
            f"allowed-tools: {tools_str}\n"
            f"tags: {tags_yaml}\n"
            f"---\n\n"
            f"{body}\n"
        )

    def validate_draft(self, content: str, strict: bool = True) -> SkillValidationResult:
        """对 SKILL.md 草稿执行全量静态与格式校验。"""
        with self._stats_lock:
            self._total_validations += 1

        val = validate_skill_format(content, strict=strict)
        body_lines = val.get("body_lines", 0)

        if body_lines > 500:
            line_status = "exceeded"
        elif body_lines > 400:
            line_status = "critical"
        elif body_lines > 300:
            line_status = "warning"
        elif body_lines >= 100:
            line_status = "sweet_spot"
        else:
            line_status = "compact"

        return SkillValidationResult(
            valid=val.get("valid", False),
            name=val.get("name", ""),
            description=val.get("description", ""),
            tags=val.get("tags", []),
            allowed_tools=val.get("allowed_tools", []),
            body_lines=body_lines,
            line_status=line_status,
            errors=val.get("errors", []),
            warnings=val.get("warnings", []),
        )

    def simulate_trigger(self, content: str, queries: List[str]) -> SkillSimulationResult:
        """沙盒环境模拟 Agent 自然语言触发测试。"""
        with self._stats_lock:
            self._total_simulations += 1

        try:
            parsed = SkillLoader.parse(content)
            name = parsed.get("name", "")
            description = parsed.get("description", "")
            tags = parsed.get("tags", [])
        except Exception:
            name = ""
            description = content[:200]
            tags = []

        keywords = self._extract_trigger_keywords(name, description, tags)
        results: List[QuerySimulationItem] = []
        passed_count = 0

        for q in queries:
            matched_kw: List[str] = []
            q_lower = q.lower()
            for kw in keywords:
                if kw.lower() in q_lower:
                    matched_kw.append(kw)

            # 置信度计算：命中关键词权重 + 字符重合比例
            if keywords:
                overlap_ratio = len(matched_kw) / min(len(keywords), 5)
            else:
                overlap_ratio = 0.0

            exact_hit = (name.lower() in q_lower) or any(t.lower() in q_lower for t in tags)
            confidence = min(1.0, 0.40 * float(exact_hit) + 0.60 * overlap_ratio)
            is_matched = confidence >= 0.35 or bool(matched_kw)

            if is_matched:
                passed_count += 1
                explanation = f"命中关键词: [{', '.join(matched_kw[:3])}]" if matched_kw else "命中技能名称/标签"
            else:
                explanation = "未提取到匹配意图特征"

            results.append(
                QuerySimulationItem(
                    query=q,
                    matched=is_matched,
                    confidence=round(confidence, 2),
                    matched_keywords=matched_kw,
                    explanation=explanation,
                )
            )

        pass_rate = round(passed_count / max(len(queries), 1), 2)
        return SkillSimulationResult(
            skill_name=name or "untitled-skill",
            total_queries=len(queries),
            passed_queries=passed_count,
            pass_rate=pass_rate,
            results=results,
        )

    def publish_skill(
        self,
        skill_name: str,
        content: str,
        base_dir: Optional[str] = None,
    ) -> SkillPublishResult:
        """校验并上架发布技能至存储目录。"""
        val = self.validate_draft(content, strict=True)
        if not val.valid:
            error_msgs = "; ".join(e.get("message", "") for e in val.errors)
            return SkillPublishResult(
                success=False,
                skill_name=skill_name,
                target_path="",
                content_hash="",
                body_lines=val.body_lines,
                message=f"校验失败阻断发布: {error_msgs}",
            )

        root = Path(base_dir) if base_dir else Path.home() / ".openviking" / "skills"
        target_folder = root / skill_name
        target_folder.mkdir(parents=True, exist_ok=True)
        target_file = target_folder / "SKILL.md"

        target_file.write_text(content, encoding="utf-8")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        with self._stats_lock:
            self._total_published += 1

        return SkillPublishResult(
            success=True,
            skill_name=skill_name,
            target_path=str(target_file),
            content_hash=content_hash,
            body_lines=val.body_lines,
            message="技能校验通过并已成功持久化上架",
        )

    def get_stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            return {
                "total_scaffolds": self._total_scaffolds,
                "total_validations": self._total_validations,
                "total_simulations": self._total_simulations,
                "total_published": self._total_published,
            }

    @staticmethod
    def _extract_trigger_keywords(name: str, description: str, tags: List[str]) -> List[str]:
        words = set()
        if name:
            words.update(part for part in re.split(r"[-_]", name) if len(part) >= 2)
        for t in tags:
            if t:
                words.add(t)

        # 细粒度分词与中英文 n-gram 候选
        segments = [s.strip() for s in re.split(r"[、，, \t\n/；;。与及和]+", description) if s.strip()]
        for seg in segments:
            if 2 <= len(seg) <= 10:
                words.add(seg)
            for n in (2, 3):
                for i in range(len(seg) - n + 1):
                    chunk = seg[i:i+n]
                    if not any(c in "的了是在有和与及" for c in chunk):
                        words.add(chunk)

        stop_words = {"this", "that", "with", "from", "when", "using", "用于", "包含", "进行", "以及"}
        return [w for w in words if w.lower() not in stop_words and len(w) >= 2]

    @staticmethod
    def _render_template_body(template_type: str, name: str, description: str) -> str:
        if template_type == "diagnosis":
            return (
                f"# {name} 故障诊断与根因分析 SOP\n\n"
                f"> **定位说明**：{description}\n\n"
                f"## 一、 核心公理与触发契约\n"
                f"- **第一性原理**：直击故障物理现场，严禁旁路伪修复。\n"
                f"- **Fail-Fast 契约**：日志前置截断分析，精准识别堆栈根因。\n\n"
                f"## 二、 标准执行工序 (SOP)\n"
                f"1. **日志收集**：提取最近 5 行异常错误特征；\n"
                f"2. **红灯测试**：优先编写失败测试用例复现缺陷；\n"
                f"3. **绿灯修复**：单Seam精准修复代码；\n"
                f"4. **门禁验证**：全量单元测试与安全扫描验证。\n\n"
                f"## 三、 绝对禁止红线 (Negative Boundaries)\n"
                f"- 🚫 严禁捕获异常后静默 `pass`；\n"
                f"- 🚫 严禁使用硬编码 sleep 轮询。\n"
            )
        elif template_type == "ui":
            return (
                f"# {name} 座舱级高密设计体系规范\n\n"
                f"> **视觉契约**：{description}\n\n"
                f"## 一、 三大物理公理\n"
                f"- **NO GREEN EVER 🚫**：全系统禁用绿色，正常中性灰，偏离基线上色；\n"
                f"- **座舱最高信息密度律**：字号硬下限 $\\ge 12\\text{{px}}$ (`text-xs`)，数值等宽；\n"
                f"- **$X/Y$ 进度契约**：完成才 $+1$，严禁预支。\n\n"
                f"## 二、 组件设计与布局 SOP\n"
                f"1. **容器卡片**：内边距收敛至 `p-3`~`p-3.5`，微圆角 `rounded-md`；\n"
                f"2. **状态胶囊**：正向使用冰青 `cyan-500`，异常使用玫瑰红 `rose-500`。\n\n"
                f"## 三、 绝对禁止红线\n"
                f"- 🚫 严禁出现 `< 12px` 微字（包括 11px/10px/8px）；\n"
                f"- 🚫 严禁硬编码 Mock 假数字。\n"
            )
        else:
            return (
                f"# {name} 标准工程技能规范\n\n"
                f"> **核心概述**：{description}\n\n"
                f"## 一、 领域原则与接口契约\n"
                f"- 遵循单一真相源 (SSOT) 原则；\n"
                f"- 保持代码在 100~300 行黄金甜点区。\n\n"
                f"## 二、 执行流程\n"
                f"1. 接收自然语言意图并自动解析参数；\n"
                f"2. 调用相关 MCP 工具执行业务动作；\n"
                f"3. 校验产物并交付验证清单。\n\n"
                f"## 三、 边界与异常处理\n"
                f"- 发生网络异常时执行指数退避重试；\n"
                f"- 遇到未定义错误优雅降级。\n"
            )
