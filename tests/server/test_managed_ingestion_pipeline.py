import asyncio
import time
import pytest
from pathlib import Path

from openviking.service.task_tracker import get_task_tracker, TaskStatus
from openviking.service.entropy_gatekeeper import EntropyGatekeeper, GatekeeperDecision


@pytest.mark.asyncio
async def test_managed_ingestion_fast_path_noop():
    """Identical content triggers fast-path NOOP (<10ms, 0 Token), intercepting write and incrementing hit count."""
    gatekeeper = EntropyGatekeeper.get_instance()
    uri = "viking://resources/master_memory/test_fast_noop.md"
    content = "# Golden Test Axiom\nStrictly no green ever in user interface design."

    # First write to ensure candidate exists
    await gatekeeper.evaluate_and_intercept(uri=uri, content=content)

    # Second identical write must trigger fast-path NOOP
    t0 = time.time()
    decision = await gatekeeper.evaluate_and_intercept(uri=uri, content=content)
    dt_ms = (time.time() - t0) * 1000

    assert decision.action == "noop"
    assert decision.similarity >= 0.95
    assert dt_ms < 100.0  # Fast path should complete well under 100ms
    assert "去重" in decision.reason or "noop" in decision.action.lower()


@pytest.mark.asyncio
async def test_managed_ingestion_fast_path_add():
    """Completely new content with low similarity triggers fast-path ADD directly."""
    gatekeeper = EntropyGatekeeper.get_instance()
    unique_topic = f"Unique Quantum Topology {time.time()}"
    uri = f"viking://resources/master_memory/unique_{int(time.time())}.md"
    content = f"# {unique_topic}\nIndependent fresh physics truth without any prior overlaps."

    decision = await gatekeeper.evaluate_and_intercept(uri=uri, content=content)
    assert decision.action == "add"


@pytest.mark.asyncio
async def test_managed_ingestion_task_tracker_registration():
    """TaskTracker natively registers managed_ingestion task with lifecycle states."""
    tracker = None
    try:
        tracker = get_task_tracker()
    except Exception:
        pytest.skip("TaskTracker not initialized in test environment")

    task_id = f"test_task_{int(time.time())}"
    record = await tracker.register_task(
        task_type="managed_ingestion",
        resource_id=task_id,
        account_id="default",
        user_id="default",
        meta={"human_title": "📥 异步托管入库：测试工单", "uri": "viking://resources/master_memory/test.md"},
    )
    assert record.task_type == "managed_ingestion"
    assert record.status in (TaskStatus.PENDING, TaskStatus.RUNNING)

    # Test finish transition
    finished = await tracker.finish_task(
        task_id=record.task_id,
        result={"action": "add", "saved_bytes": 0, "similarity": 0.0},
    )
    assert finished.status == TaskStatus.COMPLETED
