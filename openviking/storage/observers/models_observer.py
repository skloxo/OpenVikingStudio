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
from typing import Any, Dict, List, Optional, Tuple

from openviking.storage.observers.base_observer import BaseObserver
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_USAGE_FILE = Path(os.path.expanduser("~/.openviking/models_token_usage.json"))


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

    def _classify_model(self, model_name: str, active_map: Dict[str, Tuple[str, str]]) -> str:
        """Classify a model name into VLM, Embedding, Rerank, Compressor, or Archived.
        
        Strict active matching: only models configured in ov.conf belong to active categories.
        """
        nl = model_name.strip().lower()

        # Strict active matching
        for cat, (act_model, _) in active_map.items():
            act_lower = act_model.strip().lower()
            if nl == act_lower:
                return cat
            # Handle canonical alias for reranker
            if cat == "Rerank" and act_lower in ("qwen3-vl-rer", "qwen3-vl-reranker") and nl in ("qwen3-vl-rer", "qwen3-vl-reranker"):
                return cat
            if cat == "Compressor" and ("llmlingua-2" in act_lower and "llmlingua-2" in nl):
                return cat

        # All other models belong to Archived
        return "Archived"

    def _get_grouped_rows(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group all usage into active categories and Archived section."""
        active_identities = self._get_active_identities()
        all_records = self._collect_all_records()

        groups: Dict[str, List[Dict[str, Any]]] = {
            "VLM": [],
            "Embedding": [],
            "Rerank": [],
            "Compressor": [],
            "Archived": [],
        }

        matched_keys = set()
        for key, row in all_records.items():
            cat = self._classify_model(row["Model"], active_identities)
            groups[cat].append(row)
            matched_keys.add(key)

        # Guarantee that configured active models always appear even with 0 calls
        for cat, (act_model, act_prov) in active_identities.items():
            has_active_row = any(
                r["Model"].lower() == act_model.lower() or act_model.lower() in r["Model"].lower()
                for r in groups[cat]
            )
            if not has_active_row:
                groups[cat].insert(
                    0,
                    {
                        "Model": act_model,
                        "Provider": act_prov,
                        "Calls": 0,
                        "Prompt": 0,
                        "Completion": 0,
                        "Total": 0,
                        "Last Updated": "--",
                    },
                )

        # Sort archived models by total tokens descending
        groups["Archived"].sort(key=lambda r: r["Total"], reverse=True)

        return groups

    def get_status_table(self) -> str:
        """Format usage tables for active models and archived models."""
        from tabulate import tabulate

        grouped = self._get_grouped_rows()
        active_identities = self._get_active_identities()

        lines: List[str] = []
        for cat in ("VLM", "Embedding", "Rerank", "Compressor"):
            # Only display if category instance was provided
            if cat in active_identities and grouped[cat]:
                lines.append(f"\n{cat} Models:")
                lines.append(tabulate(grouped[cat], headers="keys", tablefmt="pretty"))

        if grouped["Archived"]:
            lines.append("\nArchived Models:")
            lines.append(tabulate(grouped["Archived"], headers="keys", tablefmt="pretty"))

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
        rows = self._get_grouped_rows().get("Archived", [])
        return rows if rows else None

    def __str__(self) -> str:
        return self.get_status_table()

    def is_healthy(self) -> bool:
        return any((self._vlm_instance, self._embedding_instance, self._rerank_instance, self._compressor_instance))

    def has_errors(self) -> bool:
        return False
