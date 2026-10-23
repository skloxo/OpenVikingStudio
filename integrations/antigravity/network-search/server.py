#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Network Search Gateway FastMCP Server (network-search v1.1.2).
SSOT: integrations/antigravity/network-search/

First Principles:
1. "Orthogonal Decoupling": Dedicated microservice on port 18888.
2. "12 Standardized Atomic MCP Tools": Covering multi-cloud rotation, academic/finance/code retrieval, and headless dynamic rendering.
3. "Fail-Safe Proxying": Relays calls to local Search Gateway (:18888) with graceful offline diagnostics.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

mcp = FastMCP("network-search")

GATEWAY_URL = os.environ.get("SEARCH_GATEWAY_URL", "http://127.0.0.1:18888").rstrip("/")
DEFAULT_TIMEOUT = 15.0


def _call_gateway(endpoint: str, data: Optional[Dict[str, Any]] = None) -> str:
    """内部通用网关请求转发器。"""
    url = f"{GATEWAY_URL}{endpoint}"
    try:
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        else:
            req = urllib.request.Request(url, method="GET")

        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and "results" in parsed:
                    lines = [f"=== Search Gateway Results ({len(parsed['results'])}) ==="]
                    for idx, r in enumerate(parsed["results"][:10], 1):
                        title = r.get("title", "").strip()
                        link = r.get("url") or r.get("link") or ""
                        snippet = r.get("content") or r.get("snippet") or r.get("text") or ""
                        lines.append(f"[{idx}] {title}\nURL: {link}\nSnippet: {snippet[:300]}\n")
                    return "\n".join(lines)
                elif isinstance(parsed, dict) and "text" in parsed:
                    return parsed["text"]
                return body
            except Exception:
                return body
    except Exception as e:
        return f"[Search Gateway Offline/Error] 无法连接搜索网关 ({url}): {e}"


@mcp.tool
def web_search(query: str, max_results: int = 5) -> str:
    """在 Web 上搜索最新信息。多路宽幅自适应检索 (Keenable 80万次池 -> Tavily -> SearXNG 本地保底)。"""
    return _call_gateway("/v1/search", {"query": query, "limit": max_results})


@mcp.tool
def search_academic(query: str, max_results: int = 5) -> str:
    """学术论文与专业期刊专项检索。优先匹配 Google Scholar 与 Semantic Scholar 数据集。"""
    return _call_gateway("/v1/search", {"query": query, "category": "academic", "limit": max_results})


@mcp.tool
def search_finance(query: str, max_results: int = 5) -> str:
    """财经要闻与上市公司公开信息快搜。检索最新财报、市场行情与研报资讯。"""
    return _call_gateway("/v1/search", {"query": query, "category": "finance", "limit": max_results})


@mcp.tool
def search_code(query: str, max_results: int = 5) -> str:
    """GitHub/GitLab 源码与算法实现定位。直达权威代码实现与库范例。"""
    return _call_gateway("/v1/search", {"query": query, "category": "code", "limit": max_results})


@mcp.tool
def search_news(query: str, max_results: int = 5) -> str:
    """实时新闻资讯与突发快讯秒级获取。聚焦时效性新闻与政策动态。"""
    return _call_gateway("/v1/search", {"query": query, "category": "news", "limit": max_results})


@mcp.tool
def search_deep(query: str, max_results: int = 8) -> str:
    """深度推演宽幅搜索。自动进行多关键词并发扇出与文献交叉验证。"""
    return _call_gateway("/v1/search", {"query": query, "mode": "deep", "limit": max_results})


@mcp.tool
def web_fetch(url: str) -> str:
    """基础网页正文脱水提取。过滤 HTML 噪音与广告脚本，返回精纯 Markdown 正文。"""
    return _call_gateway("/v1/fetch", {"url": url, "headless": False})


@mcp.tool
def web_fetch_deep(url: str) -> str:
    """深度无头浏览器渲染抓取。支持本地 Playwright 动态 SPA 单页应用渲染与反爬穿透。"""
    return _call_gateway("/v1/fetch", {"url": url, "headless": True})


@mcp.tool
def search_provider_status() -> str:
    """检查当前 26 个 Key 矩阵与渠道健康度 (Keenable、Exa、Tavily、SearXNG、Crawl4AI)。"""
    return _call_gateway("/v1/status")


@mcp.tool
def search_accounting_summary() -> str:
    """查看历史搜索开销与配额流水账。统计各渠道真实 Credits 消耗与 45 天滚动归档态势。"""
    return _call_gateway("/v1/accounting/summary")


@mcp.tool
def search_rotate_keys() -> str:
    """手动触发失效 Key 轮询或权重自愈。重置 429 冷却标记并重新均衡各池配额。"""
    return _call_gateway("/v1/keys/rotate", {})


@mcp.tool
def search_key_audit() -> str:
    """导出各搜索引擎调用明细与响应时延日志。输出脱敏 SHA256 指纹审计数据。"""
    return _call_gateway("/v1/keys/audit")


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        port = int(os.environ.get("SEARCH_GATEWAY_PORT", "18888"))
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")
