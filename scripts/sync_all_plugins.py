#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking & Antigravity 全系 7 大插件一键同步与版本对齐总控脚本
对齐四大真相源 (SSOT)：
1. 母本 plugin.json
2. 母本 setup.py (动态读取)
3. 部署端 plugin.json (~/.gemini/config/plugins/<name>)
4. 宿主注册表 config.json (~/.gemini/config/config.json)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_SRC_DIR = REPO_ROOT / "integrations" / "antigravity"
INSTALLED_DIR = Path.home() / ".gemini" / "config" / "plugins"
CFG_FILE = Path.home() / ".gemini" / "config" / "config.json"
PYTHON_EXE = sys.executable

ALL_7_PLUGINS = [
    "openviking-memory",
    "openviking-ops",
    "fleet-mesh",
    "cpa-squad",
    "keepass-vault",
    "dify",
    "agent-circuit-breaker"
]


def sync_plugin(plugin_name: str) -> bool:
    src_dir = PLUGINS_SRC_DIR / plugin_name
    setup_file = src_dir / "setup.py"
    if not setup_file.exists():
        print(f"❌ {plugin_name}: 缺少 setup.py 安装向导！")
        return False

    print(f"\n🔄 正在自举安装/更新: {plugin_name}...")
    try:
        # 兼容 agent-circuit-breaker 的 install 参数模式与其它插件的 --install 参数模式
        if plugin_name == "agent-circuit-breaker":
            cmd = [PYTHON_EXE, str(setup_file), "install"]
        else:
            cmd = [PYTHON_EXE, str(setup_file), "--install"]
        
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(cmd, cwd=str(src_dir), capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=15)
        if res.returncode == 0:
            print(f"  ✔ {plugin_name} 自举部署成功 (Exit 0)")
            return True
        else:
            print(f"  ❌ {plugin_name} 部署失败 (Exit {res.returncode}):\n{res.stderr or res.stdout}")
            return False
    except Exception as e:
        print(f"  ❌ {plugin_name} 执行异常: {e}")
        return False


def verify_alignment():
    print("\n" + "=" * 80)
    print("📊 [插件生态单一真相源 (SSOT) 对齐审计大盘]")
    print("=" * 80)
    print(f"{'插件名称':<25} | {'母本版本':<10} | {'安装目录版本':<12} | {'宿主注册版本':<12} | 状态")
    print("-" * 80)

    if not CFG_FILE.exists():
        print("❌ 宿主 config.json 不存在！")
        return False

    with open(CFG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg_plugins = cfg.get("plugins", {})

    all_pass = True
    for p_name in ALL_7_PLUGINS:
        src_pj = PLUGINS_SRC_DIR / p_name / "plugin.json"
        src_ver = "N/A"
        if src_pj.exists():
            with open(src_pj, "r", encoding="utf-8") as f:
                src_ver = json.load(f).get("version", "N/A")

        inst_pj = INSTALLED_DIR / p_name / "plugin.json"
        inst_ver = "N/A"
        if inst_pj.exists():
            with open(inst_pj, "r", encoding="utf-8") as f:
                inst_ver = json.load(f).get("version", "N/A")

        cfg_ver = "N/A"
        if p_name in cfg_plugins:
            p_info = cfg_plugins[p_name]
            if isinstance(p_info, dict):
                cfg_ver = p_info.get("installedFrom", {}).get("version", p_info.get("version", "N/A"))

        matched = (src_ver == inst_ver == cfg_ver) and src_ver != "N/A"
        if not matched:
            all_pass = False

        status = "✅ PASS" if matched else "❌ DRIFT"
        print(f"{p_name:<25} | {src_ver:<10} | {inst_ver:<12} | {cfg_ver:<12} | {status}")

    print("=" * 80)
    if all_pass:
        print("🎉 全系 7 大插件单一真相源 (SSOT) 100% 对齐，0 漂移，开箱即用！")
    else:
        print("⚠️ 存在版本漂移，请检查上述标记为 DRIFT 的插件！")
    return all_pass


def main():
    print("🚀 启动全系 7 大插件一键同步与版本闭环...")
    success_count = 0
    for p in ALL_7_PLUGINS:
        if sync_plugin(p):
            success_count += 1

    print(f"\n📦 安装阶段完成: {success_count}/{len(ALL_7_PLUGINS)} 个插件已同步")
    ok = verify_alignment()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
