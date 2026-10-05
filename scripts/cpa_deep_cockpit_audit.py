#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
CPA 高并发全系统悬空功能与虚假断层深度红队审讯器
针对全系统 13 个重点交互座舱/工作台和核心后端服务进行逐个全量审讯
"""

import os
import sys
import json
import time
import re
import urllib.request
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_CPA_URL = os.environ.get("CPA_API_URL", "http://127.0.0.1:8317/v1/chat/completions")

def load_cpa_key() -> str:
    key = os.environ.get("CPA_API_KEY", "")
    if key:
        return key
    conf_path = Path.home() / ".openviking" / "ov.conf"
    if conf_path.is_file():
        try:
            cfg = json.loads(conf_path.read_text(encoding="utf-8"))
            return (
                cfg.get("cpa", {}).get("api_key")
                or cfg.get("llm", {}).get("api_key")
                or cfg.get("vlm", {}).get("api_key")
                or cfg.get("server", {}).get("root_api_key", "")
            )
        except Exception:
            pass
    return ""

CPA_KEY = load_cpa_key()

TARGET_FILES = [
    "src/routes/skills/-components/skill-opt-cockpit.tsx",
    "src/routes/skills/-components/skill-opt-workbench.tsx",
    "src/routes/skills/-components/skill-zip-cockpit.tsx",
    "src/routes/skills/-components/skill-livegen-cockpit.tsx",
    "src/routes/retrieval/-components/llmlingua-dehydration-cockpit.tsx",
    "src/routes/retrieval/-components/tokenshift-cockpit.tsx",
    "src/routes/retrieval/-components/dspy-compiler-cockpit.tsx",
    "src/routes/retrieval/-components/context-router-cockpit.tsx",
    "src/routes/retrieval/-components/entropy-crystallizer-cockpit.tsx",
    "src/routes/retrieval/-components/skill-kd-cockpit.tsx",
    "src/routes/retrieval/-components/bm25-hybrid-cockpit.tsx",
    "src/routes/settings/-components/privacy-tab.tsx",
    "openviking/service/skill_opt_service.py",
    "openviking/service/skill_evolution_pipeline.py",
]

PROMPT = """你是一个严苛的分布式代码与系统架构红队审查专家。
请审查目标代码，判断其是否存在以下 4 类【悬空功能与虚假断层】问题：
1. 【硬编码静态预设/孤岛玩具】：组件仅支持几个写死的静态常数/预设示例（如 PRESETS, DEFAULT_SAMPLE），没有全量实体选择器（如无法从 759 个技能、全量 Wiki 文档、真实代码中选择），成了孤立玩具；
2. 【无真实物理落盘】：操作/采纳仅停留在前端 React state/textarea 中，刷新即丢，缺乏保存回写（Save/Apply to Disk）闭环；
3. 【路径扫描错位与数据失真】：后端只扫描历史旧单层目录（如 ~/.openviking/skills），漏掉 VikingFS 生产落地目录（如 ~/.openviking/data/viking/default/.../skills），导致数量缩水（如 659 vs 759）；
4. 【空动作/伪响应】：按钮或接口只有静态 fallback，没有真实连接底层。

请给出详细判定，必须直接输出纯 JSON（包含以下字段）：
{
  "file_name": "文件名",
  "is_dangling": true,
  "severity": "CRITICAL" | "HIGH" | "MEDIUM",
  "dangling_type": "ISOLATED_PLAYGROUND" | "NO_PERSISTENCE_LOOP" | "PATH_DISCREPANCY" | "FAKE_ACTION",
  "phenomenon": "前端界面看到的表象与操作体验断层",
  "root_cause": "深入物理源码的根因（指明具体变量名/常量名/函数名）",
  "impact": "对用户的危害与业务断层后果",
  "remediation": "彻底根治打通的具体工程方案"
}"""

def audit_file(rel_path: str) -> Dict[str, Any]:
    p = Path(rel_path)
    if not p.exists():
        return {"file": rel_path, "error": "file not found"}
    content = p.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    snippet = "\n".join(lines[:300])

    payload = {
        "model": "mux-flash",
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"请深度审查以下源码文件: {p.name}\n\n```\n{snippet}\n```"}
        ],
        "max_tokens": 1200,
        "temperature": 0.1,
    }

    req = urllib.request.Request(
        DEFAULT_CPA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CPA_KEY}",
        },
        method="POST"
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # 提取 JSON
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                parsed = json.loads(m.group(0))
            else:
                parsed = {"raw": raw}
            return {
                "file": rel_path,
                "name": p.name,
                "elapsed": round(time.perf_counter() - t0, 2),
                "audit": parsed,
                "error": None
            }
    except Exception as exc:
        return {
            "file": rel_path,
            "name": p.name,
            "elapsed": round(time.perf_counter() - t0, 2),
            "audit": None,
            "error": str(exc)
        }

def run_targeted_audit():
    print(f"🚀 启动 CPA 高并发定向深度审计总线 (目标: {len(TARGET_FILES)} 个核心交互与后端服务)...")
    results = []
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(audit_file, f): f for f in TARGET_FILES}
        for fut in as_completed(futures):
            f = futures[fut]
            try:
                res = fut.result()
                results.append(res)
                aud = res.get("audit") or {}
                sev = aud.get("severity", "INFO")
                dtype = aud.get("dangling_type", "UNKNOWN")
                print(f"   [{sev}] {f} ➔ {dtype} (耗时 {res.get('elapsed')}s)")
            except Exception as e:
                print(f"   ❌ {f} error: {e}")

    total_time = round(time.perf_counter() - t_start, 2)
    print(f"\n🎉 CPA 审计全量完成！总耗时: {total_time}s")

    out_file = Path("docs/architecture/DEEP_DANGLING_AUDIT_REPORT.json")
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📄 审计成果已落盘: {out_file}")

if __name__ == "__main__":
    run_targeted_audit()
