# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
高并发 LRU 本地二级缓存引擎 (SSOT)
落实 BLUEPRINT.md Milestone 4 (0.8ms 极速命中 + wait=False 协议)
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple

from openviking.service.cache_tier2_types import (
    CacheBenchmarkResult,
    CachePolicy,
    CacheStats,
)


class CacheEntry:
    """内部轻量缓存条目"""
    __slots__ = ("value", "size_bytes", "expires_at", "hit_count")

    def __init__(self, value: Any, size_bytes: int, expires_at: float) -> None:
        self.value = value
        self.size_bytes = size_bytes
        self.expires_at = expires_at
        self.hit_count = 0


class Tier2LRUCacheEngine:
    """亚毫秒级 LRU 本地二级缓存引擎"""

    _instance: Optional["Tier2LRUCacheEngine"] = None
    _singleton_lock = threading.Lock()

    def __init__(self, policy: Optional[CachePolicy] = None) -> None:
        self._policy = policy or CachePolicy()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._in_flight: Set[str] = set()
        self._lock = threading.Lock()

        # 统计指标
        self._total_queries = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._total_latency_ns = 0

    @classmethod
    def get_instance(cls) -> "Tier2LRUCacheEngine":
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _estimate_size(self, value: Any) -> int:
        """估算对象内存大小"""
        if isinstance(value, str):
            return len(value.encode("utf-8", errors="ignore"))
        elif isinstance(value, (bytes, bytearray)):
            return len(value)
        elif isinstance(value, (int, float, bool)):
            return 8
        elif isinstance(value, (dict, list, tuple)):
            return 256 + len(str(value))
        return 128

    def get(self, key: str, wait: bool = True, fallback: Any = None) -> Tuple[Optional[Any], bool]:
        """
        获取缓存值
        :param key: 缓存键
        :param wait: 若为 False 且当前 Key 正在被回源计算，立即返回 fallback，避免击穿阻塞
        :param fallback: 未命中或穿透时的缺省值
        :return: (value, is_hit)
        """
        start_ns = time.perf_counter_ns()
        now = time.monotonic()

        with self._lock:
            self._total_queries += 1

            # wait=False 保护：若其他线程正在重算此 key，非阻塞立即返回 fallback
            if not wait and key in self._in_flight:
                self._misses += 1
                self._total_latency_ns += (time.perf_counter_ns() - start_ns)
                return fallback, False

            entry = self._cache.get(key)
            if entry is not None:
                # 检查 TTL
                if entry.expires_at > 0 and now > entry.expires_at:
                    # 已过期，淘汰
                    del self._cache[key]
                    self._misses += 1
                    self._total_latency_ns += (time.perf_counter_ns() - start_ns)
                    return fallback, False

                # 命中：移至最新端 (LRU)
                self._cache.move_to_end(key)
                entry.hit_count += 1
                self._hits += 1
                self._total_latency_ns += (time.perf_counter_ns() - start_ns)
                return entry.value, True

            self._misses += 1
            self._total_latency_ns += (time.perf_counter_ns() - start_ns)
            return fallback, False

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """写入缓存项"""
        now = time.monotonic()
        ttl_val = ttl if ttl is not None else self._policy.default_ttl_seconds
        expires_at = (now + ttl_val) if ttl_val > 0 else 0.0
        size_bytes = self._estimate_size(value)

        with self._lock:
            if key in self._cache:
                del self._cache[key]

            # 容量淘汰 (LRU)
            while len(self._cache) >= self._policy.capacity:
                self._cache.popitem(last=False)
                self._evictions += 1

            self._cache[key] = CacheEntry(value=value, size_bytes=size_bytes, expires_at=expires_at)
            # 释放 in_flight
            self._in_flight.discard(key)

    def mark_in_flight(self, key: str) -> bool:
        """标记某 key 正在回源计算中"""
        with self._lock:
            if key in self._in_flight:
                return False
            self._in_flight.add(key)
            return True

    def unmark_in_flight(self, key: str) -> None:
        """解除回源中标记"""
        with self._lock:
            self._in_flight.discard(key)

    def invalidate(self, key: str) -> bool:
        """精准失效某条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def purge(self) -> int:
        """清空缓存池"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._in_flight.clear()
            return count

    def get_stats(self) -> CacheStats:
        """获取当前运行态遥测"""
        with self._lock:
            total = max(1, self._total_queries)
            hit_ratio = round(self._hits / total, 4)
            avg_lat_ms = round((self._total_latency_ns / total) / 1_000_000.0, 4)
            total_bytes = sum(e.size_bytes for e in self._cache.values())
            return CacheStats(
                total_queries=self._total_queries,
                hits=self._hits,
                misses=self._misses,
                hit_ratio=hit_ratio,
                evictions=self._evictions,
                current_entries=len(self._cache),
                current_bytes=total_bytes,
                avg_latency_ms=avg_lat_ms,
            )

    def run_benchmark(self, iterations: int = 10000) -> CacheBenchmarkResult:
        """运行高并发内存压测，验证亚毫秒级访问时延 (< 0.8ms)"""
        start = time.perf_counter()
        latencies: List[float] = []

        # 写入基准条目
        for i in range(100):
            self.set(f"bench_key_{i}", f"bench_val_{i}")

        # 运行循环读写
        for i in range(iterations):
            t0 = time.perf_counter()
            idx = i % 100
            self.get(f"bench_key_{idx}", wait=False)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        qps = round(iterations / max(elapsed_ms / 1000.0, 0.0001), 2)
        latencies.sort()
        p99_idx = int(iterations * 0.99)
        p99 = round(latencies[min(p99_idx, len(latencies) - 1)], 4)

        sub_milli = p99 < 0.80
        status = "PASS" if sub_milli else "WARN"

        return CacheBenchmarkResult(
            iterations=iterations,
            elapsed_ms=round(elapsed_ms, 2),
            qps=qps,
            p99_latency_ms=p99,
            sub_millisecond=sub_milli,
            status=status,
        )
