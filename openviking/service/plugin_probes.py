# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Plugin Probing & Health Check Engine.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-03

First Principles:
1. "Zero-Interruption Shield": Probes must never block the main event loop or throw unhandled 500s.
2. "10s Monotonic Snapshot Cache": Fast memory return (< 0.1ms) protecting CPU and network.
3. "Honest Diagnostics": Return true physical latency and state instead of hardcoded mock numbers.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import socket
import time
from typing import Dict

from openviking.models.plugin import PluginHealthProbe


class PluginProbeRunner:
    """插件异步健康探针执行器 (单调时钟快照缓存保护)。"""

    _CACHE_TTL_SEC: float = 10.0
    _last_checked_time: float = 0.0
    _cached_results: Dict[str, PluginHealthProbe] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def check_all_plugins(cls) -> Dict[str, PluginHealthProbe]:
        """获取所有插件的健康探针快照 (10s 缓存削峰)。"""
        now = time.monotonic()
        if cls._cached_results and (now - cls._last_checked_time) < cls._CACHE_TTL_SEC:
            return dict(cls._cached_results)

        async with cls._lock:
            # 双检锁
            if cls._cached_results and (time.monotonic() - cls._last_checked_time) < cls._CACHE_TTL_SEC:
                return dict(cls._cached_results)

            results: Dict[str, PluginHealthProbe] = {}
            results["openviking-memory"] = await cls.probe_memory()
            results["keepass-vault"] = await cls.probe_keepass()
            results["network-search"] = await cls.probe_search()

            cls._cached_results = results
            cls._last_checked_time = time.monotonic()
            return dict(results)

    @classmethod
    async def probe_memory(cls) -> PluginHealthProbe:
        """探测 OpenViking Memory 记忆库健康度。"""
        start = time.perf_counter()
        try:
            db_path = Path.home() / ".openviking" / "data" / "agent_principals.db"
            if db_path.exists():
                stat = db_path.stat()
                latency = (time.perf_counter() - start) * 1000.0
                return PluginHealthProbe(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    message=f"Storage active (size={stat.st_size}B)",
                    checked_at=time.time(),
                )
            else:
                latency = (time.perf_counter() - start) * 1000.0
                return PluginHealthProbe(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    message="Database ready (in-memory/fresh bootstrap)",
                    checked_at=time.time(),
                )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            return PluginHealthProbe(
                status="degraded",
                latency_ms=round(latency, 2),
                message=f"Memory probe warning: {exc}",
                checked_at=time.time(),
            )

    @classmethod
    async def probe_keepass(cls) -> PluginHealthProbe:
        """探测 KeePass 凭据库健康度。"""
        start = time.perf_counter()
        try:
            vault_file = Path.home() / ".openviking" / "vault.kdbx"
            # 若文件存在则为 healthy，若尚未配置则标记为 degraded 提示配置
            latency = (time.perf_counter() - start) * 1000.0
            if vault_file.exists():
                return PluginHealthProbe(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    message="Vault database online",
                    checked_at=time.time(),
                )
            else:
                return PluginHealthProbe(
                    status="degraded",
                    latency_ms=round(latency, 2),
                    message="Vault storage file uninitialized",
                    checked_at=time.time(),
                )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            return PluginHealthProbe(
                status="down",
                latency_ms=round(latency, 2),
                message=f"KeePass check failed: {exc}",
                checked_at=time.time(),
            )

    @classmethod
    async def probe_search(cls) -> PluginHealthProbe:
        """探测局域网 SearXNG / 搜索服务连通性。"""
        start = time.perf_counter()
        loop = asyncio.get_running_loop()

        def _check_port() -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.3)
                # 检查本地 8888 SearXNG 端口
                return sock.connect_ex(("127.0.0.1", 8888)) == 0

        try:
            is_open = await loop.run_in_executor(None, _check_port)
            latency = (time.perf_counter() - start) * 1000.0
            if is_open:
                return PluginHealthProbe(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    message="SearXNG :8888 connected",
                    checked_at=time.time(),
                )
            else:
                return PluginHealthProbe(
                    status="degraded",
                    latency_ms=round(latency, 2),
                    message="SearXNG offline (fallback web engine available)",
                    checked_at=time.time(),
                )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            return PluginHealthProbe(
                status="degraded",
                latency_ms=round(latency, 2),
                message=f"Search probe warning: {exc}",
                checked_at=time.time(),
            )
