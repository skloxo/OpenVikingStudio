#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: satellite_mcp_server ──────────────────────────────────────────
"""
OpenViking Satellite MCP Server (Standalone Zero-Dependency Distribution - v1.4.32)

专为远程算力节点 (Mac Studio / 2080Ti / 远程工作站) 与外部 Agent (WorkBuddy / Cursor / Claude Code) 设计的独立单文件轻量分发包。
特点：
1. 零 Monorepo 依赖：拷贝单文件即可独立运行，仅需 pip install "mcp[cli]" pydantic
2. 纯安全数据面：暴露 16 大全能实用数据与感知工具，物理隔离本地底层破坏性运维接口
3. 优雅向后兼容垫片：调用被精简管理工具时友好拦截，杜绝 JSON-RPC 协议异常断流
4. 抖动自愈重试：内置指数退避重试，抵抗 FRP / SSH 隧道远程网络抖动
5. 跨平台原生加固：自动处理 Windows cmd/powershell UTF-8 编码重置
"""

# SECTION: Imports
import inspect
import json
import logging
import os
import re
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# SECTION: Platform Compatibility & Stdio
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from pydantic import Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openviking-satellite-mcp")

# SECTION: Configuration & Remote HTTP Client
DEFAULT_API = os.environ.get("OPENVIKING_API", "http://127.0.0.1:1933").rstrip("/")
DEFAULT_API_KEY = os.environ.get("OPENVIKING_API_KEY", "")


def _get_config() -> Dict[str, str]:
    api_key = os.environ.get("OPENVIKING_API_KEY") or os.environ.get("OPENVIKING_ROOT_API_KEY") or ""
    if not api_key:
        for conf_file in ("ov.conf", "ovcli.conf"):
            p = Path.home() / ".openviking" / conf_file
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        api_key = data.get("server", {}).get("root_api_key") or data.get("root_api_key", "")
                        if api_key:
                            break
                except Exception:
                    pass
    return {
        "api": os.environ.get("OPENVIKING_API", DEFAULT_API).rstrip("/"),
        "api_key": api_key or DEFAULT_API_KEY,
    }


class SatelliteHTTPClient:
    """具备网络抖动自愈重试机制的纯数据客户端"""

    def __init__(self):
        cfg = _get_config()
        self.api = cfg["api"]
        self.api_key = cfg["api_key"]

    def _request(self, method: str, path: str, body: Any = None, timeout: int = 30, params: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{self.api}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        cfg = _get_config()
        api_key = cfg["api_key"] or self.api_key

        headers = {
            "Content-Type": "application/json",
            "X-OpenViking-Account": "default",
            "X-OpenViking-User": "satellite",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, headers=headers, method=method)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urlopen(req, timeout=timeout) as resp:
                    content = resp.read().decode("utf-8")
                    if not content:
                        return {"ok": True}
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"raw": content}
            except HTTPError as e:
                if e.code in (502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                body_text = ""
                try:
                    body_text = e.read().decode("utf-8")
                except Exception:
                    pass
                return {"error": f"HTTP {e.code}: {body_text}", "is_http_error": True, "code": e.code}
            except URLError as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {"error": f"远程 OpenViking 连接失败: {e.reason}。请检查 OPENVIKING_API 地址与网络代理。"}
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {"error": str(e)}
        return {"error": "请求超时或超过最大重试次数"}

    def get(self, path: str, params: Optional[dict] = None, timeout: int = 30) -> Any:
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path: str, body: Any = None, timeout: int = 30) -> Any:
        return self._request("POST", path, body, timeout=timeout)


http_client = SatelliteHTTPClient()


def _format_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def _validate_uri(uri: Any, param_name: str = "uri") -> Optional[str]:
    if isinstance(uri, str) and uri and not uri.startswith("viking://"):
        return f"参数 {param_name} 格式错误: '{uri}' 必须以 'viking://' 开头"
    return None

# SECTION: FastMCP Instance & Graceful Deprecation Shim
mcp = FastMCP(
    name="openviking-satellite",
    instructions=(
        "OpenViking Satellite MCP Server — 远程卫星端知识中枢客户端。"
        "提供体外大脑语义检索 (openviking_find)、记忆分层读取、代码结构大纲、知识存盘与自演进上报。"
    ),
)


