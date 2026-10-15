#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
全系统悬空功能与虚假断层自动化审计总线 (CPA High-Concurrency Dangling Feature Auditor)
调度 CPA 多并发工兵模型 (mux-flash)，全盘地毯式排查：
1. 硬编码假数据/静态示例 (Hardcoded Samples / Mocks without DB linking)
2. 缺乏实体选择器/孤岛操作台 (Isolated Workbench without Selector)
3. 路径错位与数据失真 (Path Mismatch, e.g. 659 vs 759)
4. 假按钮与无物理落盘 (Fake Actions / No Backend Mutations)
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

def _load_cpa_key() -> str:
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

CPA_KEY = _load_cpa_key()

AUDIT_PROMPT = """你是一个严苛的代码架构审查与死穴红队分析专家。
请审查以下前端组件或后端接口源码，重点挑刺并排查以下 4 类【悬空功能与虚假断层 (Dangling & Fake Features)】缺陷：

1. 【硬编码假数据与静态示例 (Hardcoded Samples / Mocks)】：
   - 是否硬编码了 DEFAULT_SAMPLE、MOCK 数据、假列表、虚假固定数字？
   - 是否存在组件没有读取真实后端数据，却伪装成真实监控或操作大盘的情况？

2. 【孤岛工作台与缺乏全量选择器 (Isolated Workbench / No Entity Selector)】：
   - 交互工作台是否只能处理写死的 1 个示例，而无法从系统全量资产（例如 759 个全量技能、真实会话列表、真实记忆表）中搜索和自由选择？
   - 是否存在无法载入真实资产进行调优的断层？

3. 【路径错位与数据失真 (Path Discrepancies & Data Distortion)】：
   - 是否硬编码了旧路径（如 ~/.openviking/skills）而遗漏了 VikingFS 生产路径，导致统计数量失真（如 659 vs 759）？
   - 是否存在接口返回假数据或静态 fallback？

4. 【假按钮与无真实物理落盘 (Fake Buttons & No Real Mutations)】：
   - 前端按钮是否只有 console.log、setTimeout、toast 提示，但实际没有调用后端接口？
   - 或者后端接口执行成功后，根本没有物理写入文件或 SQLite 数据库？

【输出格式要求】：
请只输出严格的 JSON 格式（不要包含 markdown 代码块包围，直接输出纯 JSON），字段如下：
{
  "has_dangling_issue": true/false,
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "NONE",
  "issues": [
    {
      "category": "HARDCODED_SAMPLE" | "ISOLATED_WORKBENCH" | "PATH_MISMATCH" | "FAKE_ACTION" | "OTHER",
      "title": "一句话问题描述",
      "detail": "具体缺陷特征与代码依据（指出具体行号或常量名）",
      "impact": "对用户的危害与业务断层后果",
      "remediation": "彻底根治的工程改造方案"
    }
  ]
}
若无任何悬空问题，has_dangling_issue 为 false，issues 为空列表。"""

def call_cpa_audit(file_path: Path, max_tokens: int = 1500) -> Dict[str, Any]:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    # 截取关键代码（前 300 行或 15000 字符）
    sample_content = "\n".join(content.splitlines()[:350])
    
    payload = {
        "model": "mux-flash",
        "messages": [
            {"role": "system", "content": AUDIT_PROMPT},
            {"role": "user", "content": f"【目标待审源码文件: {file_path.name}】:\n```\n{sample_content}\n```"}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    
    req = urllib.request.Request(
        DEFAULT_CPA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CPA_KEY}",
            "User-Agent": "OpenViking-CPA-Auditor/1.0",
        },
        method="POST"
    )
    
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # 清洗可能存在的 markdown 代码块
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
            parsed = json.loads(raw_text)
            elapsed = time.perf_counter() - t0
            return {
                "file": str(file_path),
                "name": file_path.name,
                "elapsed_sec": round(elapsed, 2),
                "data": parsed,
                "error": None
            }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return {
            "file": str(file_path),
            "name": file_path.name,
            "elapsed_sec": round(elapsed, 2),
            "data": None,
            "error": str(exc)
        }

if __name__ == "__main__":
    print("CPA Dangling Feature Auditor ready.")
