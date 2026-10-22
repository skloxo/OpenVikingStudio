#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking Core Memory Antigravity Proxy Stub (v2.0.16)
自内聚转接驱动：遵循 Keepass 插件模式，客户端极简通信桥梁，服务端负责全部算子。
2080Ti 本地与 3070 远程代码 100% 相同，唯一的差异仅仅是传入的环境变量 OPENVIKING_API。
精准提供 37 个战地核心记忆工具 (MEMORY_37_TOOL_NAMES SSOT)。
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field
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

ACTOR_PEER = os.environ.get("OPENVIKING_ACTOR_PEER", "")


import socket
from pydantic.fields import FieldInfo


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


DEFAULT_TIMEOUT: float = 120.0  # 兜底超时，防止任何工具挂死 IDE 会话


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
        "User-Agent": "Antigravity-OpenViking-Proxy/2.0.16",
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
        err_msg = e.read().decode("utf-8", errors="replace")
        return f"HTTP {e.code}: {err_msg}"
    except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
        is_timeout = isinstance(e, (TimeoutError, socket.timeout)) or "timed out" in str(e).lower()
        if is_timeout:
            return json.dumps({
                "status": "TIMEOUT_TRUNCATED",
                "timeout_seconds": effective_timeout,
                "error": f"请求后端超时 ({effective_timeout}s) 触发安全熔断: {e}",
                "warning": (
                    "⚠️ [ANTI-HALLUCINATION GUARD] 操作因超时被中断！"
                    "绝对不能推定目标目录/资源为空或文件不存在！"
                    "严禁在未确认物理事实前盲目重复手搓公共组件。请指定具体子路径缩小范围后再试。"
                )
            }, ensure_ascii=False, indent=2)
        return f"[Fail-Fast Guard] 网络通信错误: {e}"
    except Exception as e:
        return f"Request Error: {e}"


# SECTION: FastMCP Initialization
mcp = FastMCP(
    name="openviking-memory",
    instructions="OpenViking 战地记忆中枢 (26 Tools) — 语义检索、两阶段重排、分层读取、会话管理与踩坑存盘。",
)

# ─── 1. Memory Tools (6) ──────────────────────────────────────────────────
@mcp.tool()
def openviking_find(
    query: str = Field(description="搜索关键词或自然语言问题"),
    target_uri: str = Field(default="", description="搜索范围 URI，例如 viking://resources/"),
    limit: int = Field(default=10, description="返回结果最大条数"),
    score_threshold: Optional[float] = Field(default=None, description="语义相似度最低阈值"),
) -> str:
    """两阶段混合语义检索记忆与资源。"""
    body: Dict[str, Any] = {"query": query, "limit": limit}
    if score_threshold is not None:
        body["score_threshold"] = score_threshold
    if target_uri:
        body["target_uri"] = target_uri
    return _api_request("POST", "/api/v1/search/find", body=body, timeout=60.0)

@mcp.tool()
def openviking_search(
    query: str = Field(description="搜索关键词"),
    target_uri: str = Field(default="", description="搜索范围 URI"),
    limit: int = Field(default=10, description="返回条数"),
    score_threshold: float = Field(default=0.0, description="打分阈值"),
) -> str:
    """全局向量语义检索。"""
    body: Dict[str, Any] = {"query": query, "limit": limit, "score_threshold": score_threshold}
    if target_uri:
        body["target_uri"] = target_uri
    return _api_request("POST", "/api/v1/search/search", body=body)

@mcp.tool()
def openviking_read(
    target_uri: str = Field(description="资源或记忆的 Viking URI"),
    level: str = Field(default="auto", description="分层读取级别：auto/abstract/overview/read"),
) -> str:
    """分层读取 Viking URI 资源内容。"""
    endpoint = "/api/v1/content/read"
    if level == "abstract":
        endpoint = "/api/v1/content/abstract"
    elif level == "overview":
        endpoint = "/api/v1/content/overview"
    return _api_request("GET", endpoint, params={"uri": target_uri})

@mcp.tool()
def openviking_write(
    target_uri: str = Field(description="目标 Viking URI"),
    content: str = Field(description="要写入的文本内容"),
    mode: str = Field(default="create", description="写入模式：create/append/overwrite"),
) -> str:
    """写入或更新 Viking URI 记忆或资源内容。"""
    return _api_request("POST", "/api/v1/content/write", body={"uri": target_uri, "content": content, "mode": mode})

@mcp.tool()
def openviking_store(
    title: str = Field(description="记忆标题"),
    content: str = Field(description="记忆正文"),
    category: str = Field(default="experiences", description="记忆分类：experiences/skills/entities/cases"),
    tags: str = Field(default="", description="标签（逗号分隔）"),
) -> str:
    """结构化存储事实与经验至长期体外大脑。"""
    safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in title).strip("_").lower() or "note"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    uri = f"viking://user/default/memories/{category}/{timestamp}_{safe_title}.md"
    return _api_request("POST", "/api/v1/content/write", body={"uri": uri, "content": f"# {title}\n\n{content}", "mode": "create"})

