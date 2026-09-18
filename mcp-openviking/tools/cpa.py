# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
# ─── MODULE: tools.cpa ───────────────────────────────────────────────────
"""
用途: CPA 弹性统一算力总线与智能体参谋团 (MCP 工具层)
功能:
- openviking_cpa_consult: 参谋咨询 / 红蓝对抗 / 决策仲裁 / 多视角会诊
- openviking_cpa_fanout: 工兵多路温和并发处理 (文件审查、摘要提取、批量诊断)
依赖: 标准库 (urllib, json, concurrent.futures, pathlib, os, time)
被调用: mcp_openviking_server.py
"""

import os
import sys
import json
import time
import logging
import urllib.request
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import Field
from mcp.server.fastmcp import FastMCP

from _core.config import _make_error
from .observability import _record_harness_call

logger = logging.getLogger("openviking-mcp")

DEFAULT_CPA_URL = os.environ.get("CPA_API_URL", "http://127.0.0.1:8317/v1/chat/completions")

# 昂贵教师模型守卫名单与正则特征 (GPT 家族、Claude Opus 家族、OpenAI 推理模型家族)
TEACHER_MODEL_PATTERNS = [
    re.compile(r"gpt-(?:5|4|o[13]|4o)", re.IGNORECASE),
    re.compile(r"chatgpt-4o", re.IGNORECASE),
    re.compile(r"o[13](?:-mini|-preview|-pro)?\b", re.IGNORECASE),
    re.compile(r"claude-(?:[3-5](?:\.\d+)?-)?opus", re.IGNORECASE),
    re.compile(r"claude-opus", re.IGNORECASE),
]

# 受限/避免在工兵任务中调用的模型 (小米 MiMO 系列：商业付费 Token 且极易 429 限速)
RESTRICTED_MODEL_PATTERNS = [
    re.compile(r"mimo", re.IGNORECASE),
    re.compile(r"xiaomimimo", re.IGNORECASE),
]


def is_teacher_model(model_name: str) -> bool:
    """判定是否为昂贵受限的‘教师模型’ (Teacher Model)"""
    if not model_name:
        return False
    name = model_name.strip()
    return any(p.search(name) for p in TEACHER_MODEL_PATTERNS)


def is_restricted_model(model_name: str) -> bool:
    """判定是否为工兵任务受限模型 (如商业付费且易限速的小米 MiMO)"""
    if not model_name:
        return False
    name = model_name.strip()
    return any(p.search(name) for p in RESTRICTED_MODEL_PATTERNS)


MODEL_FALLBACK_CHAINS = {
    # 👷 工兵模型池（海量 Token，免费高吞吐抗造，由 CPA 自动负载均衡与多通道容灾）
    # 真实模型名备选：dots3-note-prev, agnes-3.0-flash, DeepSeek-V4-Flash-Vision-Exp, Qwen3.8-Flash-Next, DeepSeek-V4-Flash, sensenova-6.8-flash-lite
    "worker": [
        {"model": "mux-flash", "timeout": 20, "slice": 25000},
        {"model": "dots3-note-prev", "timeout": 20, "slice": 25000},
        {"model": "agnes-3.0-flash", "timeout": 20, "slice": 25000},
        {"model": "Qwen3.8-Flash-Next", "timeout": 20, "slice": 25000},
        {"model": "DeepSeek-V4-Flash", "timeout": 20, "slice": 20000},
        {"model": "sensenova-6.8-flash-lite", "timeout": 20, "slice": 20000},
    ],
    # 🧠 教师模型池（极昂贵，仅限重大死锁、终极架构仲裁或多脑终审会诊，严禁滥用）
    "mentor": [
        {"model": "claude-opus-5", "timeout": 25},
        {"model": "gpt-5.6", "timeout": 25},
        {"model": "deepseek-v4-pro", "timeout": 25},
    ],
}

