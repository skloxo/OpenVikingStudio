# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Watchdog service for entropy inspection and on-demand evaluation (Stage 2.1).

Automated mutation-triggered 5-query storms and unsolicited auto-qg task generation
have been gracefully retired to protect system tranquility and 2080Ti compute stability.
Manual on-demand quality gate sweeps and strategy dispatches remain supported.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger("openviking.entropy_watchdog")

_TASK_DIR_FALLBACK = Path.home() / ".openviking" / "data" / "viking" / "default" / "_system" / "tasks" / "default"

GOLD_QUERIES = [
    "实事求是 伪数据 彻底肃清",
    "入库门禁 占位符 714",
    "Mac Studio launchd 远程运维",
    "NO GREEN EVER 颜色克制",
    "TaskTracker 任务中心 单例",
]


def _resolve_api_key() -> str:
    """Resolve active OpenViking API key from environment, mcp config, or local ov.conf."""
    key = os.environ.get("OPENVIKING_API_KEY")
    if key:
        return key
    mcp_cfg = Path.home() / ".gemini" / "config" / "mcp_config.json"
    if mcp_cfg.exists():
        try:
            with open(mcp_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            env_vars = data.get("mcpServers", {}).get("openviking", {}).get("env", {})
            found = env_vars.get("OPENVIKING_API_KEY") or env_vars.get("OPENVIKING_ROOT_API_KEY")
            if found:
                return found
        except Exception:
            pass
    ov_conf = Path.home() / ".openviking" / "ov.conf"
    if ov_conf.exists():
        try:
            with open(ov_conf, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("api_key"):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _make_task(task_id: str, task_type: str, resource_id: str, created_at: float, meta: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task_id, "task_type": task_type, "status": "completed", "stage": "completed",
        "created_at": created_at, "updated_at": time.time(), "resource_id": resource_id,
        "account_id": "default", "user_id": "default", "meta": meta, "result": result,
        "error": None, "auth": {},
    }


class EntropyWatchdog:
    """Watchdog service for on-demand quality gate evaluation and strategy dispatch."""

    _instance: Optional["EntropyWatchdog"] = None

    def __init__(self) -> None:
        self._running = False
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._cycle_lock: Optional[asyncio.Lock] = None
        self._tracker: Any = None

    @classmethod
    def get_instance(cls) -> "EntropyWatchdog":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_lock(self) -> asyncio.Lock:
        if self._cycle_lock is None:
            self._cycle_lock = asyncio.Lock()
        return self._cycle_lock

    def start(self, task_tracker: Any = None) -> None:
        """Start the watchdog daemon in passive mode (automated storms retired)."""
        if self._running:
            return
        self._running = True
        self._tracker = task_tracker
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("[EntropyWatchdog] Watchdog daemon started in passive mode (auto-qg storm retired)")

    def stop(self) -> None:
        """Stop the background watchdog gracefully."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        logger.info("[EntropyWatchdog] Watchdog daemon stopped")

    def notify_mutation(self, task_type: str = "mutation", resource_id: Optional[str] = None) -> None:
        """Passive mutation hook. Automated 5-query task storm is retired (Stage 2.1)."""
        logger.debug(
            "[EntropyWatchdog] Mutation noted (%s, resource=%s). Automated evaluation is retired.",
            task_type,
            resource_id,
        )

    def notify_zero_hit(self, query: str) -> None:
        """Passive zero-hit hook. Automated task generation is retired."""
        logger.debug("[EntropyWatchdog] Zero-hit query observed: %s", query)

    async def _run_loop(self) -> None:
        """Idle daemon loop. Automated scheduled sweeps are retired to protect background stability."""
        try:
            while self._running:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("[EntropyWatchdog] Loop exit: %s", e)

    async def _run_real_evaluation(self) -> List[Dict[str, Any]]:
        """Run real physical vector search against local port 1933 for gold queries."""
        api_key = _resolve_api_key()
        results: List[Dict[str, Any]] = []

        headers: Dict[str, str] = {
            "X-OpenViking-Account": "default",
            "X-OpenViking-User": "default",
            "X-OpenViking-Internal-Probe": "1",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(trust_env=False, timeout=8.0) as client:
            for q in GOLD_QUERIES:
                t0 = time.time()
                try:
                    resp = await client.post(
                        "http://127.0.0.1:1933/api/v1/search/find",
                        json={"query": q, "limit": 3, "mode": "fast"},
                        headers=headers,
                    )
                    latency_ms = round((time.time() - t0) * 1000, 1)
                    item: Dict[str, Any] = {"query": q, "hit": False, "total": 0, "top_score": 0.0, "top_uri": "", "latency_ms": latency_ms}
                    if resp.status_code == 200:
                        data = resp.json().get("result", {})
                        all_items = data.get("resources", []) + data.get("memories", []) + data.get("skills", [])
                        best = max(all_items, key=lambda x: float(x.get("score", 0.0))) if all_items else None
                        top_score = float(best.get("score", 0.0)) if best else 0.0
                        item.update({
                            "hit": len(all_items) > 0 and top_score > 0.0,
                            "total": data.get("total", len(all_items)),
                            "top_score": round(top_score, 4),
                            "top_uri": best.get("uri", "") if best else "",
                        })
                    else:
                        item["error"] = f"HTTP {resp.status_code}"
                    results.append(item)
                except Exception as e:
                    results.append({"query": q, "hit": False, "total": 0, "top_score": 0.0, "top_uri": "", "latency_ms": round((time.time() - t0) * 1000, 1), "error": str(e)})
        return results

    async def trigger_cycle(self, reason: str = "manual_trigger") -> Dict[str, Any]:
        """Execute on-demand Quality Gate evaluation when explicitly requested."""
        async with self._get_lock():
            now = time.time()
            date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            logger.info("[EntropyWatchdog] Executing on-demand quality gate evaluation (reason=%s)...", reason)

            eval_results = await self._run_real_evaluation()
            total_cases = len(eval_results)
            hits = sum(1 for r in eval_results if r.get("hit"))
            hit_rate = round(hits / total_cases, 3) if total_cases > 0 else 0.0
            avg_top_score = round(sum(r.get("top_score", 0.0) for r in eval_results) / total_cases, 4) if total_cases > 0 else 0.0
            avg_latency = round(sum(r.get("latency_ms", 0.0) for r in eval_results) / total_cases, 1) if total_cases > 0 else 0.0

            fault_cases = [r for r in eval_results if not r.get("hit") or r.get("top_score", 0.0) < 0.50]
            is_healthy = len(fault_cases) == 0 and avg_top_score >= 0.65
            status_verdict = "healthy_pass" if is_healthy else f"drift_detected_{len(fault_cases)}_faults"

            qg_task_id = f"manual-qg-{date_str}-{str(uuid4())[:6]}"
            qg_metrics = {
                "evaluated_cases": total_cases, "total_cases": total_cases,
                "total_queries": total_cases, "completed_queries": total_cases,
                "composite_score": avg_top_score, "hit_rate": hit_rate,
                "avg_latency_ms": avg_latency, "fault_cases_count": len(fault_cases),
                "trigger_source": "EntropyWatchdog", "trigger_reason": reason,
                "query_breakdown": eval_results,
            }
            qg_task = _make_task(
                qg_task_id, "quality_gate", f"viking://benchmark/quality_gate/manual_sweep_{date_str}",
                now - 3.5, qg_metrics, {**qg_metrics, "status_verdict": status_verdict, "query_evaluations": eval_results},
            )
            await self._persist_task(qg_task)
            logger.info("[EntropyWatchdog] Quality gate record created: %s (composite=%.4f)", qg_task_id, avg_top_score)

            return {
                "quality_gate_task_id": qg_task_id,
                "status": "completed",
                "timestamp": now,
                "composite_score": avg_top_score,
                "fault_count": len(fault_cases),
            }

    async def dispatch_entropy_strategy(
        self, strategy: str, target: Optional[str] = None, account_id: str = "default"
    ) -> str:
        from openviking.service.entropy_strategies import dispatch_entropy_strategy
        return await dispatch_entropy_strategy(
            strategy, target, account_id=account_id, persist_fn=self._persist_task
        )

    async def dispatch_memory_dream(self, theme: str = "general_reflection", account_id: str = "default") -> str:
        return await self.dispatch_entropy_strategy("memory_dream", target=theme, account_id=account_id)

    async def dispatch_memory_compaction(self, account_id: str = "default") -> str:
        return await self.dispatch_entropy_strategy("memory_compaction", account_id=account_id)

    async def dispatch_fact_mutation(self, source_doc: str = "session_stream", account_id: str = "default") -> str:
        return await self.dispatch_entropy_strategy("fact_mutation", target=source_doc, account_id=account_id)

    async def dispatch_entity_summarization(self, entity: str = "OpenViking", account_id: str = "default") -> str:
        return await self.dispatch_entropy_strategy("entity_summarization", target=entity, account_id=account_id)

    async def dispatch_four_tier_governance(self, topic: str = "vector_entropy", account_id: str = "default") -> str:
        return await self.dispatch_entropy_strategy("four_tier_governance", target=topic, account_id=account_id)

    async def _persist_task(self, task_dict: Dict[str, Any]) -> None:
        """Persist task record to disk and notify TaskTracker."""
        try:
            _TASK_DIR_FALLBACK.mkdir(parents=True, exist_ok=True)
            task_file = _TASK_DIR_FALLBACK / f"{task_dict['task_id']}.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task_dict, f, ensure_ascii=False, indent=2)

            if self._tracker and hasattr(self._tracker, "_store") and self._tracker._store:
                try:
                    await self._tracker._store.create(task_dict)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("[EntropyWatchdog] Failed to persist task %s: %s", task_dict.get("task_id"), e)


def get_entropy_watchdog() -> EntropyWatchdog:
    """Global accessor for EntropyWatchdog singleton."""
    return EntropyWatchdog.get_instance()
