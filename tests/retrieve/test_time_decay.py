# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for event time-decay ranking mathematics and 3-day protection window.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from openviking.utils.time_decay import (
    DEFAULT_DECAY,
    DEFAULT_SCALE,
    build_time_decay_fusion_spec,
    build_time_decay_post_process_ops,
    parse_duration_ms,
)
from openviking_cli.exceptions import InvalidArgumentError


def test_parse_duration_ms_valid():
    """Verify standard duration strings convert to milliseconds correctly."""
    assert parse_duration_ms("0") == 0
    assert parse_duration_ms("30m") == 30 * 60 * 1000
    assert parse_duration_ms("2h") == 2 * 3600 * 1000
    assert parse_duration_ms("3d") == 3 * 86400 * 1000
    assert parse_duration_ms("7d") == 7 * 86400 * 1000


def test_parse_duration_ms_invalid():
    """Verify invalid format or negative values raise ValueError."""
    with pytest.raises(ValueError, match="must be '0' or a non-negative integer"):
        parse_duration_ms("invalid")

    with pytest.raises(ValueError, match="must be '0' or a non-negative integer"):
        parse_duration_ms("-3d")

    with pytest.raises(ValueError, match="must be '0' or a non-negative integer"):
        parse_duration_ms("10s")  # s is not in m/h/d

    with pytest.raises(ValueError, match="must be '0' or a non-negative integer"):
        parse_duration_ms("2w")


def test_build_time_decay_fusion_spec():
    """Verify score fusion specification format and defaults."""
    spec = build_time_decay_fusion_spec(protection="3d", field="created_at")
    assert spec.field == "created_at"
    assert spec.offset_ms == parse_duration_ms("3d")
    assert spec.scale_ms == parse_duration_ms("7d")
    assert spec.decay == DEFAULT_DECAY
    assert spec.origin_ms > 0


def test_build_time_decay_post_process_ops():
    """Verify post processing operations list structure."""
    origin_dt = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)
    ops = build_time_decay_post_process_ops(protection="3d", origin=origin_dt)
    assert len(ops) == 1
    assert ops[0]["op"] == "score_fusion"
    assert ops[0]["fusion_by"] == "multiply"
    assert ops[0]["addition_score"][0]["offset"] == "3d"
    assert ops[0]["addition_score"][0]["scale"] == DEFAULT_SCALE
    assert ops[0]["addition_score"][0]["decay"] == DEFAULT_DECAY
    assert ops[0]["addition_score"][0]["origin"] == "2026-10-18T12:00:00.000Z"


def test_time_decay_math_protection_and_half_life():
    """
    Mathematical verification of exponential decay with 3-day protection window:
    - delta <= protection (3d): factor = 1.0 (no decay)
    - delta = protection (3d) + scale (7d) = 10d: factor = 0.5 (half-life)
    - delta = protection (3d) + 2 * scale (14d) = 17d: factor = 0.25 (two half-lives)
    """
    now = datetime.now(timezone.utc)
    protection_ms = parse_duration_ms("3d")
    scale_ms = parse_duration_ms("7d")
    decay = 0.5

    def calculate_decay_factor(event_time: datetime) -> float:
        delta_ms = max(0, int((now - event_time).total_seconds() * 1000))
        if delta_ms <= protection_ms:
            return 1.0
        effective_delta = delta_ms - protection_ms
        # Exponential decay: decay ^ (effective_delta / scale)
        return math.pow(decay, effective_delta / scale_ms)

    # 1. Fresh event within 1 day (< 3d protection): 100% factor
    event_1d = now - timedelta(days=1)
    assert calculate_decay_factor(event_1d) == 1.0

    # 2. Event exactly at 2.99 days (< 3d protection): 100% factor
    event_3d_edge = now - timedelta(days=2.99)
    assert calculate_decay_factor(event_3d_edge) == 1.0

    # 3. Event at 10 days (3d protection + 7d half-life): exactly 0.5
    event_10d = now - timedelta(days=10)
    factor_10d = calculate_decay_factor(event_10d)
    assert pytest.approx(factor_10d, rel=1e-5) == 0.5

    # 4. Event at 17 days (3d protection + 14d two half-lives): exactly 0.25
    event_17d = now - timedelta(days=17)
    factor_17d = calculate_decay_factor(event_17d)
    assert pytest.approx(factor_17d, rel=1e-5) == 0.25

    # 5. Future event (skewed clock): clamp to 0 delta, factor = 1.0
    future_event = now + timedelta(hours=2)
    assert calculate_decay_factor(future_event) == 1.0