SYSTEM_PROMPTS = {
    "consult": "你作为系统顶级分布式架构师。请直击底层物理本质与数学/逻辑根因，给出最优解耦设计，严禁废话。",
    "adversarial": (
        "【红队严苛审查员】毫不留情挑刺方案，严禁客套！"
        "指出至少3个致命隐患：1.并发竞态与死锁 2.内存泄漏与状态膨胀 3.异常静默降级 4.破坏性变更。逐条说明后果与防御手段。"
    ),
    "council": "你作为系统参谋专家。请基于你的独特模型体系与工程哲学，对用户提出的复杂问题给出深刻见解与最佳建议。",
    "tradeoff": "你作为决策仲裁专家。请客观输出核心维度对比表（复杂度、运行时开销、破坏性、可维护性），指出各自最大隐患与终审建议。",
    "worker": "你是一个极速、高密度的信息脱水与审查工兵。请按指令处理输入，直接输出高度结构化、无客套废话的脱水成果物。",
}


WORKER_MODEL_HINT = (
    "💡 正确工兵模型：\n"
    "  • 平时统一调用工兵别名：'mux-flash'\n"
    "  • 需区分物理真实模型时：'dots3-note-prev', 'agnes-3.0-flash', 'DeepSeek-V4-Flash-Vision-Exp', "
    "'Qwen3.8-Flash-Next', 'DeepSeek-V4-Flash', 'sensenova-6.8-flash-lite'"
)


def _load_cpa_key() -> str:
    key = os.environ.get("CPA_API_KEY", "")
    if key:
        return key
    conf_path = Path.home() / ".openviking" / "ov.conf"
    if conf_path.exists():
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return (
                    data.get("cpa", {}).get("api_key")
                    or data.get("vlm", {}).get("api_key")
                    or data.get("llm", {}).get("api_key")
                    or ""
                )
        except Exception:
            pass
    return ""


def _call_cpa_raw(
    prompt: str,
    model: str,
    sys_prompt: str,
    timeout: int = 25,
    max_tokens: int = 2000,
    base_url: str = DEFAULT_CPA_URL,
) -> str:
    key = _load_cpa_key()
    if not key:
        raise RuntimeError("未在环境变量 CPA_API_KEY 或 ~/.openviking/ov.conf 中配置 CPA API Key")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    req = urllib.request.Request(
        base_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"Empty choices from CPA model {model}")
        msg = choices[0].get("message", {})
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()


