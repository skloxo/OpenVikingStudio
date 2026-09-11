#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: satellite_mcp_server ──────────────────────────────────────────
"""
OpenViking Satellite MCP Server (Standalone Zero-Dependency Distribution - v1.4.43)
专为远程算力节点与外部 Agent 设计的轻量单文件分发包（16 大纯安全数据与感知工具）。
"""

# SECTION: Imports
import asyncio
import inspect
import json
import logging
import os
import platform
import re
import socket
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

_HEAVY_TOOLS = {"openviking_find", "openviking_search", "openviking_smart_read"}
_heavy_semaphore: Optional[asyncio.Semaphore] = None

def _get_heavy_semaphore() -> asyncio.Semaphore:
    global _heavy_semaphore
    if _heavy_semaphore is None: _heavy_semaphore = asyncio.Semaphore(2)
    return _heavy_semaphore

if sys.platform == "win32":
    for _s in (sys.stdin, sys.stdout, sys.stderr):
        try: _s.reconfigure(encoding="utf-8")
        except Exception: pass

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from pydantic import Field

# Pydantic 2.9+ / FastMCP 1.29+ compatibility shim
try:
    import mcp.server.fastmcp.utilities.func_metadata as _fm
    from pydantic import create_model as _pydantic_create_model
    _orig_create_wrapped = getattr(_fm, "_create_wrapped_model", None)
    if _orig_create_wrapped:
        def _safe_create_wrapped_model(func_name: str, annotation: Any):
            try: return _orig_create_wrapped(func_name, annotation)
            except Exception: return _pydantic_create_model(f"{func_name}Output", result=(annotation, ...))
        _fm._create_wrapped_model = _safe_create_wrapped_model
except Exception: pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openviking-satellite-mcp")

# SECTION: Configuration & Remote HTTP Client
DEFAULT_API = os.environ.get("OPENVIKING_API", "http://127.0.0.1:1933").rstrip("/")
DEFAULT_API_KEY = os.environ.get("OPENVIKING_API_KEY", "")


def _get_config() -> Dict[str, str]:
    api_key = os.environ.get("OPENVIKING_API_KEY") or os.environ.get("OPENVIKING_ROOT_API_KEY") or ""
    api_url = os.environ.get("OPENVIKING_API", "").rstrip("/")
    if not api_key or not api_url:
        for conf_file in ("ov.conf", "ovcli.conf"):
            p = Path.home() / ".openviking" / conf_file
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sd = data.get("server", data) if isinstance(data, dict) else {}
                    api_key = api_key or sd.get("root_api_key") or sd.get("api_key", "")
                    api_url = api_url or (sd.get("url") or data.get("url") or "").rstrip("/")
                    if api_key and api_url:
                        break
                except Exception:
                    pass
    return {"api": api_url or DEFAULT_API, "api_key": api_key or DEFAULT_API_KEY}


