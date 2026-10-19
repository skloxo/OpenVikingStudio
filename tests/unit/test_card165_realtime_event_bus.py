# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Test suite for Card-165: Full-Duplex Real-Time Event Bus & Instant Skills Query Invalidation."""

import asyncio
import json
import pytest
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from openviking.service.skill_event_bus import SkillEventBus, SkillEvent
from openviking.storage.skill_ingestion_store import SkillIngestionStore, IngestionStatus
from openviking.service.skill_autonomous_pipeline import SkillAutonomousPipeline

TEST_SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

SAMPLE_CARD165_SKILL = """---
name: mock-card165-realtime-bus
description: 全双工实时事件总线测试规约。
triggers:
  - realtime-bus
  - card165-test
allowed-tools:
  - run_command
---

# Mock Card165 Realtime Bus

## 1. 触发意图与场景
- 触发关键词：realtime-bus, card165-test。

## 2. 边界约束与负向判定
- **何时严禁使用**：脱机环境下严禁依赖实时网络推送。

## 3. 标准排查清单 (Workflow)
1. 监听事件队列与 WebSocket / SSE 数据流 (input / 参数)；
2. 捕获 PIPELINE_PULSE 并执行断言 (assert / 断言 / 返回值)；
3. 处理网络抖动与退避自愈 (retry / 兜底 / 自愈)。

## 4. 工具调用示例
```bash
echo "test event bus"
```
"""


@pytest.fixture(autouse=True)
def reset_bus():
    """Reset event bus singleton before each test."""
    SkillEventBus.reset_instance_for_testing()
    yield
    SkillEventBus.reset_instance_for_testing()


