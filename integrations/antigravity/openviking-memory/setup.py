#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking 核心记忆反重力官方标准插件 (v2.0.12 - 工业自适应弹性版)
支持跨平台一键开箱安装、绝对路径 Hook 自适应渲染、API 凭据智能探测与毫秒级巡检。
用法:
  python setup.py --install                 # 一键安装并动态挂载至 Antigravity 插件目录
  python setup.py --install --api <URL> --key <KEY>
  python setup.py --inspect                 # 插件健康状态与 PreInvocation 预取毫秒级巡检
  python setup.py --uninstall               # 优雅卸载
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
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_SRC_DIR = Path(__file__).resolve().parent
DEFAULT_TARGET_DIR = Path.home() / ".gemini" / "config" / "plugins" / "openviking-memory"


def get_python_cmd() -> str:
    """获取规范化绝对 Python 解释器路径"""
    py_path = sys.executable.replace("\\", "/")
    return f'"{py_path}"' if " " in py_path else py_path


def sniff_api_credentials(fallback_api="http://127.0.0.1:1933"):
    """多级智能嗅探可用的 OpenViking API 与 Key"""
    api = os.environ.get("OPENVIKING_API", "").strip()
    key = os.environ.get("OPENVIKING_API_KEY", "").strip()

    # 1. 尝试从既有插件 config.json 读取
    for check_cfg in [
        PLUGIN_SRC_DIR / "config.json",
        DEFAULT_TARGET_DIR / "config.json"
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

    # 2. 尝试从 WSL 或本地 .openviking/ov.conf 读取 root_api_key
    if not key:
        conf_candidates = [
            Path.home() / ".openviking" / "ov.conf",
            Path("/mnt/c/Users") / os.environ.get("USERNAME", "") / ".openviking" / "ov.conf",
        ]
        # WSL 探测
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
                except Exception:
                    pass

    api = (api or fallback_api).rstrip("/")
    if not api.startswith("http://") and not api.startswith("https://"):
        api = "http://" + api

    return api, key


def verify_connection(api: str, key: str):
    """真实探测 OpenViking 服务连通性与身份"""
    url = f"{api.rstrip('/')}/api/v1/system/status"
    headers = {"User-Agent": "Antigravity-OpenViking-Plugin/2.0.12"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            latency_ms = (time.time() - t0) * 1000
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "ok":
                user = data.get("result", {}).get("user", "authenticated_user")
                return True, user, latency_ms, ""
            return False, "", latency_ms, data.get("error") or "服务端返回状态非 ok"
    except Exception as e:
        return False, "", 0, str(e)


def build_hooks_json(target_dir: Path) -> dict:
    """
    根据目标安装目录，使用绝对 Python 解释器与绝对脚本路径动态构建 hooks.json
    携带纯标准库隔离参数 (-E -s -S)，毫秒级冷启动防御超温死锁
    """
    py_cmd = get_python_cmd()
    pre_script = (target_dir / "hooks" / "ov_pre_invocation.py").resolve()
    arch_script = (target_dir / "hooks" / "ov_session_archiver.py").resolve()

    pre_path = str(pre_script).replace("\\", "/")
    arch_path = str(arch_script).replace("\\", "/")

    pre_cmd = f'{py_cmd} -E -s -S "{pre_path}"' if " " in pre_path else f"{py_cmd} -E -s -S {pre_path}"
    arch_cmd = f'{py_cmd} -E -s -S "{arch_path}"' if " " in arch_path else f"{py_cmd} -E -s -S {arch_path}"

    return {
        "openviking-memory-prefetch": {
            "PreInvocation": [
                {
                    "type": "command",
                    "command": pre_cmd,
                    "timeout": 4
                }
            ]
        },
        "openviking-session-archiver": {
            "Stop": [
                {
                    "type": "command",
                    "command": arch_cmd,
                    "timeout": 3
                }
            ]
        }
    }


def install_plugin(target_dir: Path, api: str, key: str):
    """全量标准安装规范"""
    print(f"📦 正在准备安装 OpenViking 核心记忆插件至: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 复制构件：hooks, rules, skills, assets, plugin.json, README.md
    copy_items = ["hooks", "rules", "skills", "assets", "plugin.json", "README.md", "setup.py"]
    for item_name in copy_items:
        src = PLUGIN_SRC_DIR / item_name
        dst = target_dir / item_name
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    # 2. 赋予脚本执行权限
    hooks_dst = target_dir / "hooks"
    if hooks_dst.exists():
        for s in hooks_dst.glob("*.py"):
            try:
                os.chmod(s, os.stat(s).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass

    # 3. 动态渲染 hooks.json (强制绝对路径 + 隔离参数)
    hooks_cfg = build_hooks_json(target_dir)
    hooks_file = target_dir / "hooks.json"
    with open(hooks_file, "w", encoding="utf-8") as f:
        json.dump(hooks_cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  ✔ hooks.json 动态构建完成 (绝对路径 + -E -s -S 隔离)")

    # 4. 验证并写入 config.json
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
    print(f"  ✔ config.json 凭据落盘完成 (权限: 0600)")

    print("\n🎉 OpenViking 核心记忆插件标准部署完成！")
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

    # 1. 检查构件完整性
    for f in [cfg_file, hooks_file, plugin_file]:
        if not f.exists():
            print(f"❌ 关键文件缺失: {f.name}")
            return False
        print(f"  ✔ 构件存在: {f.name}")

    # 2. 检查 hooks.json 绝对路径
    with open(hooks_file, "r", encoding="utf-8") as f:
        hooks_data = json.load(f)
    pre_cmd = hooks_data.get("openviking-memory-prefetch", {}).get("PreInvocation", [{}])[0].get("command", "")
    if "-E -s -S" not in pre_cmd or ("/" not in pre_cmd and "\\" not in pre_cmd):
        print(f"⚠️ PreInvocation 命令未达工业级标准: {pre_cmd}")
    else:
        print(f"  ✔ PreInvocation Hook 命令已配置绝对路径与隔离参数")

    # 3. 检查后端服务连通性
    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    api = cfg.get("api_url", "")
    key = cfg.get("api_key", "")
    ok, user, latency, err = verify_connection(api, key)
    if ok:
        print(f"  ✔ OpenViking 核心服务连通良好: {api} ({latency:.1f}ms, 用户: {user})")
    else:
        print(f"❌ OpenViking 核心服务不可达: {err}")

    # 4. 模拟 PreInvocation Hook 实跑探针
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
    parser = argparse.ArgumentParser(description="OpenViking 核心记忆反重力标准插件安装器")
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

    # 默认或显式指定 --install 时执行标准安装
    api, key = sniff_api_credentials()
    if args.api:
        api = args.api.strip()
    if args.key:
        key = args.key.strip()

    install_plugin(target_dir, api, key)
    print("\n" + "=" * 50)
    inspect_plugin(target_dir)


if __name__ == "__main__":
    main()