def get_resolved_actor_peer(default_client: str = "workbuddy") -> str:
    """解析并返回合规 Agent 身份 (client@node，如 antigravity@3070 / workbuddy@3070)"""
    explicit = os.environ.get("OPENVIKING_ACTOR_PEER", "").strip()
    if explicit: return explicit
    node = os.environ.get("OPENVIKING_NODE", "").strip().lower()
    if not node:
        if sys.platform == "win32":
            comp = os.environ.get("COMPUTERNAME", "").lower()
            node = "3070" if "3070" in comp else ("2080ti" if "2080" in comp else "win")
        elif sys.platform == "darwin": node = "mac"
        else:
            hname = socket.gethostname().lower()
            node = "3070" if "3070" in hname else ("2080ti" if ("2080" in hname or Path("/mnt/c").exists()) else (hname.split(".")[0] or "linux"))
    client = os.environ.get("OPENVIKING_CLIENT", "").strip().lower()
    if not client:
        full_ctx = (sys.executable + " " + " ".join(sys.argv) + " " + os.getcwd()).lower() + " " + (" ".join(os.environ.keys()) + " " + " ".join(os.environ.values())).lower()
        if any(x in full_ctx for x in ("antigravity", "gemini")): client = "antigravity"
        elif any(x in full_ctx for x in ("workbuddy", "codebuddy")): client = "workbuddy"
        elif any(x in full_ctx for x in ("mimocode", "xiaomimo")): client = "xiaomimo"
        elif "openclaw" in full_ctx: client = "openclaw"
        elif "hermes" in full_ctx: client = "hermes"
        else: client = default_client
    clean_client = re.sub(r"[^a-zA-Z0-9_.-]", "", client) or default_client
    clean_node = re.sub(r"[^a-zA-Z0-9_-]", "", node) or "remote"
    return f"{clean_client}@{clean_node}"


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
        peer_id = get_resolved_actor_peer("workbuddy")

        headers = {
            "Content-Type": "application/json",
            "X-OpenViking-Account": "default",
            "X-OpenViking-User": os.environ.get("OPENVIKING_USER", "default"),
            "X-OpenViking-Actor-Peer": peer_id,
            "X-Caller": peer_id,
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, headers=headers, method=method)

        start_time = time.time()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urlopen(req, timeout=timeout) as resp:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    content = resp.read().decode("utf-8")
                    logger.debug(f"[Satellite_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms status={resp.status}")
                    if not content: return {"ok": True}
                    try: return json.loads(content)
                    except json.JSONDecodeError: return {"raw": content}
            except HTTPError as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                if e.code in (502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                body_text = ""
                try:
                    body_text = e.read().decode("utf-8")
                except Exception:
                    pass
                return {"error": f"[BACKEND_ERROR] HTTP {e.code}: {body_text}", "is_http_error": True, "code": e.code, "elapsed_ms": elapsed_ms}
            except (TimeoutError, URLError) as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                err_msg = str(getattr(e, "reason", e))
                if "timed out" in err_msg.lower() or isinstance(e, TimeoutError):
                    return {"error": f"[BRIDGE_TIMEOUT] 桥接层请求后端超时 ({timeout}s): {err_msg}", "code": "BRIDGE_TIMEOUT", "elapsed_ms": elapsed_ms}
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {"error": f"[CONNECTION_ERROR] 远程 OpenViking 连接失败: {err_msg}", "code": "CONNECTION_ERROR", "elapsed_ms": elapsed_ms}
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {"error": f"[CLIENT_ERROR] {str(e)}", "elapsed_ms": elapsed_ms}
        return {"error": f"[BRIDGE_TIMEOUT] 请求后端超时 ({timeout}s)"}

    def get(self, path: str, params: Optional[dict] = None, timeout: int = 30) -> Any:
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path: str, body: Any = None, timeout: int = 30) -> Any:
        return self._request("POST", path, body, timeout=timeout)


http_client = SatelliteHTTPClient()


def _compact_search_result(data: Any) -> Any:
    """渐进式分级展开：对检索结果中超过 350 字符的 abstract 进行紧凑截断，避免污染上下文。"""
    if not isinstance(data, (dict, list)):
        return data
    import copy
    try:
        data = copy.deepcopy(data)
    except Exception:
        return data

    def _trunc(items):
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and isinstance(it.get("abstract"), str) and len(it["abstract"]) > 350:
                    u = it.get("uri", "")
                    it["abstract"] = it["abstract"][:350] + (f"... [高密摘要截断，请使用 openviking_read(uri='{u}')]" if u else "... [高密摘要截断]")

    target = data.get("result", data) if isinstance(data, dict) else data
    if isinstance(target, dict):
        for k in ("memories", "resources", "skills", "results"):
            if k in target:
                _trunc(target[k])
    elif isinstance(target, list):
        _trunc(target)
    return data


def _format_result(result: Any) -> str:
    return result if isinstance(result, str) else json.dumps(_compact_search_result(result), ensure_ascii=False, indent=2)


def _validate_uri(uri: Any, param_name: str = "uri") -> Optional[str]:
    return f"参数 {param_name} 格式错误: '{uri}' 必须以 'viking://' 开头" if (isinstance(uri, str) and uri and not uri.startswith("viking://")) else None

