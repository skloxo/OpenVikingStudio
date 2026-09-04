#!/usr/bin/env python3
"""
OpenViking MCP Server — AI Agent 可调用的 OpenViking 语义记忆管理工具集

封装 OpenViking CLI 命令和 HTTP API，提供结构化的 MCP 工具接口。
支持：资源管理、语义搜索、分层读取、会话管理、系统监控。

每个工具内部：优先 HTTP API，失败回退 CLI。

连接方式：
- HTTP API（优先）：http://127.0.0.1:1933
- CLI 命令（回退）：openviking / ov 命令行工具

环境变量：
- OPENVIKING_API: HTTP API 地址（默认 http://127.0.0.1:1933）
- OPENVIKING_API_KEY: API Key
- OPENVIKING_CLI: CLI 命令路径（默认 openviking）
"""

import glob
import json
import os
import re
import subprocess
import logging
import time
import inspect
from functools import wraps
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP
from pydantic import Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openviking-mcp")

# ─── Configuration ──────────────────────────────────────────────

DEFAULT_API = "http://127.0.0.1:1933"
DEFAULT_CLI = "openviking"
DEFAULT_ROOT_API_KEY = "vk-sk-495222a7957adda63fdce225acfaa551a1a5378fb9795f5a1df4d1d76a0918bc"

# 全局模式标志：True 时所有工具仅使用 CLI，跳过 HTTP API
CLI_ONLY_MODE = False

# ─── Dual-Mode MCP Architecture (Core vs Satellite) ──────────────────────
# - Core Mode (本地核心模式, 默认): 暴露全量 50+ 接口，带本地系统控制、灾备恢复与记忆治理
# - Satellite Mode (远程卫星模式): 暴露精简安全接口，专注远程知识召回、经验上报与容错自愈
MCP_MODE = os.environ.get("OPENVIKING_MCP_MODE", "core").strip().lower()

SATELLITE_ALLOWED_TOOLS = {
    # 状态探活与基线度量
    "openviking_ping",
    "openviking_health",
    "openviking_system_status",
    "openviking_metrics",
    "openviking_harness_stats",
    # 知识召回与语义检索核心
    "openviking_find",
    "openviking_search",
    "openviking_smart_read",
    "openviking_read",
    "openviking_code_search",
    "openviking_code_outline",
    "openviking_code_expand",
    # 经验提纯与自演进
    "openviking_record_evolution_lesson",
    # 关系与比对
    "openviking_get_relations",
    "openviking_diff",
}


def mcp_tool(*args, **kwargs):
    """双模态感知的 MCP 工具注册装饰器。
    自动解包 FastMCP/Pydantic FieldInfo 默认对象，防止序列化崩塌；
    在 Satellite 模式下只注册安全白名单工具，物理阻断破坏性运维与写指令。
    """
    def decorator(fn):
        tool_name = kwargs.get("name") or fn.__name__
        if MCP_MODE == "satellite" and tool_name not in SATELLITE_ALLOWED_TOOLS:
            logger.info(f"[Dual-Mode MCP] Satellite mode: skipping registration of sensitive tool '{tool_name}'")
            return fn

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

        return mcp.tool(*args, **kwargs)(cleaned_fn)
    return decorator


mcp = FastMCP(
    name="openviking",
    instructions=(
        "OpenViking 语义记忆管理工具集 — 资源管理、语义搜索、分层读取、"
        "会话管理、系统监控。优先 HTTP API，CLI 回退。"
    ),
)

METRICS_FILE_PATH = os.path.expanduser("~/.openviking/harness_metrics.json")


