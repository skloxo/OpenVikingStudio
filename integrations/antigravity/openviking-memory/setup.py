#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking 核心记忆反重力标准插件 (v2.0.11) — 一键开箱即用配置脚本
用法:
  python3 setup.py --api http://127.0.0.1:1933 --key <YOUR_API_KEY>
  或直接交互式运行:
  python3 setup.py
"""

import argparse
import json
import os
import stat
import sys
import urllib.request
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="配置 OpenViking 反重力标准插件连接凭据")
    parser.add_argument("--api", type=str, default="", help="OpenViking 服务端地址 (例如 http://127.0.0.1:1933)")
    parser.add_argument("--key", type=str, default="", help="专属 API Key 凭据 (可在 OpenViking Studio 用户列表复制)")
    return parser.parse_args()


def prompt_input(prompt_text: str, default_val: str = "") -> str:
    default_str = f" [{default_val}]" if default_val else ""
    try:
        val = input(f"{prompt_text}{default_str}: ").strip()
        return val or default_val
    except (KeyboardInterrupt, EOFError):
        print("\n已取消配置。")
        sys.exit(1)


def verify_connection(api: str, key: str):
    url = f"{api.rstrip('/')}/api/v1/system/status"
    headers = {"User-Agent": "Antigravity-OpenViking-Plugin/2.0.11"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
        
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "ok":
                user = data.get("result", {}).get("user", "unknown")
                return True, user, ""
            return False, "", data.get("error") or "未知错误"
    except Exception as e:
        return False, "", str(e)


def main():
    print("=" * 60)
    print("🚀 OpenViking 核心记忆反重力官方标准插件 (v2.0.11) 快速配置")
    print("=" * 60)
    
    args = parse_args()
    api = args.api.strip()
    key = args.key.strip()
    
    plugin_dir = Path(__file__).resolve().parent
    config_file = plugin_dir / "config.json"
    
    # 尝试读取旧配置作为默认值
    old_api = "http://127.0.0.1:1933"
    old_key = ""
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                c = json.load(f)
                old_api = c.get("api_url", old_api)
                old_key = c.get("api_key", old_key)
        except Exception:
            pass

    if not api:
        api = prompt_input("1. 请输入 OpenViking 核心服务地址", old_api)
    if not key:
        masked_hint = f"{old_key[:10]}...{old_key[-6:]}" if len(old_key) > 16 else old_key
        prompt_title = f"2. 请输入您的专属 API Key" + (f" (回车保留当前: {masked_hint})" if masked_hint else "")
        key_input = prompt_input(prompt_title, "")
        key = key_input if key_input else old_key

    api = api.rstrip("/")
    if not api.startswith("http://") and not api.startswith("https://"):
        api = "http://" + api

    print(f"\n📡 正在验证连接: {api} ...")
    ok, user, err = verify_connection(api, key)
    
    if not ok:
        print(f"❌ 连接验证失败: {err}")
        print("💡 请检查: 1. OpenViking 服务是否已启动; 2. API Key 是否正确有效。")
        sys.exit(1)
        
    print(f"✅ 验证通过！成功识别用户身份: 【{user}】")
    
    # 写入私有 config.json (chmod 600)
    cfg_data = {
        "api_url": api,
        "api_key": key,
        "verified_user": user
    }
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        
    try:
        os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass

    # 确保 hooks 脚本具备执行权限
    hooks_dir = plugin_dir / "hooks"
    if hooks_dir.exists():
        for script in hooks_dir.glob("*.py"):
            try:
                curr = os.stat(script).st_mode
                os.chmod(script, curr | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass

    print(f"💾 插件凭据已就绪: {config_file} (权限: 0600 严格隔离)")
    print("=" * 60)
    print("🎉 配置全部完成！反重力 IDE 已自动挂载 OpenViking 核心记忆 v2.0.11！")
    print("=" * 60)


if __name__ == "__main__":
    main()
