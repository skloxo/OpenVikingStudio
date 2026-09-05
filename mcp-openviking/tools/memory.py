# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.memory ──────────────────────────────────────────────────
"""
用途: 语义记忆管理、两阶段重排检索、长期知识存盘与分层读取
依赖: _core.config, tools.observability
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import logging
from typing import Any, Callable, Dict
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _validate_uri,
    _validate_limit,
    _validate_score_threshold,
    _validate_level,
    _normalize_level,
    _make_error,
    _run_cli,
    http_client,
    _api_then_cli,
    _format_result,
    _has_error,
    _handle_cli_error,
    CLI_ONLY_MODE,
)
from .observability import _record_harness_call

logger = logging.getLogger("openviking-mcp")

# SECTION: Tool Registration
def register_memory_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_add_resource(
        path_or_url: str = Field(description="资源路径（本地文件/目录）或 URL"),
        target_uri: str = Field(default="", description="目标 Viking URI（精确位置）"),
        parent: str = Field(default="", description="父级 URI（自动创建）"),
        reason: str = Field(default="", description="添加原因（提升检索质量）"),
        wait: bool = Field(default=False, description="等待语义处理完成"),
        watch_interval: int = Field(default=0, description="定时更新间隔（分钟），>0 创建监控任务"),
    ) -> str:
        """添加资源到 OpenViking（支持本地文件、目录、URL）。CLI 优先，HTTP 回退。"""
        for uri_param, uri_val in [("target_uri", target_uri), ("parent", parent)]:
            err = _validate_uri(uri_val, uri_param)
            if err:
                return _make_error(err)

        def _cli():
            args = ["add", path_or_url]
            if target_uri:
                args.extend(["--to", target_uri])
            if parent:
                args.extend(["--parent", parent])
            if reason:
                args.extend(["--reason", reason])
            if wait:
                args.append("--wait")
            if watch_interval > 0:
                args.extend(["--watch-interval", str(watch_interval)])
            return _run_cli(args, timeout=120)

        def _api():
            body = {"path": path_or_url}
            if target_uri:
                body["to"] = target_uri
            if parent:
                body["parent"] = parent
            if reason:
                body["reason"] = reason
            if wait:
                body["wait"] = True
            if watch_interval > 0:
                body["watch_interval"] = watch_interval
            return http_client.post("/api/v1/resources", body)

        result = _cli()
        if _has_error(result):
            logger.warning("CLI add 失败，回退到 HTTP API")
            result = _api()
        return _format_result(result)
    registered["openviking_add_resource"] = openviking_add_resource

    @mcp_tool()
    def openviking_list_resources(
        target_uri: str = Field(default="viking://resources/", description="列出的 URI 路径"),
    ) -> str:
        """列出资源"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.get("/api/v1/fs/ls", {"uri": target_uri})

        return _api_then_cli(_api, ["ls", target_uri])
    registered["openviking_list_resources"] = openviking_list_resources

    @mcp_tool()
    def openviking_delete_resource(
        target_uri: str = Field(description="要删除的资源 Viking URI"),
    ) -> str:
        """删除资源"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.delete(f"/api/v1/fs?uri={target_uri}")

        return _api_then_cli(_api, ["rm", target_uri])
    registered["openviking_delete_resource"] = openviking_delete_resource

    @mcp_tool()
    def openviking_find(
        query: str = Field(description="搜索查询文本"),
        target_uri: str = Field(default="", description="限定搜索范围的 URI"),
        limit: int = Field(default=5, description="返回结果数量"),
        score_threshold: float = Field(default=0.0, description="最低相关性分数（0-1）"),
        level: str = Field(default="", description="限定层级：0(L0摘要), 1(L1概览), 2(L2全文), 0,1,2(全部)"),
        filter_tags: str = Field(default="", description="过滤标签（逗号分隔）"),
    ) -> str:
        """两阶段混合语义召回 + Cross-Encoder 深度重排。返回综合评分最高的相关上下文。"""
        query_str = str(query) if not hasattr(query, 'default') else ""
        target_uri_str = str(target_uri) if isinstance(target_uri, str) else ""
        level_str = str(level).strip() if isinstance(level, str) else ""
        filter_tags_str = str(filter_tags).strip() if isinstance(filter_tags, str) else ""

        if not isinstance(limit, int):
            try:
                limit = int(getattr(limit, 'default', 5))
            except Exception:
                limit = 5
        if not isinstance(score_threshold, (int, float)):
            try:
                score_threshold = float(getattr(score_threshold, 'default', 0.0))
            except Exception:
                score_threshold = 0.0

        for err in [
            _validate_uri(target_uri_str, "target_uri") if target_uri_str else None,
            _validate_limit(limit),
            _validate_score_threshold(score_threshold),
        ]:
            if err:
                return _make_error(err)

        def _api():
            body: Dict[str, Any] = {"query": query_str, "limit": limit}
            if target_uri_str:
                body["target_uri"] = target_uri_str
            if score_threshold > 0:
                body["score_threshold"] = score_threshold
            if level_str:
                body["level"] = level_str
            if filter_tags_str:
                body["filter"] = {"tags": [t.strip() for t in filter_tags_str.split(",") if t.strip()]}
            return http_client.post("/api/v1/search/find", body, timeout=60)

        _record_harness_call("find")
        return _api_then_cli(_api, ["search", query_str, "--limit", str(limit)])
    registered["openviking_find"] = openviking_find

    @mcp_tool()
    def openviking_search(
        query: str = Field(description="搜索查询文本"),
        target_uri: str = Field(default="", description="限定搜索范围的 URI"),
        limit: int = Field(default=5, description="返回结果数量"),
        score_threshold: float = Field(default=0.0, description="最低相关性分数"),
    ) -> str:
        """标准语义向量检索"""
        query_str = str(query) if not hasattr(query, 'default') else ""
        target_uri_str = str(target_uri) if isinstance(target_uri, str) else ""

        if not isinstance(limit, int):
            try:
                limit = int(getattr(limit, 'default', 5))
            except Exception:
                limit = 5
        if not isinstance(score_threshold, (int, float)):
            try:
                score_threshold = float(getattr(score_threshold, 'default', 0.0))
            except Exception:
                score_threshold = 0.0

        for err in [
            _validate_uri(target_uri_str, "target_uri") if target_uri_str else None,
            _validate_limit(limit),
            _validate_score_threshold(score_threshold),
        ]:
            if err:
                return _make_error(err)

        def _api():
            body = {"query": query_str, "limit": limit}
            if target_uri_str:
                body["target_uri"] = target_uri_str
            if score_threshold > 0:
                body["score_threshold"] = score_threshold
            return http_client.post("/api/v1/search/search", body)

        return _api_then_cli(_api, ["search", query_str, "--limit", str(limit)])
    registered["openviking_search"] = openviking_search

    @mcp_tool()
    def openviking_read(
        target_uri: str = Field(description="资源 Viking URI"),
        level: Any = Field(default=2, description="读取层级：0(L0摘要~100tokens), 1(L1概览~2000tokens), 2(L2全文)"),
    ) -> str:
        """分层读取资源内容。level=0/L0 摘要，level=1/L1 概览，level=2/L2 全文。优先 HTTP API。"""
        for err in [_validate_uri(target_uri), _validate_level(level)]:
            if err:
                return _make_error(err)

        lvl_num = _normalize_level(level)

        def _api():
            if lvl_num == 0:
                return http_client.get("/api/v1/content/abstract", {"uri": target_uri})
            elif lvl_num == 1:
                return http_client.get("/api/v1/content/overview", {"uri": target_uri})
            else:
                return http_client.get("/api/v1/content/read", {"uri": target_uri})

        def _cli():
            if lvl_num == 0:
                return _run_cli(["abstract", target_uri])
            elif lvl_num == 1:
                return _run_cli(["overview", target_uri])
            else:
                return _run_cli(["read", target_uri], timeout=60)

        return _api_then_cli(_api, ["read", target_uri], timeout=60)
    registered["openviking_read"] = openviking_read

    @mcp_tool()
    def openviking_write(
        target_uri: str = Field(description="目标 Viking URI"),
        content: str = Field(description="写入内容"),
        mode: str = Field(default="replace", description="写入模式：replace(覆盖), append(追加), create(新建/创建目录)"),
    ) -> str:
        """写入/修改文件。mode=create 时等同于 mkdir。"""
        if not isinstance(mode, str):
            mode = "replace"
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            res = http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": mode})
            if isinstance(res, dict) and "HTTP 404" in str(res.get("error")) and mode == "replace":
                return http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": "create"})
            return res

        def _cli():
            if mode == "create" and not content:
                return _run_cli(["mkdir", target_uri])
            return _run_cli(["write", target_uri, "--content", content, "--mode", mode])

        return _api_then_cli(_api, ["write", target_uri, "--content", content, "--mode", mode])
    registered["openviking_write"] = openviking_write

    @mcp_tool()
    def openviking_reindex(
        target_uri: str = Field(description="要重建索引的 Viking URI"),
        mode: str = Field(default="vectors_only", description="重建模式：vectors_only(仅向量), semantic_and_vectors(语义+向量)"),
    ) -> str:
        """重建语义/向量索引"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.post("/api/v1/content/reindex", {"uri": target_uri, "mode": mode}, timeout=180)

        return _api_then_cli(_api, ["reindex", target_uri, "--mode", mode], timeout=180)
    registered["openviking_reindex"] = openviking_reindex

    @mcp_tool()
    def openviking_store(
        session_id: str = Field(default="", description="会话 ID（留空使用当前会话）"),
        role: str = Field(default="user", description="消息角色：user/assistant/system"),
        content: str = Field(default="", description="消息内容（为空时仅提交会话）"),
    ) -> str:
        """存储消息到长期记忆。content 为空时等同于 commit。"""
        def _api():
            if content:
                body = {"role": role, "parts": [{"type": "text", "text": content}]}
                if session_id:
                    return http_client.post(f"/api/v1/sessions/{session_id}/messages", body)
                return http_client.post("/api/v1/sessions", {"session_id": session_id or "default", "message": body})
            if session_id:
                return http_client.post(f"/api/v1/sessions/{session_id}/commit")
            return http_client.post("/api/v1/sessions/default/commit")

        _record_harness_call("store")
        return _api_then_cli(_api, ["session", "commit"], timeout=60)
    registered["openviking_store"] = openviking_store

    @mcp_tool()
    def openviking_commit(
        session_id: str = Field(default="", description="会话 ID（留空使用当前会话）"),
    ) -> str:
        """提交当前会话记忆（归档消息 + 异步提取长期记忆）"""
        def _api():
            if session_id:
                return http_client.post(f"/api/v1/sessions/{session_id}/commit")
            return http_client.post("/api/v1/sessions/default/commit")

        return _api_then_cli(_api, ["session", "commit"], timeout=60)
    registered["openviking_commit"] = openviking_commit

    @mcp_tool()
    def openviking_smart_read(
        query: str = Field(description="搜索查询文本"),
        level: int = Field(default=1, description="读取层级：0(L0摘要), 1(L1概览), 2(L2全文)"),
        limit: int = Field(default=3, description="搜索结果数量"),
        score_threshold: float = Field(default=0.0, description="最低相关性分数（0-1）"),
    ) -> str:
        """智能读取：搜索 + 批量读取组合操作。一次调用完成搜索并返回每个结果的详细内容。"""
        for err in [
            _validate_level(level),
            _validate_limit(limit),
            _validate_score_threshold(score_threshold),
        ]:
            if err:
                return _make_error(err)

        search_body = {"query": query, "limit": limit}
        if score_threshold > 0:
            search_body["score_threshold"] = score_threshold

        if CLI_ONLY_MODE or not http_client.available:
            search_args = ["search", query, "--limit", str(limit)]
            if score_threshold > 0:
                search_args.extend(["--score-threshold", str(score_threshold)])
            search_result = _run_cli(search_args)
            if _has_error(search_result):
                return _handle_cli_error(search_result)
            results = search_result.get("results", [])
        else:
            search_result = http_client.post("/api/v1/search/find", search_body)
            if _has_error(search_result):
                search_args = ["search", query, "--limit", str(limit)]
                if score_threshold > 0:
                    search_args.extend(["--score-threshold", str(score_threshold)])
                search_result = _run_cli(search_args)
                if _has_error(search_result):
                    return _handle_cli_error(search_result)
            results = search_result.get("results", [])

        detailed_results = []
        for item in results:
            uri = item.get("uri", item.get("id", ""))
            if not uri:
                detailed_results.append({"search_result": item, "content": {"error": "无 URI"}})
                continue

            if CLI_ONLY_MODE or not http_client.available:
                if level == 0:
                    content = _run_cli(["abstract", uri])
                elif level == 1:
                    content = _run_cli(["overview", uri])
                else:
                    content = _run_cli(["read", uri], timeout=60)
            else:
                if level == 0:
                    content = http_client.get("/api/v1/content/abstract", {"uri": uri})
                elif level == 1:
                    content = http_client.get("/api/v1/content/overview", {"uri": uri})
                else:
                    content = http_client.get("/api/v1/content/read", {"uri": uri})

            detailed_results.append({
                "search_result": item,
                "content": content,
            })

        return _format_result({
            "query": query,
            "level": level,
            "total_results": len(detailed_results),
            "results": detailed_results,
        })
    registered["openviking_smart_read"] = openviking_smart_read

    return registered
