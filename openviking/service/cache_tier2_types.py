# Copyright (c) 2026 OpenViking Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0.

"""
高并发 LRU 本地二级缓存引擎强类型 DTO 定义 (SSOT)
落实 BLUEPRINT.md Milestone 4 (0.8ms 极速命中 + wait=False 协议)
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class CachePolicy(BaseModel):
    """缓存池策略配置"""
    model_config = ConfigDict(extra="ignore")

    capacity: int = Field(10000, description="最大条目容量上限")
    max_bytes: int = Field(64 * 1024 * 1024, description="最大内存占用 (默认 64MB)")
    default_ttl_seconds: float = Field(300.0, description="默认过期时间 (秒)")
    enable_wait_false: bool = Field(True, description="开启 wait=False 穿透击穿保护")


class CacheStats(BaseModel):
    """缓存运行态遥测指标"""
    model_config = ConfigDict(extra="ignore")

    total_queries: int = Field(0, description="累计查询次数")
    hits: int = Field(0, description="命中次数")
    misses: int = Field(0, description="未命中次数")
    hit_ratio: float = Field(0.0, description="缓存命中率 (0.0~1.0)")
    evictions: int = Field(0, description="LRU 淘汰驱逐次数")
    current_entries: int = Field(0, description="当前在籍条目数")
    current_bytes: int = Field(0, description="当前内存占用 (bytes)")
    avg_latency_ms: float = Field(0.0, description="平均查询耗时 (ms)")


class CacheBenchmarkResult(BaseModel):
    """高并发基准测试报告"""
    model_config = ConfigDict(extra="ignore")

    iterations: int = Field(..., description="测试执行总迭代次数")
    elapsed_ms: float = Field(..., description="总执行耗时 (ms)")
    qps: float = Field(..., description="每秒吞吐量 (QPS)")
    p99_latency_ms: float = Field(..., description="P99 访问延迟 (ms)")
    sub_millisecond: bool = Field(True, description="是否满足 < 0.8ms 亚毫秒硬契约")
    status: str = Field("PASS", description="基准测试裁决: PASS | WARN | FAIL")
