# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Search Key Rotator, Credit Extractor & Audit Logger.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-SEARCH-ROTATOR

First Principles:
1. "Zero Credential Exposure": Real keys are masked into 8-char SHA256 fingerprints.
2. "Authoritative Credit Extraction": Prioritize official HTTP headers/body over hardcoded estimates.
3. "Round-Robin with Failover": 429 rate limit triggers 60s cooldown and instant key failover.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from openviking.service.search_accounting_store import SearchAccountingStore
from openviking_cli.utils import get_logger

logger = get_logger(__name__)


class SearchKeyItem:
    """单个搜索 API Key 的元数据与运行态指标。"""

    def __init__(
        self,
        key_id: str,
        engine: str,
        alias: str,
        api_key: str,
        monthly_quota: float,
    ):
        self.key_id = key_id
        self.engine = engine  # 'keenable' | 'exa' | 'tavily'
        self.alias = alias
        self.api_key = api_key
        self.monthly_quota = monthly_quota
        self.fingerprint = self._compute_fingerprint(engine, api_key)
        self.status = "ready"  # ready | active | rate_limited | exhausted
        self.cooldown_until = 0.0
        self.total_calls = 0
        self.failed_calls = 0

    @staticmethod
    def _compute_fingerprint(engine: str, key: str) -> str:
        prefix_map = {"keenable": "kb", "exa": "exa", "tavily": "tv"}
        pfx = prefix_map.get(engine.lower(), engine[:3].lower())
        h = hashlib.sha256(key.strip().encode("utf-8")).hexdigest()[:8]
        return f"{pfx}_{h}"

    def is_available(self) -> bool:
        """检查 Key 当前是否脱离 429 冷却与配额耗尽。"""
        if self.status == "exhausted":
            return False
        if self.status == "rate_limited":
            if time.monotonic() > self.cooldown_until:
                self.status = "ready"
                return True
            return False
        return True

    def mark_rate_limited(self, cooldown_sec: float = 60.0) -> None:
        """标记该 Key 进入 429 冷却保护。"""
        self.status = "rate_limited"
        self.cooldown_until = time.monotonic() + cooldown_sec
        logger.warning(
            "[SEARCH_KEY_COOLDOWN] fp=%s engine=%s entered %ss cooldown",
            self.fingerprint,
            self.engine,
            cooldown_sec,
        )