# SECTION: FastMCP Instance & Graceful Deprecation Shim
mcp = FastMCP(
    name="openviking-satellite",
    instructions="OpenViking Satellite MCP Server — 远程卫星端知识中枢客户端。提供体外大脑语义检索 (openviking_find)、分层读取、代码大纲、知识存盘与自演进上报。",
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
                    val = bound.arguments.get(name, param.default)
                    if hasattr(val, "default"):
                        d = getattr(val, "default")
                        bound.arguments[name] = "" if d is None or "PydanticUndefined" in str(type(d)) else d
                    elif name not in bound.arguments:
                        bound.arguments[name] = val
                return fn(*bound.args, **bound.kwargs)
            except Exception as e:
                logger.error(f"[Tool Execution Error] {tool_name}: {e}")
                return _format_result({"error": str(e)})

        @wraps(fn)
        async def mcp_async_fn(*f_args, **f_kwargs):
            if tool_name in _HEAVY_TOOLS:
                async with _get_heavy_semaphore():
                    return await asyncio.to_thread(cleaned_fn, *f_args, **f_kwargs)
            return await asyncio.to_thread(cleaned_fn, *f_args, **f_kwargs)

        mcp.tool(*args, **tool_kwargs)(mcp_async_fn)
        return cleaned_fn
    return decorator


# 注入优雅垫片：未暴露的运维特权工具被调用时不抛异常，返回友好提示
_orig_call_tool = mcp._tool_manager.call_tool


async def _graceful_satellite_call(name: str, arguments: dict[str, Any], context: Any = None, convert_result: bool = False) -> Any:
    tool = mcp._tool_manager.get_tool(name)
    if not tool and name.startswith("openviking_"):
        logger.info(f"[Shim Intercepted] Satellite client invoked trimmed tool: {name}")
        msg = json.dumps({
            "status": "skipped", "tool": name,
            "message": f"[Satellite Mode] 工具 '{name}' 为本地核心运维特权接口，卫星客户端已安全解耦。",
            "suggestion": "请使用 openviking_find, openviking_smart_read 或在服务端节点执行运维指令。",
        }, ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=msg)] if convert_result else msg
    return await _orig_call_tool(name, arguments, context=context, convert_result=convert_result)


mcp._tool_manager.call_tool = _graceful_satellite_call

# SECTION: 16 Safe Satellite Tools
@_safe_tool()
def openviking_find(
    query: str = Field(description="搜索查询文本"), target_uri: str = Field(default="", description="限定搜索范围 URI"),
    limit: int = Field(default=5, description="返回结果数量"), score_threshold: float = Field(default=0.0, description="最低相关性分数（0-1）"),
    level: str = Field(default="", description="限定层级：0(L0), 1(L1), 2(L2)"), filter_tags: str = Field(default="", description="过滤标签"),
    mode: str = Field(default="fast", description="检索模式：fast(默认), thinking, quick"),
) -> str:
    """两阶段混合语义召回 + Cross-Encoder 深度重排。返回综合评分最高的相关上下文。"""
    body: Dict[str, Any] = {"query": query, "limit": limit}
    if mode: body["mode"] = mode.strip()
    if target_uri: body["target_uri"] = target_uri
    if score_threshold > 0: body["score_threshold"] = score_threshold
    if level: body["level"] = level.strip()
    if filter_tags: body["filter"] = {"tags": [t.strip() for t in filter_tags.split(",") if t.strip()]}
    return _format_result(http_client.post("/api/v1/search/find", body, timeout=60))


@_safe_tool()
def openviking_search(
    query: str = Field(description="搜索查询文本"), target_uri: str = Field(default="", description="限定搜索范围 URI"),
    limit: int = Field(default=5, description="返回数量"), score_threshold: float = Field(default=0.0, description="最低分数"),
) -> str:
    """标准语义向量检索"""
    body: Dict[str, Any] = {"query": query, "limit": limit}
    if target_uri: body["target_uri"] = target_uri
    if score_threshold > 0: body["score_threshold"] = score_threshold
    return _format_result(http_client.post("/api/v1/search/search", body))


