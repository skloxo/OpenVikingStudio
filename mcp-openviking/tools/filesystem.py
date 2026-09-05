# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.filesystem ──────────────────────────────────────────────
"""
用途: VikingFS 目录树、文件列表、移动、重命名、差异比对、标签与 WebDAV
依赖: _core.config
被调用: mcp_openviking_server.py
"""

# SECTION: Imports
import logging
from typing import Callable, Dict
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from _core.config import (
    _get_config,
    _validate_uri,
    _make_error,
    _run_cli,
    http_client,
    _api_then_cli,
    _format_result,
)

logger = logging.getLogger("openviking-mcp")

# SECTION: Tool Registration
def register_filesystem_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Callable]:
    registered: Dict[str, Callable] = {}

    @mcp_tool()
    def openviking_ls(
        target_uri: str = Field(default="viking://", description="要浏览的 Viking URI"),
        compact: bool = Field(default=True, description="紧凑输出"),
        detail: bool = Field(default=False, description="详细模式（包含 stat 信息）"),
    ) -> str:
        """列出 Viking URI 目录条目。detail=True 时显示详细 stat 信息。"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            result = http_client.get("/api/v1/fs/ls", {"uri": target_uri})
            if detail and "error" not in result:
                stat = http_client.get("/api/v1/fs/stat", {"uri": target_uri})
                if "error" not in stat:
                    result["stat"] = stat
            return result

        def _cli():
            args = ["ls"]
            if target_uri:
                args.append(target_uri)
            if compact:
                args.append("--compact")
            return _run_cli(args)

        return _api_then_cli(_api, ["ls", target_uri] + (["--compact"] if compact else []))
    registered["openviking_ls"] = openviking_ls

    @mcp_tool()
    def openviking_tree(
        target_uri: str = Field(default="viking://", description="要展示的 Viking URI"),
        depth: int = Field(default=3, description="树深度"),
    ) -> str:
        """树形展示 Viking URI 目录结构"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.post("/api/v1/fs/tree", {"uri": target_uri, "depth": depth})

        return _api_then_cli(_api, ["tree", target_uri, "--depth", str(depth)])
    registered["openviking_tree"] = openviking_tree

    @mcp_tool()
    def openviking_mv(
        source: str = Field(description="源 Viking URI"),
        target: str = Field(description="目标 Viking URI"),
    ) -> str:
        """移动/重命名资源"""
        for err in [_validate_uri(source, "source"), _validate_uri(target, "target")]:
            if err:
                return _make_error(err)

        def _api():
            return http_client.post("/api/v1/fs/mv", {"source": source, "target": target})

        return _api_then_cli(_api, ["mv", source, target])
    registered["openviking_mv"] = openviking_mv

    @mcp_tool()
    def openviking_rename(
        target_uri: str = Field(description="Viking URI"),
        new_name: str = Field(description="新名称"),
    ) -> str:
        """重命名资源（不移动位置）"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)

        def _api():
            return http_client.post("/api/v1/fs/rename", {"uri": target_uri, "name": new_name})

        def _cli():
            return _run_cli(["mv", target_uri, new_name])

        return _api_then_cli(_api, ["mv", target_uri, new_name])
    registered["openviking_rename"] = openviking_rename

    @mcp_tool()
    def openviking_tag(
        target_uri: str = Field(description="Viking URI"),
        action: str = Field(description="操作：get/set/remove"),
        tags: str = Field(default="", description="标签列表（逗号分隔，set/remove 时必填）"),
    ) -> str:
        """标签管理：获取、设置、移除标签"""
        err = _validate_uri(target_uri)
        if err:
            return _make_error(err)
        valid = {"get", "set", "remove"}
        if action not in valid:
            return _make_error(f"无效操作: {action}。可选: {', '.join(sorted(valid))}")

        def _api():
            if action == "get":
                return http_client.get("/api/v1/tags", {"uri": target_uri})
            elif action == "set":
                return http_client.post("/api/v1/tags", {"uri": target_uri, "tags": [t.strip() for t in tags.split(",")]})
            else:
                return http_client.delete(f"/api/v1/tags?uri={target_uri}&tags={tags}")

        def _cli():
            args = ["tag", action, target_uri]
            if tags:
                args.extend(["--tags", tags])
            return _run_cli(args)

        return _api_then_cli(_api, ["tag", action, target_uri] + (["--tags", tags] if tags else []))
    registered["openviking_tag"] = openviking_tag

    @mcp_tool()
    def openviking_diff(
        source_uri: str = Field(description="源 Viking URI"),
        target_uri: str = Field(description="目标 Viking URI 或本地文件路径"),
    ) -> str:
        """比较两个资源的差异"""
        err = _validate_uri(source_uri, "source_uri")
        if err:
            return _make_error(err)
        return _format_result(_run_cli(["diff", source_uri, target_uri], timeout=60))
    registered["openviking_diff"] = openviking_diff

    @mcp_tool()
    def openviking_webdav_info() -> str:
        """获取 WebDAV 访问信息"""
        cfg = _get_config()
        return _format_result({
            "webdav_url": f"{cfg['api']}/webdav/resources",
            "description": "支持 OPTIONS/PROPFIND/GET/HEAD/PUT/DELETE/MKCOL/MOVE",
            "mount_example": f"mount -t davfs {cfg['api']}/webdav/resources /mnt/openviking",
        })
    registered["openviking_webdav_info"] = openviking_webdav_info

    return registered
