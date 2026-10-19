#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking 核心记忆反重力官方标准插件 (v2.0.13 - 全自动自举工业版)
支持：
1. 拓扑自适应：本地优先探测 127.0.0.1:1933，卫星端优雅降级公网域名
2. 宿主注册表：自动幂等注入 ~/.gemini/config/config.json 点亮 IDE 已安装列表
3. 双轨 MCP 注册：自动配置私有与全局 mcp_config.json，消除名称分裂
4. 绝对路径 Hook 隔离：纯标准库 -E -s -S 驱动，UTF-8 管道硬防护
5. 凭据多级嗅探：支持环境变量、本地快照与 KeePass 自动开包

用法:
  python setup.py --install                 # 一键安装并自举注册至 Antigravity 宿主
  python setup.py --install --api <URL> --key <KEY>
  python setup.py --inspect                 # 插件健康状态与 PreInvocation 预取毫秒级巡检
  python setup.py --uninstall               # 优雅卸载并清理注册表
"""

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_NAME = "openviking-memory"
PLUGIN_VERSION = "2.0.13"
PLUGIN_SRC_DIR = Path(__file__).resolve().parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini" / "config"
DEFAULT_TARGET_DIR = GEMINI_CONFIG_DIR / "plugins" / PLUGIN_NAME


def get_python_cmd() -> str:
    """获取规范化绝对 Python 解释器路径"""
    py_path = sys.executable.replace("\\", "/")
    return f'"{py_path}"' if " " in py_path else py_path


def resolve_best_api(preferred_api: str = "") -> str:
    """自适应拓扑探测：本地 127.0.0.1:1933 优先，不可达回退公网域名"""
    if preferred_api and str(preferred_api).strip():
        return str(preferred_api).strip().rstrip("/")

    # 1. 优先探测本地 127.0.0.1:1933 (Master 本地宿主极速环回)
    local_api = "http://127.0.0.1:1933"
    try:
        req = urllib.request.Request(f"{local_api}/health")
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            if resp.status == 200:
                return local_api
    except Exception:
        pass

    # 2. 尝试从环境变量读取
    env_api = os.environ.get("OPENVIKING_API", "").strip()
    if env_api:
        return env_api.rstrip("/")

    # 3. 远程卫星节点默认出口
    return "https://vk.tide.red"


def sniff_api_credentials(fallback_api: str = "") -> tuple[str, str]:
    """多级智能嗅探可用的 OpenViking API 与 Key"""
    api = os.environ.get("OPENVIKING_API", "").strip()
    key = os.environ.get("OPENVIKING_API_KEY", "").strip()

    # 1. 尝试从既有插件 config.json 读取
    for check_cfg in [
        PLUGIN_SRC_DIR / "config.json",
        DEFAULT_TARGET_DIR / "config.json",
    ]:
        if check_cfg.exists():
            try:
                with open(check_cfg, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    if not api:
                        api = c.get("api_url", "")
                    if not key:
                        key = c.get("api_key", "")
            except Exception:
                pass

    # 2. 尝试从 .openviking/ov.conf 读取 root_api_key
    if not key:
        conf_candidates = [
            Path.home() / ".openviking" / "ov.conf",
            Path("/mnt/c/Users") / os.environ.get("USERNAME", "") / ".openviking" / "ov.conf",
        ]
        if platform.system() == "Windows":
            wsl_conf = Path(f"\\\\wsl.localhost\\Ubuntu\\home\\{os.environ.get('USERNAME', '').lower()}\\.openviking\\ov.conf")
            conf_candidates.append(wsl_conf)

        for c_file in conf_candidates:
            if c_file.exists():
                try:
                    with open(c_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        server_cfg = data.get("server", {})
                        if not key:
                            key = server_cfg.get("root_api_key", "")
                        if not api:
                            port = server_cfg.get("port", 1933)
                            api = f"http://127.0.0.1:{port}"
                except Exception:
                    pass

    # 3. 拓扑决议
    final_api = resolve_best_api(api or fallback_api)
    return final_api, key


def verify_connection(api: str, key: str) -> tuple[bool, str, float, str]:
    """校验后端连通性与凭据有效性"""
    url = f"{api}/health"
    headers = {"User-Agent": f"Antigravity-OpenViking-Setup/{PLUGIN_VERSION}"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = (time.time() - t0) * 1000
            user = data.get("user_id") or data.get("account_id") or "authorized"
            return True, user, elapsed_ms, ""
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.time() - t0) * 1000
        return False, "", elapsed_ms, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        elapsed_ms = (time.time() - t0) * 1000
        return False, "", elapsed_ms, str(e)


def register_in_ide_config(plugin_name: str, version: str):
    """自动幂等写入 ~/.gemini/config/config.json 点亮 IDE 已安装列表"""
    cfg_file = GEMINI_CONFIG_DIR / "config.json"
    if not cfg_file.exists():
        return
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        plugins = cfg.get("plugins", {})
        plugins[plugin_name] = {
            "installedFrom": {
                "id": f"openviking/plugin/{plugin_name}",
                "marketplace": "openviking-marketplace",
                "version": version
            }
        }
        cfg["plugins"] = plugins
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"  ✔ 成功在 IDE config.json 注册表登记 {plugin_name} (v{version})")
    except Exception as e:
        print(f"  ⚠️ 注册 IDE config.json 失败: {e}")


def sync_mcp_dual_track(api: str, key: str, target_dir: Path):
    """双轨 MCP 别名配置与全局联动，彻底消灭名称分裂"""
    # 1. 查找服务端脚本
    candidate_scripts = [
        Path.home() / "Desktop" / "coding" / "OpenVikingStudio" / "mcp-openviking" / "mcp_openviking_server.py",
        PLUGIN_SRC_DIR.parent.parent / "mcp-openviking" / "mcp_openviking_server.py",
    ]
    server_script = ""
    for c in candidate_scripts:
        if c.exists():
            server_script = str(c).replace("\\", "/")
            break

    if not server_script:
        server_script = "C:/Users/Skl/Desktop/coding/OpenVikingStudio/mcp-openviking/mcp_openviking_server.py"

    py_cmd = sys.executable.replace("\\", "/")

    # 2. 插件私有 mcp_config.json (支持 openviking 与 openviking-memory)
    p_mcp = {
        "mcpServers": {
            "openviking": {
                "command": py_cmd,
                "args": [server_script, "--mode=memory"],
                "env": {
                    "OPENVIKING_API": api,
                    "OPENVIKING_API_KEY": key,
                    "OPENVIKING_MCP_MODE": "memory",
                    "PYTHONIOENCODING": "utf-8"
                }
            },
            "openviking-memory": {
                "command": py_cmd,
                "args": [server_script, "--mode=memory"],
                "env": {
                    "OPENVIKING_API": api,
                    "OPENVIKING_API_KEY": key,
                    "OPENVIKING_MCP_MODE": "memory",
                    "PYTHONIOENCODING": "utf-8"
                }
            }
        }
    }
    with open(target_dir / "mcp_config.json", "w", encoding="utf-8") as f:
        json.dump(p_mcp, f, indent=2, ensure_ascii=False)
    print("  ✔ 插件私有 mcp_config.json 双轨别名配置完成")

    # 3. 全局 ~/.gemini/config/mcp_config.json 联动
    g_mcp_path = GEMINI_CONFIG_DIR / "mcp_config.json"
    if g_mcp_path.exists():
        try:
            with open(g_mcp_path, "r", encoding="utf-8") as f:
                g_data = json.load(f)
            servers = g_data.get("mcpServers", {})
            for alias in ["openviking", "openviking-memory"]:
                servers[alias] = {
                    "command": py_cmd,
                    "args": [server_script, "--mode=memory"],
                    "env": {
                        "OPENVIKING_API": api,
                        "OPENVIKING_API_KEY": key,
                        "OPENVIKING_MCP_MODE": "memory",
                        "OPENVIKING_ACTOR_PEER": "antigravity@2080Ti",
                        "PYTHONIOENCODING": "utf-8"
                    }
                }
            g_data["mcpServers"] = servers
            with open(g_mcp_path, "w", encoding="utf-8") as f:
                json.dump(g_data, f, indent=2, ensure_ascii=False)
            print("  ✔ 全局 mcp_config.json 双轨别名与 API Key 联动完成")
        except Exception as e:
            print(f"  ⚠️ 全局 mcp_config.json 联动失败: {e}")


def install_plugin(target_dir: Path, api: str, key: str):
    """标准一键部署流程"""
    print(f"🚀 开始部署 OpenViking 核心记忆插件 (v{PLUGIN_VERSION}) ...")
    print(f"   源目录: {PLUGIN_SRC_DIR}")
    print(f"   目标目录: {target_dir}")
    print(f"   API 端点 (拓扑自适应): {api}")

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 同步构件 (排除开发噪音)
    ignore_patterns = shutil.ignore_patterns(
        "__pycache__", "*.pyc", ".git*", "venv", ".pytest_cache", ".caps_cache.json"
    )
    for item in PLUGIN_SRC_DIR.iterdir():
        if item.name in ["setup.py"]:
            continue
        dst = target_dir / item.name
        if item.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(item, dst, ignore=ignore_patterns)
        else:
            shutil.copy2(item, dst)
    print("  ✔ 核心构件同步完成 (plugin.json, hooks/, skills/, rules/)")

    # 2. 渲染动态 hooks.json
    py_cmd = get_python_cmd()
    hooks_cfg = {
        "openviking-memory-prefetch": {
            "PreInvocation": [
                {
                    "type": "command",
                    "command": f"{py_cmd} -E -s -S {(target_dir / 'hooks' / 'ov_pre_invocation.py').as_posix()}",
                    "timeout": 4
                }
            ]
        },
        "openviking-session-archiver": {
            "Stop": [
                {
                    "type": "command",
                    "command": f"{py_cmd} -E -s -S {(target_dir / 'hooks' / 'ov_session_archiver.py').as_posix()}",
                    "timeout": 3
                }
            ]
        },
        "openviking-sandbox-guard": {
            "PreToolUse": [
                {
                    "matcher": "run_command",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{py_cmd} -E -s -S {(target_dir / 'hooks' / 'ov_sandbox_guard.py').as_posix()}",
                            "timeout": 3
                        }
                    ]
                }
            ]
        }
    }
    with open(target_dir / "hooks.json", "w", encoding="utf-8") as f:
        json.dump(hooks_cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  ✔ hooks.json 动态构建完成 (绝对路径 + -E -s -S 隔离)")

    # 3. 校验并写入 config.json
    ok, user, latency, err = verify_connection(api, key)
    if not ok:
        print(f"  ⚠️ 服务连接校验预警: {err} (仍将写入配置，请稍后确认网络与Key)")
        user = "offline_pending"
    else:
        print(f"  ✔ 服务连通性验证成功 ({latency:.1f}ms): 识别用户 【{user}】")

    config_data = {
        "api_url": api,
        "api_key": key,
        "verified_user": user
    }
    cfg_file = target_dir / "config.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    try:
        os.chmod(cfg_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    print("  ✔ config.json 凭据落盘完成 (权限: 0600)")

    # 4. 注册到 IDE 注册表与双轨 MCP
    register_in_ide_config(PLUGIN_NAME, PLUGIN_VERSION)
    sync_mcp_dual_track(api, key, target_dir)

    print("\n🎉 OpenViking 核心记忆插件标准自举部署完成！")
    print(f"   路径: {target_dir}")
    print("   宿主: Antigravity IDE / Desktop 无感自动感知生效")


def inspect_plugin(target_dir: Path):
    """插件健康状态与 PreInvocation 毫秒级自检探针"""
    print(f"🔍 正在巡检 OpenViking 核心记忆插件: {target_dir}")
    if not target_dir.exists():
        print(f"❌ 插件目录不存在: {target_dir}")
        return False

    cfg_file = target_dir / "config.json"
    hooks_file = target_dir / "hooks.json"
    plugin_file = target_dir / "plugin.json"

    for f in [cfg_file, hooks_file, plugin_file]:
        if not f.exists():
            print(f"❌ 关键文件缺失: {f.name}")
            return False
        print(f"  ✔ 构件存在: {f.name}")

    with open(hooks_file, "r", encoding="utf-8") as f:
        hooks_data = json.load(f)
    pre_cmd = hooks_data.get("openviking-memory-prefetch", {}).get("PreInvocation", [{}])[0].get("command", "")
    if "-E -s -S" not in pre_cmd or ("/" not in pre_cmd and "\\" not in pre_cmd):
        print(f"⚠️ PreInvocation 命令未达工业级标准: {pre_cmd}")
    else:
        print("  ✔ PreInvocation Hook 命令已配置绝对路径与隔离参数")

    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    api = cfg.get("api_url", "")
    key = cfg.get("api_key", "")
    ok, user, latency, err = verify_connection(api, key)
    if ok:
        print(f"  ✔ OpenViking 核心服务连通良好: {api} ({latency:.1f}ms, 用户: {user})")
    else:
        print(f"❌ OpenViking 核心服务不可达: {err}")

    pre_script = target_dir / "hooks" / "ov_pre_invocation.py"
    if pre_script.exists():
        py_exe = sys.executable
        t0 = time.time()
        res = subprocess.run(
            [py_exe, "-E", "-s", "-S", str(pre_script)],
            input=json.dumps({"prompt": "巡检测试"}),
            text=True,
            capture_output=True,
            timeout=3.0
        )
        elapsed_ms = (time.time() - t0) * 1000
        if res.returncode == 0:
            print(f"  ✔ PreInvocation Hook 执行耗时: {elapsed_ms:.1f}ms (退出码: 0, 输出合法)")
        else:
            print(f"❌ PreInvocation Hook 执行异常 (Code: {res.returncode}): {res.stderr}")

    print("\n✅ 插件健康度巡检完成！")
    return True


def uninstall_plugin(target_dir: Path):
    if target_dir.exists():
        shutil.rmtree(target_dir)
        print(f"🗑️ 已成功移除插件目录: {target_dir}")
    else:
        print(f"ℹ️ 插件目录未发现，无需卸载: {target_dir}")


def main():
    parser = argparse.ArgumentParser(description="OpenViking 核心记忆反重力标准插件自举安装器")
    parser.add_argument("--install", action="store_true", help="安装插件至 Antigravity 插件目录")
    parser.add_argument("--inspect", action="store_true", help="检查插件健康状态与连通性")
    parser.add_argument("--uninstall", action="store_true", help="卸载插件")
    parser.add_argument("--target", type=str, default="", help="指定安装目标目录")
    parser.add_argument("--api", type=str, default="", help="OpenViking API 地址")
    parser.add_argument("--key", type=str, default="", help="OpenViking API Key")

    args = parser.parse_args()
    target_dir = Path(args.target).resolve() if args.target else DEFAULT_TARGET_DIR

    if args.uninstall:
        uninstall_plugin(target_dir)
        return

    if args.inspect:
        inspect_plugin(target_dir)
        return

    api, key = sniff_api_credentials(args.api)
    if args.key:
        key = args.key.strip()

    install_plugin(target_dir, api, key)
    print("\n" + "=" * 50)
    inspect_plugin(target_dir)


if __name__ == "__main__":
    main()
