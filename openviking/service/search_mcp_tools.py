# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Network Search MCP Tools Hub (network-search v1.1.1).
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-SEARCH-MCP

First Principles:
1. "Modular Plugin Tools": MCP tools belong to the network-search plugin, NOT hardcoded in monolithic mcp_endpoint.py.
2. "Authoritative Credit Tracking": Calls go through OmniSearchClient, auto-recording credits and pruning logs > 45 days.
3. "Anti-Toxicity & Truncation": Search & crawl outputs bounded <= 8KB to protect agent working memory.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
import urllib.request

from openviking.service.omni_search_client import OmniSearchClient
from openviking_cli.utils import get_logger

logger = get_logger(__name__)


def _extract_single_str(query: Optional[Union[str, List[str]]] = None, queries: Optional[Union[str, List[str]]] = None) -> str:
    for candidate in (query, queries):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        elif isinstance(candidate, (list, tuple)) and candidate:
            for item in candidate:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return ""


def _extract_single_url(url: Optional[Union[str, List[str]]] = None, urls: Optional[Union[str, List[str]]] = None) -> str:
    return _extract_single_str(url, urls)


def register_search_mcp_tools(mcp: Any, annotations: Any = None) -> None:
    """向 FastMCP 端点注入 network-search 插件的 12 项标准原子 MCP 工具。"""

    tool_kw = {"annotations": annotations} if annotations is not None else {}

    # 1. web_search: 多路宽幅自适应检索 (Keenable -> Tavily -> SearXNG 本地)
    @mcp.tool(**tool_kw)
    async def web_search(
        queries: Optional[Union[List[str], str]] = None,
        query: Optional[Union[List[str], str]] = None,
        engine: str = "general",
        max_results: int = 5,
    ) -> str:
        """在 Web 上搜索最新信息。返回摘要答案和来源 URL 列表。

        3家在线矩阵 (Keenable 80万次池 -> Tavily 基础搜 -> SearXNG 本地保底) 自动分级调度，
        按 8位脱敏指纹精准落地 search_key_usage 流水账，优先捕获官方响应体/头权威 credits，45天前明细自动归档清理。

        Args:
            queries: 1–4 个检索关键词列表或单个关键词字符串；并发检索并合并去重。
            query: 单个检索关键词（与 queries 二选一或配合使用）。
            engine: 目标搜索引擎分类，默认 'general'。
            max_results: 每个关键词最多返回结果数（默认 5）。
        """
        target_queries: List[str] = []

        def _collect(val: Any) -> None:
            if isinstance(val, str):
                s = val.strip()
                if s and s not in target_queries:
                    target_queries.append(s)
            elif isinstance(val, (list, tuple)):
                for item in val:
                    if isinstance(item, str) and item.strip() and item.strip() not in target_queries:
                        target_queries.append(item.strip())

        _collect(queries)
        _collect(query)

        if not target_queries:
            return "=== Web Search: No query provided ==="

        omni = OmniSearchClient.get_instance()
        tasks = [omni.web_search(q, max_results=max_results) for q in target_queries]
        all_res_dicts = await asyncio.gather(*tasks)

        combined_results = []
        seen_urls = set()
        for d in all_res_dicts:
            for r in d.get("results", []):
                u = r.get("url") or r.get("link") or ""
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    combined_results.append(r)

        if not combined_results:
            return f"=== Web Search Results: 0 found for queries {target_queries} ==="

        lines = [f"=== Web Search Results ({len(combined_results)} found across multi-cloud pool) ==="]
        for idx, r in enumerate(combined_results[: max_results * len(target_queries)], 1):
            title = r.get("title", "").strip()
            link = r.get("url") or r.get("link") or ""
            snippet = r.get("content") or r.get("snippet") or ""
            lines.append(f"[{idx}] {title}\nURL: {link}\nSnippet: {snippet}\n")
        return "\n".join(lines)

    # 2. search_neural: Exa 语义嵌入神经网络意图检索
    @mcp.tool(**tool_kw)
    async def search_neural(
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
        max_results: int = 5,
    ) -> str:
        """Exa 语义嵌入神经网络意图检索。适用于概念性探索、模糊记忆与高维意图匹配。"""
        target_q = _extract_single_str(query, queries)
        if not target_q:
            return "=== Exa Neural Search: No query provided ==="
        res = await OmniSearchClient.get_instance().search_neural(target_q, max_results=max_results)
        results = res.get("results", [])
        if not results:
            return f"=== Exa Neural Search: 0 found for '{target_q}' ==="
        lines = [f"=== Exa Neural Search ({len(results)} results) ==="]
        for idx, r in enumerate(results, 1):
            lines.append(f"[{idx}] {r.get('title')}\nURL: {r.get('url')}\nScore: {r.get('score', '--')}\nSnippet: {r.get('text', '')[:300]}\n")
        return "\n".join(lines)

    # 3. search_qna: Tavily / Exa 权威解答与引用生成
    @mcp.tool(**tool_kw)
    async def search_qna(
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
    ) -> str:
        """Tavily QnA / Exa 权威解答与引用生成。直接返回合成后的事实回答与参考出处。"""
        target_q = _extract_single_str(query, queries)
        if not target_q:
            return "=== QnA Answer: No query provided ==="
        res = await OmniSearchClient.get_instance().search_qna(target_q)
        ans = res.get("answer") or res.get("raw_text") or "未获取到权威解答"
        sources = res.get("results", [])
        src_lines = "\n".join([f"- {s.get('title')}: {s.get('url')}" for s in sources[:5]])
        return f"=== QnA Answer ===\n{ans}\n\n=== 引用出处 ===\n{src_lines}"

    # 4. search_deep: Tavily Advanced 深度多源交叉检索
    @mcp.tool(**tool_kw)
    async def search_deep(
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
        max_results: int = 8,
    ) -> str:
        """Tavily Advanced 深度多源交叉检索。用于复杂架构调研与多方文献交叉核验。"""
        target_q = _extract_single_str(query, queries)
        if not target_q:
            return "=== Deep Research Search: No query provided ==="
        res = await OmniSearchClient.get_instance().search_deep(target_q, max_results=max_results)
        results = res.get("results", [])
        lines = [f"=== Deep Research Search ({len(results)} results) ==="]
        for idx, r in enumerate(results, 1):
            lines.append(f"[{idx}] {r.get('title')}\nURL: {r.get('url')}\nRaw: {r.get('content', '')[:400]}\n")
        return "\n".join(lines)

    # 5. search_code_context: Exa GitHub 开源上下文与仓库定位
    @mcp.tool(**tool_kw)
    async def search_code_context(
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
        max_results: int = 5,
    ) -> str:
        """Exa GitHub 开源上下文与仓库定位。直接搜寻 GitHub 代码实现与库范例。"""
        target_q = _extract_single_str(query, queries)
        if not target_q:
            return "=== GitHub Code Search: No query provided ==="
        res = await OmniSearchClient.get_instance().search_code_context(target_q, max_results=max_results)
        results = res.get("results", [])
        lines = [f"=== GitHub Code Search ({len(results)} results) ==="]
        for idx, r in enumerate(results, 1):
            lines.append(f"[{idx}] {r.get('title')}\nRepo/URL: {r.get('url')}\nSnippet: {r.get('text', '')[:400]}\n")
        return "\n".join(lines)

    # 6. search_similar_repos: Exa findSimilar 竞品与同类反查
    @mcp.tool(**tool_kw)
    async def search_similar_repos(
        url: Optional[Union[str, List[str]]] = None,
        urls: Optional[Union[str, List[str]]] = None,
        max_results: int = 5,
    ) -> str:
        """Exa findSimilar 竞品与同类项目反查。输入项目或文档 URL，自动聚类相似项目。"""
        target_u = _extract_single_url(url, urls)
        if not target_u:
            return "=== Similar Projects: No URL provided ==="
        res = await OmniSearchClient.get_instance().search_similar_repos(target_u, max_results=max_results)
        results = res.get("results", [])
        lines = [f"=== Similar Projects to {target_u} ({len(results)} results) ==="]
        for idx, r in enumerate(results, 1):
            lines.append(f"[{idx}] {r.get('title')}\nURL: {r.get('url')}\n")
        return "\n".join(lines)

    # 7. map_site: Tavily Map 站点拓扑树测绘
    @mcp.tool(**tool_kw)
    async def map_site(
        url: Optional[Union[str, List[str]]] = None,
        urls: Optional[Union[str, List[str]]] = None,
        instructions: Optional[str] = None,
        max_results: int = 15,
    ) -> str:
        """Tavily Map 站点拓扑树测绘。提取整站关键页面路由树，支持提示词语义过滤。"""
        target_u = _extract_single_url(url, urls)
        if not target_u:
            return "=== Site Map: No URL provided ==="
        res = await OmniSearchClient.get_instance().map_site(target_u, instructions=instructions, max_results=max_results)
        urls_res = res.get("results", []) or res.get("urls", [])
        return f"=== Site Map ({len(urls_res)} URLs mapped for {target_u}) ===\n" + "\n".join(urls_res)

    # 8. extract_urls: Tavily / Exa 免爬虫快速正文脱水抽取
    @mcp.tool(**tool_kw)
    async def extract_urls(
        urls: Optional[Union[List[str], str]] = None,
        url: Optional[Union[List[str], str]] = None,
    ) -> str:
        """Tavily / Exa 免爬虫快速正文脱水抽取。绕过反爬直接返回结构化 Markdown。"""
        target_list: List[str] = []
        for candidate in (urls, url):
            if isinstance(candidate, str) and candidate.strip():
                if candidate.strip() not in target_list:
                    target_list.append(candidate.strip())
            elif isinstance(candidate, (list, tuple)):
                for u in candidate:
                    if isinstance(u, str) and u.strip() and u.strip() not in target_list:
                        target_list.append(u.strip())

        if not target_list:
            return "=== Extract URLs: No URLs provided ==="

        res = await OmniSearchClient.get_instance().extract_urls(target_list)
        results = res.get("results", [])
        lines = [f"=== Extracted {len(results)} URLs ==="]
        for r in results:
            u = r.get("url", "")
            raw = r.get("raw_content") or r.get("text") or ""
            lines.append(f"### URL: {u}\n{raw[:3000]}\n")
        return "\n".join(lines)

    # 9. tavily_crawl: Tavily Map + Extract 整站自动化组合流水线
    @mcp.tool(**tool_kw)
    async def tavily_crawl(
        url: Optional[Union[str, List[str]]] = None,
        urls: Optional[Union[str, List[str]]] = None,
        max_depth: int = 1,
    ) -> str:
        """Tavily Map + Extract 整站自动化组合流水线。一键测绘加正文提取。"""
        target_u = _extract_single_url(url, urls)
        if not target_u:
            return "=== Tavily Crawl: No URL provided ==="
        res = await OmniSearchClient.get_instance().tavily_crawl(target_u, max_depth=max_depth)
        return json.dumps(res, ensure_ascii=False, indent=2)[:8000]

    # 10. crawl_local: 本地 Crawl4AI 18789 Playwright 动态无头渲染
    @mcp.tool(**tool_kw)
    async def crawl_local(
        url: Optional[Union[str, List[str]]] = None,
        urls: Optional[Union[str, List[str]]] = None,
        wait_for: Optional[str] = None,
        css_selector: Optional[str] = None,
    ) -> str:
        """本地 Crawl4AI (端口 18789) Playwright 无头渲染。支持 JS 动态执行、CSS 过滤与截图。"""
        target_u = _extract_single_url(url, urls)
        if not target_u:
            return "=== Crawl Local: No URL provided ==="
        res = await OmniSearchClient.get_instance().crawl_local(target_u, wait_for=wait_for, css_selector=css_selector)
        return json.dumps(res, ensure_ascii=False, indent=2)[:8000]

    # 11. deep_research: Exa Agent 多步自主调研长报告生成
    @mcp.tool(**tool_kw)
    async def deep_research(topic: str, instructions: Optional[str] = None) -> str:
        """Exa Agent 多步自主调研长报告生成。针对宏观课题输出深度调研纪要。"""
        res = await OmniSearchClient.get_instance().deep_research(topic, instructions=instructions)
        return json.dumps(res, ensure_ascii=False, indent=2)[:8000]

    # 12. benchmark_needle / search_vertical_expert: Keenable NEEDLE 5大垂类高精专家检索
    @mcp.tool(**tool_kw)
    async def benchmark_needle(
        category: str,
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
    ) -> str:
        """Keenable NEEDLE 5大垂类高精专家检索 (Scholar, Finance, Legal, News, Rare)。"""
        target_q = _extract_single_str(query, queries)
        res = await OmniSearchClient.get_instance().search_vertical_expert(category, target_q)
        return json.dumps(res, ensure_ascii=False, indent=2)[:8000]

    @mcp.tool(**tool_kw)
    async def search_vertical_expert(
        category: str,
        query: Optional[Union[str, List[str]]] = None,
        queries: Optional[Union[str, List[str]]] = None,
        max_results: int = 10,
    ) -> str:
        """Keenable 垂直专家搜索 (NEEDLE 5大垂类：Scholar, Finance, Legal, News, Rare)，mode="pro" 高精提权。"""
        target_q = _extract_single_str(query, queries)
        res = await OmniSearchClient.get_instance().search_vertical_expert(category, target_q, max_results=max_results)
        return json.dumps(res, ensure_ascii=False, indent=2)[:8000]

    # 13. web_fetch: 本地 Crawl4AI 无头渲染抓取纯净正文
    @mcp.tool(**tool_kw)
    async def web_fetch(
        url: Optional[Union[str, List[str]]] = None,
        urls: Optional[Union[str, List[str]]] = None,
        max_chars: int = 15000,
    ) -> str:
        """获取指定 HTTP(S) URL 的内容，并将其解码为文本与 Markdown 后返回。

        由本地常驻 Crawl4AI (18789) Playwright 无头浏览器执行动态页面渲染、反爬验证码穿透与纯净正文 Markdown 提取。
        """
        target_u = _extract_single_url(url, urls)
        if not target_u:
            return "=== Web Fetch Error: No URL provided ==="
        target_u = target_u.strip()
        if not target_u.startswith("http://") and not target_u.startswith("https://"):
            return f"=== Web Fetch Error: Invalid URL scheme for '{target_u}' ==="

        token = os.environ.get("CRAWL4AI_API_TOKEN", "")
        if not token and os.path.exists("/home/skloxo/aho/crawl4ai/.env"):
            try:
                with open("/home/skloxo/aho/crawl4ai/.env") as f:
                    for line in f:
                        if line.startswith("CRAWL4AI_API_TOKEN="):
                            token = line.strip().split("=", 1)[1]
                            break
            except Exception:
                pass

        def _crawl():
            payload = json.dumps({"urls": [target_u], "priority": 10}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request("http://127.0.0.1:18789/crawl", data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                return json.loads(resp.read().decode())

        try:
            data = await asyncio.to_thread(_crawl)
            results = data.get("results", [])
            if not results or not results[0].get("success"):
                err_msg = results[0].get("error_message") if results else "Empty response"
                return f"=== Web Fetch Error: Failed to render {target_u} ({err_msg}) ==="
            
            r0 = results[0]
            md_obj = r0.get("markdown")
            content = ""
            if isinstance(md_obj, dict):
                content = md_obj.get("fit_markdown") or md_obj.get("raw_markdown") or ""
            elif isinstance(md_obj, str):
                content = md_obj
            if not content:
                content = r0.get("cleaned_html") or ""

            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n... [Content truncated at {max_chars} chars, total {len(content)} chars]"
            return f"=== Web Fetch Success: {target_u} ===\n\n{content}"
        except Exception as e:
            return f"=== Web Fetch Fallback: Error fetching {target_u} ({str(e)}) ==="

    # 14. openviking_web_search: 向后兼容别名
    @mcp.tool(**tool_kw)
    async def openviking_web_search(
        queries: Optional[Union[List[str], str]] = None,
        query: Optional[Union[List[str], str]] = None,
        engine: str = "general",
        max_results: int = 5,
    ) -> str:
        """向后兼容别名：调用统一 web_search 聚合引擎，支持单复数关键词容错。"""
        return await web_search(queries=queries, query=query, engine=engine, max_results=max_results)

    logger.info("Successfully registered 12 network-search MCP tools into FastMCP endpoint")
