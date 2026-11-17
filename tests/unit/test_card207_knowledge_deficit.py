# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-207: Knowledge Deficit frequency funnel, similarity clustering, scaffolding & dual-track fulfillment tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking.service.knowledge_deficit import (
    BlindspotLedger,
    classify_deficit_route,
    compute_query_similarity,
    extract_entity_and_category,
)
from openviking.service.search_service import SearchService


def test_similarity_and_dual_track_classification():
    assert compute_query_similarity("耿晓光", "耿晓光 电话") >= 0.72
    entity, cat = extract_entity_and_category("耿晓光 联系方式?")
    assert entity == "耿晓光"
    assert cat == "personnel_contact"
    assert classify_deficit_route("耿晓光 部门", entity_category=cat) == "human_assistance"
    assert classify_deficit_route("FastAPI lifespan dependency injection") == "autonomous_researcher"


def test_frequency_funnel_promotes_at_threshold_and_flips_on_fulfill(tmp_path: Path):
    ledger = BlindspotLedger(
        db_path=tmp_path / "deficits.db",
        deliverables_dir=tmp_path / "wiki_remediation",
        miss_threshold=3,
    )

    first = ledger.record_miss("耿晓光 电话")
    assert first is not None
    assert first["status"] == "observing"
    assert first["miss_count"] == 1
    assert first["scaffold_markdown"] == ""

    second = ledger.record_miss("耿晓光 分机")
    assert second is not None
    assert second["deficit_id"] == first["deficit_id"]
    assert second["status"] == "observing"
    assert second["miss_count"] == 2

    third = ledger.record_miss("耿晓光")
    assert third is not None
    assert third["deficit_id"] == first["deficit_id"]
    assert third["status"] == "pending_fulfillment"
    assert third["miss_count"] == 3
    assert "# 待完善知识卡片: 耿晓光" in third["scaffold_markdown"]
    assert "```mermaid" in third["scaffold_markdown"]
    assert [s["step"] for s in third["step_trace"]] == [
        "step_miss_capture",
        "step_reflection",
        "step_ticket_enqueue",
    ]
    assert all(s["status"] == "completed" for s in third["step_trace"])

    summary_before = ledger.get_summary()
    assert summary_before["pending_fulfillment_count"] == 1
    assert summary_before["fulfilled_count"] == 0

    fulfilled = ledger.fulfill_deficit(
        third["deficit_id"],
        fields={"所属部门": "总务管理部", "办公分机": "8012"},
        track="human_assistance",
    )
    assert fulfilled["status"] == "fulfilled"
    assert fulfilled["deliverable_uri"] == f"viking://resources/wiki_remediation/{third['deficit_id']}.md"
    deliverable = tmp_path / "wiki_remediation" / f"{third['deficit_id']}.md"
    assert deliverable.is_file()
    assert "8012" in deliverable.read_text(encoding="utf-8")

    summary_after = ledger.get_summary()
    assert summary_after["pending_fulfillment_count"] == 0
    assert summary_after["fulfilled_count"] == 1


@pytest.mark.asyncio
async def test_search_service_captures_zero_hit_miss_fail_open(tmp_path: Path):
    ledger = BlindspotLedger(
        db_path=tmp_path / "search_deficits.db",
        deliverables_dir=tmp_path / "wiki",
        miss_threshold=3,
    )
    empty_result = MagicMock()
    empty_result.__len__.return_value = 0
    empty_result.memories = []
    empty_result.resources = []
    empty_result.skills = []

    mock_vfs = MagicMock()
    mock_vfs.find = AsyncMock(return_value=empty_result)
    svc = SearchService(viking_fs=mock_vfs)

    ctx = MagicMock()
    ctx.account_id = "default"
    ctx.user = MagicMock(user_id="tester")

    with patch("openviking.service.knowledge_deficit.BlindspotLedger.get_instance", return_value=ledger):
        res = await svc.find("华庭安防NVR密码规范", ctx=ctx, limit=5)

    assert len(res) == 0
    items = ledger.list_deficits(status="observing")
    assert len(items) == 1
    assert items[0]["canonical_query"] == "华庭安防NVR密码规范"
