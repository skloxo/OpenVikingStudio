# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Retrieval Gold Benchmark Suite, Asymmetric Decay Engine,
and Knowledge Hygiene Audit (Card-Hygiene-AsymmetricDecayAndBench / v1.5.31).
"""

import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.retrieve.asymmetric_decay import (
    AsymmetricDecayEngine,
    DecayConfig,
    DecayAssessment,
)
from openviking.retrieve.knowledge_hygiene import (
    KnowledgeHygieneEngine,
    HygieneReport,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier


def test_gold_benchmarks_dataset_integrity():
    """Verify gold_benchmarks.json structure, coverage, and validation rules."""
    dataset_path = Path(__file__).parents[2] / "openviking" / "retrieve" / "gold_benchmarks.json"
    assert dataset_path.exists(), f"Benchmark file not found at {dataset_path}"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "benchmarks" in data
    benchmarks = data["benchmarks"]
    assert len(benchmarks) == 32, f"Expected 32 gold benchmarks, got {len(benchmarks)}"

    categories = set()
    for item in benchmarks:
        assert "id" in item
        assert "category" in item
        assert "query" in item
        assert "expected_keywords" in item
        assert "expected_uri_pattern" in item
        assert len(item["query"].strip()) > 0
        categories.add(item["category"])

    expected_categories = {"symbols", "errors", "architecture", "domain"}
    assert categories == expected_categories, f"Categories mismatch: {categories}"


def test_asymmetric_decay_axiom_immunity():
    """Verify master memory and system rules are 100% immune to decay."""
    engine = AsymmetricDecayEngine()
    current_ts = time.time()
    one_year_ago = current_ts - (365 * 86400)

    # Master memory axiom item
    uri = "viking://resources/master_memory/rules/agent_ten_laws.md"
    assessment: DecayAssessment = engine.evaluate_candidate(
        uri=uri,
        raw_score=0.95,
        updated_ts=one_year_ago,
        status="active",
        now_ts=current_ts,
    )
    assert assessment.adjusted_score == 0.95, "Axiom memory must not be decayed"
    assert assessment.decay_factor == 1.0
    assert assessment.is_immune is True


def test_asymmetric_decay_half_life_and_status_penalty():
    """Verify non-axiom memories decay exponentially and disputed items are penalized."""
    # Custom config with 7 days default half life and 0.01 floor
    config = DecayConfig(default_half_life_days=7.0, min_decay_floor=0.01)
    engine = AsymmetricDecayEngine(config=config)
    current_ts = time.time()
    fourteen_days_ago = current_ts - (14 * 86400)

    # 1. Normal active item after 2 half-lives (14 days): 0.8 * (0.5^2) = 0.20
    uri_normal = "viking://resources/project/module_feature.md"
    assessment_normal: DecayAssessment = engine.evaluate_candidate(
        uri=uri_normal,
        raw_score=0.80,
        updated_ts=fourteen_days_ago,
        status="active",
        now_ts=current_ts,
    )
    assert pytest.approx(assessment_normal.decay_factor, abs=0.02) == 0.25
    assert pytest.approx(assessment_normal.adjusted_score, abs=0.02) == 0.20

    # 2. Disputed item penalty: multiplier 0.50 applied
    uri_disputed = "viking://resources/project/disputed_logic.md"
    assessment_disputed: DecayAssessment = engine.evaluate_candidate(
        uri=uri_disputed,
        raw_score=0.80,
        updated_ts=current_ts,  # fresh
        status="disputed",
        now_ts=current_ts,
    )
    assert assessment_disputed.decay_factor == 0.50
    assert assessment_disputed.adjusted_score == 0.40
    assert assessment_disputed.penalty_reason == "marked_disputed_or_unverified"


def test_knowledge_hygiene_engine_metrics():
    """Verify hygiene engine detects dormant items, isolates, and computes score."""
    current_ts = time.time()
    stale_ts = current_ts - (65 * 86400)  # 65 days ago

    mock_items = [
        # Normal active entry
        {
            "uri": "viking://resources/master_memory/core.md",
            "updated_ts": current_ts,
            "call_count": 50,
            "status": "active",
        },
        # Dormant dead-weight entry
        {
            "uri": "viking://resources/old_session/dead_log.txt",
            "updated_ts": stale_ts,
            "call_count": 0,
            "status": "active",
        },
        # Conflicted / superseded entry
        {
            "uri": "viking://resources/old_session/superseded_decision.md",
            "updated_ts": stale_ts,
            "call_count": 1,
            "status": "superseded",
        },
    ]

    engine = KnowledgeHygieneEngine()
    report: HygieneReport = engine.inspect_items(mock_items, dormant_threshold_days=30.0)

    assert report.total_inspected == 3
    assert report.dormant_count >= 1
    assert report.disputed_count >= 1
    assert 0 <= report.health_score <= 100
    assert len(report.recommendations) > 0


def test_retrieval_benchmark_api_endpoints():
    """Verify FastAPI routes for benchmark suites, run, and hygiene report."""
    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="test-user"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. GET /api/v1/retrieval/benchmark/suites
    res_suites = client.get("/api/v1/retrieval/benchmark/suites")
    assert res_suites.status_code == 200
    data_suites = res_suites.json()
    assert data_suites.get("status") == "ok"
    result_suites = data_suites["result"]
    assert "total_queries" in result_suites
    assert "categories" in result_suites
    assert result_suites["total_queries"] == 32

    # 2. POST /api/v1/retrieval/benchmark/run (filtered by category 'symbols')
    res_run = client.post(
        "/api/v1/retrieval/benchmark/run",
        json={"category": "symbols", "top_k": 5},
    )
    assert res_run.status_code == 200
    data_run = res_run.json()
    assert data_run.get("status") == "ok"
    result_run = data_run["result"]
    assert "results" in result_run
    assert "mrr" in result_run
    assert "hit_rate" in result_run
    assert len(result_run["results"]) == 8

    # 3. GET /api/v1/retrieval/hygiene/report
    res_hygiene = client.get("/api/v1/retrieval/hygiene/report")
    assert res_hygiene.status_code == 200
    data_hygiene = res_hygiene.json()
    assert data_hygiene.get("status") == "ok"
    result_hygiene = data_hygiene["result"]
    assert "health_score" in result_hygiene
    assert "dormant_count" in result_hygiene
    assert "total_inspected" in result_hygiene
