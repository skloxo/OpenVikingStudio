# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for RNFV plan execution and two-phase write transaction (Card-184)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openviking.core.context import ContextLevel
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier
from openviking.storage.acl import AclUpdate
from openviking.storage.context_update_execution import (
    PlanWork,
    commit_and_enqueue_plan,
    enqueue_direct_index_actions,
    vectorize_resource_file,
)
from openviking.storage.context_update_plan import (
    ContentTreeAction,
    ContentTreeOperation,
    ContextUpdatePlan,
    DirectIndexAction,
    FileRefreshIntent,
)
from openviking.storage.index_action import FieldPatch, IndexAction
from openviking.utils.ingest_options import IngestOptions


@pytest.fixture
def dummy_ctx():
    return RequestContext(
        user=UserIdentifier(account_id="test_acc", user_id="user_123"),
        role=Role.ADMIN,
    )



def test_plan_work_contract():
    work = PlanWork(
        semantic_requested=True,
        vector_requested=False,
        semantic_action="refresh",
    )
    assert work.semantic_requested is True
    assert work.vector_requested is False
    assert work.semantic_action == "refresh"
    with pytest.raises(AttributeError):
        work.semantic_requested = False


@pytest.mark.asyncio
async def test_enqueue_direct_index_actions_empty(dummy_ctx):
    result = await enqueue_direct_index_actions([], ctx=dummy_ctx)
    assert result is False


@pytest.mark.asyncio
async def test_enqueue_direct_index_actions_delete_and_patch(dummy_ctx):
    delete_action = DirectIndexAction(
        uri="viking://user/default/resources/orphan.txt",
        record_id="rec_orphan_1",
        level=int(ContextLevel.DETAIL),
        action=IndexAction.DELETE,
    )
    patch_action = DirectIndexAction(
        uri="viking://user/default/resources/active.txt",
        record_id="rec_active_1",
        level=int(ContextLevel.DETAIL),
        action=IndexAction.UPDATE_FIELDS,
        field_patch=FieldPatch(values={"search_tags": ["tag1"]}),
    )

    mock_queue = MagicMock()
    mock_queue_manager = MagicMock()
    mock_queue_manager.EMBEDDING = "embedding"
    mock_queue_manager.get_queue.return_value = mock_queue

    mock_telemetry = MagicMock()
    mock_telemetry.telemetry_id = "tel_123"

    with patch("openviking.storage.queuefs.get_queue_manager", return_value=mock_queue_manager), \
         patch("openviking.telemetry.get_current_telemetry", return_value=mock_telemetry), \
         patch("openviking.utils.embedding_utils._enqueue_embedding_message", new_callable=AsyncMock) as mock_enqueue:
        mock_enqueue.return_value = True

        enqueued = await enqueue_direct_index_actions(
            [delete_action, patch_action],
            ctx=dummy_ctx,
        )

        assert enqueued is True
        assert mock_enqueue.call_count == 2
        # Verify first call is delete message
        first_msg = mock_enqueue.call_args_list[0][0][1]
        assert first_msg.context_data["action"] == "delete"
        assert first_msg.context_data["record_ids"] == ["rec_orphan_1"]

        # Verify second call is update_fields message
        second_msg = mock_enqueue.call_args_list[1][0][1]
        assert second_msg.context_data["action"] == "update_fields"
        assert second_msg.context_data["record_id"] == "rec_active_1"


@pytest.mark.asyncio
async def test_commit_and_enqueue_plan_two_phase_decoupling(dummy_ctx):
    # Phase 1: Content Tree Action
    content_action = ContentTreeAction(
        relative_path="",
        operation=ContentTreeOperation.UPSERT,
        new_kind="file",
        artifact_path="file.txt",
        md5="098f6bcd4621d373cade4e832627b4f6",
    )
    # Phase 2: Index & Refresh
    index_action = DirectIndexAction(
        uri="viking://user/default/resources/file.txt",
        record_id="rec_file_1",
        level=int(ContextLevel.DETAIL),
        action=IndexAction.UPDATE_FIELDS,
        field_patch=FieldPatch(values={"search_tags": ["custom-tag"]}),
    )
    refresh_intent = FileRefreshIntent(
        file_uri="viking://user/default/resources/file.txt",
        md5="098f6bcd4621d373cade4e832627b4f6",
    )

    plan = ContextUpdatePlan(
        root_uri="viking://user/default/resources/file.txt",
        context_type="resource",
        content_tree_actions=(content_action,),
        direct_index_actions=(index_action,),
        file_refresh=refresh_intent,
    )

    mock_target = MagicMock()
    mock_target.write_file = AsyncMock()
    mock_store = MagicMock()
    mock_store.read_bytes = AsyncMock(return_value=b"hello world")

    mock_summarizer = MagicMock()
    mock_summarizer.refresh_file_parent = AsyncMock(return_value={"enqueued_count": 1, "semantic_action": "refresh"})

    with patch("openviking.storage.context_update_execution.enqueue_direct_index_actions", new_callable=AsyncMock) as mock_direct:
        mock_direct.return_value = True

        work = await commit_and_enqueue_plan(
            plan,
            ctx=dummy_ctx,
            inline_store=mock_store,
            inline_ref="ref_1",
            target=mock_target,
            summarizer=mock_summarizer,
            file_created=False,
            force_refresh=True,
        )

        # 1. Content tree action executed
        mock_target.write_file.assert_awaited_once_with("", b"hello world")
        # 2. Direct index action enqueued
        mock_direct.assert_awaited_once()
        # 3. Parent refresh enqueued
        mock_summarizer.refresh_file_parent.assert_awaited_once()

        # 4. PlanWork accurately reports downstream requests
        assert work.semantic_requested is True
        assert work.vector_requested is True
        assert work.semantic_action == "refresh"