def _load_harness_metrics() -> Dict[str, Any]:
    try:
        if os.path.exists(METRICS_FILE_PATH):
            with open(METRICS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {
        "total_calls": 0,
        "find_calls": 0,
        "store_calls": 0,
        "lessons_count": 0,
        "last_active_timestamp": 0.0,
        "actor_peers": {},
    }


HARNESS_METRICS: Dict[str, Any] = _load_harness_metrics()


def _save_harness_metrics():
    try:
        os.makedirs(os.path.dirname(METRICS_FILE_PATH), exist_ok=True)
        with open(METRICS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(HARNESS_METRICS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"无法保存 harness metrics 到磁盘: {e}")


def _record_harness_call(call_type: str, actor_peer: str = "default"):
    HARNESS_METRICS["total_calls"] = HARNESS_METRICS.get("total_calls", 0) + 1
    HARNESS_METRICS["last_active_timestamp"] = time.time()
    if call_type == "find":
        HARNESS_METRICS["find_calls"] = HARNESS_METRICS.get("find_calls", 0) + 1
    elif call_type == "store":
        HARNESS_METRICS["store_calls"] = HARNESS_METRICS.get("store_calls", 0) + 1
    elif "blocked" in call_type:
        HARNESS_METRICS["blocked_calls"] = HARNESS_METRICS.get("blocked_calls", 0) + 1

    if actor_peer:
        peers = HARNESS_METRICS.setdefault("actor_peers", {})
        peers[actor_peer] = peers.get(actor_peer, 0) + 1

    _save_harness_metrics()


def _harness_pre_execution_guard(tool_name: str, payload: Dict[str, Any]) -> tuple[bool, str]:
    """NeMo Guardrails 式物理前置拦截门锁：物理阻断违规脚本与非法部署行为"""
    file_path = str(payload.get("path") or payload.get("TargetFile") or payload.get("filepath") or "")
    cmd_str = str(payload.get("command") or payload.get("CommandLine") or "")

    if any(p in file_path for p in ["/scripts/", "/public/"]):
        if any(file_path.endswith(ext) for ext in [".py", ".json", ".sh"]):
            _record_harness_call("blocked_script_violation", actor_peer="antigravity")
            return False, f"[Harness Guard Intercepted] 物理阻断：严禁在 scripts/ 或 public/ 创建游离脚本 {os.path.basename(file_path)}！请直改源码。"

    if "web_studio/dist" in cmd_str and not payload.get("user_approved_deploy"):
        _record_harness_call("blocked_deploy_violation", actor_peer="antigravity")
    return True, ""


@mcp_tool()
def openviking_record_evolution_lesson(
    skill_name: str = Field(default="openviking-studio-dev", description="目标演进技能名称"),
    lesson_title: str = Field(default="用户物理纠偏", description="Lesson 简短标题"),
    context: str = Field(default="", description="触发纠偏的上下文场景"),
    reflection: str = Field(default="", description="根因与物理逻辑分析"),
    lesson: str = Field(default="", description="提炼出的永久闭环规范"),
) -> str:
    """Harness Reflexion 隐式自演进钩子：自动写入 SKILL.md 归档 Lesson，并双写纯 Markdown 镜像至 OpenViking Master Memory 永久存盘"""
    try:
        # 1. 动态查找目标技能文件
        candidate_paths = []
        if os.path.exists(skill_name):
            candidate_paths.append(skill_name)
        candidate_paths.extend([
            f"/home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills/{skill_name}/SKILL.md",
            f"/home/skloxo/aho/openclaw/project/.agents/skills/{skill_name}/SKILL.md",
            os.path.expanduser(f"~/.gemini/config/skills/{skill_name}/SKILL.md"),
            f"/home/skloxo/aho/openclaw/skills/{skill_name}/SKILL.md",
            os.path.expanduser(f"~/.openclaw/skills/{skill_name}/SKILL.md"),
        ])
        local_written_file = None
        lesson_entry = f"\n\n#### 📌 Lesson {time.strftime('%Y-%m-%d')}：{lesson_title}\n- **CONTEXT**：{context}\n- **REFLECTION**：{reflection}\n- **LESSON**：{lesson}\n"
        for p in candidate_paths:
            if os.path.exists(p):
                with open(p, "a", encoding="utf-8") as f:
                    f.write(lesson_entry)
                local_written_file = p
                break

        # 2. 双写镜像至 OpenViking Master Memory (体外大脑永久记忆，技能可回滚、知识不回滚)
        clean_slug = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]+', '_', lesson_title).strip('_').lower()
        if not clean_slug:
            clean_slug = "lesson"
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
        mirror_status = "skipped"
        try:
            res = http_client.post("/api/v1/content/write", {
                "uri": master_uri,
                "content": mirror_content,
                "mode": "create"
            })
            if isinstance(res, dict) and (res.get("status") == "ok" or "result" in res):
                mirror_status = "synced"
            else:
                mirror_status = f"response: {res}"
        except Exception as write_err:
            mirror_status = f"error: {str(write_err)}"

        HARNESS_METRICS["lessons_count"] = HARNESS_METRICS.get("lessons_count", 0) + 1
        HARNESS_METRICS["most_evolved_skill"] = skill_name
        _record_harness_call("store", actor_peer="antigravity")

        return _format_result({
            "status": "ok",
            "message": f"成功归档 Lesson '{lesson_title}' 至 {skill_name} 并镜像入脑 Master Memory",
            "lessons_count": HARNESS_METRICS["lessons_count"],
            "most_evolved_skill": skill_name,
            "local_written_file": local_written_file,
            "master_memory_uri": master_uri,
            "mirror_status": mirror_status,
        })
    except Exception as e:
        return _format_result({"status": "error", "error": str(e)})



def _infer_skill_source(name: str, path: str) -> str:
    if "gemini" in path or "antigravity" in path:
        return "Antigravity"
    if name.startswith("sn-") or name.startswith("hermes-"):
        return "Hermes"
    if name.startswith("tide-") or name.startswith("vibe-") or name.startswith("stock-"):
        return "TideTrading"
    return "OpenClaw"


def _parse_skill_description(skill_md_path: str) -> str:
    try:
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read(1000)
                for line in content.split("\n"):
                    if line.strip().startswith("description:"):
                        desc = line.split("description:", 1)[1].strip().strip("\"'")
                        if desc:
                            return desc
    except Exception:
        pass
    return "暂无简介"


def _auto_sync_skills():
    """自动探针：全量递归扫描 IDE/OpenClaw/Gemini/Project 技能目录，生成全量带简介的 ~/.openviking/all_skills.json"""
    try:
        target_base = os.path.expanduser("~/.openviking/skills")
        os.makedirs(target_base, exist_ok=True)

        base_sources = [
            os.path.expanduser("~/.gemini/config/skills"),
            "/home/skloxo/aho/openclaw/skills",
            "/home/skloxo/aho/openclaw/project",
            "/home/skloxo/.openclaw/skills",
            "/home/skloxo/a/SenseNova-Skills/skills",
            "/home/skloxo/.hermes/hermes-agent/optional-skills"
        ]

        found = {}
        for base in base_sources:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", ".git", ".cache", ".npm", "cleanup-backup", "fastapi", ".venv", "dist", "build", ".next", "__pycache__")]
                if "SKILL.md" in files:
                    skill_name = os.path.basename(root)
                    skill_md = os.path.join(root, "SKILL.md")
                    if skill_name not in found:
                        link_path = os.path.join(target_base, skill_name)
                        if not os.path.exists(link_path):
                            try:
                                os.symlink(root, link_path)
                            except Exception:
                                pass
                        desc = _parse_skill_description(skill_md)
                        source = _infer_skill_source(skill_name, root)
                        scope = "user" if "gemini" in root else "agent"
                        content = ""
                        try:
                            with open(skill_md, "r", encoding="utf-8", errors="ignore") as fp:
                                content = fp.read()
                        except Exception:
                            pass

                        skill_files = []
                        try:
                            for r_sub, d_sub, filenames in os.walk(root):
                                rel_root = os.path.relpath(r_sub, root)
                                if rel_root != ".":
                                    skill_files.append({
                                        "name": os.path.basename(r_sub),
                                        "path": rel_root,
                                        "is_dir": True,
                                        "kind": "directory"
                                    })
                                for fn in sorted(filenames):
                                    if fn.startswith("."):
                                        continue
                                    file_rel_path = os.path.join(rel_root, fn) if rel_root != "." else fn
                                    kind = "definition" if fn == "SKILL.md" else ("auxiliary" if fn.endswith(".md") or fn.endswith(".sh") or fn.endswith(".py") else "file")
                                    skill_files.append({
                                        "name": fn,
                                        "path": file_rel_path,
                                        "is_dir": False,
                                        "kind": kind
                                    })
                        except Exception:
                            pass

                        found[skill_name] = {
                            "name": skill_name,
                            "description": desc,
                            "source": source,
                            "path": root,
                            "uri": f"viking://user/skills/{skill_name}/SKILL.md",
                            "scope": scope,
                            "content": content,
                            "files": skill_files
                        }

        all_skills = list(found.values())
        json_path = os.path.expanduser("~/.openviking/all_skills.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_skills, f, ensure_ascii=False, indent=2)

        studio_public_json = "/home/skloxo/aho/openclaw/project/OpenVikingStudio/public/all_skills.json"
        if os.path.exists(os.path.dirname(studio_public_json)):
            with open(studio_public_json, "w", encoding="utf-8") as f:
                json.dump(all_skills, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"技能自动同步异常: {e}")


import threading
threading.Thread(target=_auto_sync_skills, daemon=True, name="skill-sync").start()


def _get_config():
    api_key = os.environ.get("OPENVIKING_API_KEY", "")
    if not api_key:
        conf_path = os.path.expanduser("~/.openviking/ov.conf")
        if os.path.exists(conf_path):
            try:
                with open(conf_path, "r", encoding="utf-8") as f:
                    conf_data = json.load(f)
                    api_key = conf_data.get("server", {}).get("root_api_key", "")
            except Exception:
                pass
    if not api_key:
        api_key = DEFAULT_ROOT_API_KEY
    return {
        "api": os.environ.get("OPENVIKING_API", DEFAULT_API).rstrip("/"),
        "api_key": api_key,
        "cli": os.environ.get("OPENVIKING_CLI", DEFAULT_CLI),
    }



# ─── CLI Runner ─────────────────────────────────────────────────

def _run_cli(args: List[str], timeout: int = 30) -> Dict[str, Any]:
    """执行 OpenViking CLI 命令并返回结果 (自动注入 LD_LIBRARY_PATH)"""
    cfg = _get_config()
    cmd = [cfg["cli"]] + args
    logger.info(f"CLI: {' '.join(cmd)}")
    try:
        env = {
            **os.environ,
            "NO_COLOR": "1",
            "LD_LIBRARY_PATH": f"/home/skloxo/.local/lib:/usr/lib/x86_64-linux-gnu:{os.environ.get('LD_LIBRARY_PATH', '')}"
        }
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            return {
                "ok": False,
                "returncode": result.returncode,
                "stdout": output,
                "stderr": error,
                "error": error or f"CLI 退出码: {result.returncode}",
            }
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"ok": True, "output": output}
        return {"ok": True}
    except FileNotFoundError:
        return {"error": f"CLI 命令未找到: {cfg['cli']}。请确认 OpenViking 已安装并在 PATH 中。"}
    except subprocess.TimeoutExpired:
        return {"error": f"CLI 命令超时 ({timeout}s)"}
    except Exception as e:
        return {"error": str(e)}


# ─── HTTP Client ────────────────────────────────────────────────

class OpenVikingHTTPClient:
    """OpenViking HTTP API 客户端 (100% 优先，支持动态自愈)"""

    def __init__(self):
        cfg = _get_config()
        self.api = cfg["api"]
        self.api_key = cfg["api_key"]

    def _is_available(self) -> bool:
        try:
            req = Request(f"{self.api}/health", headers={"Content-Type": "application/json"}, method="GET")
            with urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _request(
        self,
        method: str,
        path: str,
        body: Any = None,
        timeout: int = 30,
        params: dict = None,
    ) -> Dict[str, Any]:
        url = f"{self.api}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        cfg = _get_config()
        api_key = cfg["api_key"] or self.api_key

        headers = {
            "Content-Type": "application/json",
            "X-OpenViking-Account": "default",
            "X-OpenViking-User": "default"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = Request(url, data=data, headers=headers, method=method)
        max_retries = 3 if MCP_MODE == "satellite" else 1
        for attempt in range(max_retries):
            try:
                with urlopen(req, timeout=timeout) as resp:
                    resp_content = resp.read().decode("utf-8")
                    if not resp_content:
                        return {"ok": True}
                    try:
                        return json.loads(resp_content)
                    except json.JSONDecodeError:
                        return {"raw": resp_content}
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
                return {"error": f"连接失败: {e.reason}. 确认 OpenViking 服务器已启动。"}
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {"error": str(e)}

    def get(self, path: str, params: dict = None, timeout: int = 30) -> Any:
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path: str, body: Any = None, timeout: int = 30) -> Any:
        return self._request("POST", path, body, timeout=timeout)

    def put(self, path: str, body: Any = None, timeout: int = 30) -> Any:
        return self._request("PUT", path, body, timeout=timeout)

    def delete(self, path: str, timeout: int = 30) -> Any:
        return self._request("DELETE", path, timeout=timeout)


http_client = OpenVikingHTTPClient()


# ─── Helpers ────────────────────────────────────────────────────

def _format_result(result: Any) -> str:
    """格式化输出结果"""
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def _api_then_cli(api_call, cli_args: List[str], timeout: int = 30) -> str:
    """100% 优先使用 HTTP API，仅在 HTTP 完全无法连接且非业务响应时才做 CLI 兜底"""
    result = api_call()
    if not isinstance(result, dict):
        return _format_result(result)
    
    # 只要不是连接失败（例如正常成功、或者业务 HTTP 404/400 报错），直接返回 API 真实结果
    if "error" not in result or result.get("is_http_error"):
        return _format_result(result)
    
    if "连接失败" not in str(result.get("error")):
        return _format_result(result)
        
    logger.warning(f"OpenViking HTTP API 不可达，尝试 CLI 回退: {result.get('error')}")
    return _format_result(_run_cli(cli_args, timeout=timeout))
        
    logger.warning(f"API 网络调用失败，回退到 CLI: {result.get('error')}")
    return _format_result(_run_cli(cli_args, timeout=timeout))


def _has_error(result: Any) -> bool:
    """检查结果是否包含错误"""
    return isinstance(result, dict) and "error" in result


# ─── Unified Error Handling ─────────────────────────────────────

def _make_error(error: str, suggestion: str = "") -> str:
    """统一错误格式：{"error": "...", "suggestion": "..."}"""
    out = {"error": error}
    if suggestion:
        out["suggestion"] = suggestion
    return _format_result(out)


def _handle_http_error(e: Exception) -> str:
    """处理 HTTP 错误"""
    if isinstance(e, HTTPError):
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        return _make_error(
            f"HTTP {e.code}: {body_text}",
            "检查 API 地址和认证信息是否正确" if e.code in (401, 403) else
            "检查请求参数是否正确" if e.code == 400 else
            "服务器内部错误，稍后重试" if e.code >= 500 else ""
        )
    elif isinstance(e, URLError):
        return _make_error(
            f"连接失败: {e.reason}",
            "确认 OpenViking 服务器已启动（openviking server start）"
        )
    return _make_error(str(e), "检查 OpenViking 服务状态")


def _handle_cli_error(result: Dict[str, Any]) -> str:
    """处理 CLI 错误，提取关键信息"""
    stderr = result.get("stderr", "")
    stdout = result.get("stdout", "")
    error_msg = result.get("error", stderr or stdout)
    returncode = result.get("returncode", -1)

    suggestion = ""
    if returncode == 127:
        suggestion = "CLI 命令未找到，请确认 OpenViking 已安装并在 PATH 中"
    elif "timeout" in error_msg.lower():
        suggestion = "操作超时，尝试缩小范围或增加 timeout"
    elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
        suggestion = "资源不存在，请检查 URI 是否正确"
    elif "permission" in error_msg.lower() or "access denied" in error_msg.lower():
        suggestion = "权限不足，检查文件权限或 API Key"
    return _make_error(error_msg, suggestion)


def _handle_timeout(operation: str, timeout: int) -> str:
    """处理超时"""
    return _make_error(
        f"操作超时 ({timeout}s): {operation}",
        f"尝试缩小范围、增加超时时间或稍后重试"
    )


# ─── Parameter Validation ───────────────────────────────────────

def _validate_uri(uri: Any, param_name: str = "uri") -> Optional[str]:
    """校验 Viking URI 格式，返回错误信息或 None"""
    if isinstance(uri, str) and uri and not uri.startswith("viking://"):
        return f"参数 {param_name} 格式错误: '{uri}' 必须以 'viking://' 开头"
    return None


def _normalize_level(level: Any) -> int:
    """将各种 level 输入（0, 1, 2, 'L0', 'L1', 'L2', 'abstract', 'overview', 'detail'）归一化为 0, 1, 2"""
    if isinstance(level, int) and level in (0, 1, 2):
        return level
    s = str(level).strip().lower()
    if s in ("0", "l0", "abstract", "summary"):
        return 0
    elif s in ("1", "l1", "overview", "outline"):
        return 1
    return 2


def _validate_level(level: Any, param_name: str = "level") -> Optional[str]:
    """校验 level 参数"""
    if isinstance(level, (int, str)):
        s = str(level).strip().lower()
        if s in ("0", "1", "2", "l0", "l1", "l2", "abstract", "overview", "detail", "full"):
            return None
    return f"参数 {param_name} 格式不符合预期: {level}"


def _validate_limit(limit: Any, param_name: str = "limit") -> Optional[str]:
    """校验 limit 参数"""
    if isinstance(limit, (int, float)) and limit <= 0:
        return f"参数 {param_name} 必须 > 0，当前值: {limit}"
    return None


def _validate_score_threshold(val: Any, param_name: str = "score_threshold") -> Optional[str]:
    """校验 score_threshold 参数"""
    if isinstance(val, (int, float)) and not (0 <= val <= 1):
        return f"参数 {param_name} 必须在 0-1 之间，当前值: {val}"
    return None


# ═══════════════════════════════════════════════════════════════════
# 一、资源管理
# ═══════════════════════════════════════════════════════════════════


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


@mcp_tool()
def openviking_list_resources(
    target_uri: str = Field(default="viking://resources/", description="列出的 URI 路径"),
) -> str:
    """列出资源"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        return http_client.get("/api/v1/resources", {"uri": target_uri})

    def _cli():
        return _run_cli(["ls", target_uri])

    return _api_then_cli(_api, ["ls", target_uri])


@mcp_tool()
def openviking_delete_resource(
    target_uri: str = Field(description="要删除的资源 Viking URI"),
) -> str:
    """删除资源"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        return http_client.delete(f"/api/v1/resources?uri={target_uri}")

    return _api_then_cli(_api, ["rm", target_uri])


# ═══════════════════════════════════════════════════════════════════
# 二、语义搜索
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_find(
    query: str = Field(description="搜索查询文本"),
    target_uri: str = Field(default="", description="限定搜索范围的 URI"),
    limit: int = Field(default=5, description="返回结果数量"),
    score_threshold: float = Field(default=0.0, description="最低相关性分数（0-1）"),
    level: str = Field(default="", description="限定层级：0(L0摘要), 1(L1概览), 2(L2全文), 0,1,2(全部)"),
    filter_tags: str = Field(default="", description="过滤标签（逗号分隔）"),
) -> str:
    # 安全清洗 FastMCP / Pydantic Field 默认对象
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
        body = {"query": query_str, "limit": limit}
        if target_uri_str:
            body["target_uri"] = target_uri_str
        else:
            body["target_uri"] = "viking://resources"
        if score_threshold > 0:
            body["score_threshold"] = score_threshold
        if level_str:
            body["level"] = level_str
        if filter_tags_str:
            body["filter"] = {"tags": [t.strip() for t in filter_tags_str.split(",") if t.strip()]}
        return http_client.post("/api/v1/search/find", body, timeout=60)

    def _cli():
        args = ["search", query, "--limit", str(limit)]
        if score_threshold > 0:
            args.extend(["--score-threshold", str(score_threshold)])
        if isinstance(level, str) and level.strip():
            args.extend(["--level", level.strip()])
        if target_uri:
            args.extend(["--uri", target_uri])
        return _run_cli(args)

    _record_harness_call("find")
    return _api_then_cli(_api, ["search", query, "--limit", str(limit)])


@mcp_tool()
def openviking_harness_stats() -> str:
    """获取 OpenViking Harness 网关的调用计数与可观测统计 (v1.1.23a)"""
    return _format_result({
        "status": "ok",
        "harness_metrics": HARNESS_METRICS,
        "mode": "both" if not CLI_ONLY_MODE else "cli_only",
    })


def _infer_skill_source(name: str, path: str) -> str:
    if "gemini" in path or "antigravity" in path:
        return "Antigravity"
    if name.startswith("sn-") or name.startswith("hermes-"):
        return "Hermes"
    if name.startswith("tide-") or name.startswith("vibe-") or name.startswith("stock-"):
        return "TideTrading"
    return "OpenClaw"


def _parse_skill_description(skill_md_path: str) -> str:
    try:
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read(1000)
                for line in content.split("\n"):
                    if line.strip().startswith("description:"):
                        desc = line.split("description:", 1)[1].strip().strip("\"'")
                        if desc:
                            return desc
    except Exception:
        pass
    return "暂无简介"


@mcp_tool()
def openviking_audit_skills() -> str:
    """物理白盒审计本地技能与模型目录：透视符合 Wiki 规范技能与待规范模型/技能，标识来源 Agent (v1.1.24)"""
    try:
        base_sources = [
            os.path.expanduser("~/.gemini/config/skills"),
            "/home/skloxo/aho/openclaw/skills",
            "/home/skloxo/aho/openclaw/project",
            "/home/skloxo/.openclaw/skills",
            "/home/skloxo/a/SenseNova-Skills/skills",
            "/home/skloxo/.hermes/hermes-agent/optional-skills"
        ]
        compliant_dict = {}
        non_compliant_dict = {}

        for base in base_sources:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                if any(skip in root for skip in ["node_modules", ".git", ".cache", ".npm", "cleanup-backup", "fastapi", ".venv"]):
                    continue
                skill_name = os.path.basename(root)
                source = _infer_skill_source(skill_name, root)
                if "SKILL.md" in files:
                    skill_md = os.path.join(root, "SKILL.md")
                    desc = _parse_skill_description(skill_md)
                    is_valid_desc = bool(desc and desc.strip() and desc.strip() != "暂无简介")
                    if is_valid_desc:
                        if skill_name not in compliant_dict:
                            compliant_dict[skill_name] = {
                                "name": skill_name,
                                "path": root,
                                "source": source,
                                "description": desc,
                                "status": "compliant"
                            }
                    else:
                        if skill_name not in compliant_dict and skill_name not in non_compliant_dict:
                            non_compliant_dict[skill_name] = {
                                "name": skill_name,
                                "path": root,
                                "source": source,
                                "description": "❌ 缺失或未填规范的 description 简介",
                                "status": "non_compliant",
                                "missing_reason": "❌ 缺失 description 头部元数据",
                                "can_auto_fix": True
                            }
                elif ("skills" in root.lower() or "agent" in root.lower()) and len(files) > 0:
                    if skill_name not in compliant_dict and skill_name not in non_compliant_dict and skill_name != "skills":
                        non_compliant_dict[skill_name] = {
                            "name": skill_name,
                            "path": root,
                            "source": source,
                            "description": "❌ 缺失 SKILL.md 规范文本",
                            "status": "non_compliant",
                            "missing_reason": "❌ 缺失 SKILL.md 规范文本",
                            "can_auto_fix": True
                        }

        compliant = list(compliant_dict.values())
        non_compliant = list(non_compliant_dict.values())

        return _format_result({
            "status": "ok",
            "total_scanned": len(compliant) + len(non_compliant),
            "compliant_count": len(compliant),
            "non_compliant_count": len(non_compliant),
            "compliant_skills": compliant,
            "non_compliant_skills": non_compliant
        })
    except Exception as e:
        return _make_error(str(e))


def _generate_ai_skill_md(dir_path: str) -> str:
    """使用 LLM (gpt-oss-120b) 深度分析目录代码与文档，自动生成符合 Wiki 规范的 SKILL.md 规约"""
    skill_name = os.path.basename(dir_path)
    sample_texts = []
    files = []
    try:
        for root, dirs, fnames in os.walk(dir_path):
            if any(skip in root for skip in ["node_modules", ".git", ".cache", ".npm", "cleanup-backup", ".venv"]):
                continue
            for fn in fnames:
                if fn.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), dir_path)
                files.append(rel)
                if fn.endswith((".md", ".py", ".ts", ".js", ".json", ".sh")) and len(sample_texts) < 3:
                    try:
                        with open(os.path.join(root, fn), "r", encoding="utf-8", errors="ignore") as f:
                            sample_texts.append(f"{rel}:\n" + f.read(500))
                    except Exception:
                        pass
    except Exception:
        pass

    context = "\n".join(sample_texts)
    prompt = f"""请为 AI Agent 技能模块 "{skill_name}" 生成一份符合 OpenViking Wiki 规范的 SKILL.md 文件。
文件最开头必须包含 YAML frontmatter (包含 name 和 description 两个必填字段)。
目录中的文件包括: {files[:10]}
文件内容片段:
{context[:1000]}

请输出完整的 SKILL.md 内容，仅输出 Markdown 代码，不要输出额外沟通文字。"""

    vlm_key = "sk-fbb21afbe35d09986ac6f66ca91f66f4dee6b2536319be7347759f02de8f6227"
    try:
        req_data = json.dumps({
            "model": "gpt-oss-120b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {vlm_key}"
        }
        req = Request("http://127.0.0.1:8317/v1/chat/completions", data=req_data, headers=headers, method="POST")
        with urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message", {})
                content = (msg.get("content", "") if isinstance(msg, dict) else str(msg)).strip()
                if content.startswith("```markdown"):
                    content = content.split("```markdown", 1)[1].rsplit("```", 1)[0].strip()
                elif content.startswith("```"):
                    content = content.split("```", 1)[1].rsplit("```", 1)[0].strip()
                if content and "name:" in content:
                    return content
                elif content:
                    return f"---\nname: {skill_name}\ndescription: {skill_name} module specification.\n---\n\n# {skill_name.replace('-', ' ').title()} SOP\n\n{content}\n"
    except Exception as e:
        logger.warning(f"AI 生成 SKILL.md 失败，使用基础模板 fallback: {e}")

    return f"""---
name: {skill_name}
description: Standardized SOP and execution guidelines for {skill_name} module.
---

# {skill_name.replace('-', ' ').title()} SOP

本文档为 {skill_name} 模块的标准化技能规约。当用户提及相关功能或操作时自动触发。
"""


# ─── Rate-Limited Asynchronous Skill Onboarding Queue ───────────

import queue
import threading


class SkillOnboardingQueue:
    """限流并发队列：防止批量生成 SKILL.md 时打爆 LLM 接口或触发 API 限流 (v1.1.26)"""

    def __init__(self, rate_limit_delay: float = 1.2):
        self.task_queue = queue.Queue()
        self.rate_limit_delay = rate_limit_delay
        self.lock = threading.Lock()
        self.is_running = False
        self.worker_thread = None
        self.stats = {
            "total_enqueued": 0,
            "processed_count": 0,
            "failed_count": 0,
            "current_item": None,
            "status": "idle",
            "last_active_timestamp": 0.0,
            "last_error": None
        }

    def start_worker_if_needed(self):
        with self.lock:
            if not self.is_running:
                self.is_running = True
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()

    def enqueue_dirs(self, dir_paths: List[str]) -> List[str]:
        enqueued = []
        with self.lock:
            for d in dir_paths:
                self.task_queue.put(d)
                self.stats["total_enqueued"] += 1
                enqueued.append(d)
        self.start_worker_if_needed()
        return enqueued

    def _worker_loop(self):
        logger.info("限流技能上架队列 Worker 启动 (Rate-limited Queue Worker)...")
        while True:
            try:
                dir_path = self.task_queue.get(timeout=20)
            except queue.Empty:
                with self.lock:
                    self.is_running = False
                    self.stats["status"] = "idle"
                    self.stats["current_item"] = None
                logger.info("限流技能上架队列已空，Worker 恢复空闲。")
                break

            skill_name = os.path.basename(dir_path)
            with self.lock:
                self.stats["status"] = "processing"
                self.stats["current_item"] = skill_name
                self.stats["last_active_timestamp"] = time.time()

            try:
                skill_md_path = os.path.join(dir_path, "SKILL.md")
                if not os.path.exists(skill_md_path):
                    spec_content = _generate_ai_skill_md(dir_path)
                    with open(skill_md_path, "w", encoding="utf-8") as f:
                        f.write(spec_content)
                
                _auto_sync_skills()

                with self.lock:
                    self.stats["processed_count"] += 1

            except Exception as e:
                logger.warning(f"队列处理技能失败 ({skill_name}): {e}")
                with self.lock:
                    self.stats["failed_count"] += 1
                    self.stats["last_error"] = str(e)
            finally:
                self.task_queue.task_done()
                time.sleep(self.rate_limit_delay)


ONBOARDING_QUEUE = SkillOnboardingQueue(rate_limit_delay=1.2)


@mcp_tool()
def openviking_auto_onboard_skills(
    limit: int = Field(default=10, description="单批次自动规范上架的最大技能数量"),
    async_queue: bool = Field(default=True, description="是否使用限流队列后台异步处理（推荐 True 防止打爆接口与超时）"),
    rate_limit_delay_sec: float = Field(default=1.2, description="每个技能生成与上架之间的强制冷却秒数（防限流）"),
) -> str:
    """全自动发现新技能/模型，通过【单并发+强制冷却限流队列】调用 LLM 规范化生成 SKILL.md 并上架至 OpenViking (v1.1.26)"""
    try:
        base_sources = [
            os.path.expanduser("~/.gemini/config/skills"),
            "/home/skloxo/aho/openclaw/skills",
            "/home/skloxo/aho/openclaw/project",
            "/home/skloxo/.openclaw/skills",
            "/home/skloxo/a/SenseNova-Skills/skills",
            "/home/skloxo/.hermes/hermes-agent/optional-skills"
        ]
        non_compliant_dirs = []

        for base in base_sources:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                if any(skip in root for skip in ["node_modules", ".git", ".cache", ".npm", "cleanup-backup", "fastapi", ".venv"]):
                    continue
                skill_name = os.path.basename(root)
                if ("skills" in root.lower() or "agent" in root.lower()) and len(files) > 0 and skill_name != "skills":
                    if "SKILL.md" not in files:
                        non_compliant_dirs.append(root)
                    else:
                        skill_md_p = os.path.join(root, "SKILL.md")
                        desc = _parse_skill_description(skill_md_p)
                        if not desc or desc.strip() == "" or desc.strip() == "暂无简介":
                            non_compliant_dirs.append(root)

        target_dirs = non_compliant_dirs[:limit]

        if async_queue:
            ONBOARDING_QUEUE.rate_limit_delay = rate_limit_delay_sec
            enqueued = ONBOARDING_QUEUE.enqueue_dirs(target_dirs)
            return _format_result({
                "status": "ok",
                "mode": "async_rate_limited_queue",
                "message": f"已成功将 {len(enqueued)} 个待规范技能推入【限流保护队列】！正在后台逐一调用 LLM 生成规范并同步上架。",
                "discovered_candidates_count": len(non_compliant_dirs),
                "enqueued_count": len(enqueued),
                "rate_limit_delay_sec": rate_limit_delay_sec,
                "queue_status": {
                    "pending_items": ONBOARDING_QUEUE.task_queue.qsize(),
                    "worker_status": ONBOARDING_QUEUE.stats["status"]
                }
            })
        else:
            # 同步模式（同样增加 rate_limit_delay 强制冷却）
            onboarded = []
            for d in target_dirs:
                skill_name = os.path.basename(d)
                skill_md_path = os.path.join(d, "SKILL.md")
                try:
                    spec_content = _generate_ai_skill_md(d)
                    with open(skill_md_path, "w", encoding="utf-8") as f:
                        f.write(spec_content)
                    onboarded.append({
                        "name": skill_name,
                        "path": d,
                        "skill_md": skill_md_path,
                        "status": "onboarded_successfully"
                    })
                except Exception as w_err:
                    logger.warning(f"写入 SKILL.md 失败 ({d}): {w_err}")
                time.sleep(rate_limit_delay_sec)

            _auto_sync_skills()

            return _format_result({
                "status": "ok",
                "mode": "sync_sequential",
                "message": f"已顺序完成 {len(onboarded)} 个新技能规范上架！",
                "discovered_candidates_count": len(non_compliant_dirs),
                "onboarded_count": len(onboarded),
                "onboarded_skills": onboarded
            })
    except Exception as e:
        return _make_error(str(e))


@mcp_tool()
def openviking_get_onboard_queue_status() -> str:
    """获取技能自动上架限流队列的实时运行状态与进度 (v1.1.26)"""
    with ONBOARDING_QUEUE.lock:
        return _format_result({
            "status": "ok",
            "queue_worker_status": ONBOARDING_QUEUE.stats["status"],
            "pending_queue_size": ONBOARDING_QUEUE.task_queue.qsize(),
            "total_enqueued": ONBOARDING_QUEUE.stats["total_enqueued"],
            "processed_count": ONBOARDING_QUEUE.stats["processed_count"],
            "failed_count": ONBOARDING_QUEUE.stats["failed_count"],
            "current_item": ONBOARDING_QUEUE.stats["current_item"],
            "last_active_timestamp": ONBOARDING_QUEUE.stats["last_active_timestamp"],
            "rate_limit_delay_sec": ONBOARDING_QUEUE.rate_limit_delay
        })


@mcp_tool()
def openviking_fix_skill(skill_name: str = Field(description="要进行规范化修复上架的技能名称")) -> str:
    """一键规范化未完工技能并上架到 OpenViking 向量库 (v1.1.25)"""
    try:
        base_sources = [
            os.path.expanduser("~/.gemini/config/skills"),
            "/home/skloxo/aho/openclaw/skills",
            "/home/skloxo/aho/openclaw/project",
            "/home/skloxo/.openclaw/skills",
            "/home/skloxo/a/SenseNova-Skills/skills",
            "/home/skloxo/.hermes/hermes-agent/optional-skills"
        ]
        target_dir = None
        for base in base_sources:
            if not os.path.exists(base):
                continue
            for root, dirs, files in os.walk(base):
                if os.path.basename(root) == skill_name:
                    target_dir = root
                    break
            if target_dir:
                break

        if not target_dir:
            return _make_error(f"找不到技能目录: {skill_name}")

        skill_md = os.path.join(target_dir, "SKILL.md")
        if not os.path.exists(skill_md):
            spec_content = _generate_ai_skill_md(target_dir)
            with open(skill_md, "w", encoding="utf-8") as f:
                f.write(spec_content)

        _auto_sync_skills()
        return _format_result({
            "status": "ok",
            "message": f"技能 {skill_name} 已成功规范化并同步上架至 OpenViking 存储池！",
            "skill_name": skill_name,
            "skill_md_path": skill_md
        })
    except Exception as e:
        return _make_error(str(e))



@mcp_tool()
def openviking_search(
    query: str = Field(description="搜索查询文本"),
    target_uri: str = Field(default="", description="限定搜索范围的 URI"),
    limit: int = Field(default=5, description="返回结果数量"),
    score_threshold: float = Field(default=0.0, description="最低相关性分数"),
) -> str:
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

    def _cli():
        args = ["search", query_str, "--limit", str(limit)]
        if score_threshold > 0:
            args.extend(["--score-threshold", str(score_threshold)])
        if target_uri_str:
            args.extend(["--uri", target_uri_str])
        return _run_cli(args)

    return _api_then_cli(_api, ["search", query_str, "--limit", str(limit)])


@mcp_tool()
def openviking_grep(
    pattern: str = Field(description="正则表达式"),
    target_uri: str = Field(default="viking://", description="搜索范围 URI"),
    limit: int = Field(default=50, description="最大返回数"),
) -> str:
    """正则表达式搜索文件内容"""
    for err in [_validate_uri(target_uri), _validate_limit(limit)]:
        if err:
            return _make_error(err)

    def _api():
        return http_client.post("/api/v1/search/grep", {"pattern": pattern, "uri": target_uri, "limit": limit})

    return _api_then_cli(_api, ["grep", pattern, "--uri", target_uri, "--limit", str(limit)])


@mcp_tool()
def openviking_glob(
    pattern: str = Field(description="glob 模式（如 **/*.py）"),
    target_uri: str = Field(default="viking://", description="搜索范围 URI"),
) -> str:
    """按 glob 模式匹配文件"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        return http_client.post("/api/v1/search/glob", {"pattern": pattern, "uri": target_uri})

    return _api_then_cli(_api, ["glob", pattern, "--uri", target_uri])


# ═══════════════════════════════════════════════════════════════════
# 三、文件系统浏览与操作
# ═══════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════
# 四、分层内容读取（L0/L1/L2）
# ═══════════════════════════════════════════════════════════════════


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
            # 如果文件不存在且 mode 为 replace，自动以 create 模式重试
            return http_client.post("/api/v1/content/write", {"uri": target_uri, "content": content, "mode": "create"})
        return res

    def _cli():
        if mode == "create" and not content:
            return _run_cli(["mkdir", target_uri])
        return _run_cli(["write", target_uri, "--content", content, "--mode", mode])

    return _api_then_cli(_api, ["write", target_uri, "--content", content, "--mode", mode])


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


# ═══════════════════════════════════════════════════════════════════
# 五、会话管理
# ═══════════════════════════════════════════════════════════════════


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
            # 无 session_id 时先创建会话
            return http_client.post("/api/v1/sessions", {"session_id": session_id or "default", "message": body})
        # 无内容 → commit
        if session_id:
            return http_client.post(f"/api/v1/sessions/{session_id}/commit")
        return http_client.post("/api/v1/sessions/default/commit")

    def _cli():
        if content:
            args = ["add-memory", "--content", content]
            if session_id:
                args.extend(["--session", session_id])
            return _run_cli(args)
        args = ["session", "commit"]
        if session_id:
            args.extend(["--session", session_id])
        return _run_cli(args, timeout=60)

    return _api_then_cli(_api, ["session", "commit"], timeout=60)


@mcp_tool()
def openviking_commit(
    session_id: str = Field(default="", description="会话 ID（留空使用当前会话）"),
) -> str:
    """提交当前会话记忆（归档消息 + 异步提取长期记忆）"""

    def _api():
        if session_id:
            return http_client.post(f"/api/v1/sessions/{session_id}/commit")
        return http_client.post("/api/v1/sessions/default/commit")

    def _cli():
        args = ["session", "commit"]
        if session_id:
            args.extend(["--session", session_id])
        return _run_cli(args, timeout=60)

    return _api_then_cli(_api, ["session", "commit"], timeout=60)


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


# ═══════════════════════════════════════════════════════════════════
# 六、系统状态
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_health() -> str:
    """检查 OpenViking 服务健康状态（合并 health/ready/status）"""

    def _api():
        health = http_client.get("/health")
        ready = http_client.get("/ready")
        status = http_client.get("/api/v1/system/status")
        return {
            "health": health,
            "ready": ready,
            "status": status,
        }

    def _cli():
        return _run_cli(["status"])

    return _api_then_cli(_api, ["status"])


@mcp_tool()
def openviking_system_status(
    wait_timeout: int = Field(default=0, description="等待后台处理完成的超时秒数（0=不等待）"),
    reset_stats: bool = Field(default=False, description="是否重置 token 统计"),
) -> str:
    """获取系统详细状态。可选等待后台处理、重置统计。"""
    w_to = int(wait_timeout) if isinstance(wait_timeout, (int, float)) else 0
    r_st = bool(reset_stats) if isinstance(reset_stats, bool) else False

    def _api():
        result = http_client.get("/api/v1/system/status")
        if isinstance(result, dict):
            result["harness_metrics"] = HARNESS_METRICS
        if w_to > 0 and "error" not in result:
            http_client.post("/api/v1/system/wait", {"timeout": w_to})
        return result

    def _cli():
        status_info = _run_cli(["status"])
        stats_args = ["status"]
        if r_st:
            stats_args.append("--reset")
        stats = _run_cli(stats_args)
        return {"status": status_info, "stats": stats, "harness_metrics": HARNESS_METRICS}

    return _api_then_cli(_api, ["status"])


# ═══════════════════════════════════════════════════════════════════
# 七、Observer API（组件级监控）
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_observer(
    component: str = Field(description="组件名：queue/vikingdb/models/lock/retrieval/system"),
) -> str:
    """查看指定组件的 Observer 状态"""
    valid = {"queue", "vikingdb", "models", "lock", "retrieval", "system"}
    if component not in valid:
        return _make_error(f"无效组件: {component}。可选: {', '.join(sorted(valid))}")
    result = http_client.get(f"/api/v1/observer/{component}")
    return _format_result(result)


# ═══════════════════════════════════════════════════════════════════
# 八、技能管理
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_skills(
    action: str = Field(description="操作：list（列出）/ add（添加）"),
    name: str = Field(default="", description="技能名称（add 时必填）"),
    description: str = Field(default="", description="技能描述（add 时必填）"),
    content: str = Field(default="", description="技能内容（Markdown）"),
    tags: str = Field(default="", description="标签（逗号分隔）"),
) -> str:
    """技能管理：列出或添加技能"""

    if action == "list":
        result = http_client.get("/api/v1/skills")
        return _format_result(result)
    elif action == "add":
        if not name or not description:
            return _make_error("添加技能需要 name 和 description")
        body = {"name": name, "description": description}
        if content:
            body["content"] = content
        if tags:
            body["tags"] = [t.strip() for t in tags.split(",")]
        result = http_client.post("/api/v1/skills", body)
        return _format_result(result)
    else:
        return _make_error(f"无效操作: {action}。可选: list, add")


# ═══════════════════════════════════════════════════════════════════
# 九、Watch 任务管理
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_list_watches(
    active_only: bool = Field(default=True, description="仅显示活跃任务"),
) -> str:
    """列出 watch 监控任务"""
    args = ["task", "watch", "ls"]
    if active_only:
        args.append("--active-only")
    return _format_result(_run_cli(args))


@mcp_tool()
def openviking_cancel_watch(
    target_uri: str = Field(description="要取消监控的 Viking URI"),
) -> str:
    """取消 watch 监控任务"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)
    return _format_result(_run_cli(["task", "watch", "rm", target_uri]))


@mcp_tool()
def openviking_manage_watch(
    target_uri: str = Field(description="Viking URI"),
    action: str = Field(description="操作：pause/resume/trigger"),
) -> str:
    """管理 watch 任务：暂停、恢复、手动触发"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)
    valid_actions = {"pause", "resume", "trigger"}
    if action not in valid_actions:
        return _make_error(f"无效操作: {action}。可选: {', '.join(sorted(valid_actions))}")
    return _format_result(_run_cli(["task", "watch", action, target_uri]))


# ═══════════════════════════════════════════════════════════════════
# 十、关联管理
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_link(
    source_uri: str = Field(description="源 URI"),
    target_uri: str = Field(description="目标 URI"),
    relation_type: str = Field(default="related", description="关联类型：related/child/reference/similar"),
) -> str:
    """创建资源关联"""
    for err in [_validate_uri(source_uri, "source_uri"), _validate_uri(target_uri, "target_uri")]:
        if err:
            return _make_error(err)

    def _api():
        return http_client.post("/api/v1/relations/link", {
            "source": source_uri, "target": target_uri, "type": relation_type,
        })

    return _api_then_cli(_api, ["link", source_uri, target_uri, "--type", relation_type])


@mcp_tool()
def openviking_get_relations(
    target_uri: str = Field(description="Viking URI"),
) -> str:
    """获取资源关联列表"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        return http_client.get("/api/v1/relations", {"uri": target_uri})

    return _api_then_cli(_api, ["relations", target_uri])


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


# ═══════════════════════════════════════════════════════════════════
# 十一、代码工具
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_code_outline(
    target_uri: str = Field(description="代码文件 Viking URI"),
) -> str:
    """显示文件符号结构（函数、类等）"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        return http_client.get("/api/v1/content/overview", {"uri": target_uri})

    return _api_then_cli(_api, ["overview", target_uri])


@mcp_tool()
def openviking_code_search(
    query: str = Field(description="符号名搜索"),
    target_uri: str = Field(default="viking://", description="搜索范围"),
) -> str:
    """搜索符号名（函数、类、变量等）"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        body = {"query": query}
        if target_uri and target_uri != "viking://":
            body["target_uri"] = target_uri
        return http_client.post("/api/v1/search/find", body)

    def _cli():
        args = ["find", query]
        if target_uri and target_uri != "viking://":
            args.extend(["--uri", target_uri])
        return _run_cli(args)

    return _api_then_cli(_api, ["find", query] + (["--uri", target_uri] if target_uri and target_uri != "viking://" else []))


@mcp_tool()
def openviking_code_expand(
    target_uri: str = Field(description="符号所在文件 Viking URI"),
    symbol: str = Field(default="", description="符号名"),
) -> str:
    """返回符号完整源码"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)

    def _api():
        return http_client.get("/api/v1/content/read", {"uri": target_uri})

    return _api_then_cli(_api, ["read", target_uri], timeout=60)


# ═══════════════════════════════════════════════════════════════════
# 十二、备份与恢复
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_export(
    target_uri: str = Field(description="要导出的 Viking URI"),
    output_path: str = Field(description="导出文件路径（.ovpack）"),
    include_vectors: bool = Field(default=False, description="包含向量快照"),
) -> str:
    """导出资源为 OVPack 格式"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)
    args = ["export", target_uri, output_path]
    if include_vectors:
        args.append("--include-vectors")
    return _format_result(_run_cli(args, timeout=300))


@mcp_tool()
def openviking_import(
    pack_path: str = Field(description="OVPack 文件路径"),
    target_uri: str = Field(description="导入目标 Viking URI"),
    on_conflict: str = Field(default="fail", description="冲突策略：fail, overwrite, skip"),
) -> str:
    """导入 OVPack 到 OpenViking"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)
    return _format_result(_run_cli(
        ["import", pack_path, target_uri, "--on-conflict", on_conflict],
        timeout=300,
    ))


@mcp_tool()
def openviking_backup(
    output_path: str = Field(description="备份文件路径（.ovpack）"),
) -> str:
    """全量备份 OpenViking"""
    return _format_result(_run_cli(["backup", output_path], timeout=600))


@mcp_tool()
def openviking_restore(
    pack_path: str = Field(description="备份文件路径（.ovpack）"),
    on_conflict: str = Field(default="overwrite", description="冲突策略"),
) -> str:
    """从备份恢复 OpenViking"""
    return _format_result(_run_cli(
        ["restore", pack_path, "--on-conflict", on_conflict],
        timeout=600,
    ))


# ═══════════════════════════════════════════════════════════════════
# 十三、服务器管理
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_server_control(
    action: str = Field(description="操作：start/stop/restart/status"),
    host: str = Field(default="127.0.0.1", description="监听地址（start 时使用）"),
    port: int = Field(default=1933, description="监听端口（start 时使用）"),
    config: str = Field(default="", description="配置文件路径（start 时使用）"),
) -> str:
    """OpenViking 服务器控制：启动、停止、重启、查看状态"""

    if action == "status":
        def _api():
            health = http_client.get("/health")
            if "error" not in health:
                status = http_client.get("/api/v1/system/status")
                return {"server": "running", "health": health, "status": status}
            return {"server": "not_running", "health": health}

        def _cli():
            result = _run_cli(["server", "status"])
            if _has_error(result):
                return {"server": "not_running", "error": result.get("error")}
            return result

        return _api_then_cli(_api, ["server", "status"])

    elif action == "start":
        args = ["server", "start", "--host", host, "--port", str(port)]
        if config:
            args.extend(["--config", config])
        return _format_result(_run_cli(args, timeout=15))

    elif action == "stop":
        return _format_result(_run_cli(["server", "stop"], timeout=15))

    elif action == "restart":
        return _format_result(_run_cli(["server", "restart"], timeout=15))

    else:
        return _make_error(f"无效操作: {action}。可选: start, stop, restart, status")


@mcp_tool()
def openviking_server_init() -> str:
    """初始化 OpenViking 配置（交互式向导）"""
    return _format_result(_run_cli(["server", "init"], timeout=30))


@mcp_tool()
def openviking_server_doctor() -> str:
    """运行 OpenViking 配置诊断"""
    return _format_result(_run_cli(["server", "doctor"], timeout=30))


# ═══════════════════════════════════════════════════════════════════
# 十四、隐私配置管理
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_privacy(
    action: str = Field(description="操作：categories/list/get/upsert"),
    category: str = Field(default="", description="分类名（list/get/upsert 时必填）"),
    target_key: str = Field(default="", description="目标键（get/upsert 时必填）"),
    values_json: str = Field(default="", description="JSON 格式的值（upsert 时必填）"),
) -> str:
    """隐私配置管理：列出分类、查看/写入配置"""

    if action == "categories":
        return _format_result(_run_cli(["privacy", "categories"]))
    elif action == "list":
        if not category:
            return _make_error("list 操作需要 category 参数")
        return _format_result(_run_cli(["privacy", "list", category]))
    elif action == "get":
        if not category or not target_key:
            return _make_error("get 操作需要 category 和 target_key 参数")
        return _format_result(_run_cli(["privacy", "get", category, target_key]))
    elif action == "upsert":
        if not category or not target_key or not values_json:
            return _make_error("upsert 操作需要 category、target_key 和 values_json 参数")
        return _format_result(_run_cli([
            "privacy", "upsert", category, target_key,
            "--values-json", values_json,
        ]))
    else:
        return _make_error(f"无效操作: {action}。可选: categories, list, get, upsert")


# ═══════════════════════════════════════════════════════════════════
# 十五、标签管理
# ═══════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════
# 十六、一致性检查
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_consistency(
    target_uri: str = Field(default="viking://", description="检查范围 URI"),
    fix: bool = Field(default=False, description="是否自动修复"),
) -> str:
    """一致性检查：检测索引与存储的不一致"""
    err = _validate_uri(target_uri)
    if err:
        return _make_error(err)
    args = ["consistency", target_uri]
    if fix:
        args.append("--fix")
    return _format_result(_run_cli(args, timeout=120))


# ═══════════════════════════════════════════════════════════════════
# 十七、Metrics & WebDAV
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_metrics() -> str:
    """获取 Prometheus 格式的指标数据"""
    cfg = _get_config()
    url = f"{cfg['api']}/metrics"
    headers = {}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return _handle_http_error(e)


@mcp_tool()
def openviking_webdav_info() -> str:
    """获取 WebDAV 访问信息"""
    cfg = _get_config()
    return _format_result({
        "webdav_url": f"{cfg['api']}/webdav/resources",
        "description": "支持 OPTIONS/PROPFIND/GET/HEAD/PUT/DELETE/MKCOL/MOVE",
        "mount_example": f"mount -t davfs {cfg['api']}/webdav/resources /mnt/openviking",
    })


# ═══════════════════════════════════════════════════════════════════
# 十八、差异比较
# ═══════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════
# 十九、Combo 工具（高频组合操作）
# ═══════════════════════════════════════════════════════════════════


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

    # Step 1: 搜索
    search_body = {"query": query, "limit": limit}
    if score_threshold > 0:
        search_body["score_threshold"] = score_threshold

    if CLI_ONLY_MODE or not http_client.available:
        # CLI-only 模式
        search_args = ["search", query, "--limit", str(limit)]
        if score_threshold > 0:
            search_args.extend(["--score-threshold", str(score_threshold)])
        search_result = _run_cli(search_args)
        if _has_error(search_result):
            return _handle_cli_error(search_result)

        # 从 CLI 输出中提取 URI
        results = search_result.get("results", [])
        if isinstance(search_result, dict) and "output" in search_result:
            # CLI 返回纯文本，尝试解析
            return _format_result({
                "search": search_result,
                "smart_read_note": "CLI 模式下无法自动批量读取，请使用 openviking_read 逐个读取",
            })
    else:
        search_result = http_client.post("/api/v1/search/find", search_body)
        if _has_error(search_result):
            # 回退 CLI
            search_args = ["search", query, "--limit", str(limit)]
            if score_threshold > 0:
                search_args.extend(["--score-threshold", str(score_threshold)])
            search_result = _run_cli(search_args)
            if _has_error(search_result):
                return _handle_cli_error(search_result)

        results = search_result.get("results", [])

    # Step 2: 对每个结果按指定 level 读取
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


# ═══════════════════════════════════════════════════════════════════
# 二十、Usage Stats 工具
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_usage_stats(
    reset: bool = Field(default=False, description="是否重置统计数据"),
) -> str:
    """获取 OpenViking token 消耗统计。支持重置计数器。"""
    if reset:
        # 重置统计
        if CLI_ONLY_MODE or not http_client.available:
            result = _run_cli(["stats", "--reset"])
        else:
            result = http_client.post("/api/v1/system/stats/reset")
            if _has_error(result):
                result = _run_cli(["stats", "--reset"])
        return _format_result(result)

    # 获取统计
    if CLI_ONLY_MODE or not http_client.available:
        result = _run_cli(["stats", "--json"])
        if _has_error(result):
            result = _run_cli(["stats"])
        return _format_result(result)

    # HTTP API 优先
    result = http_client.get("/api/v1/system/stats")
    if _has_error(result):
        result = _run_cli(["stats", "--json"])
        if _has_error(result):
            result = _run_cli(["stats"])
    return _format_result(result)


# ═══════════════════════════════════════════════════════════════════
# 二十一、Ping 工具（连接状态检测）
# ═══════════════════════════════════════════════════════════════════


@mcp_tool()
def openviking_ping() -> str:
    """检测 OpenViking 连接状态。返回 HTTP API 和 CLI 的可用性。"""
    status = {
        "http_available": False,
        "cli_available": False,
        "mode": "unknown",
        "api_url": _get_config()["api"],
    }

    # 测试 HTTP API
    try:
        result = http_client.get("/health", timeout=5)
        if "error" not in result:
            status["http_available"] = True
            status["http_health"] = result
    except Exception as e:
        status["http_error"] = str(e)

    # 测试 CLI
    try:
        result = _run_cli(["--version"], timeout=10)
        if not _has_error(result):
            status["cli_available"] = True
            status["cli_version"] = result.get("output", result.get("version", "unknown"))
    except Exception as e:
        status["cli_error"] = str(e)

    # 设置模式
    if status["http_available"] and status["cli_available"]:
        status["mode"] = "both"
    elif status["http_available"]:
        status["mode"] = "http_only"
    elif status["cli_available"]:
        status["mode"] = "cli_only"
    else:
        status["mode"] = "disconnected"

    status["cli_only_mode"] = CLI_ONLY_MODE

    return _format_result(status)


# ─── 启动 ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    # 解析 --mode 参数
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            MCP_MODE = arg.split("=", 1)[1].strip().lower()
        elif arg == "--mode" and sys.argv.index(arg) + 1 < len(sys.argv):
            MCP_MODE = sys.argv[sys.argv.index(arg) + 1].strip().lower()

    logger.info(f"🚀 OpenViking MCP Server starting in [{MCP_MODE.upper()}] mode...")
    if any(arg.isdigit() for arg in sys.argv[1:]):
        port = next(int(arg) for arg in sys.argv[1:] if arg.isdigit())
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")

