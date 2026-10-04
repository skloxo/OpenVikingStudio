# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""System hardware, filesystem, and embedding probes with memory snapshot caching."""

import asyncio
import time
from typing import Any, Optional

from openviking.core.defensive import defensive
from openviking.pyagfs.exceptions import AGFSInvalidOperationError, AGFSNotSupportedError
from openviking.storage.viking_fs import get_viking_fs
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

_GPU_CACHE: Optional[tuple[float, dict]] = None
_SYS_RES_CACHE: Optional[tuple[float, dict]] = None
_SYSTEM_TELEMETRY_CACHE_TTL = 5.0  # 5秒内存快照缓存，阻断高频重复的 nvidia-smi 进程分叉与 /proc 读取
_LAST_CPU_TIMES: Optional[tuple[float, float]] = None


def _is_ready_check_ok(value) -> bool:
    """Return whether one readiness check value represents a healthy state."""
    if isinstance(value, dict):
        status = value.get("status")
        if status not in ("ok", "not_configured", "not_supported"):
            return False
        nested = value.get("checks")
        if nested is None:
            return True
        return all(_is_ready_check_ok(item) for item in nested.values())
    return value in ("ok", "not_configured", "not_supported")


async def _probe_agfs_readiness() -> dict[str, object]:
    """Return structured AGFS readiness, including multi-write sync health when available."""
    viking_fs = get_viking_fs()
    checks: dict[str, object] = {}

    await viking_fs.ls("viking://", ctx=None)
    checks["filesystem"] = "ok"

    try:
        await viking_fs.system_sync_status("viking://", ctx=None)
        checks["multiwrite_sync"] = "ok"
    except (AGFSInvalidOperationError, AGFSNotSupportedError):
        checks["multiwrite_sync"] = "not_supported"

    return {"status": "ok", "checks": checks}


async def _embedding_probe(embedder) -> str:
    """Quick embedding probe: embed a single token and check for errors."""
    from openviking.models.embedder.base import embed_compat

    try:
        await embed_compat(embedder, "ok", is_query=True)
        return "ok"
    except Exception as e:
        provider = getattr(embedder, "provider", "unknown")
        model = getattr(embedder, "model_name", "unknown")
        return f"error: provider={provider} model={model}: {e}"


async def probe_gpu_telemetry() -> dict[str, Any]:
    """Return real GPU VRAM usage and compute utilization via nvidia-smi probe."""
    global _GPU_CACHE
    now = time.monotonic()
    if _GPU_CACHE is not None and (now - _GPU_CACHE[0]) < _SYSTEM_TELEMETRY_CACHE_TTL:
        return _GPU_CACHE[1]

    err_reason: Optional[str] = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
        if proc.returncode == 0 and stdout:
            line = stdout.decode().strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                used_mb = float(parts[0])
                total_mb = float(parts[1])
                gpu_util = float(parts[2])
                res = {
                    "available": True,
                    "used_gb": round(used_mb / 1024.0, 2),
                    "total_gb": round(total_mb / 1024.0, 2),
                    "gpu_percent": round(gpu_util, 1),
                    "error": None,
                }
                _GPU_CACHE = (now, res)
                return res
        else:
            err_reason = f"nvidia-smi exit code {proc.returncode}"
    except Exception as e:
        err_reason = str(e)
        logger.debug(f"GPU telemetry probe unavailable: {e}")

    unavailable = {
        "available": False,
        "used_gb": None,
        "total_gb": None,
        "gpu_percent": None,
        "error": err_reason or "nvidia-smi unavailable",
    }
    _GPU_CACHE = (now, unavailable)
    return unavailable


@defensive(
    domain="system",
    name="read_host_mem",
    fallback={"available": False, "total_gb": None, "used_gb": None, "memory_percent": None},
    log_level="debug",
)
def _read_host_mem() -> dict[str, Any]:
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = int(parts[1].strip().split()[0])
        total_kb = mem.get("MemTotal", 0)
        avail_kb = mem.get("MemAvailable", 0)
        used_kb = max(0, total_kb - avail_kb)
        mem_percent = round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0.0
        return {
            "available": True,
            "total_gb": round(total_kb / (1024 * 1024), 2),
            "used_gb": round(used_kb / (1024 * 1024), 2),
            "memory_percent": mem_percent,
        }
    except Exception as e:
        logger.debug(f"Host meminfo probe unavailable: {e}")
        return {"available": False, "total_gb": None, "used_gb": None, "memory_percent": None}


@defensive(
    domain="system",
    name="read_host_cpu",
    fallback=0.0,
    log_level="debug",
)
def _read_host_cpu() -> float:
    global _LAST_CPU_TIMES
    try:
        with open("/proc/stat") as f:
            cpu_line = f.readline()
        fields = [float(x) for x in cpu_line.split()[1:8]]
        if len(fields) >= 4:
            idle = fields[3]
            total = sum(fields)
            if _LAST_CPU_TIMES:
                prev_idle, prev_total = _LAST_CPU_TIMES
                diff_idle = idle - prev_idle
                diff_total = total - prev_total
                _LAST_CPU_TIMES = (idle, total)
                if diff_total > 0:
                    cpu_percent = round((1.0 - (diff_idle / diff_total)) * 100, 1)
                    return max(0.0, min(100.0, cpu_percent))
            _LAST_CPU_TIMES = (idle, total)
            return round((1.0 - (idle / total)) * 100, 1) if total > 0 else 0.0
    except Exception as e:
        logger.debug(f"Host cpu stat probe unavailable: {e}")
    return 0.0


def probe_system_host_resources() -> dict[str, Any]:
    """Return real host CPU, memory, and system resource metrics with snapshot caching."""
    global _SYS_RES_CACHE
    now = time.monotonic()
    if _SYS_RES_CACHE is not None and (now - _SYS_RES_CACHE[0]) < _SYSTEM_TELEMETRY_CACHE_TTL:
        return _SYS_RES_CACHE[1]

    mem_info = _read_host_mem()
    cpu_percent = _read_host_cpu()
    mem_ok = mem_info.get("available", True)
    res = {
        "status": "ok" if mem_ok else "degraded",
        "cpu_percent": cpu_percent,
        "memory_available": mem_ok,
        "memory_percent": mem_info.get("memory_percent"),
        "memory_used_gb": mem_info.get("used_gb"),
        "memory_total_gb": mem_info.get("total_gb"),
    }
    _SYS_RES_CACHE = (now, res)
    return res
