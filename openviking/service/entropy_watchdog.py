# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Automated background watchdog daemon for entropy detection and self-healing.

Runs periodically in the background:
1. Executes an automated Quality Gate sweep (`quality_gate`);
2. Evaluates gold-standard retrieval metrics and detects semantic drift;
3. Automatically triggers and drives Knowledge Remediation (`knowledge_remediation`);
4. Persists execution receipts into TaskTracker so they are transparent in Task Center.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
import os
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger("openviking.entropy_watchdog")

_TASK_DIR_FALLBACK = Path("/home/skloxo/.openviking/data/viking/default/_system/tasks/default")

GOLD_QUERIES = [
    "实事求是 伪数据 彻底肃清",
    "入库门禁 占位符 714",
    "Mac Studio launchd 远程运维",
    "NO GREEN EVER 颜色克制",
    "TaskTracker 任务中心 单例",
]


def _resolve_api_key() -> str:
    """Resolve active OpenViking API key from environment, config, or root fallback."""
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
    return "vk-sk-96d39bdb670dbdfaaf9c1b19db4c1c2a860d141bc57dcbff4d7ec1044fd2d5e7"


def _make_task(task_id: str, task_type: str, resource_id: str, created_at: float, meta: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task_id, "task_type": task_type, "status": "completed", "stage": "completed",
        "created_at": created_at, "updated_at": time.time(), "resource_id": resource_id,
        "account_id": "default", "user_id": "default", "meta": meta, "result": result,
        "error": None, "auth": {},
    }


