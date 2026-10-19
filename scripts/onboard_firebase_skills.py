#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
通过 OpenViking 技能中心标准 Gatekeeper & Ingestion Pipeline 规范入库 Firebase 技能
流程：
1. 提取 SKILL.md 并规范化 Frontmatter v2.0 (triggers >= 3, allowed-tools, domain)
2. POST /api/v1/skills/ingestion/validate (静态安全门禁，确保 APPROVED)
3. POST /api/v1/skills/ingestion/submit (提交到 Staging Inbox)
4. POST /api/v1/skills/ingestion/process-batch (触发后台 Worker 流水线固化入库)
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
import yaml

TOKEN = "ZGVmYXVsdA.YW50aWdyYXZpdHlAMjA4MHRp.6f2c93702a448bb7e9dfeb89a269e072ccfdf133a4246c7a8e98b32102d8f2df"
BASE_URL = "http://127.0.0.1:1933/api/v1/skills/ingestion"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

def main():
    fb_dir = Path(r"C:\Users\Skl\.gemini\config\plugins\firebase\skills")
    if not fb_dir.exists():
        print(f"[-] 目录未找到: {fb_dir}", file=sys.stderr)
        return

    skill_dirs = [d for d in fb_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
    print(f"🚀 发现 {len(skill_dirs)} 个待规范入库的 Firebase 技能...")

    submitted = []

    for d in skill_dirs:
        skill_file = d / "SKILL.md"
        raw = skill_file.read_text(encoding="utf-8")
        parts = re.split(r"^---\s*$", raw, flags=re.MULTILINE)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = "---".join(parts[2:])
        else:
            fm = {"name": d.name.replace("_", "-")}
            body = raw

        s_name = fm.get("name", d.name).replace("_", "-")
        desc = fm.get("description", f"Firebase skill for {s_name}")
        if isinstance(desc, str):
            desc = desc.strip()

        # 规范化 Frontmatter v2.0
        fm["name"] = s_name
        fm["version"] = "1.0.0"
        fm["domain"] = "cloud-infra"
        fm["description"] = desc[:300] if desc else f"Firebase skill for {s_name}"

        clean_kw = s_name.replace("firebase-", "").replace("-", " ")
        fm["triggers"] = [
            f"firebase {clean_kw}",
            f"{s_name}",
            f"configure {clean_kw}",
            "firebase cloud tools"
        ]
        fm["allowed-tools"] = ["run_command", "view_file", "write_to_file"]

        norm_content = f"---\n{yaml.dump(fm, allow_unicode=True, sort_keys=False)}---\n{body}"

        # 1. Validate
        v_payload = json.dumps({"content": norm_content, "filename": "SKILL.md"}).encode("utf-8")
        v_req = urllib.request.Request(f"{BASE_URL}/validate", data=v_payload, headers=HEADERS)

        try:
            with urllib.request.urlopen(v_req, timeout=5) as resp:
                v_res = json.loads(resp.read().decode("utf-8"))
                if not v_res.get("is_valid"):
                    print(f"[-] {s_name} 校验未通过: {v_res.get('violations')}")
                    continue
        except Exception as e:
            print(f"[-] {s_name} 校验异常: {e}")
            continue

        # 2. Submit to staging inbox
        s_payload = json.dumps({
            "skill_name": s_name,
            "content": norm_content,
            "author": "antigravity@2080ti",
            "source_path": str(skill_file)
        }).encode("utf-8")
        s_req = urllib.request.Request(f"{BASE_URL}/submit", data=s_payload, headers=HEADERS)

        try:
            with urllib.request.urlopen(s_req, timeout=5) as resp:
                s_res = json.loads(resp.read().decode("utf-8"))
                receipt_id = s_res.get("receipt_id")
                print(f"[+] {s_name} 门禁通过并暂存成功 -> Receipt: {receipt_id}")
                submitted.append(s_name)
        except Exception as e:
            print(f"[-] {s_name} 暂存异常: {e}")

    print(f"\n✅ 暂存入库成功: {len(submitted)} / {len(skill_dirs)}")

    # 3. 驱动流水线批处理
    if submitted:
        print("⚙️ 触发后台 Worker 流水线批量入库并固化...")
        p_req = urllib.request.Request(
            f"{BASE_URL}/process-batch?batch_size={len(submitted)}",
            data=b"",
            headers=HEADERS
        )
        try:
            with urllib.request.urlopen(p_req, timeout=30) as resp:
                p_res = json.loads(resp.read().decode("utf-8"))
                summary = p_res.get("worker_summary", {})
                print("🏁 流水线处理结果:\n", json.dumps(summary, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[-] 流水线处理异常: {e}")

if __name__ == "__main__":
    main()