def register_cpa_tools(mcp: FastMCP, mcp_tool: Callable) -> Dict[str, Any]:
    registered: Dict[str, Any] = {}

    @mcp_tool()
    def openviking_cpa_consult(
        topic: str = Field(description="咨询主题、架构疑问或代码设计方案"),
        context: str = Field(default="", description="可选相关代码切片、配置、报错日志或背景说明"),
        mode: str = Field(
            default="adversarial",
            description="参谋模式：adversarial (红队对抗挑刺) / consult (顶级架构师) / council (多模型会诊) / tradeoff (架构仲裁)",
        ),
        model: str = Field(default="", description="可选指定主试模型（留空则按 mentor 链自动降级调度）"),
    ) -> str:
        """【CPA 智囊参谋与对抗研讨】调度强大模型进行深度架构推导、红蓝对抗找茬或多模型会诊"""
        if not isinstance(context, str):
            context = ""
        if not isinstance(mode, str):
            mode = "adversarial"
        if not isinstance(model, str):
            model = ""

        _record_harness_call("cpa_consult", actor_peer="cpa")

        if model and is_teacher_model(model):
            if mode in ("adversarial", "worker", "scan", "extract"):
                _record_harness_call("teacher_guard_intercept", actor_peer="cpa")
                return _make_error(
                    f"🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】\n"
                    f"检测到试图在 '{mode}' 模式下调用昂贵教师模型 '{model}'！\n"
                    "物理契约：红蓝对抗与信息脱水属于工兵任务，Token 消耗巨大，严禁使用 GPT/Claude 教师模型！\n"
                    f"{WORKER_MODEL_HINT}"
                )

        if model and is_restricted_model(model):
            if mode in ("adversarial", "worker", "scan", "extract"):
                _record_harness_call("restricted_guard_intercept", actor_peer="cpa")
                return _make_error(
                    f"🚫 【CPA 受限模型守卫拦截 (Restricted Model Guard)】\n"
                    f"检测到试图在 '{mode}' 工兵模式下调用受限模型 '{model}'！\n"
                    "物理契约：小米 MiMO 属于商业付费 API 且极易 429 限速，严禁用于工兵杂活！\n"
                    f"{WORKER_MODEL_HINT}"
                )

        full_prompt = f"【主题/方案】：\n{topic}\n"
        if context:
            full_prompt += f"\n【参考上下文/代码/日志】：\n{context}\n"

        if mode == "council":
            models = ["claude-opus-5", "deepseek-v4-pro"]
            results: Dict[str, str] = {}
            executor = ThreadPoolExecutor(max_workers=len(models))
            futures = {
                executor.submit(_call_cpa_raw, full_prompt, m, SYSTEM_PROMPTS["council"], 25, 2000): m
                for m in models
            }
            try:
                for fut in as_completed(futures, timeout=35.0):
                    m = futures[fut]
                    try:
                        results[m] = fut.result()
                    except Exception as e:
                        results[m] = f"[调用跳过/降级]: {e}"
            except TimeoutError:
                for _, m in futures.items():
                    if m not in results:
                        results[m] = "[超时熔断: 超过35s未响应，自动放弃以保全生命线]"
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            lines = ["## 🧠 CPA 多模型参谋团研讨汇总 (Multi-Perspective Council)\n"]
            for m, r in results.items():
                lines.append(f"### 视角：`{m}`\n{r}\n")
            return "\n".join(lines)

        sys_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["consult"])
        # 红队对抗优先使用工兵模型群（速度快、Token海量，不耗贵模型）；架构咨询使用导师链
        chain = MODEL_FALLBACK_CHAINS["worker"] if mode == "adversarial" else MODEL_FALLBACK_CHAINS["mentor"]
        if model:
            chain = [{"model": model, "timeout": 25}] + chain

        last_err = None
        for step in chain:
            m = str(step["model"])
            t = int(step["timeout"])
            try:
                ans = _call_cpa_raw(full_prompt, m, sys_prompt, timeout=t, max_tokens=2500)
                if ans:
                    return f"### 🧠 CPA 参谋回复 (`{m}` · 模式: `{mode}`)\n\n{ans}"
            except Exception as e:
                last_err = e
                logger.warning(f"[CPA Consult] 模型 {m} 异常({e})，降级到下一候选...")
                time.sleep(0.3)

        return _make_error(f"所有参谋模型尝试失败 ({last_err})，请检查 CPA 代理服务连通性。")

    registered["openviking_cpa_consult"] = openviking_cpa_consult

    @mcp_tool()
    def openviking_cpa_fanout(
        prompt: str = Field(description="工兵批量处理任务指令（如：检查并发死锁、提纯L0摘要、排查隐藏Bug）"),
        items: List[str] = Field(description="待处理的文件路径列表或文本片段列表"),
        concurrency: int = Field(default=8, description="并发路数（有效范围 1~15，默认 8）"),
        total_timeout: float = Field(default=45.0, description="全局硬看门狗超时时间（秒，默认 45s）"),
        worker_model: str = Field(default="", description="可选指定具体工兵模型（默认使用工兵降级链，严禁使用 GPT/Claude 教师模型）"),
    ) -> str:
        """【CPA 工兵多路并发处理】以温和并发度 (≤15路) 批量吞吐海量文件审查、代码提纯或多点排查"""
        if not items:
            return _make_error("items 列表不能为空")

        if not isinstance(concurrency, int):
            concurrency = 8
        if not isinstance(total_timeout, (int, float)):
            total_timeout = 45.0
        if not isinstance(worker_model, str):
            worker_model = ""

        _record_harness_call("cpa_fanout", actor_peer="cpa")

        if worker_model and is_teacher_model(worker_model):
            _record_harness_call("teacher_guard_intercept", actor_peer="cpa")
            return _make_error(
                f"🚫 【CPA 教师模型守卫拦截 (Teacher Model Guard)】\n"
                f"检测到试图在工兵多路并发 (fanout) 中调用昂贵教师模型 '{worker_model}'！\n"
                "物理契约：工兵多路并发严禁混入任何昂贵教师模型 (GPT / Claude)！\n"
                f"{WORKER_MODEL_HINT}"
            )

        if worker_model and is_restricted_model(worker_model):
            _record_harness_call("restricted_guard_intercept", actor_peer="cpa")
            return _make_error(
                f"🚫 【CPA 受限模型守卫拦截 (Restricted Model Guard)】\n"
                f"检测到试图在工兵多路并发 (fanout) 中调用受限模型 '{worker_model}'！\n"
                "物理契约：小米 MiMO 属于商业付费 API 且极易 429 限速，严禁用于工兵批量任务！\n"
                f"{WORKER_MODEL_HINT}"
            )

        actual_concurrency = max(1, min(concurrency, 15))
        results = []

        def worker_unit(item: str) -> Dict[str, Any]:
            p = Path(item)
            content = p.read_text(encoding="utf-8", errors="ignore") if p.is_file() else item
            item_name = p.name if p.is_file() else (item[:30] + "..." if len(item) > 30 else item)

            worker_chain = MODEL_FALLBACK_CHAINS["worker"]
            if worker_model:
                worker_chain = [{"model": worker_model, "timeout": 20, "slice": 25000}] + worker_chain

            for idx, step in enumerate(worker_chain):
                m = str(step["model"])
                t = int(step["timeout"])
                s = int(step["slice"])
                sub_prompt = f"【处理任务】：{prompt}\n\n【待处理目标 ({item_name})】：\n{content[:s]}"
                try:
                    ans = _call_cpa_raw(sub_prompt, m, SYSTEM_PROMPTS["worker"], timeout=t, max_tokens=1500)
                    if ans:
                        return {"item": item, "status": "ok", "content": ans, "model": m, "retry": idx}
                except Exception as e:
                    logger.debug(f"[CPA Worker] {item_name} 模型 {m} 失败: {e}，重试降级...")
                    time.sleep(0.3)

            return {"item": item, "status": "fail", "error": "所有降级模型均超时或异常"}

        executor = ThreadPoolExecutor(max_workers=actual_concurrency)
        futures = {executor.submit(worker_unit, it): it for it in items}

        try:
            for fut in as_completed(futures, timeout=total_timeout):
                results.append(fut.result())
        except TimeoutError:
            logger.warning(f"[CPA Fanout] 触发全局 {total_timeout}s 保护上限，熔断未完成任务以保全生命线！")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # 整理脱水汇报
        lines = [f"## ⚡ CPA 工兵并发脱水报告 (完成 {len(results)}/{len(items)} 项，并发度: {actual_concurrency})\n"]
        for r in results:
            tag = "✅" if r.get("status") == "ok" else "❌"
            m_tag = f"(`{r.get('model', 'none')}`)" if r.get("status") == "ok" else ""
            lines.append(f"### {tag} 目标: `{r.get('item')}` {m_tag}\n")
            lines.append(f"{r.get('content') or r.get('error')}\n")

        if len(results) < len(items):
            lines.append(f"\n> ⚠️ 剩余 {len(items) - len(results)} 项因全局超时 ({total_timeout}s) 自动熔断保全。")

        return "\n".join(lines)

    registered["openviking_cpa_fanout"] = openviking_cpa_fanout

    return registered
