# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for WikiDehydrationEngine circuit breaker and multi-tier degradation fallback.
Verifies failure tripping, cooldown expiry, half-open recovery, and fast fallback routing.
"""

from unittest.mock import MagicMock, patch
import urllib.error

from openviking.service.wiki_dehydration_engine import (
    DehydrationRequest,
    WikiDehydrationEngine,
)

SAMPLE_PROSE = """
众所周知，在大型系统设计中，降级与熔断机制是保障高可用的基石。
系统必须在外部依赖超时或崩溃时，实现平滑降级，严禁阻塞核心主干链路。
任何情况下都不能返回虚假或者不完整的数据。
"""


def test_circuit_breaker_trips_after_consecutive_failures():
    """Verify circuit breaker trips to OPEN after consecutive remote timeouts."""
    engine = WikiDehydrationEngine()
    engine.reset_circuit_breaker()
    assert engine.is_circuit_open() is False

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        # Attempt 1: Fails both ports (11432, 11433)
        res1 = engine._compress_remote("test segment 1", rate=0.5)
        assert res1 is None
        assert engine._consecutive_remote_failures == 1
        assert engine.is_circuit_open() is False

        # Attempt 2: Fails both ports again -> reaches threshold (2) -> TRIPS
        res2 = engine._compress_remote("test segment 2", rate=0.5)
        assert res2 is None
        assert engine._consecutive_remote_failures == 2
        assert engine.is_circuit_open() is True
        assert engine._circuit_tripped_count == 1

        # Attempt 3: Circuit is OPEN -> Should return None instantly without calling urlopen
        with patch("urllib.request.urlopen") as mock_urlopen:
            res3 = engine._compress_remote("test segment 3", rate=0.5)
            assert res3 is None
            assert mock_urlopen.call_count == 0


def test_circuit_breaker_cooldown_and_half_open_recovery():
    """Verify circuit cooldown allows a half-open probe, which recovers on success."""
    engine = WikiDehydrationEngine()
    engine.reset_circuit_breaker()

    base_time = 2000.0

    with patch("openviking.service.wiki_dehydration_engine.time.monotonic", return_value=base_time):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Timeout")):
            engine._compress_remote("fail 1", rate=0.5)
            engine._compress_remote("fail 2", rate=0.5)
            assert engine.is_circuit_open() is True

        # At t=2015.0 (< 30s cooldown): still OPEN
        with patch("openviking.service.wiki_dehydration_engine.time.monotonic", return_value=base_time + 15.0):
            assert engine.is_circuit_open() is True

        # At t=2035.0 (> 30s cooldown): Half-Open state (is_circuit_open returns False)
        with patch("openviking.service.wiki_dehydration_engine.time.monotonic", return_value=base_time + 35.0):
            assert engine.is_circuit_open() is False

            # Half-open probe succeeds
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b'{"compressed_prompt": "compressed text"}'
            mock_resp.__enter__.return_value = mock_resp

            with patch("urllib.request.urlopen", return_value=mock_resp):
                success_res = engine._compress_remote("test probe", rate=0.5)
                assert success_res == "compressed text"
                assert engine._consecutive_remote_failures == 0
                assert engine._circuit_open_until == 0.0
                assert engine._remote_success_count >= 1


def test_dehydrate_with_open_circuit_uses_fallback_immediately():
    """Verify dehydration request uses fast syntactic pruner when circuit is open."""
    engine = WikiDehydrationEngine()
    engine.reset_circuit_breaker()

    # Manually trip circuit
    engine._consecutive_remote_failures = 2
    engine._circuit_open_until = 9999999999.0
    assert engine.is_circuit_open() is True

    req = DehydrationRequest(content=SAMPLE_PROSE, preserve_structure=True)
    res = engine.dehydrate(req)

    assert "syntactic-pruner (circuit-open fallback)" in res.engine_used
    assert "降级与熔断机制" in res.dehydrated_content
    assert "必须" in res.dehydrated_content
    assert "严禁" in res.dehydrated_content
    assert res.tokens_saved >= 1


def test_dehydration_stats_circuit_metrics():
    """Verify telemetry stats reflect circuit breaker state and manual reset works."""
    engine = WikiDehydrationEngine()
    engine.reset_circuit_breaker()

    stats = engine.get_stats()
    assert stats.circuit_breaker_open is False
    assert stats.consecutive_failures == 0

    # Trip circuit
    engine._record_remote_failure()
    engine._record_remote_failure()
    stats_tripped = engine.get_stats()
    assert stats_tripped.circuit_breaker_open is True
    assert stats_tripped.consecutive_failures == 2
    assert stats_tripped.circuit_tripped_count >= 1

    # Reset
    engine.reset_circuit_breaker()
    stats_reset = engine.get_stats()
    assert stats_reset.circuit_breaker_open is False
    assert stats_reset.consecutive_failures == 0
