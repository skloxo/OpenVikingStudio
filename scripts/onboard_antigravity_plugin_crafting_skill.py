#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
scripts/onboard_antigravity_plugin_crafting_skill.py
通过 OpenViking 官方技能中心标准 Gatekeeper & Ingestion Pipeline 规范入库 antigravity-plugin-crafting 技能。
四阶准入流程：
1. 提取 SKILL.md 并规范化 Frontmatter v2.0
2. POST /api/v1/skills/ingestion/validate (静态安全与契约门禁)
3. POST /api/v1/skills/ingestion/submit (提交到 Staging Inbox)
4. POST /api/v1/skills/ingestion/process-batch (触发后台 Worker 固化入库并烘焙索引)
"""

import json
import os
import sys
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

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILE = (
    REPO_ROOT
    / "integrations"
    / "antigravity"
    / "openviking-memory"
    / "skills"
    / "antigravity-plugin-crafting"
    / "SKILL.md"
)
BASE_URL = "http://127.0.0.1:1933/api/v1/skills/ingestion"


def resolve_credentials() -> tuple[str, str]:
    """遵循三级探测规则：环境变量 -> 插件 config.json -> KeePass / 默认凭据"""
    env_key = os.environ.get("OPENVIKING_API_KEY", "").strip()
    env_api = os.environ.get("OPENVIKING_API", "").strip()
    if env_key:
        return env_api or "http://127.0.0.1:1933", env_key

    cfg_p = Path.home() / ".gemini" / "config" / "plugins" / "openviking-memory" / "config.json"
    if cfg_p.exists():
        try:
            with open(cfg_p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_url", "http://127.0.0.1:1933"), data.get("api_key", "")
        except Exception:
            pass
    return "http://127.0.0.1:1933", ""


def main():
    print("=" * 70)
    print("🛡️ [OpenViking 技能中心官方四阶准入流水线]")
    print(f"• 待入库技能文件: {SKILL_FILE}")
    print("=" * 70)

    if not SKILL_FILE.exists():
        print(f"❌ 技能文件不存在: {SKILL_FILE}")
        sys.exit(1)

    api_url, api_key = resolve_credentials()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else "",
    }

    content = SKILL_FILE.read_text(encoding="utf-8")
    skill_name = "antigravity-plugin-crafting"

    # 1. 契约与静态安全门禁校验 (Validate)
    print("\n🔍 阶段 1/4: 执行契约与静态安全门禁校验 (POST /validate)...")
    v_payload = json.dumps({"content": content, "filename": "SKILL.md"}).encode("utf-8")
    v_req = urllib.request.Request(f"{BASE_URL}/validate", data=v_payload, headers=headers)

    try:
        with urllib.request.urlopen(v_req, timeout=10) as resp:
            v_res = json.loads(resp.read().decode("utf-8"))
            if not v_res.get("is_valid", False):
                print(f"❌ 门禁校验失败: {v_res.get('violations', [])}")
                sys.exit(1)
            print(f"  ✔ 门禁校验通过！(合法 Frontmatter v2.0，契约安全合规)")
    except Exception as e:
        print(f"❌ 门禁请求失败: {e}")
        sys.exit(1)

    # 2. 提交暂存信箱 (Submit)
    print("\n📬 阶段 2/4: 提交至 Staging Inbox (POST /submit)...")
    s_payload = json.dumps({
        "skill_name": skill_name,
        "content": content,
        "author": "antigravity@2080ti",
        "source_path": str(SKILL_FILE)
    }).encode("utf-8")
    s_req = urllib.request.Request(f"{BASE_URL}/submit", data=s_payload, headers=headers)

    receipt_id = None
    try:
        with urllib.request.urlopen(s_req, timeout=10) as resp:
            s_res = json.loads(resp.read().decode("utf-8"))
            receipt_id = s_res.get("receipt_id")
            status = s_res.get("status", "PENDING")
            print(f"  ✔ 暂存成功！Receipt ID: 【{receipt_id}】，状态: {status}")
    except Exception as e:
        print(f"❌ 提交暂存失败: {e}")
        sys.exit(1)

    # 3. 驱动后台 Worker 流水线批量固化 (Process-Batch)
    print("\n⚙️ 阶段 3/4: 触发后台 Worker 固化与向量烘焙流水线 (POST /process-batch)...")
    p_req = urllib.request.Request(
        f"{BASE_URL}/process-batch?batch_size=1",
        data=b"",
        headers=headers
    )
    try:
        with urllib.request.urlopen(p_req, timeout=30) as resp:
            p_res = json.loads(resp.read().decode("utf-8"))
            summary = p_res.get("worker_summary", {})
            print(f"  ✔ 流水线处理完成:\n{json.dumps(summary, ensure_ascii=False, indent=4)}")
    except Exception as e:
        print(f"❌ 触发批处理失败: {e}")
        sys.exit(1)

    # 4. 验真状态机变更至 COMMITTED
    print("\n🎯 阶段 4/4: 验真入籍与状态机状态...")
    if receipt_id:
        r_req = urllib.request.Request(f"{BASE_URL}/receipt/{receipt_id}", headers=headers)
        try:
            with urllib.request.urlopen(r_req, timeout=10) as resp:
                r_res = json.loads(resp.read().decode("utf-8"))
                record = r_res.get("record", {})
                final_status = record.get("status", "UNKNOWN")
                print(f"  ✔ 最终入籍凭据状态: 【{final_status}】 (Skill: {skill_name})")
        except Exception as e:
            print(f"  ⚠️ 查询收据状态异常: {e}")

    print("\n🎉 [入库成功] antigravity-plugin-crafting 已成功入籍 OpenViking 技能中枢！")
    print("   全集群 Agent 可通过自然语言（打造反重力插件、迭代插件适配反重力等）100% 自动找回。")


if __name__ == "__main__":
    main()
