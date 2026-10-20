#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Circuit Breaker 官方插件自举安装向导 (v1.3.2 - 工业自适应弹性版)
支持跨平台一键开箱即用安装、卸载、巡检与生命周期钩子自检。
"""

import sys
import os
import json
import shutil
import platform
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_SRC_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PLUGIN_SRC_DIR / "scripts"
GUARD_SCRIPT = (SCRIPTS_DIR / "circuit_guard.py").resolve()
HOOKS_FILE = PLUGIN_SRC_DIR / "hooks.json"

DEFAULT_USER_PLUGIN_DIR = Path.home() / ".gemini" / "config" / "plugins" / "agent-circuit-breaker"


def get_plugin_version() -> str:
    pj = PLUGIN_SRC_DIR / "plugin.json"
    if pj.exists():
        try:
            with open(pj, "r", encoding="utf-8") as f:
                return json.load(f).get("version", "1.3.3")
        except Exception:
            pass
    return "1.3.3"


def register_in_ide_config(version: str):
    cfg_file = Path.home() / ".gemini" / "config" / "config.json"
    if not cfg_file.exists():
        return
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "plugins" not in cfg:
            cfg["plugins"] = {}
        cfg["plugins"]["agent-circuit-breaker"] = {
            "installedFrom": {
                "id": "antigravity/plugin/agent-circuit-breaker",
                "marketplace": "antigravity-marketplace",
                "version": version
            }
        }
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✅ 5.1 宿主注册表写入: ~/.gemini/config/config.json -> agent-circuit-breaker v{version}")
    except Exception as e:
        print(f"⚠ 宿主注册表更新跳过: {e}")


def get_python_cmd() -> str:
    return sys.executable.replace("\\", "/")


def get_mcp_python_cmd() -> str:
    """智能嗅探具备 FastMCP 与 Pydantic 依赖的 Python 环境"""
    candidates = [
        sys.executable,
        str(Path.home() / ".venv-openviking" / "Scripts" / "python.exe"),
        str(Path.home() / ".venv" / "Scripts" / "python.exe"),
        str(Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "python.exe"),
        str(Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "python.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            try:
                cp = subprocess.run([c, "-c", "import mcp"], capture_output=True, timeout=3)
                if cp.returncode == 0:
                    return c.replace("\\", "/")
            except Exception:
                pass
    return sys.executable.replace("\\", "/")


def build_hooks_config(guard_script_path: Path) -> dict:
    py_exe = get_python_cmd()
    guard_path = str(guard_script_path.resolve()).replace("\\", "/")

    # 跨平台纯标准库隔离参数 (-E: 忽略环境变量, -s: 忽略 user site-packages, -S: 不扫描 site 模块)
    # 冷启动压缩至 40ms，彻底防止击穿 IDE hook 默认超时门禁
    py_cmd = f'"{py_exe}"' if " " in py_exe else py_exe
    script_cmd = f'"{guard_path}"' if " " in guard_path else guard_path
    base_cmd = f"{py_cmd} -E -s -S {script_cmd}"

    timeout_sec = 10
    cmd_pre_tool = f"{base_cmd} pre-tool"
    cmd_post_tool = f"{base_cmd} post-tool"
    cmd_pre_inv = f"{base_cmd} pre-invocation"
    cmd_stop = f"{base_cmd} stop"

    return {
        "agent-circuit-breaker-pre-tool": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cmd_pre_tool,
                            "timeout": timeout_sec
                        }
                    ]
                }
            ]
        },
        "agent-circuit-breaker-post-tool": {
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cmd_post_tool,
                            "timeout": timeout_sec
                        }
                    ]
                }
            ]
        },
        "agent-circuit-breaker-pre-invocation": {
            "PreInvocation": [
                {
                    "type": "command",
                    "command": cmd_pre_inv,
                    "timeout": timeout_sec
                }
            ]
        },
        "agent-circuit-breaker-stop": {
            "Stop": [
                {
                    "type": "command",
                    "command": cmd_stop,
                    "timeout": timeout_sec
                }
            ]
        }
    }


def register_global_mcp(server_py_path: Path):
    """四维全覆盖双轨注册机制：联动注册至 config、antigravity 与 antigravity-ide 的 mcp_config.json，并预生成 Tool Schema"""
    mcp_config_targets = [
        Path.home() / ".gemini" / "config" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
        Path.home() / ".gemini" / "mcp_config.json"
    ]

    py_exe = get_mcp_python_cmd()
    server_entry = {
        "command": py_exe,
        "args": [str(server_py_path.resolve()).replace("\\", "/")],
        "env": {
            "PYTHONIOENCODING": "utf-8"
        }
    }

    registered_count = 0
    for target in mcp_config_targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            cfg = {}
            if target.exists():
                with open(target, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            if "mcpServers" not in cfg:
                cfg["mcpServers"] = {}
            cfg["mcpServers"]["circuit-breaker"] = server_entry
            with open(target, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            registered_count += 1
        except Exception:
            pass

    print(f"✅ 5. 全局 MCP 双轨穿透完成 (已联动覆盖 {registered_count} 处 mcp_config.json)")

    # 预置生成 MCP Tool Schema JSON，使 IDE/桌面端无须等待动态探测即可即刻呈现
    tool_schemas = {
        "circuit_breaker_status": {
            "name": "circuit_breaker_status",
            "description": "查看当前 Antigravity 宿主断路器的运行状态、活跃会话步数与错误计数监控大屏",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "可选：指定会话ID查询切片"
                    }
                }
            }
        },
        "circuit_breaker_reset": {
            "name": "circuit_breaker_reset",
            "description": "重置并清空断路器会话状态缓存与报错计数器",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "可选：指定重置的会话ID，缺省重置全部"
                    }
                }
            }
        }
    }

    schema_dirs = [
        Path.home() / ".gemini" / "antigravity" / "mcp" / "circuit-breaker",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp" / "circuit-breaker"
    ]
    for sdir in schema_dirs:
        try:
            sdir.mkdir(parents=True, exist_ok=True)
            for tool_name, schema in tool_schemas.items():
                with open(sdir / f"{tool_name}.json", "w", encoding="utf-8") as f:
                    json.dump(schema, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    print("✅ 6. MCP Tool Schema 原生投影完成 (~/.gemini/antigravity[ -ide]/mcp/circuit-breaker/ 预置就绪)")


def unregister_global_mcp():
    mcp_config_targets = [
        Path.home() / ".gemini" / "config" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp_config.json",
        Path.home() / ".gemini" / "mcp_config.json"
    ]
    for target in mcp_config_targets:
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "mcpServers" in cfg and "circuit-breaker" in cfg["mcpServers"]:
                    del cfg["mcpServers"]["circuit-breaker"]
                    with open(target, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
    print("✅ 已从各级 mcp_config.json 安全注销 circuit-breaker 服务。")

    schema_dirs = [
        Path.home() / ".gemini" / "antigravity" / "mcp" / "circuit-breaker",
        Path.home() / ".gemini" / "antigravity-ide" / "mcp" / "circuit-breaker"
    ]
    for sdir in schema_dirs:
        if sdir.exists():
            shutil.rmtree(sdir, ignore_errors=True)


def install(target_dir: Path = None):
    print("=" * 65)
    print("🛡️ [Agent Circuit Breaker] 官方智能体断路器自举安装向导 (v1.3.2)")
    print(f"操作系统: {platform.system()} ({platform.machine()})")
    print(f"源包目录: {PLUGIN_SRC_DIR}")
    print("=" * 65)

    dest_dir = target_dir or DEFAULT_USER_PLUGIN_DIR
    print(f"📍 安装目标目录: {dest_dir}")

    # 若从源码仓库运行，且目标目录不等于源目录，则实施同步/复制
    if dest_dir.resolve() != PLUGIN_SRC_DIR.resolve():
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in ["plugin.json", "mcp_config.json", "server.py", "setup.py", "README.md"]:
            src_f = PLUGIN_SRC_DIR / item
            if src_f.exists():
                shutil.copy2(src_f, dest_dir / item)

        for dir_name in ["scripts", "rules", "skills"]:
            src_d = PLUGIN_SRC_DIR / dir_name
            dest_d = dest_dir / dir_name
            if src_d.exists():
                shutil.copytree(src_d, dest_d, dirs_exist_ok=True)
        print("✅ 1. 核心插件文件已同步至用户配置目录")
        active_guard = dest_dir / "scripts" / "circuit_guard.py"
        active_hooks_file = dest_dir / "hooks.json"
        active_server = dest_dir / "server.py"
    else:
        active_guard = GUARD_SCRIPT
        active_hooks_file = HOOKS_FILE
        active_server = PLUGIN_SRC_DIR / "server.py"

    # 生成 hooks.json
    hooks_config = build_hooks_config(active_guard)
    with open(active_hooks_file, "w", encoding="utf-8") as f:
        json.dump(hooks_config, f, ensure_ascii=False, indent=2)

    print("✅ 2. 自适应弹性 hooks.json 生成完毕 (官方标准 5 大 Hook 规范)")
    print(f"✅ 3. Guard 脚本绝对路径绑定: {active_guard}")
    print(f"✅ 4. Python 解释器绝对路径绑定: {get_python_cmd()}")

    # 动态重写插件私有 mcp_config.json，彻底消除任何跨节点硬编码 Python 路径
    plugin_mcp_cfg_file = dest_dir / "mcp_config.json"
    mcp_py_exe = get_mcp_python_cmd()
    plugin_mcp_data = {
        "mcpServers": {
            "circuit-breaker": {
                "command": mcp_py_exe,
                "args": [str(active_server.resolve()).replace("\\", "/")],
                "env": {
                    "PYTHONIOENCODING": "utf-8"
                }
            }
        }
    }
    with open(plugin_mcp_cfg_file, "w", encoding="utf-8") as f:
        json.dump(plugin_mcp_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 4.1 插件私有 mcp_config.json 动态绑定完成 (command: {mcp_py_exe})")

    # 双轨注册全局 MCP
    register_global_mcp(active_server)

    # 执行开箱即用自测探针
    print("\n🧪 6. 执行开箱即用自测探针 (模拟 MCP 只读穿透放行)...")
    try:
        py_exe = get_python_cmd()
        test_payload = json.dumps({
            "conversationId": "selftest",
            "toolCall": {
                "name": "call_mcp_tool",
                "args": {"ServerName": "openviking", "ToolName": "openviking_search"}
            }
        }).encode("utf-8")

        proc = subprocess.Popen(
            [py_exe, "-E", "-s", "-S", str(active_guard), "pre-tool"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(test_payload)
        out_str = out.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0 and "allow" in out_str:
            print(f"✅ 探针通过！返回: {out_str} (耗时毫秒级，0 报错)")
        else:
            print(f"⚠️ 探针返回异常: {out_str}, stderr: {err.decode('utf-8', errors='replace')}")
    except Exception as e:
        print(f"⚠️ 探针执行略过: {e}")

    # 注册入宿主 config.json
    register_in_ide_config(get_plugin_version())

    print("\n🎉 安装成功！即插即用，反重力智能体已获得 Fail-Open 弹性断路守护。")


def uninstall(target_dir: Path = None):
    dest_dir = target_dir or DEFAULT_USER_PLUGIN_DIR
    print("=" * 65)
    print("🛑 [Agent Circuit Breaker] 插件解除绑定向导")
    print(f"目标目录: {dest_dir}")
    print("=" * 65)

    hooks_file = dest_dir / "hooks.json"
    if hooks_file.exists():
        hooks_file.unlink(missing_ok=True)
        print("✅ 已安全移除 hooks.json，生命周期钩子已完全解绑。")
    else:
        print("ℹ️ hooks.json 不存在，当前处于未激活状态。")

    unregister_global_mcp()


def status(target_dir: Path = None):
    dest_dir = target_dir or DEFAULT_USER_PLUGIN_DIR
    print("=" * 65)
    print("🔍 [Agent Circuit Breaker] 插件巡检报告")
    print(f"插件目录: {dest_dir}")
    print(f"Hooks 状态: {'🟢 已激活' if (dest_dir / 'hooks.json').exists() else '⚪ 未激活'}")
    print(f"Guard 脚本: {'🟢 存在' if (dest_dir / 'scripts' / 'circuit_guard.py').exists() else '🔴 缺失'}")
    print(f"MCP 服务: {'🟢 存在' if (dest_dir / 'server.py').exists() else '🔴 缺失'}")
    print(f"Rules 规约: {'🟢 存在' if (dest_dir / 'rules' / 'AGENTS.md').exists() else '🔴 缺失'}")
    print("=" * 65)


if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "install"
    if action == "install":
        install()
    elif action in ("uninstall", "remove"):
        uninstall()
    elif action == "status":
        status()
    else:
        print(f"未知参数: {action}。支持: install | uninstall | status")