def _safe_tool(*args, **kwargs):
    def decorator(fn):
        tool_kwargs = dict(kwargs)
        tool_name = tool_kwargs.get("name") or fn.__name__
        if tool_name == "openviking_find":
            orig_desc = tool_kwargs.get("description") or fn.__doc__ or ""
            prefix = "【Mandatory First Step / 开局必调】在开始回答任何工程、架构或排障问题前，必须首先调用此工具查询体外大脑（VK）中的历史经验与避坑规则。\n"
            if prefix not in orig_desc:
                tool_kwargs["description"] = prefix + orig_desc

        sig = inspect.signature(fn)

        @wraps(fn)
        def cleaned_fn(*f_args, **f_kwargs):
            try:
                bound = sig.bind_partial(*f_args, **f_kwargs)
                for name, param in sig.parameters.items():
                    if name not in bound.arguments:
                        val = param.default
                        if hasattr(val, "default"):
                            d = getattr(val, "default")
                            bound.arguments[name] = "" if d is None or "PydanticUndefined" in str(type(d)) else d
                    else:
                        val = bound.arguments[name]
                        if hasattr(val, "default"):
                            d = getattr(val, "default")
                            bound.arguments[name] = "" if d is None or "PydanticUndefined" in str(type(d)) else d
                return fn(*bound.args, **bound.kwargs)
            except Exception:
                return fn(*f_args, **f_kwargs)

        return mcp.tool(*args, **tool_kwargs)(cleaned_fn)
    return decorator


# 注入优雅垫片：未暴露的运维特权工具被调用时不抛异常，返回友好提示
_orig_call_tool = mcp._tool_manager.call_tool


async def _graceful_satellite_call(name: str, arguments: dict[str, Any], context: Any = None, convert_result: bool = False) -> Any:
    tool = mcp._tool_manager.get_tool(name)
    if not tool and name.startswith("openviking_"):
        logger.info(f"[Shim Intercepted] Satellite client invoked trimmed tool: {name}")
        msg = json.dumps({
            "status": "skipped",
            "tool": name,
            "message": f"[Satellite Mode] 工具 '{name}' 为本地核心运维特权接口，卫星客户端已安全解耦。当前卫星客户端专注于数据面语义检索与知识协作。",
            "suggestion": "请使用 openviking_find, openviking_smart_read 或在服务端节点执行运维指令。",
        }, ensure_ascii=False, indent=2)
        if convert_result:
            return [TextContent(type="text", text=msg)]
        return msg
    return await _orig_call_tool(name, arguments, context=context, convert_result=convert_result)


mcp._tool_manager.call_tool = _graceful_satellite_call

# SECTION: 16 Safe Satellite Tools
@_safe_tool()
def openviking_find(
    query: str = Field(description="搜索查询文本"),
    target_uri: str = Field(default="", description="限定搜索范围的 URI"),
    limit: int = Field(default=5, description="返回结果数量"),
    score_threshold: float = Field(default=0.0, description="最低相关性分数（0-1）"),
    level: str = Field(default="", description="限定层级：0(L0摘要), 1(L1概览), 2(L2全文), 0,1,2(全部)"),
    filter_tags: str = Field(default="", description="过滤标签（逗号分隔）"),
) -> str:
    """两阶段混合语义召回 + Cross-Encoder 深度重排。返回综合评分最高的相关上下文。"""
    body: Dict[str, Any] = {"query": query, "limit": limit}
    if target_uri:
        body["target_uri"] = target_uri
    if score_threshold > 0:
        body["score_threshold"] = score_threshold
    if level:
        body["level"] = level.strip()
    if filter_tags:
        body["filter"] = {"tags": [t.strip() for t in filter_tags.split(",") if t.strip()]}
    return _format_result(http_client.post("/api/v1/search/find", body, timeout=60))


@_safe_tool()
def openviking_search(
    query: str = Field(description="搜索查询文本"),
    target_uri: str = Field(default="", description="限定搜索范围的 URI"),
    limit: int = Field(default=5, description="返回结果数量"),
    score_threshold: float = Field(default=0.0, description="最低相关性分数"),
) -> str:
    """标准语义向量检索"""
    body: Dict[str, Any] = {"query": query, "limit": limit}
    if target_uri:
        body["target_uri"] = target_uri
    if score_threshold > 0:
        body["score_threshold"] = score_threshold
    return _format_result(http_client.post("/api/v1/search/search", body))


