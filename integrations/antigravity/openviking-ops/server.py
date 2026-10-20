#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking System Ops Antigravity Proxy Stub (v1.0.4)
系统运维治理特权转接驱动：遵循 Keepass/OpenViking 标杆插件模式，客户端极简通信桥梁。
精准提供 16 个系统运维治理特权工具 (OPS_16_TOOL_NAMES SSOT)。
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field
from pydantic.fields import FieldInfo
from mcp.server.fastmcp import FastMCP

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# SECTION: Configuration & Credential Resolution
_PLUGIN_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _PLUGIN_DIR / "config.json"
_LOCAL_CFG: Dict[str, Any] = {}
if _CONFIG_FILE.exists():
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            _LOCAL_CFG = json.load(f)
    except Exception:
        pass

API_BASE = (
    os.environ.get("OPENVIKING_API")
    or _LOCAL_CFG.get("api_url")
    or _LOCAL_CFG.get("api")
    or "http://127.0.0.1:1933"
).rstrip("/")

API_KEY = (
    os.environ.get("OPENVIKING_API_KEY")
    or os.environ.get("OPENVIKING_ROOT_API_KEY")
    or _LOCAL_CFG.get("api_key")
    or ""
)

ACTOR_PEER = os.environ.get("OPENVIKING_ACTOR_PEER", "openviking-ops@sentinel")
DEFAULT_TIMEOUT: float = 120.0


def _clean_payload(obj: Any) -> Any:
    if isinstance(obj, FieldInfo):
        return None if obj.default is ... else obj.default
    if isinstance(obj, dict):
        return {
            k: _clean_payload(v)
            for k, v in obj.items()
            if not (isinstance(v, FieldInfo) and v.default is ...)
        }
    if isinstance(obj, list):
        return [_clean_payload(v) for v in obj]
    return obj