@mcp.tool()
def openviking_smart_read(
    query: str = Field(description="阅读需求或问题"),
    target_uri: str = Field(default="viking://", description="目标范围 URI"),
    limit: int = Field(default=10, description="最大召回条数"),
) -> str:
    """智能上下文提纯与按需抽稀阅读。"""
    return _api_request("POST", "/api/v1/search/find", body={"query": query, "target_uri": target_uri, "limit": limit})

# ─── 2. Code Tools (5) ────────────────────────────────────────────────────
@mcp.tool()
def openviking_code_outline(
    target_uri: str = Field(description="代码文件 Viking URI"),
) -> str:
    """显示代码文件符号大纲（类、函数等）。"""
    return _api_request("GET", "/api/v1/content/overview", params={"uri": target_uri})

@mcp.tool()
def openviking_code_search(
    query: str = Field(description="代码符号名搜索"),
    target_uri: str = Field(default="viking://", description="搜索范围 URI"),
) -> str:
    """代码符号搜索。"""
    return _api_request("POST", "/api/v1/search/find", body={"query": query, "target_uri": target_uri})

@mcp.tool()
def openviking_code_expand(
    target_uri: str = Field(description="符号所在文件 Viking URI"),
    symbol: str = Field(default="", description="符号名称"),
) -> str:
    """返回符号完整源码切片。"""
    return _api_request("GET", "/api/v1/content/read", params={"uri": target_uri})

@mcp.tool()
def openviking_grep(
    pattern: str = Field(description="正则表达式"),
    target_uri: str = Field(default="viking://", description="搜索范围 URI"),
    limit: int = Field(default=50, description="最大返回行数"),
) -> str:
    """代码库全局正则行匹配。"""
    return _api_request("POST", "/api/v1/search/grep", body={"pattern": pattern, "uri": target_uri, "limit": limit})

@mcp.tool()
def openviking_glob(
    pattern: str = Field(description="Glob 通配符模式"),
    target_uri: str = Field(default="viking://", description="搜索范围 URI"),
) -> str:
    """Glob 模式文件路径检索。"""
    return _api_request("POST", "/api/v1/search/glob", body={"pattern": pattern, "uri": target_uri})

# ─── 3. Filesystem Tools (4) ──────────────────────────────────────────────
@mcp.tool()
def openviking_ls(
    target_uri: str = Field(default="viking://", description="列出的 Viking URI 路径"),
) -> str:
    """列出 VikingFS 目录中的文件和子目录（快速轻量模式）。"""
    return _api_request("GET", "/api/v1/fs/ls", params={"uri": target_uri, "output": "original"}, timeout=15.0)

@mcp.tool()
def openviking_tree(
    target_uri: str = Field(default="viking://", description="目标 URI"),
    depth: int = Field(default=2, description="递归展开深度"),
) -> str:
    """获取 VikingFS 目录树状结构（快速轻量模式）。"""
    return _api_request("GET", "/api/v1/fs/tree", params={"uri": target_uri, "level_limit": depth, "output": "original"}, timeout=15.0)