@pytest.mark.asyncio
async def test_event_bus_singleton_and_stats():
    """Verify singleton pattern, initial metrics and stats report."""
    bus1 = SkillEventBus.get_instance()
    bus2 = SkillEventBus.get_instance()
    assert bus1 is bus2

    stats = bus1.get_stats()
    assert stats["active_subscribers"] == 0
    assert stats["total_emitted"] == 0
    assert stats["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_event_bus_emit_and_sse_subscribe():
    """Verify SSE subscription stream receives initial CONNECTED pulse and emitted events."""
    bus = SkillEventBus.get_instance()
    generator = bus.subscribe(max_queue_size=10, heartbeat_interval=2.0)

    # 1. First yielded message should be CONNECTED
    first_msg = await anext(generator)
    assert first_msg.startswith("data: ")
    init_data = json.loads(first_msg.replace("data: ", "").strip())
    assert init_data["event"] == "CONNECTED"
    assert init_data["active_subscribers"] == 1

    # 2. Emit SKILLS_MUTATED event
    bus.emit(SkillEvent.SKILLS_MUTATED, {"reason": "test mutation", "skill_name": "test-skill"})

    second_msg = await anext(generator)
    assert second_msg.startswith("data: ")
    event_data = json.loads(second_msg.replace("data: ", "").strip())
    assert event_data["event"] == SkillEvent.SKILLS_MUTATED
    assert event_data["payload"]["skill_name"] == "test-skill"

    # 3. Clean disconnect closes generator
    await generator.aclose()
    assert bus.get_stats()["active_subscribers"] == 0


@pytest.mark.asyncio
async def test_event_bus_backpressure_drop_oldest():
    """Verify bounded queue drops oldest item without blocking when subscriber lags."""
    bus = SkillEventBus.get_instance()
    generator = bus.subscribe(max_queue_size=2)

    # Read initial CONNECTED
    await anext(generator)

    # Emit 4 events into a queue of size 2
    for i in range(4):
        bus.emit(SkillEvent.PIPELINE_PULSE, {"seq": i})

    # Should not crash; next read should yield an event (oldest were discarded)
    msg = await anext(generator)
    data = json.loads(msg.replace("data: ", "").strip())
    assert data["event"] == SkillEvent.PIPELINE_PULSE
    assert data["payload"]["seq"] in (2, 3)

    await generator.aclose()


@pytest.mark.asyncio
async def test_event_bus_websocket_subscription():
    """Verify WebSocket handler broadcasts events, handles ping-pong and cleans up on close."""
    bus = SkillEventBus.get_instance()

    sent_messages = []

    class MockWebSocket:
        def __init__(self):
            self.closed = False
            self.incoming = asyncio.Queue()

        async def accept(self):
            pass

        async def send_json(self, msg):
            sent_messages.append(msg)

        async def receive_text(self):
            # Wait for incoming text or wait to be cancelled
            return await self.incoming.get()

    ws = MockWebSocket()
    ws_task = asyncio.create_task(bus.subscribe_ws(ws))

    # Allow task to accept and register
    await asyncio.sleep(0.05)
    assert bus.get_stats()["active_subscribers"] == 1
    assert len(sent_messages) == 1
    assert sent_messages[0]["event"] == "CONNECTED"

    # Emit an event
    bus.emit(SkillEvent.PIPELINE_PULSE, {"stage": "COMMITTED", "skill_name": "ws-skill"})
    await asyncio.sleep(0.05)
    assert len(sent_messages) == 2
    assert sent_messages[1]["event"] == SkillEvent.PIPELINE_PULSE

    # Send client ping
    await ws.incoming.put(json.dumps({"action": "ping"}))
    await asyncio.sleep(0.05)
    assert any(m.get("event") == "PONG" for m in sent_messages)

    # Cancel WS task
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass

    assert bus.get_stats()["active_subscribers"] == 0


def test_pipeline_emits_realtime_events_on_commit(tmp_path):
    """Verify SkillAutonomousPipeline emits PIPELINE_PULSE and SKILLS_MUTATED when committing."""
    store = SkillIngestionStore.get_instance()
    bus = SkillEventBus.get_instance()

    captured_events = []

    # Attach dummy queue to spy on bus emissions
    spy_queue = asyncio.Queue()
    bus._subscribers.append(spy_queue)

    rec = store.enqueue_skill(
        skill_name="mock-card165-realtime-bus",
        raw_content=SAMPLE_CARD165_SKILL,
        author="card165-suite",
    )

    pipeline = SkillAutonomousPipeline(skills_root=tmp_path, store=store)
    res = pipeline.process_one_cycle(batch_size=10)

    assert res["processed_count"] >= 1
    target_item = next((r for r in res["results"] if r.get("receipt_id") == rec.receipt_id), None)
    assert target_item is not None, f"Receipt {rec.receipt_id} not found in pipeline results: {res['results']}"
    assert target_item["status"] == "COMMITTED"

    # Inspect captured events in spy_queue
    while not spy_queue.empty():
        captured_events.append(spy_queue.get_nowait())

    event_types = [e["event"] for e in captured_events]
    assert SkillEvent.PIPELINE_PULSE in event_types, f"PIPELINE_PULSE missing: {event_types}"
    assert SkillEvent.SKILLS_MUTATED in event_types, f"SKILLS_MUTATED missing: {event_types}"

    committed_pulse = next(
        e for e in captured_events
        if e["event"] == SkillEvent.PIPELINE_PULSE and e.get("payload", {}).get("stage") == "COMMITTED"
    )
    assert committed_pulse["payload"]["skill_name"] == "mock-card165-realtime-bus"


@pytest.mark.asyncio
async def test_ingestion_api_emits_enqueued_pulse():
    """Verify submit_skill_to_inbox router emits PIPELINE_PULSE with stage ENQUEUED."""
    from openviking.server.routers.skill_ingestion import submit_skill_to_inbox, SubmitSkillRequest
    from openviking.server.identity import RequestContext

    bus = SkillEventBus.get_instance()
    spy_queue = asyncio.Queue()
    bus._subscribers.append(spy_queue)

    ctx = MagicMock(spec=RequestContext)
    req = SubmitSkillRequest(
        skill_name="mock-card165-api-submit",
        content=SAMPLE_CARD165_SKILL,
        author="test-agent",
    )

    res = await submit_skill_to_inbox(payload=req, ctx=ctx)
    assert res["status"] == "ok"
    assert res["ingestion_status"] == "PENDING"

    captured = []
    while not spy_queue.empty():
        captured.append(spy_queue.get_nowait())

    pulse = next(
        (e for e in captured if e["event"] == SkillEvent.PIPELINE_PULSE and e.get("payload", {}).get("stage") == "ENQUEUED"),
        None,
    )
    assert pulse is not None, f"Expected ENQUEUED pulse, got: {captured}"
    assert pulse["payload"]["skill_name"] == "mock-card165-api-submit"

    # Clean up enqueued record so pending queue is pristine
    store = SkillIngestionStore.get_instance()
    store.update_status(res["receipt_id"], IngestionStatus.COMMITTED, "test cleanup")
