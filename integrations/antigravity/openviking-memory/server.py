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
    try:
        kwargs = {"timeout": timeout} if timeout is not None else {}
        with urllib.request.urlopen(req, **kwargs) as resp:
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
        return f"[Fail-Fast Guard] 请求后端超时 ({timeout}s) 自动熔断: {e}"
    except Exception as e:
        return f"Request Error: {e}"


# SECTION: FastMCP Initialization
mcp = FastMCP(
    name="openviking-memory",
    instructions="OpenViking 战地记忆中枢 (37 Tools) — 语义检索、两阶段重排、分层读取、会话管理与踩坑存盘。",
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
    budget: int = Field(default=4000, description="Token 预算"),
) -> str:
    """智能上下文提纯与按需抽稀阅读。"""
    return _api_request("POST", "/api/v1/search/find", body={"query": query, "target_uri": target_uri, "budget": budget})

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

@mcp.tool()
def openviking_tag(
    target_uri: str = Field(description="目标 Viking URI"),
    action: str = Field(default="list", description="操作：list/add/remove"),
    tags: str = Field(default="", description="标签（逗号分隔）"),
) -> str:
    """管理资源的标签元数据。"""
    if action == "list":
        return _api_request("GET", "/api/v1/tags", params={"uri": target_uri})
    elif action == "add":
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        return _api_request("POST", "/api/v1/tags", body={"uri": target_uri, "tags": tag_list})
    elif action == "remove":
        return _api_request("DELETE", f"/api/v1/tags?uri={urllib.parse.quote(target_uri)}&tags={urllib.parse.quote(tags)}")
    return f"Invalid action: {action}"

@mcp.tool()
def openviking_diff(
    source_uri: str = Field(description="源 Viking URI"),
    target_uri: str = Field(description="目标 Viking URI"),
) -> str:
    """比较两个 Viking URI 之间的内容差异。"""
    return _api_request("GET", "/api/v1/content/diff", params={"source": source_uri, "target": target_uri})

# ─── 4. Skills Tools (6) ──────────────────────────────────────────────────
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
def openviking_audit_skills(
    fix: bool = Field(default=False, description="是否自动修复不合规项"),
) -> str:
    """全量技能规范与合规性审计。"""
    return _api_request("GET", "/api/v1/skills/audit", params={"fix": fix})

@mcp.tool()
def openviking_auto_onboard_skills(
    path: str = Field(default="", description="外部技能目录或文件路径"),
) -> str:
    """一键自动化批量纳管野生技能。"""
    return _api_request("POST", "/api/v1/skills/ingestion/submit", body={"path": path})

@mcp.tool()
def openviking_get_onboard_queue_status() -> str:
    """获取技能入库流水线队列排队状态。"""
    return _api_request("GET", "/api/v1/skills/ingestion/queue")

@mcp.tool()
def openviking_fix_skill(
    skill_name: str = Field(description="待修复技能名"),
    issue_description: str = Field(default="", description="问题描述"),
) -> str:
    """基于诊断报错微手术自愈修复技能。"""
    return _api_request("POST", "/api/v1/skills/fix", body={"name": skill_name, "issue": issue_description})

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
    relation_type: str = Field(default="related", description="关联类型"),
) -> str:
    """在两组资源之间建立语义拓扑关联。"""
    return _api_request("POST", "/api/v1/relations/link", body={"source": source_uri, "target": target_uri, "type": relation_type})

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
    return _api_request("POST", "/api/v1/relations/unlink", body={"source": source_uri, "target": target_uri})

# ─── 6. System Tools (6) ──────────────────────────────────────────────────
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
def openviking_server_doctor(
    auto_fix: bool = Field(default=False, description="是否尝试自愈修复"),
) -> str:
    """运行全套 OpenViking 服务端环境诊断探针。"""
    return _api_request("GET", "/api/v1/system/doctor", params={"auto_fix": auto_fix})

@mcp.tool()
def openviking_privacy(
    action: str = Field(default="status", description="操作：status/categories/list/get/upsert"),
    category: str = Field(default="", description="分类"),
    target_key: str = Field(default="", description="目标键"),
    values_json: str = Field(default="", description="JSON 值"),
) -> str:
    """隐私保护与敏感数据过滤配置管理。"""
    return _api_request("GET", "/api/v1/privacy/status")

@mcp.tool()
def openviking_consistency(
    target_uri: str = Field(default="viking://", description="检查范围 URI"),
    fix: bool = Field(default=False, description="是否自动修复"),
) -> str:
    """检查文件系统与向量索引一致性。"""
    return _api_request("GET", "/api/v1/fs/consistency", params={"uri": target_uri, "fix": fix})

@mcp.tool()
def openviking_ping() -> str:
    """快速网络测速与心跳保活握手。"""
    return json.dumps({
        "status": "ok",
        "proxy": "Antigravity-Memory-Proxy-Stub",
        "version": "2.0.16",
        "api_endpoint": API_BASE,
        "tools_count": 37,
        "timestamp": time.time()
    }, ensure_ascii=False, indent=2)

# ─── 7. Observability Tools (4) ───────────────────────────────────────────
@mcp.tool()
def openviking_harness_stats(
    action: str = Field(default="get", description="操作：get/reset"),
) -> str:
    """获取 Harness 门禁拦截与调用遥测指标。"""
    return _api_request("GET", "/api/v1/system/stats")

@mcp.tool()
def openviking_usage_stats(
    period: str = Field(default="today", description="周期：today/week/month/all"),
    reset: bool = Field(default=False, description="是否重置统计"),
) -> str:
    """获取 Token 消耗与检索耗时统计。"""
    return _api_request("GET", "/api/v1/system/stats", params={"period": period, "reset": reset})

@mcp.tool()
def openviking_observer(
    component: str = Field(default="overview", description="观察组件：queue/vikingdb/models/lock/retrieval/system"),
) -> str:
    """获取指定子系统实时运转态势数据。"""
    return _api_request("GET", f"/api/v1/observer/{component}")

@mcp.tool()
def openviking_metrics(
    category: str = Field(default="all", description="指标类别"),
) -> str:
    """获取 Prometheus 格式系统指标。"""
    return _api_request("GET", "/metrics")


if __name__ == "__main__":
    # 纯净运行 FastMCP stdio 传输
    sys.argv = [sys.argv[0]]
    mcp.run(transport="stdio")