@_safe_tool()
def openviking_smart_read(
    query: str = Field(description="搜索查询文本"), level: int = Field(default=1, description="层级：0(L0), 1(L1), 2(L2)"),
    limit: int = Field(default=3, description="结果数量"), score_threshold: float = Field(default=0.0, description="最低分数"),
) -> str:
    """智能读取：搜索 + 批量读取组合操作。一次调用完成搜索并返回每个结果的详细内容。"""
    search_body: Dict[str, Any] = {"query": query, "limit": limit}
    if score_threshold > 0:
        search_body["score_threshold"] = score_threshold
    search_result = http_client.post("/api/v1/search/find", search_body)
    results = []
    if isinstance(search_result, dict):
        res_obj = search_result.get("result", {})
        if isinstance(res_obj, dict):
            results = search_result.get("results") or (res_obj.get("resources", []) + res_obj.get("memories", []))
        elif isinstance(res_obj, list):
            results = res_obj
        else:
            results = search_result.get("results", [])

    detailed = []
    for item in results:
        uri = item.get("uri", item.get("id", ""))
        if not uri:
            detailed.append({"search_result": item, "content": {"error": "无 URI"}})
            continue
        ep = "/api/v1/content/abstract" if level == 0 else ("/api/v1/content/overview" if level == 1 else "/api/v1/content/read")
        detailed.append({"search_result": item, "content": http_client.get(ep, {"uri": uri})})

    return _format_result({"query": query, "level": level, "total_results": len(detailed), "results": detailed})


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
    session_id: str = Field(default="", description="会话 ID"), role: str = Field(default="user", description="角色"),
    content: str = Field(default="", description="内容"), semantic_anchor: str = Field(default="", description="检索锚点"),
    delta: str = Field(default="", description="Git Diff/代码指纹"),
) -> str:
    """存储消息到长期记忆。支持双轨写入（semantic_anchor 检索 + delta 代码重放）。content 为空时提交。"""
    def _s(v: Any, d: str = "") -> str: return str(v).strip() if (v and not hasattr(v, "default")) else d
    sid, role_str, content_str = _s(session_id, "default"), _s(role, "user"), _s(content)
    anchor_str, delta_str = _s(semantic_anchor), _s(delta)
    if anchor_str or delta_str:
        try:
            from openviking.service.memory_dual_track import format_dual_track_markdown
            content_str = format_dual_track_markdown(content_str or "Dual-Track Memory", anchor_str, delta_str)
        except Exception:
            pass
    if content_str:
        return _format_result(http_client.post(f"/api/v1/sessions/{sid or 'default'}/messages", {"role": role_str, "parts": [{"type": "text", "text": content_str}]}))
    return _format_result(http_client.post(f"/api/v1/sessions/{sid or 'default'}/commit"))


@_safe_tool()
def openviking_write(
    target_uri: str = Field(description="目标 Viking URI"), content: str = Field(description="写入内容"),
    mode: str = Field(default="replace", description="写入模式：replace, append, create"),
) -> str:
    """写入/修改资源。支持覆盖、追加与新建。"""
    res = http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": mode})
    if isinstance(res, dict) and "HTTP 404" in str(res.get("error")) and mode == "replace":
        res = http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": "create"})
    return _format_result(res)


@_safe_tool()
def openviking_code_search(query: str = Field(description="符号名搜索"), target_uri: str = Field(default="viking://", description="搜索范围")) -> str:
    """搜索代码符号名（函数、类、变量等）"""
    body: Dict[str, Any] = {"query": query}
    if target_uri and target_uri != "viking://": body["target_uri"] = target_uri
    return _format_result(http_client.post("/api/v1/search/find", body))


@_safe_tool()
def openviking_code_outline(target_uri: str = Field(description="代码文件 Viking URI")) -> str:
    """提取文件符号结构大纲（函数、类等）"""
    return _format_result(http_client.get("/api/v1/content/overview", {"uri": target_uri}))


