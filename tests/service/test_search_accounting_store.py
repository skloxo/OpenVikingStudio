# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Search Accounting Store & 45-day rolling pruning.
"""

from datetime import datetime, timedelta
from pathlib import Path
import pytest
import sqlite3
import tempfile

from openviking.service.search_accounting_store import SearchAccountingStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_search_accounting.db"
        SearchAccountingStore.reset_instance()
        store = SearchAccountingStore(db_path=db_path)
        yield store
        SearchAccountingStore.reset_instance()


def test_record_usage_and_monthly_summary(temp_store: SearchAccountingStore):
    # 插入近期流水
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    row_id = temp_store.record_usage(
        key_fingerprint="kb_899872a3",
        engine="keenable",
        tool_name="web_search",
        status_code=200,
        credits_cost=1.0,
        latency_ms=125.5,
        created_at=now_str,
    )
    assert row_id > 0

    temp_store.record_usage(
        key_fingerprint="kb_899872a3",
        engine="keenable",
        tool_name="web_search",
        status_code=429,
        credits_cost=0.0,
        latency_ms=45.0,
        error_msg="Rate limit",
        created_at=now_str,
    )

    temp_store.record_usage(
        key_fingerprint="tv_1lQI1jVY",
        engine="tavily",
        tool_name="search_deep",
        status_code=200,
        credits_cost=2.0,
        latency_ms=310.0,
        created_at=now_str,
    )

    summary = temp_store.get_monthly_summary(now.strftime("%Y-%m"))
    assert len(summary) == 2

    kb_item = next(s for s in summary if s["key_fingerprint"] == "kb_899872a3")
    assert kb_item["total_calls"] == 2
    assert kb_item["success_calls"] == 1
    assert kb_item["rate_limit_calls"] == 1
    assert kb_item["total_credits"] == 1.0

    tv_item = next(s for s in summary if s["key_fingerprint"] == "tv_1lQI1jVY")
    assert tv_item["total_calls"] == 1
    assert tv_item["success_calls"] == 1
    assert tv_item["total_credits"] == 2.0


def test_45_day_rolling_prune_and_aggregation(temp_store: SearchAccountingStore):
    """验证超过 45 天的数据明细被彻底物理删除，且日度聚合数据无损保存。"""
    now = datetime.now()
    old_date = now - timedelta(days=50)
    old_date_str = old_date.strftime("%Y-%m-%d 10:00:00")
    recent_date_str = (now - timedelta(days=5)).strftime("%Y-%m-%d 12:00:00")

    # 1. 插入 50 天前的数据 (属于待归档清理范围)
    for _ in range(5):
        temp_store.record_usage(
            key_fingerprint="exa_d0fd541d",
            engine="exa",
            tool_name="search_neural",
            status_code=200,
            credits_cost=0.004,
            latency_ms=100.0,
            created_at=old_date_str,
        )

    # 2. 插入 5 天前的数据 (属于保留明细范围)
    for _ in range(3):
        temp_store.record_usage(
            key_fingerprint="exa_d0fd541d",
            engine="exa",
            tool_name="search_neural",
            status_code=200,
            credits_cost=0.004,
            latency_ms=90.0,
            created_at=recent_date_str,
        )

    # 初始状态检查
    stats_before = temp_store.get_database_stats()
    assert stats_before["detail_records"] == 8
    assert stats_before["archived_summary_records"] == 0

    # 3. 执行 45 天滚动归档与物理清理
    res = temp_store.rollup_and_prune_older_than(retention_days=45)
    assert res["deleted_detail_rows"] == 5
    assert res["aggregated_groups"] == 1

    # 4. 验证数据库状态：明细表只剩 3 条近期记录，归档汇总表有 1 条聚合记录
    stats_after = temp_store.get_database_stats()
    assert stats_after["detail_records"] == 3
    assert stats_after["archived_summary_records"] == 1

    # 5. 验证月度汇总：查询 50 天前所在月份，归档数据无损返回
    old_ym = old_date.strftime("%Y-%m")
    old_summary = temp_store.get_monthly_summary(old_ym)
    assert len(old_summary) == 1
    assert old_summary[0]["key_fingerprint"] == "exa_d0fd541d"
    assert old_summary[0]["total_calls"] == 5
    assert pytest.approx(old_summary[0]["total_credits"], rel=1e-3) == 0.02
