# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
ModelsObserver: Multi-model system observability tool.

Observes and reports token usage across VLM, Embedding, Rerank, and Compressor models.
Strictly differentiates active models (configured in ov.conf) from archived/historical models.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from openviking.storage.observers.base_observer import BaseObserver
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_USAGE_FILE = Path(os.path.expanduser("~/.openviking/models_token_usage.json"))

# Monotonic clock snapshot cache (SSOT) to eliminate repeated disk and SQLite queries
_CACHE_TTL = float(os.getenv("OPENVIKING_OBSERVER_CACHE_TTL", "5.0"))
_CACHED_SNAPSHOTS: Dict[Tuple[Tuple[str, Tuple[str, str]], ...], Tuple[float, Dict[str, List[Dict[str, Any]]]]] = {}
_CACHE_LOCK = threading.Lock()


def _read_persistent_usage() -> Dict[str, Any]:
    """Read persistent token usage from ~/.openviking/models_token_usage.json."""
    if not _DEFAULT_USAGE_FILE.is_file():
        return {}
    try:
        with open(_DEFAULT_USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.debug(f"Error reading persistent usage file: {e}")
        return {}


def _get_telemetry_model_usage() -> Dict[str, Any]:
    """Fetch model usage from SQLite TelemetryStore (SSOT)."""
    try:
        from openviking.telemetry.telemetry_store import TelemetryStore

        ts = TelemetryStore.get_instance()
        return ts.get_model_usage_by_window(window="all").get("by_model_type", {})
    except Exception as e:
        logger.debug(f"Failed to query model usage from TelemetryStore: {e}")
        return {}


class ModelsObserver(BaseObserver):
    """
    Observability observer for multi-model token usage monitoring.

    Groups active models by domain (VLM, Embedding, Rerank, Compressor) and archives legacy models.
    """

    def __init__(
        self,
        vlm_instance: Optional[Any] = None,
        embedding_instance: Optional[Any] = None,
        rerank_instance: Optional[Any] = None,
        compressor_instance: Optional[Any] = None,
    ):
        self._vlm_instance = vlm_instance
        self._embedding_instance = embedding_instance
        self._rerank_instance = rerank_instance
        self._compressor_instance = compressor_instance

    def _get_model_name(self, instance: Optional[Any], default_name: str) -> str:
        """Extract model name from an instance with fallbacks."""
        if not instance:
            return default_name
        model = getattr(instance, "model_name", getattr(instance, "model", None))
        if not model and hasattr(instance, "config"):
            model = getattr(instance.config, "model", None)
        return str(model or default_name)

    def _get_active_identities(self) -> Dict[str, Tuple[str, str]]:
        """Return dict of category -> (model_name, provider) for configured active models."""
        active: Dict[str, Tuple[str, str]] = {}
        if self._vlm_instance:
            m = self._get_model_name(self._vlm_instance, "mux-flash")
            p = getattr(self._vlm_instance, "provider", None) or "openai"
            active["VLM"] = (m, p)
        if self._embedding_instance:
            m = self._get_model_name(self._embedding_instance, "qwen3-vl-emb")
            p = getattr(self._embedding_instance, "provider", None) or "openai"
            active["Embedding"] = (m, p)
        if self._rerank_instance:
            m = self._get_model_name(self._rerank_instance, "qwen3-vl-rer")
            p = getattr(self._rerank_instance, "provider", None) or "openai"
            active["Rerank"] = (m, p)
        if self._compressor_instance is not None:
            m = self._get_model_name(
                self._compressor_instance,
                "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
            )
            p = getattr(self._compressor_instance, "provider", None) or "local"
            active["Compressor"] = (m, p)
        return active

    def _collect_all_records(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Merge all usage records from Telemetry SQLite, memory instances, and persistent file."""
        merged: Dict[Tuple[str, str], Dict[str, Any]] = {}

        def _record_key(m: str, p: str) -> Tuple[str, str]:
            return (m.strip(), p.strip() if p else "openai")

        def _merge_row(m: str, p: str, calls: int, prompt: int, completion: int, total: int, updated: Any):
            key = _record_key(m, p)
            ts_str = str(updated)
            if isinstance(updated, (int, float)) and updated > 0:
                try:
                    ts_str = datetime.fromtimestamp(updated).isoformat()
                except Exception:
                    ts_str = str(updated)

            if key not in merged:
                merged[key] = {
                    "Model": m,
                    "Provider": p or "openai",
                    "Calls": calls,
                    "Prompt": prompt,
                    "Completion": completion,
                    "Total": total if total > 0 else (prompt + completion),
                    "Last Updated": ts_str,
                }
            else:
                curr = merged[key]
                if calls > curr["Calls"]:
                    curr["Calls"] = calls
                    curr["Prompt"] = prompt
                    curr["Completion"] = completion
                    curr["Total"] = total if total > 0 else (prompt + completion)
                    curr["Last Updated"] = ts_str or curr["Last Updated"]

        # 1. TelemetryStore SQLite
        for _, prov_map in _get_telemetry_model_usage().items():
            for m_name, p_data in prov_map.items():
                for p_name, u in p_data.items():
                    _merge_row(
                        m=m_name,
                        p=p_name,
                        calls=u.get("call_count", 0),
                        prompt=u.get("prompt_tokens", 0),
                        completion=u.get("completion_tokens", 0),
                        total=u.get("total_tokens", 0),
                        updated=u.get("last_updated", "--"),
                    )

        # 2. In-memory instance usage
        for inst in (self._vlm_instance, self._embedding_instance, self._rerank_instance, self._compressor_instance):
            if not inst:
                continue
            u_data = None
            if hasattr(inst, "get_token_usage"):
                try:
                    u_data = inst.get_token_usage()
                except Exception as e:
                    logger.debug(f"Failed get_token_usage: {e}")
            elif hasattr(inst, "_token_tracker"):
                try:
                    u_data = inst._token_tracker.to_dict()
                except Exception as e:
                    logger.debug(f"Failed _token_tracker: {e}")

            if u_data and isinstance(u_data.get("usage_by_model"), dict):
                for m_name, m_info in u_data["usage_by_model"].items():
                    for p_name, p_info in m_info.get("usage_by_provider", {}).items():
                        _merge_row(
                            m=m_name,
                            p=p_name,
                            calls=p_info.get("call_count", 0),
                            prompt=p_info.get("prompt_tokens", 0),
                            completion=p_info.get("completion_tokens", 0),
                            total=p_info.get("total_tokens", 0),
                            updated=p_info.get("last_updated", "--"),
                        )

        # 3. Persistent JSON file
        persistent = _read_persistent_usage()
        for m_name, m_info in persistent.get("usage_by_model", {}).items():
            for p_name, p_info in m_info.get("usage_by_provider", {}).items():
                _merge_row(
                    m=m_name,
                    p=p_name,
                    calls=p_info.get("call_count", 0),
                    prompt=p_info.get("prompt_tokens", 0),
                    completion=p_info.get("completion_tokens", 0),
                    total=p_info.get("total_tokens", 0),
                    updated=p_info.get("last_updated", "--"),
                )

        return merged

    @staticmethod
    def _get_model_domain(model_name: str) -> str:
        """Classify any model into its functional domain: Rerank, Embedding, Compressor, or VLM."""
        nl = model_name.strip().lower()
        if "rerank" in nl or "rer" in nl:
            return "Rerank"
        if "embed" in nl or "emb" in nl:
            return "Embedding"
        if "lingua" in nl or "compress" in nl:
            return "Compressor"
        return "VLM"

    def _is_active_model(self, model_name: str, domain: str, active_map: Dict[str, Tuple[str, str]]) -> bool:
        """Check if model matches the active model configured for this domain."""
        if domain not in active_map:
            return False
        act_model, _ = active_map[domain]
        act_lower = act_model.strip().lower()
        nl = model_name.strip().lower()
        if nl == act_lower:
            return True
        if domain == "Rerank" and act_lower in ("qwen3-vl-rer", "qwen3-vl-reranker") and nl in ("qwen3-vl-rer", "qwen3-vl-reranker"):
            return True
        if domain == "Compressor" and ("llmlingua-2" in act_lower and "llmlingua-2" in nl):
            return True
        return False

    @classmethod
    def invalidate_cache(cls, signature: Optional[Tuple[Tuple[str, Tuple[str, str]], ...]] = None) -> None:
        """Invalidate monotonic snapshot cache for a specific signature or all signatures."""
        with _CACHE_LOCK:
            if signature is not None:
                _CACHED_SNAPSHOTS.pop(signature, None)
            else:
                _CACHED_SNAPSHOTS.clear()

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Return diagnostic metrics about the observer snapshot cache."""
        with _CACHE_LOCK:
            return {
                "active_entries": len(_CACHED_SNAPSHOTS),
                "ttl_seconds": _CACHE_TTL,
            }

    def _get_cache_signature(self) -> Tuple[Any, ...]:
        """Generate an immutable signature tuple from active model identities and instance markers."""
        active_identities = self._get_active_identities()
        sig_items = []
        inst_map = {
            "VLM": self._vlm_instance,
            "Embedding": self._embedding_instance,
            "Rerank": self._rerank_instance,
            "Compressor": self._compressor_instance,
        }
        for cat in sorted(active_identities.keys()):
            model_name, provider = active_identities[cat]
            inst = inst_map.get(cat)
            if inst is not None and (hasattr(inst, "get_token_usage") or hasattr(inst, "_token_tracker")):
                inst_marker: Any = id(inst)
            elif inst is not None:
                inst_marker = type(inst).__name__
            else:
                inst_marker = "none"
            sig_items.append((cat, model_name, provider, inst_marker))
        return tuple(sig_items)

    def _get_grouped_rows(self, force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """Group usage by domain (VLM, Embedding, Rerank, Compressor) with monotonic snapshot cache.

        For each domain:
        - Row 0: Active configured model (always present, even with 0 calls).
        - Row 1 (if historical models exist): Consolidated historical summary row.
        """
        sig = self._get_cache_signature()
        now = time.monotonic()
        if not force_refresh:
            with _CACHE_LOCK:
                cached = _CACHED_SNAPSHOTS.get(sig)
                if cached is not None and (now - cached[0]) < _CACHE_TTL:
                    return {k: [dict(r) for r in v] for k, v in cached[1].items()}

        active_identities = self._get_active_identities()
        all_records = self._collect_all_records()

        # Bucket all records by functional domain
        domain_records: Dict[str, List[Dict[str, Any]]] = {
            "VLM": [],
            "Embedding": [],
            "Rerank": [],
            "Compressor": [],
        }

        for row in all_records.values():
            domain = self._get_model_domain(row["Model"])
            domain_records[domain].append(row)

        groups: Dict[str, List[Dict[str, Any]]] = {
            "VLM": [],
            "Embedding": [],
            "Rerank": [],
            "Compressor": [],
        }

        for cat in ("VLM", "Embedding", "Rerank", "Compressor"):
            cat_records = domain_records[cat]
            active_row: Optional[Dict[str, Any]] = None
            historical_rows: List[Dict[str, Any]] = []

            for r in cat_records:
                if self._is_active_model(r["Model"], cat, active_identities):
                    if active_row is None:
                        active_row = dict(r)
                    else:
                        active_row["Calls"] += r["Calls"]
                        active_row["Prompt"] += r["Prompt"]
                        active_row["Completion"] += r["Completion"]
                        active_row["Total"] += r["Total"]
                        if r["Last Updated"] != "--":
                            active_row["Last Updated"] = r["Last Updated"]
                else:
                    historical_rows.append(r)

            # Guarantee active model is present
            if cat in active_identities:
                act_model, act_prov = active_identities[cat]
                if active_row is None:
                    active_row = {
                        "Model": act_model,
                        "Provider": act_prov,
                        "Calls": 0,
                        "Prompt": 0,
                        "Completion": 0,
                        "Total": 0,
                        "Last Updated": "--",
                    }
                groups[cat].append(active_row)
            elif active_row is not None:
                groups[cat].append(active_row)

            # Consolidate all historical models in this category into a single summary row
            if historical_rows:
                h_calls = sum(r["Calls"] for r in historical_rows)
                h_prompt = sum(r["Prompt"] for r in historical_rows)
                h_completion = sum(r["Completion"] for r in historical_rows)
                h_total = sum(r["Total"] for r in historical_rows)
                valid_ts = [r["Last Updated"] for r in historical_rows if r.get("Last Updated") and r["Last Updated"] != "--"]
                latest_ts = max(valid_ts) if valid_ts else "--"

                groups[cat].append({
                    "Model": f"历史已下线模型汇总 ({len(historical_rows)}个模型)",
                    "Provider": "historical",
                    "Calls": h_calls,
                    "Prompt": h_prompt,
                    "Completion": h_completion,
                    "Total": h_total,
                    "Last Updated": latest_ts,
                })

        with _CACHE_LOCK:
            _CACHED_SNAPSHOTS[sig] = (now, groups)

        return {k: [dict(r) for r in v] for k, v in groups.items()}

    def get_status_table(self, force_refresh: bool = False) -> str:
        """Format usage tables for active models and their historical summaries."""
        from tabulate import tabulate

        grouped = self._get_grouped_rows(force_refresh=force_refresh)
        active_identities = self._get_active_identities()

        lines: List[str] = []
        for cat in ("VLM", "Embedding", "Rerank", "Compressor"):
            # Only display if category instance was provided
            if cat in active_identities and grouped[cat]:
                lines.append(f"\n{cat} Models:")
                lines.append(tabulate(grouped[cat], headers="keys", tablefmt="pretty"))

        return "\n".join(lines).strip() if lines else "No model usage data available."

    def _get_vlm_usage(self) -> Optional[List[Dict[str, Any]]]:
        rows = self._get_grouped_rows().get("VLM", [])
        return rows if rows else None

    def _get_configured_vlm(self) -> Optional[List[Dict[str, Any]]]:
        return self._get_vlm_usage()

    def _get_embedding_usage(self) -> Optional[List[Dict[str, Any]]]:
        rows = self._get_grouped_rows().get("Embedding", [])
        return rows if rows else None

    def _get_configured_embedding(self) -> Optional[List[Dict[str, Any]]]:
        return self._get_embedding_usage()

    def _get_rerank_usage(self) -> Optional[List[Dict[str, Any]]]:
        rows = self._get_grouped_rows().get("Rerank", [])
        return rows if rows else None

    def _get_configured_rerank(self) -> Optional[List[Dict[str, Any]]]:
        return self._get_rerank_usage()

    def _get_compressor_usage(self) -> Optional[List[Dict[str, Any]]]:
        rows = self._get_grouped_rows().get("Compressor", [])
        return rows if rows else None

    def _get_archived_usage(self) -> Optional[List[Dict[str, Any]]]:
        return None

    def __str__(self) -> str:
        return self.get_status_table()

    def is_healthy(self) -> bool:
        return any((self._vlm_instance, self._embedding_instance, self._rerank_instance, self._compressor_instance))

    def has_errors(self) -> bool:
        return False
