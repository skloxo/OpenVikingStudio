# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Temporal Decay Dynamics & Hit Frequency Reinforcement Boost.
(Card-37 / v1.6.1)
"""

import math
import time
import pytest
from openviking.retrieve.asymmetric_decay import (
    AsymmetricDecayEngine,
    DecayConfig,
    DecayAssessment,
)


def test_axiom_canonical_decay_immunity():
    """Verify canonical and axiom memories are 100% immune to temporal decay (factor >= 1.0)."""
    engine = AsymmetricDecayEngine()
    current_ts = time.time()
    half_year_ago = current_ts - (180 * 86400)

    # 1. Rule URI prefix axiom immunity
    res1 = engine.evaluate_candidate(
        uri="viking://resources/master_memory/rules/first_principles.md",
        raw_score=0.90,
        updated_ts=half_year_ago,
        active_count=0,
        now_ts=current_ts,
    )
    assert res1.is_immune is True
    assert res1.decay_factor == 1.0
    assert res1.adjusted_score == 0.90

    # 2. Explicit memory_type="canonical" immunity
    res2 = engine.evaluate_candidate(
        uri="viking://resources/project/architecture_invariants.md",
        raw_score=0.85,
        updated_ts=half_year_ago,
        active_count=0,
        memory_type="canonical",
        now_ts=current_ts,
    )
    assert res2.is_immune is True
    assert res2.decay_factor == 1.0
    assert res2.adjusted_score == 0.85


def test_type_differentiated_exponential_decay():
    """Verify canonical (0.0), experience (0.007), event (0.05), and general (0.01) decay curves."""
    engine = AsymmetricDecayEngine()
    now_ts = 1000000.0

    # 60 days passed
    delta_days = 60.0
    updated_ts = now_ts - (delta_days * 86400.0)

    # Experience: lambda = 0.007 -> exp(-0.007 * 60) = exp(-0.42) ~= 0.657
    exp_res = engine.evaluate_candidate(
        uri="viking://resources/experience/bug_fix.md",
        raw_score=1.0,
        updated_ts=updated_ts,
        active_count=0,
        memory_type="experience",
        now_ts=now_ts,
    )
    expected_exp_decay = math.exp(-0.007 * 60.0)
    assert pytest.approx(exp_res.decay_factor, abs=0.03) == expected_exp_decay
    assert exp_res.lambda_val == 0.007

    # Event/Task: lambda = 0.05 -> exp(-0.05 * 60) = exp(-3.0) ~= 0.0498 -> floor 0.05
    event_res = engine.evaluate_candidate(
        uri="viking://resources/events/task_debug.md",
        raw_score=1.0,
        updated_ts=updated_ts,
        active_count=0,
        memory_type="event",
        now_ts=now_ts,
    )
    assert event_res.decay_factor == 0.05
    assert event_res.lambda_val == 0.05

    # General: lambda = 0.01 -> exp(-0.01 * 60) = exp(-0.6) ~= 0.5488
    gen_res = engine.evaluate_candidate(
        uri="viking://resources/notes/meeting.md",
        raw_score=1.0,
        updated_ts=updated_ts,
        active_count=0,
        memory_type="general",
        now_ts=now_ts,
    )
    expected_gen_decay = math.exp(-0.01 * 60.0)
    assert pytest.approx(gen_res.decay_factor, abs=0.03) == expected_gen_decay


def test_hit_frequency_reinforcement_boost():
    """Verify that active retrieval hits (N_hits) actively counteract decay:
    Score_effective = Score_semantic * exp(-lambda * dt) * (1 + beta * log(1 + N_hits))
    """
    config = DecayConfig(beta_hit_boost=0.20)
    engine = AsymmetricDecayEngine(config=config)
    now_ts = 2000000.0
    thirty_days_ago = now_ts - (30 * 86400.0)

    # 1. Experience with 0 hits: decay factor exp(-0.007 * 30) = exp(-0.21) ~= 0.8106
    dormant = engine.evaluate_candidate(
        uri="viking://resources/experience/tool_pattern.md",
        raw_score=0.80,
        updated_ts=thirty_days_ago,
        active_count=0,
        memory_type="experience",
        now_ts=now_ts,
    )
    expected_dormant_decay = math.exp(-0.007 * 30.0)
    assert pytest.approx(dormant.decay_factor, abs=0.02) == round(expected_dormant_decay, 4)
    assert dormant.hit_boost == 1.0

    # 2. Same experience with 10 hits:
    # hit_boost = 1 + 0.20 * ln(1 + 10) = 1 + 0.20 * 2.39789 ~= 1.4796
    # combined factor = 0.8106 * 1.4796 ~= 1.199
    # The active hits counteract the 30-day decay, yielding factor > 1.0!
    active = engine.evaluate_candidate(
        uri="viking://resources/experience/tool_pattern.md",
        raw_score=0.80,
        updated_ts=thirty_days_ago,
        active_count=10,
        memory_type="experience",
        now_ts=now_ts,
    )
    expected_boost = 1.0 + 0.20 * math.log1p(10)
    expected_factor = expected_dormant_decay * expected_boost
    assert pytest.approx(active.hit_boost, abs=0.02) == expected_boost
    assert pytest.approx(active.decay_factor, abs=0.03) == expected_factor
    assert active.adjusted_score > dormant.adjusted_score


def test_status_penalties_with_boost():
    """Verify that superseded and disputed penalties are strictly applied even with high hits."""
    engine = AsymmetricDecayEngine()
    now_ts = time.time()

    # Superseded item with 20 hits
    superseded = engine.evaluate_candidate(
        uri="viking://resources/old_decision.md",
        raw_score=0.90,
        updated_ts=now_ts,
        active_count=20,
        status="superseded",
        now_ts=now_ts,
    )
    # Even if hit_boost is ~1.6, superseded penalty 0.20 is multiplied
    assert superseded.penalty_reason == "superseded_by_newer_memory"
    assert superseded.decay_factor <= 0.40
