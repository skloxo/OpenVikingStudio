#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
一键批量补齐本地核心技能至 OpenViking Wiki 技能中心 (v1.0.0)
将本地合规但未收录到 VikingFS 的技能逐一推送到 POST /api/v1/skills
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

def get_api_key() -> str:
    env_key = os.environ.get("OPENVIKING_API_KEY")
    if env_key:
        return env_key
    conf_path = Path.home() / ".openviking" / "ov.conf"
    if conf_path.exists():
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                conf = json.load(f)
                return conf.get("server", {}).get("root_api_key", "")
        except Exception:
            pass
    return ""

API_URL = "http://127.0.0.1:1933/api/v1/skills"

MISSING_SKILLS = [
    "adversarial-learning",
    "agent-friendly-code-org",
    "cockpit-ui",
    "deepseek-harness-ops",
    "dify-ops",
    "homepage-ops",
    "living-asset-system",
    "n8n-ops",
    "openviking-model-evaluator",
    "openviking-plugin-ops",
    "satellite-fleet-ops",
    "web-search-pro",
    "wechat-article-reader"
]

def get_headers():
    key = get_api_key()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }

def get_installed_skills():
    req = urllib.request.Request(API_URL, headers=get_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {s["name"] for s in data.get("result", {}).get("skills", [])}
    except Exception as e:
        print(f"获取已安装技能失败: {e}", file=sys.stderr)
        return set()

def ingest_skill(skill_name: str, skill_md_path: Path):
    if not skill_md_path.exists():
        print(f"[-] 跳过 {skill_name}: 路径不存在 {skill_md_path}")
        return False

    content = skill_md_path.read_text(encoding="utf-8")
    payload = {
        "data": content,
        "target_uri": "viking://agent/skills"
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=get_headers()
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            print(f"[+] 成功收录 {skill_name} -> {res.get('result', {}).get('root_uri')} ({elapsed:.1f}s)")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[!] 收录失败 {skill_name} (HTTP {e.code}): {err_body}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[!] 收录异常 {skill_name}: {e}", file=sys.stderr)
        return False

def main():
    print("=" * 60)
    print("🚀 开始比对并批量补齐本地技能至 Wiki 技能中心...")
    print("=" * 60)

    installed = get_installed_skills()
    print(f"当前 Wiki 已收录技能总数: {len(installed)}")

    base_dir = Path.home() / ".gemini" / "config" / "skills"
    to_ingest = [s for s in MISSING_SKILLS if s not in installed]
    print(f"待补齐收录核心技能数: {len(to_ingest)} / {len(MISSING_SKILLS)}")

    success_count = 0
    fail_count = 0

    for idx, skill_name in enumerate(to_ingest, 1):
        skill_md = base_dir / skill_name / "SKILL.md"
        print(f"[{idx}/{len(to_ingest)}] 正在处理: {skill_name} ...")
        ok = ingest_skill(skill_name, skill_md)
        if ok:
            success_count += 1
        else:
            fail_count += 1
        # 强制温和冷却，防止压垮本地模型服务
        time.sleep(1.0)

    print("=" * 60)
    print(f"🏁 补齐收录完成！成功: {success_count}, 失败: {fail_count}")
    after_installed = get_installed_skills()
    print(f"当前 Wiki 技能中心最新技能总数: {len(after_installed)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
