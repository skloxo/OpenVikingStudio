#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
CPA 教师模型守卫拦截器 (CPA Teacher Model Guard Hook)

定位: PreToolUse 毫秒级物理拦截钩子 (<2ms, 纯标准库, 零依赖)
核心物理契约:
1. 教师模型 (Teacher Models: GPT / Claude 系列，如 gpt-5.6, claude-opus-5, claude-sonnet-5 等) 极度昂贵，
   严格仅限重大架构死锁推导、终极决策仲裁使用，严禁滥用于日常工兵杂活！
2. 工兵任务 (批量扫描、长日志脱水、红队挑刺、文件提取、格式转换等) 必须使用工兵模型池:
   (qwen3.8-flash-next, glm-5.3-flash, mimo-v2.5-pro, deepseek-v4-flash, 小红书工兵模型群等)。
3. 当 Agent 试图在批量工兵任务或日常对抗中调用教师模型时，本 Hook 在工具执行前即刻物理拦截并报错纠偏。
"""

import sys
import json
import re

TEACHER_PATTERNS = [
    re.compile(r"\b(gpt-5|gpt-4|claude-opus|claude-sonnet|claude-3|claude-code)\b", re.I),
    re.compile(r"\b(gpt4|gpt5|claude3|claudeopus|claudesonnet)\b", re.I),
]

WORKER_COMMAND_KEYWORDS = [
    "cpa_worker", "fanout", "batch_scan", "log_extract", "dehydrate"
]


def is_teacher_model(model_name: str) -> bool:
    if not model_name:
        return False
    name_clean = model_name.strip().lower()
    for pattern in TEACHER_PATTERNS:
        if pattern.search(name_clean):
            return True
    return False


def main():
    try:
        raw_input = sys.stdin.read() or "{}"
        payload = json.loads(raw_input)
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return

    tool_call = payload.get("toolCall", {})
    tool_name = (tool_call.get("name") or "").lower()
    tool_args = tool_call.get("args", {})

    if tool_name == "call_mcp_tool":
        sub_tool = (tool_args.get("ToolName") or "").lower()
        sub_args = tool_args.get("Arguments") or {}

        if "fanout" in sub_tool:
            model = str(sub_args.get("model", ""))
            if is_teacher_model(model):
                deny_msg = (
                    "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】\n"
                    f"检测到试图在工兵多路并发 (fanout) 中调用昂贵教师模型: '{model}'！\n"
                    "物理契约：GPT 和 Claude 属于极昂贵的【教师模型】，严禁用于工兵批量杂活！\n"
                    "💡 纠偏方案：工兵并发请使用工兵模型池 (如 qwen3.8-flash-next, glm-5.3-flash, mimo-v2.5-pro, deepseek-v4-flash)。"
                )
                print(json.dumps({"decision": "deny", "reason": deny_msg}, ensure_ascii=False))
                return

        if "consult" in sub_tool:
            mode = str(sub_args.get("mode", "adversarial")).lower()
            model = str(sub_args.get("model", ""))
            if is_teacher_model(model):
                if mode in ("worker", "adversarial", "scan", "extract"):
                    deny_msg = (
                        "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】\n"
                        f"检测到试图在 '{mode}' 模式下调用昂贵教师模型: '{model}'！\n"
                        "物理契约：红蓝对抗与信息脱水属于工兵任务，Token 消耗极大，严禁使用 GPT/Claude 教师模型！\n"
                        "💡 纠偏方案：请改用工兵模型 (如 qwen3.8-flash-next, glm-5.3-flash, mimo-v2.5-pro) 或留空 model 参数以使用默认工兵链。"
                    )
                    print(json.dumps({"decision": "deny", "reason": deny_msg}, ensure_ascii=False))
                    return

    if "cpa_fanout" in tool_name:
        model = str(tool_args.get("model", ""))
        if is_teacher_model(model):
            deny_msg = (
                "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】\n"
                f"检测到试图在工兵多路并发 (fanout) 中调用昂贵教师模型: '{model}'！\n"
                "💡 纠偏方案：请使用工兵模型池 (qwen3.8-flash-next, glm-5.3-flash, mimo-v2.5-pro, deepseek-v4-flash)。"
            )
            print(json.dumps({"decision": "deny", "reason": deny_msg}, ensure_ascii=False))
            return

    if tool_name == "run_command":
        cmd = str(tool_args.get("CommandLine", "")).lower()
        if any(kw in cmd for kw in WORKER_COMMAND_KEYWORDS):
            for pattern in TEACHER_PATTERNS:
                if pattern.search(cmd):
                    deny_msg = (
                        "🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】\n"
                        f"检测到在工兵批量命令中包含了昂贵教师模型参数！\n"
                        "物理契约：GPT 和 Claude 属于极昂贵的【教师模型】，严禁用于工兵批量杂活！\n"
                        "💡 纠偏方案：请换用 qwen3.8-flash-next / glm-5.3-flash / mimo-v2.5-pro 等工兵模型。"
                    )
                    print(json.dumps({"decision": "deny", "reason": deny_msg}, ensure_ascii=False))
                    return

    print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
