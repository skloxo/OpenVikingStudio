# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: _core.config ──────────────────────────────────────────────────
"""
用途: OpenViking MCP 基础配置管理、跨平台兼容、HTTP Client 与 CLI 执行器
依赖: 标准库 (sys, os, json, subprocess, urllib, pathlib)
被调用: mcp_openviking_server.py, tools/*.py
"""

# SECTION: Imports
import json
import logging
import os
import subprocess
import sys
import time
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

logger = logging.getLogger("openviking-mcp")

# SECTION: Constants & Environment Defaults
DEFAULT_API = os.environ.get("OPENVIKING_API", "http://127.0.0.1:1933")
DEFAULT_CLI = os.environ.get("OPENVIKING_CLI", "openviking")
DEFAULT_ROOT_API_KEY = os.environ.get("OPENVIKING_ROOT_API_KEY", "")
CLI_ONLY_MODE = False

# 卫星模式精选 16 个全能安全数据与环境感知工具
SATELLITE_ALLOWED_TOOLS = {
    # 4 大日常检索基石
    "openviking_find",
    "openviking_search",
    "openviking_smart_read",
    "openviking_read",
    "openviking_store",
    # 5 大代码与排障攻坚
    "openviking_write",
    "openviking_code_search",
    "openviking_code_outline",
    "openviking_code_expand",
    "openviking_grep",
    "openviking_record_evolution_lesson",
    # 5 大结构与环境感知
    "openviking_tree",
    "openviking_skills",
    "openviking_get_relations",
    "openviking_ping",
    "openviking_health",
    # 2 大 CPA 弹性算力协同
    "openviking_cpa_consult",
    "openviking_cpa_fanout",
}

# SECTION: Mode Resolution
def resolve_mcp_mode(argv: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None) -> str:
    """智能决议当前运行模式 (core 核心模式 vs satellite 卫星模式)"""
    args = argv if argv is not None else sys.argv[1:]
    env_map: Dict[str, str] = dict(env) if env is not None else dict(os.environ)

    cli_mode = None
    for idx, arg in enumerate(args):
        if arg.startswith("--mode="):
            cli_mode = arg.split("=", 1)[1].strip().lower()
        elif arg == "--mode" and idx < len(args) - 1:
            cli_mode = args[idx + 1].strip().lower()

    if cli_mode in ("satellite", "core"):
        return cli_mode

    env_mode = env_map.get("OPENVIKING_MCP_MODE") or env_map.get("OPENVIKING_MODE")
    if env_mode and env_mode.strip().lower() in ("satellite", "core"):
        return env_mode.strip().lower()

    target_api = env_map.get("OPENVIKING_API", DEFAULT_API).lower()
    has_root = bool(env_map.get("OPENVIKING_ROOT_API_KEY"))
    is_local = "127.0.0.1" in target_api or "localhost" in target_api
    return "core" if (is_local and has_root) else "satellite"


def _get_active_mode() -> str:
    """获取当前处于激活状态的 MCP_MODE，支持运行时动态热重载"""
    mcp_mod = sys.modules.get("mcp_openviking_server")
    if mcp_mod and hasattr(mcp_mod, "MCP_MODE"):
        return mcp_mod.MCP_MODE
    return resolve_mcp_mode()


def _get_config() -> Dict[str, str]:
    """读取并归一化服务配置，优先级：环境变量 -> ~/.openviking/ov.conf -> ~/.openviking/ovcli.conf"""
    api_key = os.environ.get("OPENVIKING_API_KEY") or os.environ.get("OPENVIKING_ROOT_API_KEY") or ""
    if not api_key:
        conf_path = Path.home() / ".openviking" / "ov.conf"
        if conf_path.exists():
            try:
                with open(conf_path, "r", encoding="utf-8") as f:
                    conf_data = json.load(f)
                    api_key = conf_data.get("server", {}).get("root_api_key", "")
            except Exception:
                pass
    if not api_key:
        cli_conf = Path.home() / ".openviking" / "ovcli.conf"
        if cli_conf.exists():
            try:
                with open(cli_conf, "r", encoding="utf-8") as f:
                    conf_data = json.load(f)
                    api_key = conf_data.get("root_api_key", "")
            except Exception:
                pass
    return {
        "api": os.environ.get("OPENVIKING_API", DEFAULT_API).rstrip("/"),
        "api_key": api_key,
        "cli": os.environ.get("OPENVIKING_CLI", DEFAULT_CLI),
    }

