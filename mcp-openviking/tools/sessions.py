# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.sessions ────────────────────────────────────────────────
"""
用途: 多智能体会话状态、知识图谱关联拓扑与链接关系管理
依赖: _core.config
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import logging
from typing import Callable, Dict
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _validate_uri,
    _validate_limit,
    _make_error,
    _run_cli,
    http_client,
    _api_then_cli,
)

logger = logging.getLogger("openviking-mcp")

# SECTION: Tool Registration
def register_sessions_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_list_sessions(
        limit: int = Field(default=20, description="返回数量"),
    ) -> str:
        """列出会话"""
        err = _validate_limit(limit)
        if err:
            return _make_error(err)

        def _api():
            return http_client.get("/api/v1/sessions", {"limit": limit})

        return _api_then_cli(_api, ["session", "list", "--limit", str(limit)])
    registered["openviking_list_sessions"] = openviking_list_sessions

    @mcp_tool()
    def openviking_get_session(
        session_id: str = Field(description="会话 ID"),
        include_context: bool = Field(default=False, description="是否包含组装上下文"),
    ) -> str:
        """获取会话详情。include_context=True 时额外返回组装上下文。"""
        def _api():
            result = http_client.get(f"/api/v1/sessions/{session_id}")
            if include_context and "error" not in result:
                ctx = http_client.get(f"/api/v1/sessions/{session_id}/context")
                if "error" not in ctx:
                    result["context"] = ctx
            return result

        return _api_then_cli(_api, ["session", "get", session_id])
    registered["openviking_get_session"] = openviking_get_session

    @mcp_tool()
    def openviking_create_session(
        session_id: str = Field(description="会话 ID"),
        user_id: str = Field(default="", description="用户 ID"),
    ) -> str:
        """创建会话"""
        sid = str(session_id) if not hasattr(session_id, 'default') else ""
        uid = str(user_id) if isinstance(user_id, str) else ""

        def _api():
            body = {"session_id": sid}
            if uid:
                body["user_id"] = uid
            return http_client.post("/api/v1/sessions", body)

        def _cli():
            args = ["session", "create", sid]
            if uid:
                args.extend(["--user", uid])
            return _run_cli(args)

        return _api_then_cli(_api, ["session", "create", sid])
    registered["openviking_create_session"] = openviking_create_session

    @mcp_tool()
    def openviking_link(
        source_uri: str = Field(description="源 URI"),
        target_uri: str = Field(description="目标 URI"),
        relation_type: str = Field(default="related", description="关联类型：related/child/reference/similar"),
    ) -> str:
        """创建知识图谱资源关联拓扑"""
        for err in [_validate_uri(source_uri, "source_uri"), _validate_uri(target_uri, "target_uri")]:
            if err:
                return _make_error(err)

        def _api():
            return http_client.post("/api/v1/relations/link", {
                "source": source_uri, "target": target_uri, "type": relation_type,
            })

        return _api_then_cli(_api, ["link", source_uri, target_uri, "--type", relation_type])
    registered["openviking_link"] = openviking_link

    @mcp_tool()
    def openviking_get_relations(
        target_uri: str = Field(description="Viking URI"),
    ) -> str:
        """获取资源关联列表与拓扑图"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.get("/api/v1/relations", {"uri": target_uri})

        return _api_then_cli(_api, ["relations", target_uri])
    registered["openviking_get_relations"] = openviking_get_relations

    @mcp_tool()
    def openviking_unlink(
        source_uri: str = Field(description="源 URI"),
        target_uri: str = Field(description="目标 URI"),
    ) -> str:
        """删除资源关联"""
        for err in [_validate_uri(source_uri, "source_uri"), _validate_uri(target_uri, "target_uri")]:
            if err:
                return _make_error(err)

        def _api():
            return http_client.post("/api/v1/relations/unlink", {"source": source_uri, "target": target_uri})

        return _api_then_cli(_api, ["unlink", source_uri, target_uri])
    registered["openviking_unlink"] = openviking_unlink

    return registered