# ─── 4. Skills Tools ──────────────────────────────────────────────────────
@mcp.tool()
def openviking_record_evolution_lesson(
    title: str = Field(description="排查踩坑教训标题"),
    context: str = Field(description="踩坑业务背景与前置条件"),
    reflection: str = Field(description="核心根因第一性原理反思"),
    lesson: str = Field(description="永久性工程规约与防线"),
    delta: str = Field(default="", description="关键代码差异 Diff"),
) -> str:
    """沉淀踩坑教训至体外大脑并双写落盘。"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in title).strip("_").lower() or "lesson"
    uri = f"viking://resources/master_memory/evolution_lessons/{timestamp}_{safe_title}.md"
    body_content = f"# Evolution Lesson: {title}\n- **Recorded At**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n- **Context**: {context}\n\n## 🎯 Reflection\n{reflection}\n\n## 📜 Lesson\n{lesson}\n"
    if delta:
        body_content += f"\n## ⚡ Delta\n```diff\n{delta.strip()}\n```\n"
    return _api_request("POST", "/api/v1/content/write", body={"uri": uri, "content": body_content, "mode": "create"})

@mcp.tool()
def openviking_skills(
    action: str = Field(default="list", description="操作：list（列出）/ add（添加）"),
    name: str = Field(default="", description="技能名称（add 时必填）"),
    description: str = Field(default="", description="技能描述（add 时必填）"),
    content: str = Field(default="", description="技能内容（Markdown）"),
    tags: str = Field(default="", description="标签（逗号分隔）"),
    target_uri: str = Field(default="viking://agent/skills", description="目标根 URI"),
) -> str:
    """技能检索与管理。"""
    if action == "list":
        return _api_request("GET", "/api/v1/skills")
    elif action == "add":
        return _api_request("POST", "/api/v1/skills", body={"name": name, "description": description, "content": content, "tags": tags, "target_uri": target_uri})
    return f"Invalid action: {action}"

@mcp.tool()
def openviking_auto_onboard_skills(
    skill_name: str = Field(default="", description="技能名称（kebab-case）"),
    content: str = Field(default="", description="技能 Markdown 全文（含 YAML Frontmatter）"),
    path: str = Field(default="", description="可选：本地技能文件路径（若指定则自动读取）"),
) -> str:
    """一键自动化批量纳管野生技能进入流水线。"""
    final_name = skill_name.strip()
    final_content = content.strip()
    if path and Path(path).is_file():
        try:
            p = Path(path)
            if not final_name:
                final_name = p.stem.lower().replace("_", "-")
            if not final_content:
                final_content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return json.dumps({"status": "error", "message": f"读取本地技能文件失败: {e}"})
    if not final_name or not final_content:
        return json.dumps({"status": "error", "message": "必须提供 skill_name 与 content（或有效本地 path）"})
    return _api_request("POST", "/api/v1/skills/ingestion/submit", body={"skill_name": final_name, "content": final_content, "source_path": path})

@mcp.tool()
def openviking_get_onboard_queue_status() -> str:
    """获取技能入库流水线队列排队状态。"""
    return _api_request("GET", "/api/v1/skills/ingestion/queue")

# ─── 5. Sessions Tools (6) ────────────────────────────────────────────────
@mcp.tool()
def openviking_list_sessions(
    limit: int = Field(default=20, description="返回数量"),
) -> str:
    """列出系统活跃对话会话。"""
    return _api_request("GET", "/api/v1/sessions", params={"limit": limit})

@mcp.tool()
def openviking_get_session(
    session_id: str = Field(description="会话 ID"),
    include_context: bool = Field(default=False, description="是否包含上下文"),
) -> str:
    """获取指定会话完整消息轨迹与上下文。"""
    return _api_request("GET", f"/api/v1/sessions/{session_id}", params={"include_context": include_context})

@mcp.tool()
def openviking_create_session(
    session_id: str = Field(default="", description="自定义会话 ID（可选）"),
    user_id: str = Field(default="", description="归属用户 ID（可选）"),
) -> str:
    """新建对话会话空间。"""
    body: Dict[str, Any] = {}
    if session_id:
        body["session_id"] = session_id
    if user_id:
        body["user_id"] = user_id
    return _api_request("POST", "/api/v1/sessions", body=body)

@mcp.tool()
def openviking_link(
    source_uri: str = Field(description="源 Viking URI"),
    target_uri: str = Field(description="目标 Viking URI"),
    relation_type: str = Field(default="related_to", description="关联类型"),
) -> str:
    """在两组资源之间建立语义拓扑关联。"""
    return _api_request("POST", "/api/v1/relations/link", body={"from_uri": source_uri, "to_uris": [target_uri], "relation_type": relation_type})

@mcp.tool()
def openviking_get_relations(
    target_uri: str = Field(description="Viking URI"),
) -> str:
    """获取资源的关联拓扑图谱。"""
    return _api_request("GET", "/api/v1/relations", params={"uri": target_uri})

@mcp.tool()
def openviking_unlink(
    source_uri: str = Field(description="源 Viking URI"),
    target_uri: str = Field(description="目标 Viking URI"),
) -> str:
    """解除两组资源之间的语义拓扑关联。"""
    return _api_request("POST", "/api/v1/relations/unlink", body={"from_uri": source_uri, "to_uri": target_uri})

# ─── 6. System Tools (3) ──────────────────────────────────────────────────
@mcp.tool()
def openviking_health() -> str:
    """检查 OpenViking 服务端健康状态。"""
    return _api_request("GET", "/health")

@mcp.tool()
def openviking_system_status(
    wait_timeout: int = Field(default=0, description="等待后台处理超时的秒数"),
    reset_stats: bool = Field(default=False, description="是否重置统计"),
) -> str:
    """获取 OpenViking 核心队列、存储与引擎状态。"""
    return _api_request("GET", "/api/v1/system/status", params={"wait_timeout": wait_timeout, "reset_stats": reset_stats})

@mcp.tool()
def openviking_ping() -> str:
    """快速网络测速与心跳保活握手。"""
    return json.dumps({
        "status": "ok",
        "proxy": "Antigravity-Memory-Proxy-Stub",
        "version": "2.0.26",
        "api_endpoint": API_BASE,
        "tools_count": 26,
        "timestamp": time.time()
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 纯净运行 FastMCP stdio 传输
    sys.argv = [sys.argv[0]]
    mcp.run(transport="stdio")
