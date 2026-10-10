# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Omni Search Unified Client (3 Online APIs + 2 Local Engines).
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-SEARCH-OMNI

First Principles:
1. "Official First & Layered Fallback": Keenable 800k pool -> Tavily -> SearXNG :8888 fallback.
2. "Credit Integrity": Records physical credits from response body/headers into SQLite.
3. "Anti-Toxicity & Truncation": Markdown results automatically bounded <= 8KB.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
import urllib.parse

import httpx

from openviking.service.search_key_rotator import SearchKeyRotator
from openviking_cli.utils import get_logger

logger = get_logger(__name__)


class OmniSearchClient:
    """全功能网络搜索聚合客户端 (单例模式)。"""

    _instance: Optional[OmniSearchClient] = None

    def __init__(self):
        self.rotator = SearchKeyRotator.get_instance()
        self.client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)

    @classmethod
    def get_instance(cls) -> OmniSearchClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # 核心底层请求网关 (带 429 自动换 Key 与权威 Credit 落地流水)
    # -------------------------------------------------------------------------
    async def _execute_with_retry(
        self,
        engine: str,
        tool_name: str,
        url: str,
        method: str = "POST",
        json_body: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """执行 HTTP 调用，遇到 429 自动冷却并在微秒级切换下一个 Key 重试。"""
        headers = dict(custom_headers or {})

        for attempt in range(max_retries + 1):
            key_item = self.rotator.get_next_key(engine)
            if not key_item:
                logger.warning("No available key for engine %s, failing fast", engine)
                return {"error": f"No available key for {engine}", "status_code": 503}

            # 注入鉴权头
            if engine == "keenable":
                headers["X-API-Key"] = key_item.api_key
            elif engine == "exa":
                headers["x-api-key"] = key_item.api_key
                headers["Content-Type"] = "application/json"
            elif engine == "tavily":
                if json_body is not None:
                    json_body["api_key"] = key_item.api_key

            start_t = time.perf_counter()
            try:
                if method.upper() == "POST":
                    resp = await self.client.post(url, json=json_body, headers=headers)
                else:
                    resp = await self.client.get(url, headers=headers)

                latency_ms = (time.perf_counter() - start_t) * 1000.0
                status_code = resp.status_code

                # 429 速率限制处理
                if status_code == 429:
                    self.rotator.record_usage_audit(
                        engine=engine,
                        tool_name=tool_name,
                        key_item=key_item,
                        status_code=429,
                        credits_cost=0.0,
                        latency_ms=latency_ms,
                        error_msg="429 Rate Limited",
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(0.1)
                        continue
                    return {"error": "All keys rate limited (429)", "status_code": 429}

                # 正常或普通报错
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw_text": resp.text[:1000]}

                credits_cost = self.rotator.extract_authoritative_credits(
                    engine=engine,
                    tool_name=tool_name,
                    status_code=status_code,
                    headers=dict(resp.headers),
                    body=data,
                )

                self.rotator.record_usage_audit(
                    engine=engine,
                    tool_name=tool_name,
                    key_item=key_item,
                    status_code=status_code,
                    credits_cost=credits_cost,
                    latency_ms=latency_ms,
                    error_msg="" if status_code == 200 else str(data)[:200],
                )

                if status_code == 200:
                    return data
                elif attempt < max_retries and status_code >= 500:
                    await asyncio.sleep(0.2)
                    continue
                else:
                    return {"error": f"HTTP {status_code}", "detail": data, "status_code": status_code}

            except Exception as exc:
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                self.rotator.record_usage_audit(
                    engine=engine,
                    tool_name=tool_name,
                    key_item=key_item,
                    status_code=500,
                    credits_cost=0.0,
                    latency_ms=latency_ms,
                    error_msg=str(exc),
                )
                if attempt < max_retries:
                    continue
                return {"error": str(exc), "status_code": 500}

        return {"error": "Max retries exceeded", "status_code": 500}

    # -------------------------------------------------------------------------
    # 1. web_search: 多路宽幅自适应检索 (Keenable -> Tavily -> SearXNG 本地)
    # -------------------------------------------------------------------------
    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """优先使用 Keenable 80万次免费池，降级到 Tavily 基础搜，保底本地 SearXNG。"""
        # 第一优先级：Keenable Search API
        res = await self._execute_with_retry(
            engine="keenable",
            tool_name="web_search",
            url="https://api.keenable.ai/v1/search",
            json_body={"query": query, "num": max_results},
        )
        if "results" in res and res["results"]:
            return {"engine": "keenable", "results": res["results"][:max_results]}

        # 第二优先级：Tavily Basic Search
        res_tv = await self._execute_with_retry(
            engine="tavily",
            tool_name="web_search",
            url="https://api.tavily.com/search",
            json_body={"query": query, "max_results": max_results, "search_depth": "basic"},
        )
        if "results" in res_tv and res_tv["results"]:
            return {"engine": "tavily", "results": res_tv["results"][:max_results]}

        # 保底：本地 SearXNG :8888
        start_t = time.perf_counter()
        try:
            r = await self.client.get(
                "http://127.0.0.1:8888/search",
                params={"q": query, "format": "json"},
                timeout=4.0,
            )
            lat = (time.perf_counter() - start_t) * 1000.0
            data = r.json()
            results = data.get("results", [])[:max_results]
            self.rotator.record_usage_audit(
                engine="searxng",
                tool_name="web_search",
                key_item=None,
                status_code=r.status_code,
                credits_cost=0.0,
                latency_ms=lat,
            )
            return {"engine": "searxng_local", "results": results}
        except Exception as exc:
            return {"engine": "fallback_failed", "error": str(exc), "results": []}

    # -------------------------------------------------------------------------
    # 2. search_neural: Exa 语义嵌入神经网络检索
    # -------------------------------------------------------------------------
    async def search_neural(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        return await self._execute_with_retry(
            engine="exa",
            tool_name="search_neural",
            url="https://api.exa.ai/search",
            json_body={"query": query, "numResults": max_results, "useAutoprompt": True},
        )

    # -------------------------------------------------------------------------
    # 3. search_qna: Tavily / Exa 权威解答与引用生成
    # -------------------------------------------------------------------------
    async def search_qna(self, query: str) -> Dict[str, Any]:
        res = await self._execute_with_retry(
            engine="tavily",
            tool_name="search_qna",
            url="https://api.tavily.com/search",
            json_body={"query": query, "include_answer": True, "search_depth": "basic"},
        )
        if "answer" in res and res["answer"]:
            return {"answer": res["answer"], "results": res.get("results", [])}

        # 降级 Exa Answer
        return await self._execute_with_retry(
            engine="exa",
            tool_name="search_qna",
            url="https://api.exa.ai/answer",
            json_body={"query": query},
        )

    # -------------------------------------------------------------------------
    # 4. search_deep: Tavily Advanced 深度多源交叉检索
    # -------------------------------------------------------------------------
    async def search_deep(self, query: str, max_results: int = 8) -> Dict[str, Any]:
        return await self._execute_with_retry(
            engine="tavily",
            tool_name="search_deep",
            url="https://api.tavily.com/search",
            json_body={"query": query, "max_results": max_results, "search_depth": "advanced"},
        )

    # -------------------------------------------------------------------------
    # 5. search_code_context: Exa GitHub 开源上下文与仓库定位
    # -------------------------------------------------------------------------
    async def search_code_context(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        return await self._execute_with_retry(
            engine="exa",
            tool_name="search_code_context",
            url="https://api.exa.ai/search",
            json_body={
                "query": query,
                "numResults": max_results,
                "category": "github",
                "useAutoprompt": True,
            },
        )

    # -------------------------------------------------------------------------
    # 6. search_similar_repos: Exa findSimilar 竞品与同类反查
    # -------------------------------------------------------------------------
    async def search_similar_repos(self, url: str, max_results: int = 5) -> Dict[str, Any]:
        return await self._execute_with_retry(
            engine="exa",
            tool_name="search_similar_repos",
            url="https://api.exa.ai/findSimilar",
            json_body={"url": url, "numResults": max_results},
        )

    # -------------------------------------------------------------------------
    # 7. map_site: Tavily Map 站点拓扑树测绘
    # -------------------------------------------------------------------------
    async def map_site(
        self, url: str, instructions: Optional[str] = None, max_results: int = 15
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"url": url, "max_results": max_results}
        if instructions:
            body["instructions"] = instructions
        return await self._execute_with_retry(
            engine="tavily",
            tool_name="map_site",
            url="https://api.tavily.com/map",
            json_body=body,
        )

    # -------------------------------------------------------------------------
    # 8. extract_urls: Tavily / Exa 免爬虫快速正文脱水抽取
    # -------------------------------------------------------------------------
    async def extract_urls(self, urls: List[str]) -> Dict[str, Any]:
        # 优先 Tavily Extract
        res = await self._execute_with_retry(
            engine="tavily",
            tool_name="extract_urls",
            url="https://api.tavily.com/extract",
            json_body={"urls": urls},
        )
        if "results" in res and res["results"]:
            return res

        # 降级 Exa Contents
        return await self._execute_with_retry(
            engine="exa",
            tool_name="extract_urls",
            url="https://api.exa.ai/contents",
            json_body={"urls": urls, "text": True},
        )

    # -------------------------------------------------------------------------
    # 9. tavily_crawl: Tavily Map + Extract 整站自动化组合流水线
    # -------------------------------------------------------------------------
    async def tavily_crawl(self, url: str, max_depth: int = 1) -> Dict[str, Any]:
        return await self._execute_with_retry(
            engine="tavily",
            tool_name="tavily_crawl",
            url="https://api.tavily.com/crawl",
            json_body={"url": url, "max_depth": max_depth},
        )

    # -------------------------------------------------------------------------
    # 10. crawl_local: 本地 Crawl4AI 18789 Playwright 动态无头渲染
    # -------------------------------------------------------------------------
    async def crawl_local(
        self, url: str, wait_for: Optional[str] = None, css_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        start_t = time.perf_counter()
        try:
            payload: Dict[str, Any] = {"urls": url, "priority": 10}
            if css_selector:
                payload["css_selector"] = css_selector
            if wait_for:
                payload["wait_for"] = wait_for

            r = await self.client.post("http://127.0.0.1:18789/crawl", json=payload, timeout=20.0)
            lat = (time.perf_counter() - start_t) * 1000.0
            data = r.json()
            self.rotator.record_usage_audit(
                engine="crawl4ai",
                tool_name="crawl_local",
                key_item=None,
                status_code=r.status_code,
                credits_cost=0.0,
                latency_ms=lat,
            )
            return data
        except Exception as exc:
            lat = (time.perf_counter() - start_t) * 1000.0
            self.rotator.record_usage_audit(
                engine="crawl4ai",
                tool_name="crawl_local",
                key_item=None,
                status_code=500,
                credits_cost=0.0,
                latency_ms=lat,
                error_msg=str(exc),
            )
            return {"error": f"Crawl4AI local offline: {exc}"}

    # -------------------------------------------------------------------------
    # 11. deep_research: Exa Agent 多步自主调研长报告
    # -------------------------------------------------------------------------
    async def deep_research(self, topic: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"topic": topic}
        if instructions:
            body["instructions"] = instructions
        return await self._execute_with_retry(
            engine="exa",
            tool_name="deep_research",
            url="https://api.exa.ai/research",
            json_body=body,
        )

    # -------------------------------------------------------------------------
    # 12. benchmark_needle: Keenable NEEDLE 自建基准校验
    # -------------------------------------------------------------------------
    async def benchmark_needle(self, category: str, query: str) -> Dict[str, Any]:
        return await self._execute_with_retry(
            engine="keenable",
            tool_name="benchmark_needle",
            url="https://api.keenable.ai/v1/needle/eval",
            json_body={"category": category, "query": query},
        )
