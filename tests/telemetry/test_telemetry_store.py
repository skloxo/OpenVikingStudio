# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for unified SQLite TelemetryStore and baseline recovery engine.
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from openviking.models.vlm.token_usage import TokenUsageTracker
from openviking.retrieve.retrieval_stats import RetrievalStatsCollector
from openviking.telemetry.telemetry_store import TelemetryStore


@pytest.fixture
def temp_telemetry_store(tmp_path):
    """Create an isolated TelemetryStore instance with a temporary database."""
    db_file = tmp_path / "_system" / "telemetry" / "telemetry.sqlite3"
    store = TelemetryStore(db_path=db_file)
    yield store
    store.shutdown()


def test_telemetry_store_init_and_schema(temp_telemetry_store):
    """Verify that tables and indexes are properly created."""
    conn = temp_telemetry_store._get_connection()
    cur = conn.cursor()

    # Check tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cur.fetchall()}
    assert "model_metrics_audit" in tables
    assert "retrieval_metrics_audit" in tables
    assert "skill_metrics_audit" in tables
    assert "system_metrics_snapshot" in tables

    # Check indexes
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row["name"] for row in cur.fetchall()}
    assert "idx_model_ts" in indexes
    assert "idx_retrieval_ts" in indexes
    assert "idx_skill_ts" in indexes
    assert "idx_system_ts" in indexes

    conn.close()


def test_model_telemetry_and_baseline_recovery(temp_telemetry_store):
    """Verify model record persistence and zero-loss baseline hydration."""
    store = temp_telemetry_store

    # 1. Write model records
    store.record_model_usage(
        model_type="vlm",
        model_name="command-r-plus",
        provider="volcengine",
        prompt_tokens=150,
        completion_tokens=50,
        call_count=1,
        duration_ms=45.2,
    )
    store.record_model_usage(
        model_type="vlm",
        model_name="command-r-plus",
        provider="volcengine",
        prompt_tokens=200,
        completion_tokens=100,
        call_count=1,
        duration_ms=62.1,
    )
    store.record_model_usage(
        model_type="embedding",
        model_name="Qwen3-Embedding-8B",
        provider="openai",
        prompt_tokens=500,
        completion_tokens=0,
        call_count=2,
        duration_ms=12.5,
    )

    store.flush()

    # 2. Query baseline
    baseline = store.get_model_baseline()
    assert "command-r-plus" in baseline
    assert "volcengine" in baseline["command-r-plus"]
    vlm_stats = baseline["command-r-plus"]["volcengine"]
    assert vlm_stats["call_count"] == 2
    assert vlm_stats["prompt_tokens"] == 350
    assert vlm_stats["completion_tokens"] == 150
    assert vlm_stats["total_tokens"] == 500

    assert "Qwen3-Embedding-8B" in baseline
    emb_stats = baseline["Qwen3-Embedding-8B"]["openai"]
    assert emb_stats["call_count"] == 2
    assert emb_stats["prompt_tokens"] == 500
    assert emb_stats["total_tokens"] == 500

    # 3. Test TokenUsageTracker hydration
    tracker = TokenUsageTracker(auto_hydrate=False)
    # Manually point to this store or hydrate
    tracker._usage_by_model.clear()
    for model_name, providers in baseline.items():
        from openviking.models.vlm.token_usage import ModelTokenUsage, TokenUsage
        tracker._usage_by_model[model_name] = ModelTokenUsage(model_name)
        for provider_name, usage_info in providers.items():
            tracker._usage_by_model[model_name].usage_by_provider[provider_name] = TokenUsage(
                prompt_tokens=usage_info["prompt_tokens"],
                completion_tokens=usage_info["completion_tokens"],
                total_tokens=usage_info["total_tokens"],
                call_count=usage_info["call_count"],
            )
        tracker._usage_by_model[model_name].total_usage.prompt_tokens = sum(
            p.prompt_tokens for p in tracker._usage_by_model[model_name].usage_by_provider.values()
        )
        tracker._usage_by_model[model_name].total_usage.completion_tokens = sum(
            p.completion_tokens for p in tracker._usage_by_model[model_name].usage_by_provider.values()
        )
        tracker._usage_by_model[model_name].total_usage.total_tokens = sum(
            p.total_tokens for p in tracker._usage_by_model[model_name].usage_by_provider.values()
        )
        tracker._usage_by_model[model_name].total_usage.call_count = sum(
            p.call_count for p in tracker._usage_by_model[model_name].usage_by_provider.values()
        )

    usage_dict = tracker.to_dict()
    assert usage_dict["total_usage"]["total_tokens"] == 1000
    assert usage_dict["total_usage"]["call_count"] == 4


def test_retrieval_telemetry_and_baseline_recovery(temp_telemetry_store):
    """Verify retrieval quality persistence and stats baseline recovery."""
    store = temp_telemetry_store

    store.record_retrieval(
        context_type="memory",
        result_count=3,
        scores=[0.92, 0.85, 0.78],
        latency_ms=35.0,
        rerank_used=True,
        rerank_fallback=False,
    )
    store.record_retrieval(
        context_type="skills",
        result_count=0,
        scores=[],
        latency_ms=15.0,
        rerank_used=False,
        rerank_fallback=False,
    )

    store.flush()

    baseline = store.get_retrieval_baseline()
    assert baseline["total_queries"] == 2
    assert baseline["total_results"] == 3
    assert baseline["zero_result_queries"] == 1
    assert baseline["rerank_used"] == 1
    assert baseline["rerank_fallback"] == 0
    assert baseline["queries_by_type"]["memory"] == 1
    assert baseline["queries_by_type"]["skills"] == 1
    assert baseline["max_score"] >= 0.92


def test_skill_telemetry_and_harness_metrics(temp_telemetry_store):
    """Verify skill event recording and windowed harness metrics computation."""
    store = temp_telemetry_store

    store.record_skill_event(
        skill_name="code-review",
        event_type="compress",
        tokens_before=4000,
        tokens_after=1800,
        tokens_saved=2200,
        duration_ms=18.5,
        success=True,
    )
    store.record_skill_event(
        skill_name="diagnosing-bugs",
        event_type="wakeup",
        tokens_before=0,
        tokens_after=0,
        tokens_saved=0,
        duration_ms=2.1,
        success=True,
    )

    store.flush()

    harness = store.get_harness_metrics_by_window("24h")
    assert harness["status"] == "ok"
    assert harness["tokens_saved_total"] == 2200
    assert harness["active_skills_count"] >= 2


def test_telemetry_trends(temp_telemetry_store):
    """Verify trend series points generation for recharts."""
    store = temp_telemetry_store

    # Insert a few retrieval records
    store.record_retrieval(
        context_type="memory",
        result_count=5,
        scores=[0.95, 0.88],
        latency_ms=45.0,
        rerank_used=True,
    )
    store.record_model_usage(
        model_type="embedding",
        model_name="Qwen3-Embedding-8B",
        provider="openai",
        prompt_tokens=300,
        completion_tokens=0,
        duration_ms=15.0,
    )

    store.flush()

    sla_trends = store.get_trends("sla", "24h")
    assert len(sla_trends) >= 1
    assert "date" in sla_trends[0]
    assert "successRate" in sla_trends[0]
    assert "tokenSavingRate" in sla_trends[0]

    retrieval_trends = store.get_trends("retrieval", "24h")
    assert len(retrieval_trends) >= 1
    assert retrieval_trends[0]["queries"] >= 1

    emb_trends = store.get_trends("embedding", "24h")
    assert len(emb_trends) >= 1
    assert emb_trends[0]["calls"] >= 1