class SearchKeyRotator:
    """26-Key 智能轮询器、权威积分抽取器与审计记录器 (单例模式)。"""

    _instance: Optional[SearchKeyRotator] = None
    _lock = threading.Lock()

    def __init__(self, config_path: Optional[Path] = None):
        self._keys_by_engine: Dict[str, List[SearchKeyItem]] = {
            "keenable": [],
            "exa": [],
            "tavily": [],
        }
        self._index_by_engine: Dict[str, int] = {
            "keenable": 0,
            "exa": 0,
            "tavily": 0,
        }
        self._keys_lock = threading.Lock()
        self._store = SearchAccountingStore.get_instance()
        self._load_keys(config_path)

    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> SearchKeyRotator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config_path=config_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _load_keys(self, config_path: Optional[Path] = None) -> None:
        """从本地凭据存储加载 Key 矩阵。"""
        path = config_path or (
            Path.home() / ".openviking" / "data" / "search" / "search_keys.json"
        )
        if not path.exists():
            logger.info("Search keys config not found at %s, using env fallbacks", path)
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self._keys_lock:
                for eng in ("keenable", "exa", "tavily"):
                    items = data.get(eng, [])
                    self._keys_by_engine[eng] = [
                        SearchKeyItem(
                            key_id=f"{eng}-{idx+1}",
                            engine=eng,
                            alias=str(it.get("alias", f"acc_{idx+1}")),
                            api_key=str(it.get("key", "")),
                            monthly_quota=float(it.get("monthly_quota", 1000.0)),
                        )
                        for idx, it in enumerate(items)
                        if it.get("key")
                    ]
            logger.info(
                "SearchKeyRotator loaded %d Keenable, %d Exa, %d Tavily keys",
                len(self._keys_by_engine["keenable"]),
                len(self._keys_by_engine["exa"]),
                len(self._keys_by_engine["tavily"]),
            )
        except Exception as exc:
            logger.error("Failed to load search keys from %s: %s", path, exc)

    def get_next_key(self, engine: str) -> Optional[SearchKeyItem]:
        """Round-Robin 获取下一个就绪的 Key。若所有 Key 均在冷却中则降级返回冷却时间最短者。"""
        engine_lower = engine.lower()
        with self._keys_lock:
            key_list = self._keys_by_engine.get(engine_lower, [])
            if not key_list:
                return None

            total = len(key_list)
            start_idx = self._index_by_engine[engine_lower]

            # 遍历一轮寻找当前可用的 Key
            for offset in range(total):
                idx = (start_idx + offset) % total
                candidate = key_list[idx]
                if candidate.is_available():
                    self._index_by_engine[engine_lower] = (idx + 1) % total
                    return candidate

            # 全部处于冷却中，选取冷却最早解除的 Key
            fallback = min(key_list, key=lambda k: k.cooldown_until)
            return fallback

    @staticmethod
    def extract_authoritative_credits(
        engine: str,
        tool_name: str,
        status_code: int,
        headers: Dict[str, str],
        body: Optional[Any] = None,
    ) -> float:
        """从官方 HTTP 响应头或响应体中提取权威消耗积分 (Credits / Cost)。

        若官方未返回，根据官方公布的基准收费标准物理计算。
        """
        if status_code != 200:
            return 0.0

        eng = engine.lower()
        norm_headers = {k.lower(): v for k, v in headers.items()}

        # 1. Tavily 引擎
        if eng == "tavily":
            # 优先从响应体提取
            if isinstance(body, dict):
                if "credits" in body and isinstance(body["credits"], (int, float)):
                    return float(body["credits"])
                if "usage" in body and isinstance(body["usage"], dict):
                    if "credits" in body["usage"]:
                        return float(body["usage"]["credits"])

            # 官方响应头回传
            if "x-tavily-credits-used" in norm_headers:
                try:
                    return float(norm_headers["x-tavily-credits-used"])
                except ValueError:
                    pass

            # 官方物理规则兜底
            if "advanced" in tool_name.lower() or "deep" in tool_name.lower():
                return 2.0  # 高级搜索 2 分
            if "extract" in tool_name.lower():
                return 1.0  # 每 5 链接基础提取 1 分
            if "crawl" in tool_name.lower():
                return 3.0  # crawl (map + extract) 约 3 分
            return 1.0  # 基础搜索 1 分

        # 2. Keenable 引擎
        elif eng == "keenable":
            for hkey in ("x-credits-used", "x-credit-cost", "x-request-cost"):
                if hkey in norm_headers:
                    try:
                        return float(norm_headers[hkey])
                    except ValueError:
                        pass
            if isinstance(body, dict) and "credits_used" in body:
                return float(body["credits_used"])
            return 1.0  # Keenable 每次调用标准记账 1.0 次

        # 3. Exa 引擎
        elif eng == "exa":
            for hkey in ("x-exa-cost", "x-exa-credits"):
                if hkey in norm_headers:
                    try:
                        return float(norm_headers[hkey])
                    except ValueError:
                        pass
            if isinstance(body, dict):
                if "cost" in body and isinstance(body["cost"], (int, float)):
                    return float(body["cost"])
            # Exa 官方规则兜底
            if "answer" in tool_name.lower() or "qna" in tool_name.lower():
                return 0.005  # $0.005/解答
            return 0.004  # $0.004/请求

        # 本地引擎 (SearXNG / Crawl4AI)
        return 0.0

    def record_usage_audit(
        self,
        engine: str,
        tool_name: str,
        key_item: Optional[SearchKeyItem],
        status_code: int,
        credits_cost: float,
        latency_ms: float,
        error_msg: str = "",
    ) -> None:
        """记录调用流水账并打印脱敏审计日志。"""
        fp = key_item.fingerprint if key_item else f"local_{engine[:4]}"
        if key_item:
            key_item.total_calls += 1
            if status_code != 200:
                key_item.failed_calls += 1
            if status_code == 429:
                key_item.mark_rate_limited(60.0)

        # 1. 日志模块标准化输出 (脱敏安全)
        logger.info(
            "[SEARCH_KEY_USAGE] fp=%s engine=%s tool=%s status=%d credits=%.4f latency=%.1fms",
            fp,
            engine,
            tool_name,
            status_code,
            credits_cost,
            latency_ms,
        )

        # 2. 物理流水落盘入库
        try:
            self._store.record_usage(
                key_fingerprint=fp,
                engine=engine,
                tool_name=tool_name,
                status_code=status_code,
                credits_cost=credits_cost,
                latency_ms=latency_ms,
                error_msg=error_msg,
            )
        except Exception as exc:
            logger.error("Failed to write search usage to store: %s", exc)

    def get_key_health_overview(self) -> Dict[str, Any]:
        """获取全量 26 个 Key 的微缩健康矩阵与月度汇总 (直出前端大盘)。"""
        monthly_data = self._store.get_monthly_summary()
        summary_by_fp = {row["key_fingerprint"]: row for row in monthly_data}

        result_matrix: List[Dict[str, Any]] = []
        with self._keys_lock:
            for engine, keys in self._keys_by_engine.items():
                for k in keys:
                    metrics = summary_by_fp.get(k.fingerprint, {})
                    total_calls = metrics.get("total_calls", 0)
                    total_credits = metrics.get("total_credits", 0.0)
                    rate_limits = metrics.get("rate_limit_calls", 0)
                    last_call = metrics.get("last_call_at", "--")

                    # 判定胶囊状态: ready | active | rate_limited | exhausted
                    status = k.status
                    if status == "ready" and total_calls > 0:
                        status = "active"

                    result_matrix.append(
                        {
                            "key_id": k.key_id,
                            "engine": k.engine,
                            "alias": k.alias,
                            "fingerprint": k.fingerprint,
                            "status": status,
                            "total_calls": total_calls,
                            "total_credits": total_credits,
                            "monthly_quota": k.monthly_quota,
                            "rate_limit_calls": rate_limits,
                            "last_call_at": last_call,
                        }
                    )

        # 计算三大引擎水位汇总
        watermarks = {
            "keenable": {
                "used_calls": sum(
                    m["total_calls"] for m in result_matrix if m["engine"] == "keenable"
                ),
                "total_quota": 800000,
                "unit": "次",
            },
            "exa": {
                "used_credits": round(
                    sum(
                        m["total_credits"] for m in result_matrix if m["engine"] == "exa"
                    ),
                    3,
                ),
                "total_quota": 90.0,
                "unit": "$",
            },
            "tavily": {
                "used_credits": round(
                    sum(
                        m["total_credits"]
                        for m in result_matrix
                        if m["engine"] == "tavily"
                    ),
                    1,
                ),
                "total_quota": 9000,
                "unit": "积分",
            },
        }

        return {
            "total_keys": len(result_matrix),
            "keys": result_matrix,
            "watermarks": watermarks,
            "updated_at": time.time(),
        }
