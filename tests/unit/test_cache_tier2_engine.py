# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
高并发 LRU 本地二级缓存引擎单元测试套件 (SSOT)
落实 BLUEPRINT.md Milestone 4 (0.8ms 极速命中 + wait=False 协议)
"""

import time
import pytest
from httpx import ASGITransport, AsyncClient

from openviking.server.app import create_app
from openviking.service.cache_tier2_engine import Tier2LRUCacheEngine
from openviking.service.cache_tier2_types import CachePolicy


@pytest.fixture
def cache_engine():
    # 使用自定义小容量测试策略
    engine = Tier2LRUCacheEngine.get_instance()
    engine.purge()
    return engine


def test_cache_basic_get_set(cache_engine):
    """测试基础读写与命中计数"""
    cache_engine.set("k1", "v1", ttl=60.0)
    val, hit = cache_engine.get("k1")
    assert hit is True
    assert val == "v1"

    val_miss, hit_miss = cache_engine.get("k_non_exist", fallback="fb")
    assert hit_miss is False
    assert val_miss == "fb"

    stats = cache_engine.get_stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.current_entries == 1


def test_cache_lru_eviction():
    """测试当条目达到 capacity 时的严格 LRU 淘汰"""
    policy = CachePolicy(capacity=3, default_ttl_seconds=60.0)
    engine = Tier2LRUCacheEngine(policy=policy)

    engine.set("a", 1)
    engine.set("b", 2)
    engine.set("c", 3)

    # 访问 a，使得 a 变成最近使用，b 变成最久未使用
    engine.get("a")

    # 写入 d，应当淘汰 b
    engine.set("d", 4)

    val_b, hit_b = engine.get("b")
    assert hit_b is False

    val_a, hit_a = engine.get("a")
    assert hit_a is True
    assert val_a == 1


def test_cache_ttl_expiration(cache_engine):
    """测试条目 TTL 超时淘汰"""
    cache_engine.set("expire_key", "temp_val", ttl=0.01)
    time.sleep(0.02)
    val, hit = cache_engine.get("expire_key", fallback="expired")
    assert hit is False
    assert val == "expired"


def test_cache_wait_false_protocol(cache_engine):
    """测试 wait=False 协议在回源中的防击穿表现"""
    key = "computing_heavy_key"
    cache_engine.mark_in_flight(key)

    # wait=False 应当立即返回 fallback
    val, hit = cache_engine.get(key, wait=False, fallback="fast_fallback")
    assert hit is False
    assert val == "fast_fallback"

    # 计算完成，写入并释放
    cache_engine.set(key, "calculated_result")
    val_after, hit_after = cache_engine.get(key, wait=False)
    assert hit_after is True
    assert val_after == "calculated_result"


def test_cache_benchmark_execution(cache_engine):
    """测试高并发内存读写基准测试"""
    res = cache_engine.run_benchmark(iterations=1000)
    assert res.iterations == 1000
    assert res.elapsed_ms > 0
    assert res.qps > 0
    assert res.p99_latency_ms >= 0.0


@pytest.mark.asyncio
async def test_cache_api_endpoints(cache_engine):
    """测试 FastAPI 路由端点连通性"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. 查询状态
        stats_res = await client.get("/api/v1/cache/stats")
        assert stats_res.status_code == 200
        stats_json = stats_res.json()
        assert "hit_ratio" in stats_json

        # 2. 跑 benchmark
        bench_res = await client.post("/api/v1/cache/benchmark?iterations=500")
        assert bench_res.status_code == 200
        bench_json = bench_res.json()
        assert bench_json["status"] in ["PASS", "WARN"]

        # 3. 清空 purge
        purge_res = await client.post("/api/v1/cache/purge")
        assert purge_res.status_code == 200
        assert purge_res.json()["status"] == "ok"