@_safe_tool()
def openviking_code_expand(target_uri: str = Field(description="符号所在文件 Viking URI"), symbol: str = Field(default="", description="符号名")) -> str:
    """返回符号所在文件完整源码切片"""
    return _format_result(http_client.get("/api/v1/content/read", {"uri": target_uri}))


@_safe_tool()
def openviking_grep(pattern: str = Field(description="正则表达式"), target_uri: str = Field(default="viking://", description="搜索范围 URI"), limit: int = Field(default=50, description="最大返回数")) -> str:
    """正则表达式匹配文件行内容"""
    return _format_result(http_client.post("/api/v1/search/grep", {"pattern": pattern, "uri": target_uri, "limit": limit}))


@_safe_tool()
def openviking_record_evolution_lesson(
    skill_name: str = Field(description="目标演进技能名称"), lesson_title: str = Field(description="Lesson 简短标题"),
    context: str = Field(default="", description="触发场景"), reflection: str = Field(default="", description="根因分析"),
    lesson: str = Field(default="", description="闭环规范"),
) -> str:
    """Harness Reflexion 隐式自演进钩子：双写纯 Markdown 镜像至 OpenViking Master Memory 永久存盘"""
    try:
        clean_slug = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]+', '_', lesson_title).strip('_').lower() or "lesson"
        date_str = time.strftime('%Y%m%d_%H%M%S')
        master_uri = f"viking://resources/master_memory/evolution_lessons/{date_str}_{skill_name}_{clean_slug}.md"
        mirror_content = f"# Evolution Lesson: {lesson_title}\n- **Skill**: `{skill_name}`\n- **Recorded At**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n- **Context**: {context}\n\n## 🔍 Reflection & Root Cause Analysis\n{reflection}\n\n## 📜 Permanent Guidelines & Lesson\n{lesson}\n"
        res = http_client.post("/api/v1/content/write", {"uri": master_uri, "content": mirror_content, "mode": "create"})
        return _format_result({"status": "ok", "message": f"成功将 Lesson '{lesson_title}' 存盘至 OpenViking Master Memory", "skill_name": skill_name, "master_memory_uri": master_uri, "response": res})
    except Exception as e:
        return _format_result({"status": "error", "error": str(e)})


@_safe_tool()
def openviking_tree(target_uri: str = Field(default="viking://", description="要展示的 Viking URI"), depth: int = Field(default=3, description="树深度")) -> str:
    """递归树形展示目录结构"""
    return _format_result(http_client.get("/api/v1/fs/tree", {"uri": target_uri, "level_limit": depth}))


@_safe_tool()
def openviking_skills(action: str = Field(default="list", description="操作：list（列出）")) -> str:
    """查看当前知识中枢托管的技能规范列表"""
    return _format_result(http_client.get("/api/v1/skills"))


@_safe_tool()
def openviking_get_relations(target_uri: str = Field(description="Viking URI")) -> str:
    """获取资源关联列表与知识图谱拓扑"""
    return _format_result(http_client.get("/api/v1/relations", {"uri": target_uri}))


@_safe_tool()
def openviking_health() -> str:
    """检查远端 OpenViking 服务健康度"""
    return _format_result({"health": http_client.get("/health"), "ready": http_client.get("/ready"), "status": http_client.get("/api/v1/system/status")})


@_safe_tool()
def openviking_ping() -> str:
    """检测远端连接状态、网络延迟与可用工具数握手自检"""
    cfg = _get_config()
    status = {"status": "ok", "client_distribution": "standalone_satellite", "server_version": "1.4.43", "mode": "satellite", "api_url": cfg["api"], "authenticated": bool(cfg["api_key"]), "tools_count": len(list(mcp._tool_manager.list_tools())), "platform": sys.platform, "latency_ms": -1.0}
    try:
        t0 = time.time()
        res = http_client.get("/health", timeout=5)
        status["latency_ms"] = round((time.time() - t0) * 1000.0, 2)
        if "error" not in res:
            status["http_available"] = True
            status["http_health"] = res
            if isinstance(res, dict) and "version" in res:
                status["server_version"] = str(res["version"])
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