@_safe_tool()
def openviking_smart_read(
    query: str = Field(description="搜索查询文本"),
    level: int = Field(default=1, description="读取层级：0(L0摘要), 1(L1概览), 2(L2全文)"),
    limit: int = Field(default=3, description="搜索结果数量"),
    score_threshold: float = Field(default=0.0, description="最低相关性分数（0-1）"),
) -> str:
    """智能读取：搜索 + 批量读取组合操作。一次调用完成搜索并返回每个结果的详细内容。"""
    search_body: Dict[str, Any] = {"query": query, "limit": limit}
    if score_threshold > 0:
        search_body["score_threshold"] = score_threshold

    search_result = http_client.post("/api/v1/search/find", search_body)
    results = search_result.get("results", []) if isinstance(search_result, dict) else []

    detailed = []
    for item in results:
        uri = item.get("uri", item.get("id", ""))
        if not uri:
            detailed.append({"search_result": item, "content": {"error": "无 URI"}})
            continue
        endpoint = "/api/v1/content/abstract" if level == 0 else ("/api/v1/content/overview" if level == 1 else "/api/v1/content/read")
        content = http_client.get(endpoint, {"uri": uri})
        detailed.append({"search_result": item, "content": content})

    return _format_result({
        "query": query,
        "level": level,
        "total_results": len(detailed),
        "results": detailed,
    })


@_safe_tool()
def openviking_read(
    target_uri: str = Field(description="资源 Viking URI"),
    level: Any = Field(default=2, description="读取层级：0(L0摘要), 1(L1概览), 2(L2全文)"),
) -> str:
    """分层读取资源内容。level=0/L0 摘要，level=1/L1 概览，level=2/L2 全文。"""
    lvl = str(level).strip().lower()
    endpoint = "/api/v1/content/abstract" if lvl in ("0", "l0", "abstract") else ("/api/v1/content/overview" if lvl in ("1", "l1", "overview") else "/api/v1/content/read")
    return _format_result(http_client.get(endpoint, {"uri": target_uri}))


@_safe_tool()
def openviking_store(
    session_id: str = Field(default="", description="会话 ID（留空使用当前会话）"),
    role: str = Field(default="user", description="消息角色：user/assistant/system"),
    content: str = Field(default="", description="消息内容（为空时仅提交会话）"),
) -> str:
    """存储消息到长期记忆。content 为空时提交并归档记忆。"""
    if content:
        body = {"role": role, "parts": [{"type": "text", "text": content}]}
        if session_id:
            return _format_result(http_client.post(f"/api/v1/sessions/{session_id}/messages", body))
        return _format_result(http_client.post("/api/v1/sessions", {"session_id": "default", "message": body}))
    return _format_result(http_client.post(f"/api/v1/sessions/{session_id or 'default'}/commit"))


@_safe_tool()
def openviking_write(
    target_uri: str = Field(description="目标 Viking URI"),
    content: str = Field(description="写入内容"),
    mode: str = Field(default="replace", description="写入模式：replace(覆盖), append(追加), create(新建/创建目录)"),
) -> str:
    """写入/修改资源。支持覆盖、追加与新建。"""
    res = http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": mode})
    if isinstance(res, dict) and "HTTP 404" in str(res.get("error")) and mode == "replace":
        res = http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": "create"})
    return _format_result(res)


@_safe_tool()
def openviking_code_search(
    query: str = Field(description="符号名搜索"),
    target_uri: str = Field(default="viking://", description="搜索范围"),
) -> str:
    """搜索代码符号名（函数、类、变量等）"""
    body: Dict[str, Any] = {"query": query}
    if target_uri and target_uri != "viking://":
        body["target_uri"] = target_uri
    return _format_result(http_client.post("/api/v1/search/find", body))


@_safe_tool()
def openviking_code_outline(
    target_uri: str = Field(description="代码文件 Viking URI"),
) -> str:
    """提取文件符号结构大纲（函数、类等）"""
    return _format_result(http_client.get("/api/v1/content/overview", {"uri": target_uri}))


@_safe_tool()
def openviking_code_expand(
    target_uri: str = Field(description="符号所在文件 Viking URI"),
    symbol: str = Field(default="", description="符号名"),
) -> str:
    """返回符号所在文件完整源码切片"""
    return _format_result(http_client.get("/api/v1/content/read", {"uri": target_uri}))


