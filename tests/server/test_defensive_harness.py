# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Defensive Code Annotation & Telemetry Harness (Card-Harness-DefensiveAndPurge)."""

import asyncio
import pytest
from openviking.core.defensive import (
    DefensiveRegistry,
    defensive,
    get_defensive_telemetry,
)


@pytest.fixture(autouse=True)
def clean_defensive_registry():
    """Reset registry before each test case."""
    DefensiveRegistry.get_instance().reset_for_testing()
    yield
    DefensiveRegistry.get_instance().reset_for_testing()


def test_sync_defensive_success():
    call_count = 0

    @defensive(domain="test", name="sync_success", fallback="fallback_val")
    def sample_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    res = sample_func(21)
    assert res == 42
    assert call_count == 1

    telemetry = get_defensive_telemetry()
    assert telemetry["total_registered"] >= 1
    site = next(s for s in telemetry["sites"] if s["name"] == "sync_success")
    assert site["executions"] == 1
    assert site["fallbacks"] == 0


def test_sync_defensive_retry_and_succeed():
    attempts = 0

    @defensive(
        domain="test",
        name="sync_retry",
        retry_count=2,
        retry_backoff=0.01,
        fallback="failed",
    )
    def flappy_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("Temporary network blip")
        return "ok"

    res = flappy_func()
    assert res == "ok"
    assert attempts == 2

    telemetry = get_defensive_telemetry()
    assert telemetry["total_executions"] == 1
    assert telemetry["total_fallbacks"] == 0


def test_sync_defensive_exhaust_and_fallback_value():
    attempts = 0

    @defensive(
        domain="sqlite",
        name="sync_fallback",
        retry_count=1,
        retry_backoff=0.01,
        fallback={"status": "degraded"},
    )
    def always_failing():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("Database locked")

    res = always_failing()
    assert res == {"status": "degraded"}
    assert attempts == 2  # initial + 1 retry

    telemetry = get_defensive_telemetry()
    assert telemetry["total_executions"] == 1
    assert telemetry["total_fallbacks"] == 1
    assert telemetry["overall_fallback_rate"] == 1.0
    assert len(telemetry["recent_triggers"]) == 1
    assert telemetry["recent_triggers"][0]["exception_type"] == "RuntimeError"


def test_sync_defensive_callable_fallback():
    @defensive(
        domain="test",
        name="callable_fallback",
        fallback=lambda: ["fallback", "list"],
    )
    def boom():
        raise ValueError("Invalid state")

    res = boom()
    assert res == ["fallback", "list"]


@pytest.mark.asyncio
async def test_async_defensive_success():
    @defensive(domain="async_test", name="async_ok", fallback=None)
    async def async_sample(val: str) -> str:
        await asyncio.sleep(0.01)
        return val.upper()

    res = await async_sample("hello")
    assert res == "HELLO"

    telemetry = get_defensive_telemetry()
    assert telemetry["total_registered"] >= 1
    site = next(s for s in telemetry["sites"] if s["name"] == "async_ok")
    assert site["executions"] == 1
    assert site["fallbacks"] == 0


@pytest.mark.asyncio
async def test_async_defensive_retry_and_fallback():
    attempts = 0

    @defensive(
        domain="async_test",
        name="async_fail",
        retry_count=2,
        retry_backoff=0.01,
        fallback=(0.0, None),
    )
    async def failing_coro():
        nonlocal attempts
        attempts += 1
        await asyncio.sleep(0.005)
        raise TimeoutError("Socket timeout")

    res = await failing_coro()
    assert res == (0.0, None)
    assert attempts == 3  # 1 initial + 2 retries

    telemetry = get_defensive_telemetry()
    assert telemetry["total_executions"] == 1
    assert telemetry["total_fallbacks"] == 1
    assert telemetry["recent_triggers"][0]["domain"] == "async_test"
    assert telemetry["recent_triggers"][0]["exception_type"] == "TimeoutError"


def test_system_host_mem_defensive_registered():
    from openviking.server.routers.system import _read_host_mem, _read_host_cpu

    # Call the functions to verify defensive wrappers
    mem = _read_host_mem()
    assert isinstance(mem, dict)
    assert "memory_percent" in mem

    cpu = _read_host_cpu()
    assert isinstance(cpu, float)

    telemetry = get_defensive_telemetry()
    site_names = [s["name"] for s in telemetry["sites"]]
    assert "read_host_mem" in site_names
    assert "read_host_cpu" in site_names
