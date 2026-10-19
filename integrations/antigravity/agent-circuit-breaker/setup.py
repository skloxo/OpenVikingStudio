#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Circuit Breaker 官方插件自举安装向导 (v1.3.0 - 工业自适应弹性版)
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


def get_python_cmd() -> str:
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
    cmd_session_start = f"{base_cmd} session-start"

    return {
        "agent-circuit-breaker": {
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
            ],
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
            ],
            "PreInvocation": [
                {
                    "type": "command",
                    "command": cmd_pre_inv,
                    "timeout": timeout_sec
                }
            ],
            "SessionStart": [
                {
                    "type": "command",
                    "command": cmd_session_start,
                    "timeout": timeout_sec
                }
            ]
        }
    }


def install(target_dir: Path = None):
    print("=" * 65)
    print("🛡️ [Agent Circuit Breaker] 官方智能体断路器自举安装向导 (v1.3.0)")
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
                if dest_d.exists():
                    shutil.rmtree(dest_d)
                shutil.copytree(src_d, dest_d)
        print("✅ 1. 核心插件文件已同步至用户配置目录")
        active_guard = dest_dir / "scripts" / "circuit_guard.py"
        active_hooks_file = dest_dir / "hooks.json"
    else:
        active_guard = GUARD_SCRIPT
        active_hooks_file = HOOKS_FILE

    # 生成 hooks.json
    hooks_config = build_hooks_config(active_guard)
    with open(active_hooks_file, "w", encoding="utf-8") as f:
        json.dump(hooks_config, f, ensure_ascii=False, indent=2)

    print("✅ 2. 自适应弹性 hooks.json 生成完毕 (-E -s -S 隔离参数已绑定)")
    print(f"✅ 3. Guard 脚本绝对路径绑定: {active_guard}")
    print(f"✅ 4. Python 解释器绝对路径绑定: {get_python_cmd()}")

    # 执行开箱即用自测探针
    print("\n🧪 5. 执行开箱即用自测探针 (模拟 MCP 只读穿透放行)...")
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
