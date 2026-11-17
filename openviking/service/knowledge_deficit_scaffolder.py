# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Reflection scaffolding, similarity clustering & dual-track routing helpers for Card-207."""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional, Sequence

TECH_ROUTE_KEYWORDS = (
    "api", "sdk", "http", "https", "rest", "graphql", "grpc", "fastapi", "pydantic",
    "python", "typescript", "javascript", "react", "vite", "tailwind", "docker",
    "kubernetes", "k8s", "nginx", "redis", "sqlite", "postgres", "oauth", "jwt",
    "mcp", "git", "linux", "wsl", "systemd", "rfc", "spec", "algorithm", "rag",
    "embedding", "bm25", "rerank", "langchain", "langgraph", "llm", "cuda", "vllm",
)

INTERNAL_ROUTE_KEYWORDS = (
    "工号", "分机", "电话", "手机", "邮箱", "部门", "团队", "负责人", "联系人",
    "华庭", "园区", "公寓", "门锁", "物业", "安防", "监控", "主机", "密码", "凭据",
    "账号", "审批", "流程", "值班", "楼栋", "机房", "专线", "跳板", "节点",
    "2080ti", "3070", "mac", "tide.red", "nvr", "sip", "voip",
)


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip())


def _extract_tokens(text: str) -> set[str]:
    norm = normalize_query(text).lower()
    words = set(re.findall(r"[a-z0-9_@.-]{2,}", norm))
    for run in re.findall(r"[\u4e00-\u9fff]+", norm):
        words.add(run)
        for i in range(len(run) - 1):
            words.add(run[i : i + 2])
    return words


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    na = math.sqrt(sum(a * a for a in vec_a))
    nb = math.sqrt(sum(b * b for b in vec_b))
    return (dot / (na * nb)) if (na > 0.0 and nb > 0.0) else 0.0


def compute_query_similarity(
    query_a: str,
    query_b: str,
    emb_a: Optional[Sequence[float]] = None,
    emb_b: Optional[Sequence[float]] = None,
) -> float:
    """Compute lexical + optional embedding similarity in [0.0, 1.0]."""
    na = normalize_query(query_a).lower()
    nb = normalize_query(query_b).lower()
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if emb_a and emb_b:
        cos = _cosine_similarity(emb_a, emb_b)
        if cos >= 0.85:
            return cos

    seq_ratio = SequenceMatcher(None, na, nb).ratio()
    tok_a, tok_b = _extract_tokens(na), _extract_tokens(nb)
    jaccard = (len(tok_a & tok_b) / len(tok_a | tok_b)) if (tok_a and tok_b) else 0.0
    containment = 0.0
    if len(na) >= 2 and len(nb) >= 2 and (na in nb or nb in na):
        ratio = min(len(na), len(nb)) / max(len(na), len(nb))
        containment = 0.78 if ratio >= 0.3 else 0.55
    return max(seq_ratio, jaccard, containment)


def extract_entity_and_category(query: str) -> tuple[str, str]:
    """Derive concise subject entity name and category from a missed query."""
    clean = normalize_query(query)
    stripped = re.sub(
        r"(的)?(联系方式|手机号|电话|分机|部门|工号|文档|配置|规范|架构|原理|怎么用|是什么|如何排查)\s*[?？]*$",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()
    entity = stripped[:64] if len(stripped) >= 2 else clean[:64]
    lower = clean.lower()
    if any(k in lower for k in ("工号", "分机", "手机", "电话", "部门", "联系人", "是谁")) or re.fullmatch(
        r"[\u4e00-\u9fff]{2,4}", entity
    ):
        return entity, "personnel_contact"
    if any(k in lower for k in ("api", "sdk", "mcp", "fastapi", "python", "http", "endpoint")):
        return entity, "technical_api"
    if any(k in lower for k in ("架构", "拓扑", "部署", "服务", "节点", "nginx", "docker", "systemd")):
        return entity, "system_architecture"
    if any(k in lower for k in ("流程", "规范", "审批", "制度", "sop", "合同", "预算")):
        return entity, "workflow_policy"
    return entity, "general_knowledge"


def classify_deficit_route(query: str, entity_category: str = "") -> str:
    """Route internal/private deficits to human_assistance and public concepts to autonomous_researcher."""
    lower = normalize_query(query).lower()
    strict_private = (
        "工号", "分机", "电话", "手机", "邮箱", "部门", "负责人", "联系人",
        "华庭", "园区", "公寓", "门锁", "物业", "安防", "监控", "主机", "密码", "凭据",
        "账号", "值班", "楼栋", "机房", "专线", "跳板", "2080ti", "3070", "mac", "tide.red", "nvr",
    )
    if entity_category == "personnel_contact" or any(k in lower for k in strict_private):
        return "human_assistance"
    if entity_category == "technical_api" or any(k in lower for k in TECH_ROUTE_KEYWORDS):
        return "autonomous_researcher"
    if any(k in lower for k in INTERNAL_ROUTE_KEYWORDS):
        return "human_assistance"
    if re.search(r"[a-zA-Z]{3,}", lower) and not re.search(r"[\u4e00-\u9fff]{2,4}\s*$", lower):
        return "autonomous_researcher"
    return "human_assistance"


def render_scaffold_markdown(record: Dict[str, Any]) -> str:
    """Build Stage-1 YAML Frontmatter + Markdown slot skeleton + Mermaid topology."""
    entity = record["entity_name"]
    category = record["entity_category"]
    route = record["suggested_route"]
    if category == "personnel_contact":
        slots = (
            "- **工号 / ID**: [待补充]\n"
            "- **所属部门 / 团队**: [待补充]\n"
            "- **联系电话 / 办公分机**: [待补充]\n"
            "- **核心负责业务**: [待补充]"
        )
        mermaid = f"graph TD\n    {entity} -->|隶属于| 待补充部门\n    {entity} -->|负责| 待补充项目或区域"
    elif route == "autonomous_researcher":
        slots = (
            "- **核心定义 / 协议版本**: [待补充]\n"
            "- **关键入口 / 接口契约**: [待补充]\n"
            "- **适用边界与常见坑点**: [待补充]\n"
            "- **权威参考链接**: [待补充]"
        )
        mermaid = f"graph LR\n    调用方 -->|请求| {entity}\n    {entity} -->|输出| 待补充产物或状态"
    else:
        slots = (
            "- **业务定位 / 归属系统**: [待补充]\n"
            "- **关键配置 / 物理锚点**: [待补充]\n"
            "- **标准处置路径 (SOP)**: [待补充]\n"
            "- **关联责任人与文档**: [待补充]"
        )
        mermaid = f"graph TD\n    问题触发 --> {entity}\n    {entity} -->|闭环方式| 待补充处理节点"

    return (
        "---\n"
        f"scaffold_id: \"{record['deficit_id']}\"\n"
        f"entity_name: \"{entity}\"\n"
        f"entity_category: \"{category}\"\n"
        f"deficit_level: \"high_frequency_miss\"\n"
        f"miss_count: {record['miss_count']}\n"
        f"status: \"{record['status']}\"\n"
        f"suggested_route: \"{route}\"\n"
        "---\n\n"
        f"# 待完善知识卡片: {entity}\n\n"
        "## 1. 核心属性槽位 (待填充)\n"
        f"{slots}\n\n"
        "## 2. 关系拓扑骨架 (Mermaid)\n"
        "```mermaid\n"
        f"{mermaid}\n"
        "```\n"
    )