@_safe_tool()
def openviking_grep(
    pattern: str = Field(description="正则表达式"),
    target_uri: str = Field(default="viking://", description="搜索范围 URI"),
    limit: int = Field(default=50, description="最大返回数"),
) -> str:
    """正则表达式匹配文件行内容"""
    return _format_result(http_client.post("/api/v1/search/grep", {"pattern": pattern, "uri": target_uri, "limit": limit}))


@_safe_tool()
def openviking_record_evolution_lesson(
    skill_name: str = Field(description="目标演进技能名称（例如 diagnosing-bugs, tdd 等）"),
    lesson_title: str = Field(description="Lesson 简短标题（概括踩坑教训与物理原则）"),
    context: str = Field(default="", description="触发纠偏的上下文场景"),
    reflection: str = Field(default="", description="根因与物理逻辑分析"),
    lesson: str = Field(default="", description="提炼出的永久闭环规范"),
) -> str:
    """Harness Reflexion 隐式自演进钩子：双写纯 Markdown 镜像至 OpenViking Master Memory 永久存盘"""
    try:
        clean_slug = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]+', '_', lesson_title).strip('_').lower() or "lesson"
        date_str = time.strftime('%Y%m%d_%H%M%S')
        mirror_filename = f"{date_str}_{skill_name}_{clean_slug}.md"
        master_uri = f"viking://resources/master_memory/evolution_lessons/{mirror_filename}"

        mirror_content = f"""# Evolution Lesson: {lesson_title}
- **Skill**: `{skill_name}`
- **Recorded At**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Context**: {context}

## 🔍 Reflection & Root Cause Analysis
{reflection}

## 📜 Permanent Guidelines & Lesson
{lesson}
"""
        res = http_client.post("/api/v1/content/write", {
            "uri": master_uri,
            "content": mirror_content,
            "mode": "create",
        })
        return _format_result({
            "status": "ok",
            "message": f"成功将 Lesson '{lesson_title}' 存盘至 OpenViking Master Memory",
            "skill_name": skill_name,
            "master_memory_uri": master_uri,
            "response": res,
        })
    except Exception as e:
        return _format_result({"status": "error", "error": str(e)})


@_safe_tool()
def openviking_tree(
    target_uri: str = Field(default="viking://", description="要展示的 Viking URI"),
    depth: int = Field(default=3, description="树深度"),
) -> str:
    """递归树形展示目录结构"""
    return _format_result(http_client.post("/api/v1/fs/tree", {"uri": target_uri, "depth": depth}))


@_safe_tool()
def openviking_skills(
    action: str = Field(default="list", description="操作：list（列出）"),
) -> str:
    """查看当前知识中枢托管的技能规范列表"""
    return _format_result(http_client.get("/api/v1/skills"))


@_safe_tool()
def openviking_get_relations(
    target_uri: str = Field(description="Viking URI"),
) -> str:
    """获取资源关联列表与知识图谱拓扑"""
    return _format_result(http_client.get("/api/v1/relations", {"uri": target_uri}))


@_safe_tool()
def openviking_health() -> str:
    """检查远端 OpenViking 服务健康度"""
    health = http_client.get("/health")
    ready = http_client.get("/ready")
    status = http_client.get("/api/v1/system/status")
    return _format_result({"health": health, "ready": ready, "status": status})


@_safe_tool()
def openviking_ping() -> str:
    """检测远端连接状态、网络延迟与可用工具数握手自检"""
    cfg = _get_config()
    status = {
        "status": "ok",
        "client_distribution": "standalone_satellite",
        "server_version": "1.4.32",
        "mode": "satellite",
        "api_url": cfg["api"],
        "authenticated": bool(cfg["api_key"]),
        "tools_count": len(list(mcp._tool_manager.list_tools())),
        "platform": sys.platform,
        "latency_ms": -1.0,
    }
    try:
        t0 = time.time()
        res = http_client.get("/health", timeout=5)
        status["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        if "error" not in res:
            status["http_available"] = True
            status["http_health"] = res
        else:
            status["status"] = "degraded"
            status["http_error"] = res.get("error")
    except Exception as e:
        status["status"] = "degraded"
        status["http_error"] = str(e)

    return _format_result(status)


# SECTION: Entry Point
if __name__ == "__main__":
    logger.info("🚀 OpenViking Standalone Satellite MCP Server starting...")
    if any(arg.isdigit() for arg in sys.argv[1:]):
        port = next(int(arg) for arg in sys.argv[1:] if arg.isdigit())
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