def _api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> str:
    url = f"{API_BASE}{endpoint}"
    if params:
        cleaned_params = _clean_payload(params)
        clean_params = {k: v for k, v in cleaned_params.items() if v is not None and v != ""}
        if clean_params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(clean_params)

    headers = {
        "User-Agent": "Antigravity-OpenViking-Ops-Proxy/1.0.4",
        "Accept": "application/json",
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if ACTOR_PEER:
        headers["X-OpenViking-Actor-Peer"] = ACTOR_PEER

    data = None
    if body is not None:
        cleaned_body = _clean_payload(body)
        data = json.dumps(cleaned_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    try:
        with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception:
                return raw
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return json.dumps({
            "error": f"HTTP {e.code}: {e.reason}",
            "details": err_body,
            "url": url,
            "status_code": e.code,
        }, ensure_ascii=False, indent=2)
    except urllib.error.URLError as e:
        return json.dumps({
            "error": f"Connection failed to OpenViking Ops API at {API_BASE}",
            "reason": str(e.reason),
            "hint": "Check if OpenViking server is running on 127.0.0.1:1933 or reachable."
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


# SECTION: FastMCP Server Initialization
mcp = FastMCP(
    name="openviking-ops",
    instructions="OpenViking 系统运维与管控特权插件 (16 Tools) — 资源索引、目录树维护、数据备份恢复、死信自愈与系统初始化。",
)


# SECTION: 1. 资源运维算子 (Resources & Indexing)
@mcp.tool()
def openviking_add_resource(
    path_or_url: str = Field(description="资源本地文件/目录路径或网络 URL"),
    target_uri: str = Field(default="", description="目标 Viking 资源 URI (例如 viking://resources/docs/)"),
    parent: str = Field(default="", description="父级目录 URI"),
    reason: str = Field(default="", description="挂载变更理由，提升语义召回精度"),
    wait: bool = Field(default=False, description="是否同步等待解析与索引构建完成"),
) -> str:
    """向 OpenViking 体外大脑挂载新资源。"""
    body = {"path": path_or_url}
    if target_uri:
        body["to"] = target_uri
    if parent:
        body["parent"] = parent
    if reason:
        body["reason"] = reason
    if wait:
        body["wait"] = True
    return _api_request("POST", "/api/v1/resources", body=body)


@mcp.tool()
def openviking_list_resources(
    target_uri: str = Field(default="viking://resources/", description="要浏览的资源目录 URI"),
) -> str:
    """列出体外大脑已挂载的资源列表。"""
    return _api_request("GET", "/api/v1/fs/ls", params={"uri": target_uri})


@mcp.tool()
def openviking_delete_resource(
    target_uri: str = Field(description="要安全注销/删除的资源 Viking URI"),
) -> str:
    """安全注销并移除指定的体外大脑资源。"""
    return _api_request("DELETE", f"/api/v1/fs?uri={urllib.parse.quote(target_uri, safe='')}")


@mcp.tool()
def openviking_reindex(
    target_uri: str = Field(default="viking://", description="要重建索引的根 URI"),
    wait: bool = Field(default=False, description="是否等待重建完毕"),
) -> str:
    """触发知识与向量库全盘或局部重索引。"""
    return _api_request("POST", "/api/v1/system/reindex", body={"uri": target_uri, "wait": wait})


@mcp.tool()
def openviking_commit(
    reason: str = Field(default="manual ops commit", description="提交说明理由"),
    wait: bool = Field(default=False, description="是否同步等待提交完成"),
) -> str:
    """工作区变更版本快照物理提交。"""
    return _api_request("POST", "/api/v1/system/commit", body={"reason": reason, "wait": wait})


# SECTION: 2. 目录树与底层文件运维算子 (Filesystem Ops)
@mcp.tool()
def openviking_mv(
    source: str = Field(description="源资源 Viking URI"),
    target: str = Field(description="目标位置 Viking URI"),
) -> str:
    """底层文件或目录安全原子重定位与移动。"""
    return _api_request("POST", "/api/v1/fs/mv", body={"source": source, "target": target})


@mcp.tool()
def openviking_rename(
    target_uri: str = Field(description="目标资源 Viking URI"),
    new_name: str = Field(description="新文件名或新目录名"),
) -> str:
    """知识库文件或目录重命名。"""
    return _api_request("POST", "/api/v1/fs/rename", body={"uri": target_uri, "name": new_name})


@mcp.tool()
def openviking_webdav_info() -> str:
    """获取 WebDAV 协议挂载端点与配额信息。"""
    return json.dumps({
        "status": "active",
        "webdav_url": f"{API_BASE}/webdav/resources",
        "supported_methods": ["OPTIONS", "PROPFIND", "GET", "HEAD", "PUT", "DELETE", "MKCOL", "MOVE"],
        "mount_example": f"mount -t davfs {API_BASE}/webdav/resources /mnt/openviking",
    }, ensure_ascii=False, indent=2)


# SECTION: 3. 质量治理与死信自愈算子 (Purity & Dead Letters)
@mcp.tool()
def openviking_memory_purity_report(
    sample_size: int = Field(default=100, description="抽样评估的记忆实体数量"),
) -> str:
    """评估体外大脑记忆纯度、概念漂移程度与信噪比 (SNR)。"""
    return _api_request("GET", "/api/v1/system/purity-report", params={"sample_size": sample_size})


@mcp.tool()
def openviking_retry_dead_letter(
    max_count: int = Field(default=10, description="单次最大重试的死信消息数"),
) -> str:
    """触发死信队列消息自愈重试与故障排查。"""
    return _api_request("POST", "/api/v1/system/dead-letters/retry", body={"max_count": max_count})


# SECTION: 4. 监听与生命周期管控算子 (Watches & Lifecycle)
@mcp.tool()
def openviking_list_watches(
    active_only: bool = Field(default=True, description="是否仅列出活跃状态的监听任务"),
) -> str:
    """查看自动刷新系统监听订阅任务清单。"""
    return _api_request("GET", "/api/v1/system/watches", params={"active_only": active_only})


@mcp.tool()
def openviking_cancel_watch(
    target_uri: str = Field(description="要取消监听的 Viking URI"),
) -> str:
    """取消指定的自动刷新系统监听任务。"""
    return _api_request("DELETE", f"/api/v1/system/watches?uri={urllib.parse.quote(target_uri, safe='')}")


@mcp.tool()
def openviking_manage_watch(
    target_uri: str = Field(description="目标 Viking URI"),
    interval_minutes: int = Field(default=10, description="轮询或检测周期（分钟）"),
    active: bool = Field(default=True, description="是否激活"),
) -> str:
    """动态更新或调整系统监听器参数。"""
    return _api_request("POST", "/api/v1/system/watches", body={
        "uri": target_uri,
        "interval_minutes": interval_minutes,
        "active": active,
    })


@mcp.tool()
def openviking_server_control(
    action: str = Field(description="操作动作：restart / reload / drain / status"),
) -> str:
    """核心中枢服务生命周期管理与优雅重启控制。"""
    return _api_request("POST", "/api/v1/system/control", body={"action": action})


@mcp.tool()
def openviking_server_init(
    force: bool = Field(default=False, description="是否强制重建底层数据表结构"),
) -> str:
    """底座存储引擎与数据表引导初始化。"""
    return _api_request("POST", "/api/v1/system/init", body={"force": force})


@mcp.tool()
def openviking_server_doctor() -> str:
    """全系统底层硬件、向量库、数据库与存储引擎深度体检诊断。"""
    return _api_request("GET", "/api/v1/system/doctor")


if __name__ == "__main__":
    mcp.run(transport="stdio")
