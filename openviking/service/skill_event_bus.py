# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Real-time Event Bus for OpenViking Server.

Provides:
1. Lightweight, in-memory pub-sub event broadcast using asyncio.Queue.
2. Non-blocking backpressure defense (bounded queue, drops on overflow).
3. Heartbeat pulse to prevent proxy connection timeout.
4. Auto cleanup on client disconnect.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from openviking_cli.utils import get_logger

logger = get_logger(__name__)


class SkillEvent:
    """Canonical Skill Event Structure."""
    SKILLS_MUTATED = "SKILLS_MUTATED"
    SKILL_ADDED = "SKILL_ADDED"
    SKILL_UPDATED = "SKILL_UPDATED"
    SKILL_DELETED = "SKILL_DELETED"
    PIPELINE_PULSE = "PIPELINE_PULSE"
    HEARTBEAT = "HEARTBEAT"


class SkillEventBus:
    """In-memory event bus broadcasting real-time skill state transitions to SSE subscribers."""

    _instance: Optional[SkillEventBus] = None

    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self._total_emitted = 0
        self._created_at = time.time()

    @classmethod
    def get_instance(cls) -> SkillEventBus:
        if cls._instance is None:
            cls._instance = SkillEventBus()
        return cls._instance

    @classmethod
    def reset_instance_for_testing(cls) -> None:
        """Testing utility to reset singleton state."""
        cls._instance = None

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Broadcast an event to all active subscriber queues in a non-blocking manner."""
        self._total_emitted += 1
        msg = {
            "event": event_type,
            "timestamp": time.time(),
            "payload": payload or {},
        }
        dead_queues = []
        for q in self._subscribers:
            try:
                if q.full():
                    try:
                        q.get_nowait()  # Drop oldest to avoid lag
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(msg)
            except Exception as e:
                logger.debug(f"Failed to push event to queue: {e}")
                dead_queues.append(q)

        if dead_queues:
            for dq in dead_queues:
                if dq in self._subscribers:
                    self._subscribers.remove(dq)

    async def subscribe(
        self,
        max_queue_size: int = 50,
        heartbeat_interval: float = 15.0,
    ) -> AsyncGenerator[str, None]:
        """Subscribe to the event stream, yielding SSE formatted strings.
        
        Yields messages in SSE format:
            data: {"event": "SKILLS_MUTATED", ...}
            \n\n
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        async with self._lock:
            self._subscribers.append(queue)
            logger.debug(f"SkillEventBus new subscriber. Total active: {len(self._subscribers)}")

        try:
            # Send initial connected pulse
            init_event = json.dumps({
                "event": "CONNECTED",
                "timestamp": time.time(),
                "active_subscribers": len(self._subscribers),
            }, ensure_ascii=False)
            yield f"data: {init_event}\n\n"

            while True:
                try:
                    # Wait for next event or heartbeat
                    msg = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                    event_json = json.dumps(msg, ensure_ascii=False)
                    yield f"data: {event_json}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat ping to keep SSE connection alive
                    ping_msg = json.dumps({
                        "event": SkillEvent.HEARTBEAT,
                        "timestamp": time.time(),
                    })
                    yield f"data: {ping_msg}\n\n"

        except (asyncio.CancelledError, GeneratorExit):
            logger.debug("Subscriber disconnected gracefully")
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
                    logger.debug(f"Subscriber removed. Remaining: {len(self._subscribers)}")

    async def subscribe_ws(
        self,
        websocket: Any,
        max_queue_size: int = 50,
    ) -> None:
        """Handle a bidirectional WebSocket connection broadcasting real-time skill events."""
        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        async with self._lock:
            self._subscribers.append(queue)
            logger.debug(f"SkillEventBus new WS subscriber. Total active: {len(self._subscribers)}")

        # Send initial CONNECTED handshake
        await websocket.send_json({
            "event": "CONNECTED",
            "timestamp": time.time(),
            "active_subscribers": len(self._subscribers),
        })

        async def ws_reader() -> None:
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        msg = json.loads(data)
                        if msg.get("action") == "ping":
                            await websocket.send_json({
                                "event": "PONG",
                                "timestamp": time.time(),
                            })
                    except Exception:
                        pass
            except Exception:
                pass

        reader_task = asyncio.create_task(ws_reader())

        try:
            while True:
                msg = await queue.get()
                await websocket.send_json(msg)
        except Exception as exc:
            logger.debug(f"WS subscriber disconnected: {exc}")
        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
                    logger.debug(f"WS subscriber removed. Remaining: {len(self._subscribers)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get rolling telemetry for the event bus."""
        return {
            "active_subscribers": len(self._subscribers),
            "total_emitted": self._total_emitted,
            "uptime_seconds": round(time.time() - self._created_at, 2),
        }
