#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
CPA 工兵分包调度器 (CPA Worker Subcontract Dispatcher)
专用于将机械体力活、红蓝对抗找茬、测试用例批量生成、长日志脱水分包给廉价/海量 Token 工兵模型。
【铁律】：严禁调用昂贵的教师模型 (GPT / Claude)，违者物理阻断并自动回退为千问/GLM工兵！
"""

import os
import sys
import json
import time
import argparse
import urllib.request
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 纯工兵模型池（海量 Token，随便用）
AUTHORIZED_WORKER_MODELS = [
    {"model": "qwen3.8-flash-next", "timeout": 25, "slice": 25000},
    {"model": "glm-5.3-flash", "timeout": 25, "slice": 25000},
    {"model": "mimo-v2.5-pro", "timeout": 30, "slice": 30000},
    {"model": "deepseek-v4-flash", "timeout": 20, "slice": 20000},
]

# 昂贵教师模型黑名单（工兵调度器物理封杀）
BANNED_TEACHER_PATTERNS = ["gpt", "claude", "opus", "sonnet", "o1", "o3"]

DEFAULT_CPA_URL = os.environ.get("CPA_API_URL", "http://127.0.0.1:8317/v1/chat/completions")


def _load_cpa_key() -> str:
    key = os.environ.get("CPA_API_KEY", "")
    if key:
        return key
    conf_path = Path.home() / ".openviking" / "ov.conf"
    if conf_path.is_file():
        try:
            cfg = json.loads(conf_path.read_text(encoding="utf-8"))
            return cfg.get("server", {}).get("root_api_key", "")
        except Exception:
            pass
    return "vk-local-worker-key"


def call_cpa_worker_single(prompt: str, content: str, task_name: str = "") -> Dict[str, Any]:
    """Dispatch single task to worker fallback chain."""
    url = DEFAULT_CPA_URL
    api_key = _load_cpa_key()

    full_content = f"【工兵任务指令】：{prompt}\n\n【待处理上下文 ({task_name})】：\n{content}"

    for idx, worker_info in enumerate(AUTHORIZED_WORKER_MODELS):
        model_name = worker_info["model"]
        timeout_sec = worker_info["timeout"]
        max_slice = worker_info["slice"]

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个极速、高密度的信息脱水与自动化测试工兵。请按指令处理输入，直接输出高度结构化、无客套废话的成果物。"
                },
                {"role": "user", "content": full_content[:max_slice]}
            ],
            "max_tokens": 2000,
            "temperature": 0.2,
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "OpenViking-CPA-Worker/1.5",
                },
                method="POST",
            )
            start_t = time.perf_counter()
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["choices"][0]["message"]["content"].strip()
                cost_ms = round((time.perf_counter() - start_t) * 1000, 1)
                return {
                    "status": "ok",
                    "model": model_name,
                    "content": ans,
                    "latency_ms": cost_ms,
                    "retry_depth": idx,
                }
        except Exception as e:
            # Try next worker model
            continue

    return {"status": "fail", "error": "所有工兵模型均响应异常或超时"}


def dispatch_subcontract(prompt: str, files_or_texts: List[str], concurrency: int = 6) -> str:
    """Dispatch batch work to worker models concurrently."""
    print(f"🚀 [CPA 工兵总包分派] 正在分包派发 {len(files_or_texts)} 个任务 (并发度: {concurrency})...")
    results = []

    def task_wrapper(item: str) -> Dict[str, Any]:
        p = Path(item)
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")
            title = p.name
        else:
            text = item
            title = item[:30]
        res = call_cpa_worker_single(prompt, text, title)
        res["target"] = item
        return res

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(task_wrapper, it): it for it in files_or_texts}
        for fut in as_completed(futures):
            results.append(fut.result())

    lines = [f"## ⚡ CPA 工兵分包执行报告 (完成 {len(results)}/{len(files_or_texts)} 项)\n"]
    for r in results:
        status_icon = "✅" if r.get("status") == "ok" else "❌"
        m = r.get("model", "none")
        ms = r.get("latency_ms", 0)
        lines.append(f"### {status_icon} 目标: `{r.get('target')}` (模型: `{m}` · 耗时: {ms}ms)")
        lines.append(r.get("content") or r.get("error", "未知错误"))
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPA 工兵分包调度器 (Strictly Worker Models)")
    parser.add_argument("prompt", help="工兵任务提示词 (如: 红蓝对抗找茬、生成测试用例、长日志脱水)")
    parser.add_argument("--files", "-f", nargs="+", help="待处理的目标文件或文本片段")
    parser.add_argument("--concurrency", "-c", type=int, default=6, help="并发工兵数 (默认 6)")
    args = parser.parse_args()

    target_items = args.files if args.files else [sys.stdin.read()]
    output = dispatch_subcontract(args.prompt, target_items, args.concurrency)
    print(output)
