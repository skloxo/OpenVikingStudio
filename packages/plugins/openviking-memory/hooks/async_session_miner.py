#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking 异步会话脱水与记忆挖掘 Worker (v2.0.42 - Async Session Miner)

职责：
1. 运行于独立脱钩后台子进程中，完全不阻塞 IDE 心流与 Stop 钩子 3s 超时门禁；
2. 扫描 transcript.jsonl，识别会话执行结果、排障因果链与 Master Memory 对账单；
3. 若发现未对账的高价值踩坑或新规，自动汇总生成 Candidate 知识元并记录审计日志；
4. 严格遵守 NO GREEN EVER 与单文件预算门禁，零噪音静默运行。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# SECTION: UTF-8 Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = PLUGIN_DIR / "config.json"
CACHE_FILE = PLUGIN_DIR / ".miner_cache.json"
LOG_FILE = PLUGIN_DIR / "session_miner.log"


def log(msg: str) -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [SessionMiner] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def load_config() -> Tuple[str, str]:
    api = os.environ.get("OPENVIKING_API", "").strip()
    key = os.environ.get("OPENVIKING_API_KEY", "").strip()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if not api:
                    api = cfg.get("api_url", "").strip()
                if not key:
                    key = cfg.get("api_key", "").strip()
        except Exception:
            pass
    return api or "http://127.0.0.1:1933", key


def load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: Dict[str, Any]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def analyze_transcript(transcript_path: Path) -> Dict[str, Any]:
    """脱水分析 transcript.jsonl，提取对账单、工具报错及自愈事实"""
    if not transcript_path.exists():
        return {"error": "transcript_not_found"}

    lines: List[Dict[str, Any]] = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if raw_line:
                    try:
                        lines.append(json.loads(raw_line))
                    except Exception:
                        continue
    except Exception as e:
        return {"error": f"read_error: {e}"}

    total_steps = len(lines)
    has_ledger = False
    ledger_content = ""
    had_error = False
    error_summary = []
    resolved_in_turn = False
    green_violations = []

    for entry in lines:
        content = str(entry.get("content") or "")
        # 1. 检查是否有对账单
        if "体外大脑对账单" in content or "Master Memory Ledger" in content:
            has_ledger = True
            ledger_content = content

        # 2. 检查是否有执行报错
        status = entry.get("status")
        if status in ("ERROR", "FAILED") or "Command exited with code 1" in content:
            had_error = True
            if len(error_summary) < 3:
                snippet = content[:150].replace("\n", " ").strip()
                error_summary.append(snippet)

        # 3. 检查是否有 NO GREEN EVER 违规词 (脏记忆扫描)
        if re.search(r"#4ade80|Terminal Neon Green|荧光绿", content):
            green_violations.append(entry.get("step_index", 0))

    if had_error and lines and lines[-1].get("status") in ("DONE", "OK"):
        resolved_in_turn = True

    return {
        "total_steps": total_steps,
        "has_ledger": has_ledger,
        "had_error": had_error,
        "error_summary": error_summary,
        "resolved_in_turn": resolved_in_turn,
        "green_violations_count": len(green_violations),
        "last_step_index": lines[-1].get("step_index", 0) if lines else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="OpenViking Async Session Miner")
    parser.add_argument("--transcript", type=str, required=True, help="Path to transcript.jsonl")
    args = parser.parse_args()

    transcript_path = Path(args.transcript).resolve()
    api, key = load_config()

    cache = load_cache()
    cached_session = cache.get(str(transcript_path), {})
    last_processed = cached_session.get("last_step_index", -1)

    result = analyze_transcript(transcript_path)
    if "error" in result:
        log(f"跳过处理: {result['error']} ({transcript_path})")
        return

    current_last_step = result["last_step_index"]
    if current_last_step <= last_processed:
        # 无增量步数，静默退出
        return

    # 更新缓存进度
    cache[str(transcript_path)] = {
        "last_step_index": current_last_step,
        "timestamp": time.time(),
        "has_ledger": result["has_ledger"],
        "resolved_error": result["resolved_in_turn"],
    }
    save_cache(cache)

    log(
        f"会话扫描完成: steps={result['total_steps']}, "
        f"has_ledger={result['has_ledger']}, "
        f"had_error={result['had_error']}, "
        f"self_healed={result['resolved_in_turn']}"
    )

    # 脏记忆警报
    if result["green_violations_count"] > 0:
        log(f"⚠️ [NO GREEN EVER 警报] 检测到 {result['green_violations_count']} 处疑似绿色历史色值提及！")

    # 若未出具对账单但修复了疑难错误，记录候选题材以便沉淀
    if result["had_error"] and result["resolved_in_turn"] and not result["has_ledger"]:
        pending_dir = PLUGIN_DIR / "pending_harvest"
        pending_dir.mkdir(parents=True, exist_ok=True)
        session_id = transcript_path.parent.name
        record_file = pending_dir / f"harvest_{session_id}.json"
        try:
            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "session_id": session_id,
                        "transcript_path": str(transcript_path),
                        "timestamp": datetime.datetime.now().isoformat(),
                        "error_summary": result["error_summary"],
                        "note": "检测到会话成功自愈报错但未显式写入体外大脑，已加入待结晶对账队列",
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            log(f"📌 已生成未回填经验候选题材: {record_file.name}")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"运行异常: {e}")
    sys.exit(0)