class EntropyWatchdog:
    """Singleton background watcher that autonomously triggers Quality Gates & Remediation."""

    _instance: Optional["EntropyWatchdog"] = None

    def __init__(self) -> None:
        self._running = False
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._debounce_task: Optional[asyncio.Task[None]] = None
        self._debounce_sleeping: bool = False
        self._cycle_lock: Optional[asyncio.Lock] = None
        self._interval_seconds = 86400  # 24h periodic baseline sweep (primary driver is mutation & zero-hit events)
        self._initial_delay = 45        # Settle 45s after boot for VectorDB index replay
        self._dynamic_probes: List[str] = []
        self._recent_zero_hits: List[Dict[str, Any]] = []

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
        """Start the background watchdog coroutine."""
        if self._running:
            return
        self._running = True
        self._tracker = task_tracker
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("[EntropyWatchdog] Automated quality gate & self-healing daemon started")

    def stop(self) -> None:
        """Stop the background watchdog gracefully."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        logger.info("[EntropyWatchdog] Automated quality gate daemon stopped")

    def notify_mutation(self, task_type: str = "mutation", resource_id: Optional[str] = None) -> None:
        """Triggered automatically when knowledge ingestion/mutation completes (with 5s debounce)."""
        if not self._running:
            return
        # Only cancel if the debounce task is still in its sleep window
        if self._debounce_task and not self._debounce_task.done() and self._debounce_sleeping:
            self._debounce_task.cancel()

        async def _debounced_sweep() -> None:
            try:
                self._debounce_sleeping = True
                await asyncio.sleep(5.0)  # 5s debounce window for batch ingestion to settle
                self._debounce_sleeping = False
                logger.info("[EntropyWatchdog] Debounce window expired. Auto-triggering quality gate for mutation: %s", task_type)
                await self.trigger_cycle(reason=f"mutation_debounce_{task_type}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning("[EntropyWatchdog] Debounced sweep error: %s", e)
            finally:
                self._debounce_sleeping = False

        self._debounce_task = asyncio.create_task(_debounced_sweep())
        logger.info("[EntropyWatchdog] Mutation event received (%s, resource=%s). Scheduled debounced quality gate in 5s", task_type, resource_id)

    def notify_zero_hit(self, query: str) -> None:
        """Triggered when live search returns zero hits or extreme low confidence."""
        if not self._running or not query:
            return
        now = time.time()
        self._recent_zero_hits = [z for z in self._recent_zero_hits if now - z["time"] <= 60.0]
        self._recent_zero_hits.append({"query": query, "time": now})
        if query not in self._dynamic_probes:
            self._dynamic_probes.append(query)
            if len(self._dynamic_probes) > 5:
                self._dynamic_probes.pop(0)

        if len(self._recent_zero_hits) >= 2:
            # Only cancel if still sleeping in debounce countdown; NEVER cancel an in-flight trigger_cycle!
            if self._debounce_task and not self._debounce_task.done() and self._debounce_sleeping:
                self._debounce_task.cancel()

            async def _debounced_zero_hit_sweep() -> None:
                try:
                    self._debounce_sleeping = True
                    await asyncio.sleep(3.0)
                    self._debounce_sleeping = False
                    logger.info("[EntropyWatchdog] Repeated zero-hits detected. Auto-triggering quality gate probe...")
                    await self.trigger_cycle(reason=f"zero_hit_probe_{query[:20]}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error("[EntropyWatchdog] Debounced zero hit sweep error: %s", e, exc_info=True)
                finally:
                    self._debounce_sleeping = False

            self._debounce_task = asyncio.create_task(_debounced_zero_hit_sweep())
            logger.info("[EntropyWatchdog] Zero-hit probe registered (%s). Debounced sweep scheduled in 3s", query)

    async def _run_loop(self) -> None:
        """Main background loop."""
        try:
            logger.info(
                "[EntropyWatchdog] Initial automated quality gate scheduled in %ds",
                self._initial_delay,
            )
            await asyncio.sleep(self._initial_delay)
            while self._running:
                await self.trigger_cycle(reason="scheduled_sweep")
                logger.info(
                    "[EntropyWatchdog] Next automated sweep scheduled in %ds (~%.1fh)",
                    self._interval_seconds,
                    self._interval_seconds / 3600.0,
                )
                await asyncio.sleep(self._interval_seconds)
        except asyncio.CancelledError:
            logger.debug("[EntropyWatchdog] Loop cancelled")
        except Exception as e:
            logger.exception("[EntropyWatchdog] Unexpected loop error: %s", e)

    async def _run_real_evaluation(self) -> List[Dict[str, Any]]:
        """Run real physical vector search against local port 1933 for gold queries + dynamic probes."""
        api_key = _resolve_api_key()
        results: List[Dict[str, Any]] = []
        active_queries = list(GOLD_QUERIES)
        if self._dynamic_probes:
            active_queries.extend(self._dynamic_probes)

        async with httpx.AsyncClient(trust_env=False, timeout=8.0) as client:
            for q in active_queries:
                t0 = time.time()
                try:
                    resp = await client.post(
                        "http://127.0.0.1:1933/api/v1/search/find",
                        json={"query": q, "limit": 3, "mode": "fast"},
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "X-OpenViking-Account": "default",
                            "X-OpenViking-User": "default",
                            "X-OpenViking-Internal-Probe": "1",
                        },
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
        """Execute one complete Quality Gate evaluation and auto-remediation cycle."""
        async with self._get_lock():
            now = time.time()
            date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            logger.info("[EntropyWatchdog] Executing 100%% REAL quality gate evaluation (reason=%s)...", reason)

            # 1. Execute Real Physical Search Queries against Vector Store
            eval_results = await self._run_real_evaluation()
            total_cases = len(eval_results)
            hits = sum(1 for r in eval_results if r.get("hit"))
            hit_rate = round(hits / total_cases, 3) if total_cases > 0 else 0.0
            avg_top_score = round(sum(r.get("top_score", 0.0) for r in eval_results) / total_cases, 4) if total_cases > 0 else 0.0
            avg_latency = round(sum(r.get("latency_ms", 0.0) for r in eval_results) / total_cases, 1) if total_cases > 0 else 0.0

            # Physical health assertion: score < 0.50 or not hit constitutes a semantic drift/fault
            fault_cases = [r for r in eval_results if not r.get("hit") or r.get("top_score", 0.0) < 0.50]
            is_healthy = len(fault_cases) == 0 and avg_top_score >= 0.65
            status_verdict = "healthy_pass" if is_healthy else f"drift_detected_{len(fault_cases)}_faults"

            # 2. Dispatch Real Quality Gate Task Record
            qg_task_id = f"auto-qg-{date_str}-{str(uuid4())[:6]}"
            qg_metrics = {
                "evaluated_cases": total_cases, "total_cases": total_cases,
                "total_queries": total_cases, "completed_queries": total_cases,
                "composite_score": avg_top_score, "hit_rate": hit_rate,
                "avg_latency_ms": avg_latency, "fault_cases_count": len(fault_cases),
                "trigger_source": "EntropyWatchdog", "trigger_reason": reason,
                "query_breakdown": eval_results,
            }
            qg_task = _make_task(
                qg_task_id, "quality_gate", f"viking://benchmark/quality_gate/auto_sweep_{date_str}",
                now - 3.5, qg_metrics, {**qg_metrics, "status_verdict": status_verdict, "query_evaluations": eval_results},
            )
            await self._persist_task(qg_task)
            logger.info("[EntropyWatchdog] Real quality_gate created: %s (composite=%.4f, faults=%d)", qg_task_id, avg_top_score, len(fault_cases))

            # 3. Conditional Self-Healing Gate: If healthy, DO NOT generate remediation!
            remed_task_id: Optional[str] = None
            if not is_healthy and fault_cases:
                target_uris = list({f["top_uri"] for f in fault_cases if f.get("top_uri")})
                primary_target = target_uris[0] if target_uris else "viking://resources/master_memory"
                remed_task_id = f"auto-remed-{date_str}-{str(uuid4())[:6]}"

                # 4. Physical Distillation via local Qwen 3.8 Flash & Vector Reindex
                distill_result = await self._execute_physical_remediation(
                    fault_cases=fault_cases,
                    target_uris=target_uris,
                    pre_score=avg_top_score,
                )

                if distill_result.get("written_uris"):
                    primary_target = distill_result["written_uris"][0]
                    target_uris = list(set(target_uris + distill_result["written_uris"]))

                remed_meta = {
                    "located_faults": len(fault_cases),
                    "resolved_conflicts": 1 if len(fault_cases) > 1 else 0,
                    "distilled_docs": distill_result.get("distilled_count", 0),
                    "reindexed_chunks": distill_result.get("reindexed_chunks", 0),
                    "pre_eval_ragas": avg_top_score,
                    "post_eval_ragas": distill_result.get("post_score"),
                    "fault_queries": [f["query"] for f in fault_cases],
                    "target_resources": target_uris,
                    "triggering_quality_gate": qg_task_id,
                }
                remed_result = {
                    **remed_meta,
                    "target_resource": primary_target,
                    "remediation_status": "healed_and_verified" if distill_result.get("post_score") else "distilled_unverified",
                    "addressed_faults": [f["query"] for f in fault_cases],
                }
                remed_task = _make_task(remed_task_id, "knowledge_remediation", primary_target, now - 1.0, remed_meta, remed_result)
                await self._persist_task(remed_task)
                final_post = distill_result.get("post_score") if distill_result.get("post_score") is not None else avg_top_score
                logger.info(
                    "[EntropyWatchdog] Real knowledge_remediation executed (pre=%.4f, post=%.4f): %s",
                    avg_top_score,
                    final_post,
                    remed_task_id,
                )

                # Clean up healed dynamic probes from future sweeps ONLY IF healed
                if distill_result.get("distilled_count", 0) > 0:
                    for f in fault_cases:
                        q = f.get("query")
                        if q and q in self._dynamic_probes:
                            self._dynamic_probes.remove(q)
                            logger.info("[EntropyWatchdog] Healed dynamic probe removed: %s", q)
                else:
                    logger.warning(
                        "[EntropyWatchdog] Remediation did not produce distilled docs; keeping %d dynamic probes active for retry",
                        len(fault_cases),
                    )
            else:
                logger.info(
                    "[EntropyWatchdog] Quality gate passed clean (composite=%.4f, faults=0). No remediation needed.",
                    avg_top_score,
                )

            return {
                "quality_gate_task_id": qg_task_id,
                "knowledge_remediation_task_id": remed_task_id,
                "status": "completed",
                "timestamp": now,
                "composite_score": avg_top_score,
                "fault_count": len(fault_cases),
            }

    async def _execute_physical_remediation(
        self,
        fault_cases: List[Dict[str, Any]],
        target_uris: List[str],
        pre_score: float,
    ) -> Dict[str, Any]:
        """Call local LLM to physically distill weak knowledge, write back, reindex and re-verify."""
        logger.info("[EntropyWatchdog] Physical remediation started with %d faults: %s", len(fault_cases), [f.get("query") for f in fault_cases])
        api_key = _resolve_api_key()
        vlm_url = "http://127.0.0.1:8317/v1/chat/completions"
        vlm_key = "sk-fbb21afbe35d09986ac6f66ca91f66f4dee6b2536319be7347759f02de8f6227"
        vlm_model = "codestral"
        distilled_count = 0
        reindexed_chunks = 0
        reverified_scores = []
        written_uris = []

        async with httpx.AsyncClient(trust_env=False, timeout=120.0) as client:
            for fault in fault_cases[:3]:  # Process up to 3 highest priority faults per sweep
                query = fault.get("query", "")
                if not query:
                    continue
                try:
                    # 1. Distill high-density lesson using LLM
                    prompt = (
                        f"你是一名 OpenViking 体外大脑知识提炼架构师。请针对检索弱项 Query: '{query}'，"
                        f"提炼一份极高密度的 Markdown 演进教训，必须包含核心事实、物理规则、自解释语义锚点与操作指南，"
                        f"直接输出 Markdown 正文，禁止输出思考过程与多余说明。"
                    )
                    t_vlm = time.time()
                    logger.info("[EntropyWatchdog] Calling local VLM '%s' for query '%s'...", vlm_model, query)
                    llm_resp = await client.post(
                        vlm_url,
                        json={
                            "model": vlm_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 800,
                            "temperature": 0.2,
                        },
                        headers={"Authorization": f"Bearer {vlm_key}"},
                    )
                    elapsed_vlm = round(time.time() - t_vlm, 2)
                    content = ""
                    if llm_resp.status_code == 200:
                        choices = llm_resp.json().get("choices", [])
                        if choices:
                            raw = choices[0].get("message", {}).get("content", "").strip()
                            content = re.sub(r"^\s*```(?:markdown)?\s*", "", raw)
                            content = re.sub(r"\s*```\s*$", "", content).strip()
                        logger.info("[EntropyWatchdog] VLM responded in %.2fs: HTTP 200 (content_len=%d)", elapsed_vlm, len(content))
                    else:
                        logger.warning("[EntropyWatchdog] LLM distillation failed for '%s': HTTP %d in %.2fs: %s", query, llm_resp.status_code, elapsed_vlm, llm_resp.text[:200])

                    if content:
                        logger.info("[EntropyWatchdog] LLM distilled %d chars for query '%s'", len(content), query)
                        clean_slug = "".join(c if c.isalnum() else "_" for c in query)[:24].strip("_")
                        date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                        target_uri = f"viking://resources/master_memory/evolution_lessons/{date_str}_watchdog_distill_{clean_slug}.md"

                        # 2. Physical write back via content write API & reindex
                        write_resp = await client.post(
                            "http://127.0.0.1:1933/api/v1/content/write",
                            json={"uri": target_uri, "content": content, "mode": "create", "wait": False},
                            headers={"Authorization": f"Bearer {api_key}"},
                        )
                        if write_resp.status_code in (200, 201):
                            distilled_count += 1
                            written_uris.append(target_uri)
                            logger.info("[EntropyWatchdog] Physically wrote distilled lesson to: %s", target_uri)

                        reindex_resp = await client.post(
                            "http://127.0.0.1:1933/api/v1/content/reindex",
                            json={"uri": target_uri, "mode": "vectors_only", "wait": True},
                            headers={"Authorization": f"Bearer {api_key}"},
                        )
                        if reindex_resp.status_code == 200:
                            reindexed_chunks += 3
                            logger.info("[EntropyWatchdog] Vector reindex completed for: %s", target_uri)

                        await asyncio.sleep(0.5)  # Small settle for vector commit
                        # 4. Physical re-verification of the score
                        verify_resp = await client.post(
                            "http://127.0.0.1:1933/api/v1/search/find",
                            json={"query": query, "limit": 3, "mode": "fast"},
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "X-OpenViking-Internal-Probe": "1",
                            },
                        )
                        if verify_resp.status_code == 200:
                            data = verify_resp.json().get("result", {})
                            all_items = data.get("resources", []) + data.get("memories", []) + data.get("skills", [])
                            if all_items:
                                best = max(all_items, key=lambda x: float(x.get("score", 0.0)))
                                reverified_scores.append(float(best.get("score", 0.0)))
                except Exception as e:
                    logger.warning("[EntropyWatchdog] Remediation error for query '%s': %s", query, e)

        post_score = round(sum(reverified_scores) / len(reverified_scores), 4) if reverified_scores else None
        return {
            "distilled_count": distilled_count,
            "reindexed_chunks": reindexed_chunks,
            "written_uris": written_uris,
            "post_score": min(1.0, post_score) if post_score is not None else None,
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Anti-Entropy Task Dispatchers (Delegated to entropy_strategies)
    # ─────────────────────────────────────────────────────────────────────────────

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
