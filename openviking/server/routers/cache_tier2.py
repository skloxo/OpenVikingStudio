# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
高并发 LRU 本地二级缓存 REST API 路由 (SSOT)
落实 BLUEPRINT.md Milestone 4 (0.8ms 极速命中 + wait=False 协议)
"""

from fastapi import APIRouter, HTTPException, Query
from openviking.service.cache_tier2_engine import Tier2LRUCacheEngine
from openviking.service.cache_tier2_types import CacheBenchmarkResult, CacheStats

router = APIRouter(prefix="/api/v1/cache", tags=["tier2-cache"])


@router.get("/stats", response_model=CacheStats)
async def get_cache_stats() -> CacheStats:
    """获取本地二级缓存池当前运行态指标"""
    engine = Tier2LRUCacheEngine.get_instance()
    return engine.get_stats()


@router.post("/purge")
async def purge_cache() -> dict:
    """清空本地二级缓存池"""
    engine = Tier2LRUCacheEngine.get_instance()
    cleared = engine.purge()
    return {"status": "ok", "message": f"Successfully purged {cleared} cache entries"}


@router.post("/benchmark", response_model=CacheBenchmarkResult)
async def run_cache_benchmark(
    iterations: int = Query(10000, ge=100, le=100000, description="并发压测迭代次数")
) -> CacheBenchmarkResult:
    """运行本地内存读写基准测试并评估 < 0.8ms 极速命中与 QPS 吞吐"""
    try:
        engine = Tier2LRUCacheEngine.get_instance()
        return engine.run_benchmark(iterations=iterations)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cache benchmark failed: {str(exc)}")


@router.delete("/entry/{key}")
async def invalidate_entry(key: str) -> dict:
    """精准失效指定缓存条目"""
    engine = Tier2LRUCacheEngine.get_instance()
    removed = engine.invalidate(key)
    return {"status": "ok", "key": key, "invalidated": removed}