# SECTION: CLI Runner
def _run_cli(args: List[str], timeout: int = 30) -> Dict[str, Any]:
    """执行 OpenViking CLI 命令并返回结果。卫星模式下直接短路，不调用本地子进程。"""
    active_mode = _get_active_mode()
    if active_mode == "satellite":
        return {"error": "卫星模式为纯 HTTP 数据客户端，不调用本地 CLI 二进制"}

    cfg = _get_config()
    cmd = [cfg["cli"]] + args
    logger.info(f"CLI: {' '.join(cmd)}")
    try:
        env = {**os.environ, "NO_COLOR": "1"}
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

# SECTION: HTTP Client
class OpenVikingHTTPClient:
    """OpenViking HTTP API 客户端 (100% 优先，支持动态自愈与卫星模式重试抖动容错)"""

    def __init__(self):
        cfg = _get_config()
        self.api = cfg["api"]
        self.api_key = cfg["api_key"]

    @property
    def available(self) -> bool:
        return self._is_available()

    def _is_available(self) -> bool:
        try:
            req = Request(f"{self.api}/health", headers={"Content-Type": "application/json"}, method="GET")
            mcp_mod = sys.modules.get("mcp_openviking_server")
            active_urlopen = getattr(mcp_mod, "urlopen", urllib.request.urlopen)
            with active_urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _request(
        self,
        method: str,
        path: str,
        body: Any = None,
        timeout: int = 30,
        params: Optional[dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self.api}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        cfg = _get_config()
        api_key = cfg["api_key"] or self.api_key

        headers = {
            "Content-Type": "application/json",
            "X-OpenViking-Account": "default",
            "X-OpenViking-User": "default",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = Request(url, data=data, headers=headers, method=method)
        active_mode = _get_active_mode()
        max_retries = 3 if active_mode == "satellite" else 1

        # 动态解析 urlopen，确保 mock 与猴子补丁 100% 生效
        mcp_mod = sys.modules.get("mcp_openviking_server")
        active_urlopen = getattr(mcp_mod, "urlopen", urllib.request.urlopen)

        start_time = time.time()
        for attempt in range(max_retries):
            try:
                with active_urlopen(req, timeout=timeout) as resp:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    resp_content = resp.read().decode("utf-8")
                    logger.debug(f"[MCP_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms status={resp.status}")
                    if not resp_content:
                        return {"ok": True}
                    try:
                        return json.loads(resp_content)
                    except json.JSONDecodeError:
                        return {"raw": resp_content}
            except HTTPError as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"[MCP_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms error=HTTP_{e.code}")
                if e.code in (502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                body_text = ""
                try:
                    body_text = e.read().decode("utf-8")
                except Exception:
                    pass
                return {
                    "error": f"[BACKEND_ERROR] HTTP {e.code}: {body_text}",
                    "is_http_error": True,
                    "code": e.code,
                    "elapsed_ms": elapsed_ms,
                }
            except TimeoutError:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(f"[MCP_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms error=BRIDGE_TIMEOUT (limit={timeout}s)")
                return {
                    "error": f"[BRIDGE_TIMEOUT] 桥接层请求后端超时 ({timeout}s)。后端可能正在执行长程检索或排队中。",
                    "code": "BRIDGE_TIMEOUT",
                    "elapsed_ms": elapsed_ms,
                }
            except URLError as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                if "timed out" in str(e.reason).lower():
                    logger.error(f"[MCP_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms error=BRIDGE_TIMEOUT")
                    return {
                        "error": f"[BRIDGE_TIMEOUT] 桥接层请求后端超时 ({timeout}s): {e.reason}",
                        "code": "BRIDGE_TIMEOUT",
                        "elapsed_ms": elapsed_ms,
                    }
                logger.warning(f"[MCP_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms error=CONNECTION_ERROR: {e.reason}")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {
                    "error": f"[CONNECTION_ERROR] 连接失败: {e.reason}. 确认 OpenViking 服务器已启动。",
                    "code": "CONNECTION_ERROR",
                    "elapsed_ms": elapsed_ms,
                }
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"[MCP_HTTP] {method} {path} attempt={attempt+1} elapsed={elapsed_ms}ms error={type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return {"error": f"[CLIENT_ERROR] {str(e)}", "elapsed_ms": elapsed_ms}
        return {"error": f"[BRIDGE_TIMEOUT] 请求后端超时 ({timeout}s) 或超过最大重试次数"}

    def get(self, path: str, params: Optional[dict] = None, timeout: int = 30) -> Any:
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path: str, body: Any = None, timeout: int = 30) -> Any:
        return self._request("POST", path, body, timeout=timeout)

    def put(self, path: str, body: Any = None, timeout: int = 30) -> Any:
        return self._request("PUT", path, body, timeout=timeout)

    def delete(self, path: str, timeout: int = 30) -> Any:
        return self._request("DELETE", path, timeout=timeout)


http_client = OpenVikingHTTPClient()

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
    """格式化输出结果为美化 JSON 字符串，并自动应用渐进式分级展开截断"""
    return result if isinstance(result, str) else json.dumps(_compact_search_result(result), ensure_ascii=False, indent=2)


def _api_then_cli(api_call, cli_args: List[str], timeout: int = 30) -> str:
    """100% 优先使用 HTTP API，仅在 HTTP 完全无法连接且非业务响应时才做 CLI 兜底"""
    result = api_call()
    if not isinstance(result, dict) or "error" not in result or result.get("is_http_error"):
        return _format_result(result)
    if "连接失败" not in str(result.get("error")):
        return _format_result(result)
    logger.warning(f"OpenViking HTTP API 不可达，尝试 CLI 回退: {result.get('error')}")
    return _format_result(_run_cli(cli_args, timeout=timeout))


def _has_error(result: Any) -> bool:
    return isinstance(result, dict) and "error" in result


def _make_error(error: str, suggestion: str = "") -> str:
    out = {"error": error}
    if suggestion:
        out["suggestion"] = suggestion
    return _format_result(out)


def _handle_http_error(e: Exception) -> str:
    if isinstance(e, HTTPError):
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        sugg = "检查 API 地址和认证" if e.code in (401, 403) else ("检查请求参数" if e.code == 400 else ("服务器错误稍后重试" if e.code >= 500 else ""))
        return _make_error(f"HTTP {e.code}: {body_text}", sugg)
    elif isinstance(e, URLError):
        return _make_error(f"连接失败: {e.reason}", "确认 OpenViking 服务已启动")
    return _make_error(str(e), "检查 OpenViking 服务状态")


def _handle_cli_error(result: Dict[str, Any]) -> str:
    err_msg = str(result.get("error") or result.get("stderr") or result.get("stdout") or "")
    returncode = result.get("returncode", -1)
    sugg = "CLI 未在 PATH 中" if returncode == 127 else ("操作超时" if "timeout" in err_msg.lower() else ("资源不存在" if "not found" in err_msg.lower() else ""))
    return _make_error(err_msg, sugg)


def _handle_timeout(operation: str, timeout: int) -> str:
    return _make_error(f"操作超时 ({timeout}s): {operation}", "尝试缩小范围或增加超时")

# SECTION: Parameter Validators
def _validate_uri(uri: Any, param_name: str = "uri") -> Optional[str]:
    """校验 Viking URI 格式，返回错误信息或 None"""
    if isinstance(uri, str) and uri and not uri.startswith("viking://"):
        return f"参数 {param_name} 格式错误: '{uri}' 必须以 'viking://' 开头"
    return None


def _normalize_level(level: Any) -> int:
    """将各种 level 输入归一化为 0, 1, 2"""
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

# SECTION: Skill Metadata Helpers
def _get_skill_base_sources() -> List[str]:
    """跨平台动态探测技能扫描基目录，兼容 Windows/WSL/Linux/macOS 任意用户。"""
    home = Path.home()
    cwd = Path.cwd()
    return [
        str(home / ".gemini" / "config" / "skills"),
        str(home / ".openclaw" / "skills"),
        str(home / ".agents" / "skills"),
        str(cwd / ".agents" / "skills"),
        str(cwd / "skills"),
        str(home / "aho" / "openclaw" / "skills"),
        str(home / "aho" / "openclaw" / "project"),
        str(home / "a" / "SenseNova-Skills" / "skills"),
        str(home / ".hermes" / "hermes-agent" / "optional-skills"),
    ]


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
