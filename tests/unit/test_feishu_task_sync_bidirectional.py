# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card 9: Feishu Task Bi-Directional Sync and Task Center Retry Engine.
"""

import asyncio
import pytest
from openviking.service.feishu_task_sync import (
    FeishuTaskStatus,
    FeishuTaskSyncBridge,
)
from openviking.service.task_tracker import TaskRecord, TaskStatus, get_task_tracker, set_task_tracker
from tests.test_task_tracker import _set_fake_global_tracker


@pytest.fixture
def clean_bridge():
    FeishuTaskSyncBridge.reset_instance_for_testing()
    tracker = _set_fake_global_tracker()
    bridge = FeishuTaskSyncBridge.get_instance()
    yield bridge, tracker
    FeishuTaskSyncBridge.reset_instance_for_testing()
    set_task_tracker(None)


@pytest.mark.asyncio
async def test_internal_status_sync_to_feishu(clean_bridge):
    """Verify internal task status progression syncs correctly to Feishu mock store."""
    bridge, tracker = clean_bridge

    # Create task with linked feishu task
    task = await tracker.create(
        task_type="managed_ingestion",
        account_id="default",
        user_id="test_user",
        meta={"feishu_task_id": "feishu_tk_101", "human_title": "Sync Test"},
    )
    assert task.task_id is not None
    assert bridge.get_feishu_task_id(task.task_id) == "feishu_tk_101"

    # 1. Update to RUNNING
    await tracker.start(task.task_id, account_id="default", user_id="test_user", stage="downloading")
    running_task = await tracker.get(task.task_id)
    await bridge.on_task_status_change(running_task)

    store_entry = bridge._mock_external_store.get("feishu_tk_101")
    assert store_entry is not None
    assert store_entry["status"] == FeishuTaskStatus.IN_PROGRESS.value
    assert store_entry["execution_run_id"] == task.task_id

    # 2. Complete task
    await tracker.complete(
        task.task_id,
        result={"message": "All ingested", "deliverable": {"uri": "viking://resources/doc.md"}},
        account_id="default",
        user_id="test_user",
    )
    completed_task = await tracker.get(task.task_id)
    await bridge.on_task_status_change(completed_task)

    store_entry = bridge._mock_external_store.get("feishu_tk_101")
    assert store_entry["status"] == FeishuTaskStatus.DONE.value
    assert store_entry["deliverable"] == {"uri": "viking://resources/doc.md"}


@pytest.mark.asyncio
async def test_internal_failure_sync_to_feishu(clean_bridge):
    """Verify task failure synchronizes error info to external task."""
    bridge, tracker = clean_bridge

    task = await tracker.create(
        task_type="official_digest",
        account_id="default",
        user_id="test_user",
        meta={"feishu_task_id": "feishu_tk_fail_202"},
    )
    await tracker.fail(
        task.task_id,
        error="Network timeout accessing host",
        account_id="default",
        user_id="test_user",
    )
    failed_task = await tracker.get(task.task_id)
    await bridge.on_task_status_change(failed_task)

    store_entry = bridge._mock_external_store.get("feishu_tk_fail_202")
    assert store_entry["status"] == FeishuTaskStatus.FAILED.value
    assert "timeout" in store_entry["error"]


@pytest.mark.asyncio
async def test_feishu_reverse_sync_completion(clean_bridge):
    """Verify Feishu external completion reflects back into internal TaskTracker."""
    bridge, tracker = clean_bridge

    task = await tracker.create(
        task_type="batch_digest",
        account_id="default",
        user_id="test_user",
        meta={"feishu_task_id": "feishu_tk_reverse_303"},
    )
    bridge.bind_task_mapping(task.task_id, "feishu_tk_reverse_303")

    # Trigger reverse sync as DONE from Feishu
    updated = await bridge.trigger_reverse_sync_from_feishu(
        feishu_task_id="feishu_tk_reverse_303",
        new_status=FeishuTaskStatus.DONE,
    )
    assert updated is not None
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result.get("sync_from") == "feishu"


@pytest.mark.asyncio
async def test_task_retry_lifecycle_and_feishu_event(clean_bridge):
    """Verify task retry mechanics: counter increment, error clearing, and feishu notification."""
    bridge, tracker = clean_bridge

    task = await tracker.create(
        task_type="node_rebuild",
        account_id="default",
        user_id="test_user",
        meta={"feishu_task_id": "feishu_tk_retry_404"},
    )
    bridge.bind_task_mapping(task.task_id, "feishu_tk_retry_404")

    # Attempt retry on pending task -> must fail precondition
    with pytest.raises(ValueError, match="Only failed or cancelled tasks"):
        await tracker.retry_task(task.task_id, account_id="default", user_id="test_user")

    # Fail the task
    await tracker.fail(task.task_id, error="CUDA out of memory", account_id="default", user_id="test_user")
    failed_task = await tracker.get(task.task_id)
    assert failed_task.status == TaskStatus.FAILED

    # Now trigger retry
    retried_task = await tracker.retry_task(
        task.task_id,
        reason="gpu_reboot_complete",
        account_id="default",
        user_id="test_user",
    )
    assert retried_task.status == TaskStatus.PENDING
    assert retried_task.error is None
    assert retried_task.meta["retry_count"] == 1
    assert retried_task.meta["last_failed_error"] == "CUDA out of memory"
    assert retried_task.meta["retry_reason"] == "gpu_reboot_complete"

    # Check Feishu mock store updated
    store_entry = bridge._mock_external_store.get("feishu_tk_retry_404")
    assert store_entry["status"] == FeishuTaskStatus.TODO.value
    assert store_entry["retry_count"] == 1


@pytest.mark.asyncio
async def test_unconfigured_feishu_audit_mode_resilience(clean_bridge):
    """Verify graceful fallback and telemetry history in unconfigured audit mode."""
    bridge, tracker = clean_bridge

    # Verify audit mode when env is unset
    assert bridge.is_feishu_configured() is False

    task = await tracker.create(
        task_type="quality_gate",
        account_id="default",
        user_id="test_user",
        meta={"feishu_task_id": "feishu_tk_audit_505"},
    )
    success = await bridge.on_task_status_change(task)
    assert success is True

    stats = bridge.get_stats()
    assert stats["total_syncs"] >= 1
    assert stats["success_syncs"] >= 1

    history = bridge.get_history(limit=10)
    assert len(history) >= 1
    assert history[-1]["feishu_task_id"] == "feishu_tk_audit_505"
