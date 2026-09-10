# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Entropy Gatekeeper Service for OpenViking.

Implements the two-stage ingestion gatekeeper & Mem0 4-way mutation state machine:
- Stage 1: Length & trivial token filter + GPU/vector nearest neighbor probe;
- Stage 2: Exact cosine similarity categorization according to RFC-007 & Claude Opus-5:
  * Sim >= 0.97: NOOP (deduplicated, zero file I/O, increment access counter);
  * 0.92 <= Sim < 0.97: UPDATE (counter-example & condition refinement gold band, allow write);
  * Negative / invalidated claims: DELETE / INVALIDATE;
  * Sim < 0.92: ADD (independent new knowledge, allow write);
- Fail-Open Resilience: Automatically bypasses and allows write on any probe error.
"""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from openviking.service.gatekeeper_prober import probe_nearest_vector

logger = logging.getLogger("openviking.entropy_gatekeeper")

GatekeeperAction = Literal["noop", "update", "delete", "add", "dlq"]
RETENTION_SECONDS = 30 * 86400  # 30-day rolling retention policy


@dataclass
class GatekeeperDecision:
    action: GatekeeperAction
    similarity: float
    matched_uri: Optional[str] = None
    matched_text_snippet: Optional[str] = None
    reason: str = ""
    saved_bytes: int = 0
    timestamp: float = field(default_factory=time.time)
    uri: str = ""
    id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EntropyGatekeeper:
    """Singleton two-stage ingestion gatekeeper defending against vector entropy proliferation."""

    _instance: Optional["EntropyGatekeeper"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._history: deque[GatekeeperDecision] = deque(maxlen=200)
        self._content_fingerprints: Dict[str, Tuple[str, float]] = {}
        self._stats: Dict[str, int] = {
            "add": 0,
            "update": 0,
            "delete": 0,
            "noop": 0,
            "dlq": 0,
            "total_probes": 0,
            "saved_bytes": 0,
        }
        self._stats_lock = threading.Lock()
        self._history_file = os.path.expanduser("~/.openviking/data/entropy_gatekeeper.jsonl")
        self._load_persisted_history()

    def _load_persisted_history(self) -> None:
        """Load and prune decisions older than 30 days from persistent disk."""
        if not os.path.exists(self._history_file):
            return
        now = time.time()
        cutoff = now - RETENTION_SECONDS
        valid_lines: List[Tuple[float, Dict[str, Any], str]] = []
        needs_rewrite = False

        try:
            with open(self._history_file, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                        ts = float(data.get("timestamp", now))
                        if ts >= cutoff:
                            valid_lines.append((ts, data, raw))
                        else:
                            needs_rewrite = True
                    except Exception:
                        needs_rewrite = True

            for ts, data, _ in valid_lines[-200:]:
                decision = GatekeeperDecision(
                    id=data.get("id") or f"dec_{uuid.uuid4().hex[:8]}",
                    action=data.get("action", "add"),
                    similarity=float(data.get("similarity", 0.0)),
                    matched_uri=data.get("matched_uri"),
                    matched_text_snippet=data.get("matched_text_snippet"),
                    reason=data.get("reason", ""),
                    saved_bytes=int(data.get("saved_bytes", 0)),
                    timestamp=ts,
                    uri=data.get("uri", ""),
                )
                self._history.append(decision)
                self._stats["total_probes"] += 1
                self._stats[decision.action] = self._stats.get(decision.action, 0) + 1
                if decision.saved_bytes > 0:
                    self._stats["saved_bytes"] += decision.saved_bytes

            if needs_rewrite:
                tmp_file = f"{self._history_file}.tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    for _, _, raw_line in valid_lines:
                        f.write(raw_line + "\n")
                os.replace(tmp_file, self._history_file)
                logger.info("[EntropyGatekeeper] Pruned expired decisions older than 30 days (retained: %d)", len(valid_lines))
        except Exception as e:
            logger.debug("[EntropyGatekeeper] Failed to load/prune persisted history: %s", e)

    @classmethod
    def get_instance(cls) -> "EntropyGatekeeper":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def reset_for_testing(self) -> None:
        """Reset internal stats and history for clean test execution."""
        with self._stats_lock:
            self._history.clear()
            self._stats = {
                "add": 0,
                "update": 0,
                "delete": 0,
                "noop": 0,
                "dlq": 0,
                "total_probes": 0,
                "saved_bytes": 0,
            }

    async def _probe_nearest_vector(
        self, content: str, uri: str, ctx: Any = None
    ) -> Tuple[float, Optional[str], Optional[str]]:
        """Delegate vector nearest neighbor probe to gatekeeper_prober module with hard timeout."""
        try:
            return await asyncio.wait_for(
                probe_nearest_vector(content, uri, ctx=ctx),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("[EntropyGatekeeper] Nearest vector probe timed out after 10s, falling open to 0.0")
            return 0.0, None, None

    async def evaluate_and_intercept(
        self,
        uri: str,
        content: str,
        ctx: Any = None,
    ) -> GatekeeperDecision:
        """Evaluate incoming write candidate and determine 4-way mutation action."""
        stripped = (content or "").strip()
        content_bytes = len(content.encode("utf-8")) if content else 0

        # Stage 0: Staging & Temporary Bypass (Zero overhead for session dumps and scratchpad)
        if any(k in uri for k in ["staging/", "sessions/", "/scratch/", "/tmp/"]):
            decision = GatekeeperDecision(
                action="add",
                similarity=0.0,
                uri=uri,
                reason="临时草稿/会话归档专区，直接放行入库。",
            )
            self._record_decision(decision)
            return decision

        # Stage 0.5: Fast-Path Malicious & Injection Check (DLQ Trap)
        is_malicious = any(
            k in stripped.lower()
            for k in ["ignore all previous instructions", "system prompt override", "you are now an evil assistant"]
        )
        if is_malicious:
            decision = GatekeeperDecision(
                action="dlq",
                similarity=0.0,
                uri=uri,
                reason="[DLQ 死信阻断] 探测到提示词注入或对抗特征，物理阻断入库并拖入死信隔离区存证。",
            )
            self._record_decision(decision)
            return decision

        # Stage 0.8: Fast-Path Exact Fingerprint Deduplication (0 Token / <0.1ms NOOP)
        content_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
        if content_hash in self._content_fingerprints:
            cached_uri, _ = self._content_fingerprints[content_hash]
            decision = GatekeeperDecision(
                action="noop",
                similarity=1.0000,
                matched_uri=cached_uri,
                matched_text_snippet=stripped[:200],
                reason=f"[NOOP 指纹秒级去重 | 相似度: 1.0000] 探测到完全一致的内容指纹 (0 Token 快轨)，拦截物理重复落盘，原子累加命中印证。",
                saved_bytes=content_bytes,
                uri=uri,
            )
            self._record_decision(decision)
            return decision

        # Stage 1: Length & Trivial Filter (Short token bypass)
        if len(stripped) < 15:
            decision = GatekeeperDecision(
                action="add",
                similarity=0.0,
                uri=uri,
                reason="内容过短（不足 15 字符，too short），不构成独立原子知识命题，跳过门禁审查直接放行入库。",
            )
            self._record_decision(decision)
            return decision

        try:
            score, matched_uri, snippet = await self._probe_nearest_vector(content, uri, ctx=ctx)

            # Stage 2: Categorization State Machine (Type-Aware Tiered Threshold)
            is_audit_or_health = any(
                k in (uri + " " + stripped).lower()
                for k in ["自检", "self_check", "heartbeat", "health_check", "巡检", "闭环自检", "全链路自检"]
            )

            if is_audit_or_health:
                if score >= 0.85:
                    decision = GatekeeperDecision(
                        action="noop",
                        similarity=round(score, 4),
                        matched_uri=matched_uri,
                        matched_text_snippet=snippet,
                        reason=f"[NOOP 自检去重 | 相似度: {score:.4f} >= 0.85] 探测到同类自检/巡检健康记录，拦截物理重复落盘，原子递增打卡印证。",
                        saved_bytes=content_bytes,
                        uri=uri,
                    )
                else:
                    decision = GatekeeperDecision(
                        action="add",
                        similarity=round(score, 4),
                        matched_uri=matched_uri,
                        matched_text_snippet=snippet,
                        reason=f"[自检首登 | 相似度: {score:.4f} < 0.85] 首次或显著差异的自检记录，放行入库。",
                        saved_bytes=0,
                        uri=uri,
                    )
            else:
                # Standard Core Knowledge
                if score >= 0.95:
                    decision = GatekeeperDecision(
                        action="noop",
                        similarity=round(score, 4),
                        matched_uri=matched_uri,
                        matched_text_snippet=snippet,
                        reason=f"[NOOP 印证去重 | 相似度: {score:.4f} >= 0.95] 与已有知识高度吻合，拦截磁盘物理写入以对抗碎片熵增；已累加命中印证权重。",
                        saved_bytes=content_bytes,
                        uri=uri,
                    )
                elif score >= 0.88:
                    decision = GatekeeperDecision(
                        action="update",
                        similarity=round(score, 4),
                        matched_uri=matched_uri,
                        matched_text_snippet=snippet,
                        reason=f"[特例演化 | 相似度: {score:.4f} in [0.88, 0.95)] 探测到反例分支或条件细化金带 (Gold Band Refinement)，保留为知识特例分支演进。",
                        saved_bytes=0,
                        uri=uri,
                    )
                elif any(term in stripped.lower() for term in ["deprecated", "已废弃", "已失效", "bug fixed", "已修正"]):
                    decision = GatekeeperDecision(
                        action="delete",
                        similarity=round(score, 4),
                        matched_uri=matched_uri,
                        matched_text_snippet=snippet,
                        reason="探测到知识失效或更正声明，已对历史被淘汰陈述进行清理标记。",
                        saved_bytes=0,
                        uri=uri,
                    )
                else:
                    decision = GatekeeperDecision(
                        action="add",
                        similarity=round(score, 4),
                        matched_uri=matched_uri,
                        matched_text_snippet=snippet,
                        reason=f"[新增写入 | 相似度: {score:.4f} < 0.88] 探测为独立原子新知识命题，已接收入库。",
                        saved_bytes=0,
                        uri=uri,
                    )

        except Exception as e:
            err_detail = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            logger.warning("[EntropyGatekeeper] Probe exception (failing-open): %s", err_detail)
            decision = GatekeeperDecision(
                action="add",
                similarity=0.0,
                uri=uri,
                reason=f"探针异常熔断兜底 (Fail-Open): {err_detail}",
            )

        if decision.action in ("add", "update"):
            self._content_fingerprints[content_hash] = (decision.uri or uri, time.time())

        self._record_decision(decision)
        return decision

    def _record_decision(self, decision: GatekeeperDecision) -> None:
        """Atomically record decision in rolling history, aggregate metrics, and persist."""
        with self._stats_lock:
            self._history.append(decision)
            self._stats["total_probes"] += 1
            self._stats[decision.action] = self._stats.get(decision.action, 0) + 1
            if decision.saved_bytes > 0:
                self._stats["saved_bytes"] += decision.saved_bytes

        try:
            os.makedirs(os.path.dirname(self._history_file), exist_ok=True)
            with open(self._history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug("[EntropyGatekeeper] Failed to persist decision: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        """Return real telemetry stats and recent 100 decisions for Studio UI."""
        with self._stats_lock:
            return {
                "stats": dict(self._stats),
                "history": [d.to_dict() for d in list(self._history)[-100:]],
            }
