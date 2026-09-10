# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Valet Ingestion Engine (自动泊车异步分流引擎) for OpenViking.

Implements the valet parking ingestion pattern:
1. Fast Handover (<2ms): Caller hands over the payload, instantly receives a 202 Ticket.
2. Async Valet Worker: Background thread performs vector probe, Mem0 4-way triage,
   and writes to Master Memory or recycles to NOOP without blocking caller.
3. Dual-Track Task Center Integration: Emits first-class BusinessJob events with deliverable links.
"""

import asyncio
import json
import logging
import os
import queue
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from openviking.service.entropy_gatekeeper import EntropyGatekeeper, GatekeeperDecision
from openviking.service.task_tracker import get_task_tracker

logger = logging.getLogger("openviking.valet_ingestion")


@dataclass
class ValetTicket:
    ticket_id: str
    uri: str
    status: str = "accepted"  # accepted | parking | parked | rejected
    created_at: float = field(default_factory=time.time)
    action: Optional[str] = None
    similarity: Optional[float] = None
    matched_uri: Optional[str] = None
    deliverable_uri: Optional[str] = None
    human_title: str = ""
    initiator: str = "Agent"
    message: str = "数据已安全接管，正在异步执行治理与入库裁决..."

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ValetIngestionEngine:
    """Singleton engine orchestrating async managed ingestion pipeline."""

    _instance: Optional["ValetIngestionEngine"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._tickets: Dict[str, ValetTicket] = {}
        self._tickets_lock = threading.Lock()
        self._inbox: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=1000)
        self._wal_file = os.path.expanduser("~/.openviking/data/valet_inbox.jsonl")
        os.makedirs(os.path.dirname(self._wal_file), exist_ok=True)
        self._stop_event = threading.Event()
        self._worker_loop: Optional[asyncio.AbstractEventLoop] = None
        self._worker_thread = threading.Thread(
            target=self._valet_worker_loop,
            name="ValetIngestionWorker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info("ValetIngestionEngine initialized and worker started.")

    @classmethod
    def get_instance(cls) -> "ValetIngestionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def handover(
        self,
        uri: str,
        content: str,
        source: str = "api",
        metadata: Optional[Dict[str, Any]] = None,
        caller: str = "Agent",
    ) -> ValetTicket:
        """Driver hands over payload, immediately receives ticket (<2ms)."""
        ticket_id = f"ticket_valet_{uuid.uuid4().hex[:8]}"
        meta = metadata.copy() if metadata else {}
        
        # Derive human-friendly title
        title_summary = meta.get("title") or Path(uri).name
        if title_summary.endswith(".md"):
            title_summary = title_summary[:-3]
        if not title_summary:
            title_summary = content[:24].replace("\n", " ").strip()
        human_title = f"📥 原子入库：{title_summary}"

        ticket = ValetTicket(
            ticket_id=ticket_id,
            uri=uri,
            human_title=human_title,
            initiator=caller,
            message=f"已接管「{title_summary}」，正在执行原子入库与轻量准入...",
        )

        with self._tickets_lock:
            self._tickets[ticket_id] = ticket

        # Real-time TaskCenter observability: register as PENDING immediately
        self._schedule_pending_registration(ticket_id, uri, caller, source, human_title)

        # Append to high-speed write-ahead log (WAL)
        try:
            record = {
                "ticket_id": ticket_id,
                "uri": uri,
                "content": content,
                "source": source,
                "caller": caller,
                "metadata": meta,
                "timestamp": time.time(),
            }
            with open(self._wal_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("Failed to write valet WAL: %s", e)

        # Queue for async processing
        try:
            self._inbox.put_nowait(record)
        except queue.Full:
            logger.error("Valet inbox queue full, rejecting ticket %s", ticket_id)
            ticket.status = "rejected"
            ticket.message = "处理队列已满，稍后重试"

        return ticket

    def _schedule_pending_registration(
        self,
        ticket_id: str,
        uri: str,
        caller: str,
        source: str,
        human_title: str,
    ) -> None:
        """Register the valet ticket as PENDING in TaskTracker immediately for real-time observability."""
        async def _register() -> None:
            try:
                tracker = get_task_tracker()
                await tracker.create(
                    task_type="valet_parking",
                    task_id=ticket_id,
                    resource_id=uri,
                    account_id="default",
                    user_id="default",
                    meta={
                        "is_business": True,
                        "human_title": human_title,
                        "initiator": caller,
                        "uri": uri,
                        "source": source,
                        "ticket_id": ticket_id,
                        "progress": {"completed": 0, "total": 1, "unit": "个节点"},
                    },
                )
            except Exception as e:
                logger.warning("Task tracker early PENDING registration failed: %s", e)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_register())
        except RuntimeError:
            if self._worker_loop and self._worker_loop.is_running():
                asyncio.run_coroutine_threadsafe(_register(), self._worker_loop)

    def get_ticket(self, ticket_id: str) -> Optional[ValetTicket]:
        with self._tickets_lock:
            return self._tickets.get(ticket_id)

    def list_tickets(self, limit: int = 50) -> List[ValetTicket]:
        with self._tickets_lock:
            tickets = list(self._tickets.values())
            tickets.sort(key=lambda t: t.created_at, reverse=True)
            return tickets[:limit]

    def _valet_worker_loop(self) -> None:
        """Background thread taking cars from inbox, evaluating, and parking."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._worker_loop = loop

        while not self._stop_event.is_set():
            try:
                record = self._inbox.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                loop.run_until_complete(self._process_valet_record(record))
            except Exception as e:
                logger.error("Error processing valet record: %s", e, exc_info=True)
            finally:
                self._inbox.task_done()

    async def _process_valet_record(self, record: Dict[str, Any]) -> None:
        ticket_id = record["ticket_id"]
        uri = record["uri"]
        content = record["content"]
        meta = record.get("metadata", {})

        gatekeeper = EntropyGatekeeper.get_instance()
        task_tracker = None
        try:
            task_tracker = get_task_tracker()
        except Exception:
            pass

        # Register and start in TaskTracker for UI observability
        caller = record.get("caller", "Agent")
        source = record.get("source", "api")
        title_summary = meta.get("title") or Path(uri).name
        if title_summary.endswith(".md"):
            title_summary = title_summary[:-3]
        if not title_summary:
            title_summary = content[:24].replace("\n", " ").strip()
        human_title = f"📥 原子入库：{title_summary}"

        if task_tracker is not None:
            try:
                await task_tracker.create(
                    task_type="valet_parking",
                    task_id=ticket_id,
                    resource_id=uri,
                    account_id="default",
                    user_id="default",
                    meta={
                        "is_business": True,
                        "human_title": human_title,
                        "initiator": caller,
                        "uri": uri,
                        "source": source,
                        "ticket_id": ticket_id,
                        "progress": {"completed": 0, "total": 1, "unit": "个节点"},
                    },
                )
                await task_tracker.start(ticket_id, account_id="default", user_id="default")
            except Exception as e:
                logger.warning("Task tracker create/start error for %s: %s", ticket_id, e)

        # Update status to parking
        with self._tickets_lock:
            if ticket_id in self._tickets:
                self._tickets[ticket_id].status = "parking"

        try:
            decision: GatekeeperDecision = await asyncio.wait_for(
                gatekeeper.evaluate_and_intercept(
                    uri=uri,
                    content=content,
                ),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[ValetIngestion] Gatekeeper evaluation timed out after 15s for uri=%s, falling open to safe add.",
                uri,
            )
            decision = GatekeeperDecision(
                action="add",
                similarity=0.0,
                uri=uri,
                reason="门禁裁决超时 (15s 看门狗熔断保护)，安全放行入库。",
            )

        deliverable = None
        action_msg = ""
        if decision.action == "noop":
            action_msg = f"同义知识已合并至既有节点 (相似度 {decision.similarity:.4f})，零冗余新增"
            deliverable = {
                "uri": decision.matched_uri or uri,
                "label": "查看既有节点知识",
                "action_type": "view_memory",
            }
        elif decision.action == "update":
            # Physically write updated content
            self._write_local_file(uri, content)
            action_msg = f"既有节点已成功升级演进 (相似度 {decision.similarity:.4f})"
            deliverable = {
                "uri": uri,
                "label": "查看升级演进知识",
                "action_type": "view_memory",
            }
        elif decision.action == "add":
            # Physically write new atomic content
            self._write_local_file(uri, content)
            action_msg = f"已成功存储落盘 (独立新知识)"
            deliverable = {
                "uri": uri,
                "label": "查看全新入库知识",
                "action_type": "view_memory",
            }
        else:
            action_msg = f"异常或更正记录已标记"

        # Update ticket final state
        with self._tickets_lock:
            if ticket_id in self._tickets:
                t = self._tickets[ticket_id]
                t.status = "parked"
                t.action = decision.action
                t.similarity = decision.similarity
                t.matched_uri = decision.matched_uri
                t.deliverable_uri = deliverable.get("uri") if deliverable else uri
                t.message = action_msg

        # Update TaskTracker record to completed with progress 1/1
        if task_tracker is not None:
            try:
                await task_tracker.complete(
                    task_id=ticket_id,
                    result={
                        "status": "ok",
                        "action": decision.action,
                        "similarity": decision.similarity,
                        "matched_uri": decision.matched_uri,
                        "message": action_msg,
                        "deliverable": deliverable,
                        "saved_bytes": decision.saved_bytes,
                        "progress": {"completed": 1, "total": 1, "unit": "个节点"},
                        "handover_count": 1,
                        "handover_total": 1,
                        "probed_candidates": 1,
                        "candidates_count": 1,
                        "evaluated_decisions": 1,
                        "verdict_count": 1,
                        "parked_nodes": 1,
                        "persisted_nodes": 1,
                        "merged_nodes": 1 if decision.action == "noop" else 0,
                    },
                    account_id="default",
                    user_id="default",
                )
            except Exception as e:
                logger.warning("Task tracker complete notification failed for %s: %s", ticket_id, e)

    def _write_local_file(self, uri: str, content: str) -> None:
        """Physical disk write helper for viking:// URIs."""
        try:
            target_path = self._resolve_uri_to_path(uri)
            if target_path:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                logger.info("Valet worker physically parked file at: %s", target_path)
        except Exception as e:
            logger.error("Failed to physically write valet file: %s", e)

    def _resolve_uri_to_path(self, uri: str) -> Optional[Path]:
        clean = uri.replace("viking://resources/", "").lstrip("/")
        base = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources"
        return base / clean
