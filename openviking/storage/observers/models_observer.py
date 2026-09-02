# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
ModelsObserver: Multi-model system observability tool.

Provides methods to observe and report token usage across VLM, Embedding, and Rerank models.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

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

        ts = TelemetryStore()
        return ts.get_model_usage_by_window(window="all").get("by_model_type", {})
    except Exception as e:
        logger.debug(f"Failed to query model usage from TelemetryStore: {e}")
        return {}


class ModelsObserver(BaseObserver):
    """
    ModelsObserver: System observability tool for multi-model token usage monitoring.

    Provides methods to query token usage status and format output for VLM, Embedding, and Rerank models.
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

    def get_status_table(self) -> str:
        return self._format_status_as_table()

    def _format_status_as_table(self) -> str:
        from tabulate import tabulate

        sections = []

        # 1. VLM section
        if self._vlm_instance:
            vlm_data = None
            try:
                vlm_data = self._get_vlm_usage()
            except Exception as e:
                logger.warning(f"Error getting VLM usage: {e}")
            if not vlm_data:
                vlm_data = self._get_configured_vlm()
            if vlm_data:
                sections.append(("VLM", vlm_data))

        # 2. Embedding section
        if self._embedding_instance:
            embedding_data = None
            try:
                embedding_data = self._get_embedding_usage()
            except Exception as e:
                logger.warning(f"Error getting Embedding usage: {e}")
            if not embedding_data:
                embedding_data = self._get_configured_embedding()
            if embedding_data:
                sections.append(("Embedding", embedding_data))

        # 3. Rerank section
        if self._rerank_instance:
            rerank_data = None
            try:
                rerank_data = self._get_rerank_usage()
            except Exception as e:
                logger.warning(f"Error getting Rerank usage: {e}")
            if not rerank_data:
                rerank_data = self._get_configured_rerank()
            if rerank_data:
                sections.append(("Rerank", rerank_data))

        # 4. Compressor section
        if self._compressor_instance is not None:
            try:
                compressor_data = self._get_compressor_usage()
                if compressor_data:
                    sections.append(("Compressor", compressor_data))
            except Exception as e:
                logger.warning(f"Error getting Compressor usage: {e}")

        if not sections:
            return "No model usage data available."

        lines = []
        for model_type, data in sections:
            lines.append(f"\n{model_type} Models:")
            lines.append(tabulate(data, headers="keys", tablefmt="pretty"))
            lines.append("")

        return "\n".join(lines)

    def _get_vlm_usage(self) -> Optional[list]:
        """Get VLM token usage from SQLite TelemetryStore and memory."""
        telemetry_by_type = _get_telemetry_model_usage()
        vlm_telemetry = telemetry_by_type.get("vlm", {})

        model_rows: Dict[str, Dict[str, Any]] = {}

        # 1. Populate from TelemetryStore SQLite
        for m_name, prov_map in vlm_telemetry.items():
            for p_name, u in prov_map.items():
                key = f"{m_name}:{p_name}"
                from datetime import datetime

                ts_str = (
                    datetime.fromtimestamp(u["last_updated"]).isoformat()
                    if u.get("last_updated")
                    else "--"
                )
                model_rows[key] = {
                    "Model": m_name,
                    "Provider": p_name,
                    "Calls": u.get("call_count", 0),
                    "Prompt": u.get("prompt_tokens", 0),
                    "Completion": u.get("completion_tokens", 0),
                    "Total": u.get("total_tokens", 0),
                    "Last Updated": ts_str,
                }

        # 2. Add memory instance usage if available
        if self._vlm_instance and hasattr(self._vlm_instance, "get_token_usage"):
            try:
                inst_usage = self._vlm_instance.get_token_usage()
                for m_name, m_data in inst_usage.get("usage_by_model", {}).items():
                    name_lower = m_name.lower()
                    if "embed" in name_lower or "rerank" in name_lower or "lingua" in name_lower:
                        continue
                    for p_name, p_data in m_data.get("usage_by_provider", {}).items():
                        key = f"{m_name}:{p_name}"
                        if key in model_rows:
                            # If memory has higher counts, take max
                            if p_data.get("call_count", 0) > model_rows[key]["Calls"]:
                                model_rows[key]["Calls"] = p_data.get("call_count", 0)
                                model_rows[key]["Prompt"] = p_data.get("prompt_tokens", 0)
                                model_rows[key]["Completion"] = p_data.get("completion_tokens", 0)
                                model_rows[key]["Total"] = p_data.get("total_tokens", 0)
                                model_rows[key]["Last Updated"] = p_data.get("last_updated", "")
                        else:
                            model_rows[key] = {
                                "Model": m_name,
                                "Provider": p_name,
                                "Calls": p_data.get("call_count", 0),
                                "Prompt": p_data.get("prompt_tokens", 0),
                                "Completion": p_data.get("completion_tokens", 0),
                                "Total": p_data.get("total_tokens", 0),
                                "Last Updated": p_data.get("last_updated", ""),
                            }
            except Exception as e:
                logger.debug(f"Error checking vlm instance usage: {e}")

        # Fallback to persistent disk tracker file if empty
        if not model_rows:
            persistent = _read_persistent_usage()
            for m_name, m_data in persistent.get("usage_by_model", {}).items():
                name_lower = m_name.lower()
                if "embed" in name_lower or "rerank" in name_lower or "lingua" in name_lower:
                    continue
                for p_name, p_data in m_data.get("usage_by_provider", {}).items():
                    key = f"{m_name}:{p_name}"
                    model_rows[key] = {
                        "Model": m_name,
                        "Provider": p_name,
                        "Calls": p_data.get("call_count", 0),
                        "Prompt": p_data.get("prompt_tokens", 0),
                        "Completion": p_data.get("completion_tokens", 0),
                        "Total": p_data.get("total_tokens", 0),
                        "Last Updated": p_data.get("last_updated", ""),
                    }

        # 3. Ensure configured model is listed
        current_model = getattr(self._vlm_instance, "model", None)
        if current_model and not any(r["Model"] == current_model for r in model_rows.values()):
            model_rows[f"{current_model}:configured"] = {
                "Model": current_model,
                "Provider": getattr(self._vlm_instance, "provider", None) or "openai",
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }

        return list(model_rows.values()) if model_rows else None

    def _get_configured_vlm(self) -> Optional[list]:
        model = getattr(self._vlm_instance, "model", None)
        if not model:
            return None
        return [
            {
                "Model": model,
                "Provider": getattr(self._vlm_instance, "provider", None) or "unknown",
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }
        ]

    def _get_embedding_usage(self) -> Optional[list]:
        """Get Embedding token usage from SQLite TelemetryStore and memory."""
        telemetry_by_type = _get_telemetry_model_usage()
        emb_telemetry = telemetry_by_type.get("embedding", {})

        model_rows: Dict[str, Dict[str, Any]] = {}

        # 1. Populate from TelemetryStore SQLite
        for m_name, prov_map in emb_telemetry.items():
            for p_name, u in prov_map.items():
                key = f"{m_name}:{p_name}"
                from datetime import datetime

                ts_str = (
                    datetime.fromtimestamp(u["last_updated"]).isoformat()
                    if u.get("last_updated")
                    else "--"
                )
                model_rows[key] = {
                    "Model": m_name,
                    "Provider": p_name,
                    "Calls": u.get("call_count", 0),
                    "Prompt": u.get("prompt_tokens", 0),
                    "Completion": u.get("completion_tokens", 0),
                    "Total": u.get("total_tokens", 0),
                    "Last Updated": ts_str,
                }

        # 2. Add memory instance usage if available
        if self._embedding_instance and hasattr(self._embedding_instance, "get_token_usage"):
            try:
                inst_usage = self._embedding_instance.get_token_usage()
                for m_name, m_data in inst_usage.get("usage_by_model", {}).items():
                    name_lower = m_name.lower()
                    if "embed" not in name_lower and "qwen3-embedding" not in name_lower:
                        continue
                    for p_name, p_data in m_data.get("usage_by_provider", {}).items():
                        key = f"{m_name}:{p_name}"
                        if key in model_rows:
                            if p_data.get("call_count", 0) > model_rows[key]["Calls"]:
                                model_rows[key]["Calls"] = p_data.get("call_count", 0)
                                model_rows[key]["Prompt"] = p_data.get("prompt_tokens", 0)
                                model_rows[key]["Completion"] = p_data.get("completion_tokens", 0)
                                model_rows[key]["Total"] = p_data.get("total_tokens", 0)
                                model_rows[key]["Last Updated"] = p_data.get("last_updated", "")
                        else:
                            model_rows[key] = {
                                "Model": m_name,
                                "Provider": p_name,
                                "Calls": p_data.get("call_count", 0),
                                "Prompt": p_data.get("prompt_tokens", 0),
                                "Completion": p_data.get("completion_tokens", 0),
                                "Total": p_data.get("total_tokens", 0),
                                "Last Updated": p_data.get("last_updated", ""),
                            }
            except Exception as e:
                logger.debug(f"Error checking embedding instance usage: {e}")

        # Fallback to persistent disk tracker file if empty
        if not model_rows:
            persistent = _read_persistent_usage()
            for m_name, m_data in persistent.get("usage_by_model", {}).items():
                name_lower = m_name.lower()
                if "embed" not in name_lower and "qwen3-embedding" not in name_lower:
                    continue
                for p_name, p_data in m_data.get("usage_by_provider", {}).items():
                    key = f"{m_name}:{p_name}"
                    model_rows[key] = {
                        "Model": m_name,
                        "Provider": p_name,
                        "Calls": p_data.get("call_count", 0),
                        "Prompt": p_data.get("prompt_tokens", 0),
                        "Completion": p_data.get("completion_tokens", 0),
                        "Total": p_data.get("total_tokens", 0),
                        "Last Updated": p_data.get("last_updated", ""),
                    }

        # 3. Ensure configured model is listed
        current_model = getattr(
            self._embedding_instance,
            "model_name",
            getattr(self._embedding_instance, "model", None),
        )
        if not current_model and hasattr(self._embedding_instance, "config"):
            current_model = getattr(self._embedding_instance.config, "model", None)
        if not current_model:
            current_model = "Qwen3-Embedding-8B"

        if current_model and not any(r["Model"] == current_model for r in model_rows.values()):
            model_rows[f"{current_model}:configured"] = {
                "Model": current_model,
                "Provider": getattr(self._embedding_instance, "provider", None) or "openai",
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }

        return list(model_rows.values()) if model_rows else None

    def _get_configured_embedding(self) -> Optional[list]:
        model = getattr(
            self._embedding_instance,
            "model_name",
            getattr(self._embedding_instance, "model", None),
        )
        if not model and hasattr(self._embedding_instance, "config"):
            model = getattr(self._embedding_instance.config, "model", None)
        if not model:
            model = "Qwen3-Embedding-8B"
        return [
            {
                "Model": model,
                "Provider": getattr(self._embedding_instance, "provider", None) or "openai",
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }
        ]

    def _get_rerank_usage(self) -> Optional[list]:
        """Get Rerank token usage from SQLite TelemetryStore and memory."""
        telemetry_by_type = _get_telemetry_model_usage()
        rerank_telemetry = telemetry_by_type.get("rerank", {})

        model_rows: Dict[str, Dict[str, Any]] = {}

        # 1. Populate from TelemetryStore SQLite
        for m_name, prov_map in rerank_telemetry.items():
            for p_name, u in prov_map.items():
                key = f"{m_name}:{p_name}"
                from datetime import datetime

                ts_str = (
                    datetime.fromtimestamp(u["last_updated"]).isoformat()
                    if u.get("last_updated")
                    else "--"
                )
                model_rows[key] = {
                    "Model": m_name,
                    "Provider": p_name,
                    "Calls": u.get("call_count", 0),
                    "Prompt": u.get("prompt_tokens", 0),
                    "Completion": u.get("completion_tokens", 0),
                    "Total": u.get("total_tokens", 0),
                    "Last Updated": ts_str,
                }

        # 2. Add memory instance usage if available
        if self._rerank_instance and hasattr(self._rerank_instance, "get_token_usage"):
            try:
                inst_usage = self._rerank_instance.get_token_usage()
                for m_name, m_data in inst_usage.get("usage_by_model", {}).items():
                    name_lower = m_name.lower()
                    if "rerank" not in name_lower:
                        continue
                    for p_name, p_data in m_data.get("usage_by_provider", {}).items():
                        key = f"{m_name}:{p_name}"
                        if key in model_rows:
                            if p_data.get("call_count", 0) > model_rows[key]["Calls"]:
                                model_rows[key]["Calls"] = p_data.get("call_count", 0)
                                model_rows[key]["Prompt"] = p_data.get("prompt_tokens", 0)
                                model_rows[key]["Completion"] = p_data.get("completion_tokens", 0)
                                model_rows[key]["Total"] = p_data.get("total_tokens", 0)
                                model_rows[key]["Last Updated"] = p_data.get("last_updated", "")
                        else:
                            model_rows[key] = {
                                "Model": m_name,
                                "Provider": p_name,
                                "Calls": p_data.get("call_count", 0),
                                "Prompt": p_data.get("prompt_tokens", 0),
                                "Completion": p_data.get("completion_tokens", 0),
                                "Total": p_data.get("total_tokens", 0),
                                "Last Updated": p_data.get("last_updated", ""),
                            }
            except Exception as e:
                logger.debug(f"Error checking rerank instance usage: {e}")

        # Fallback to persistent disk tracker file if empty
        if not model_rows:
            persistent = _read_persistent_usage()
            for m_name, m_data in persistent.get("usage_by_model", {}).items():
                name_lower = m_name.lower()
                if "rerank" not in name_lower:
                    continue
                for p_name, p_data in m_data.get("usage_by_provider", {}).items():
                    key = f"{m_name}:{p_name}"
                    model_rows[key] = {
                        "Model": m_name,
                        "Provider": p_name,
                        "Calls": p_data.get("call_count", 0),
                        "Prompt": p_data.get("prompt_tokens", 0),
                        "Completion": p_data.get("completion_tokens", 0),
                        "Total": p_data.get("total_tokens", 0),
                        "Last Updated": p_data.get("last_updated", ""),
                    }

        # 3. Ensure configured model is listed
        current_model = getattr(self._rerank_instance, "model", None)
        if not current_model and hasattr(self._rerank_instance, "config"):
            current_model = getattr(self._rerank_instance.config, "model", None)
        if not current_model:
            current_model = "qwen3-reranker-0.6b"

        if current_model and not any(r["Model"] == current_model for r in model_rows.values()):
            model_rows[f"{current_model}:configured"] = {
                "Model": current_model,
                "Provider": getattr(self._rerank_instance, "provider", None) or "openai",
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }

        return list(model_rows.values()) if model_rows else None

    def _get_configured_rerank(self) -> Optional[list]:
        """Return configured Rerank identity when usage data is unavailable."""
        if not self._rerank_instance:
            return None
        model = getattr(self._rerank_instance, "model_name", getattr(self._rerank_instance, "model", None))
        if not model and hasattr(self._rerank_instance, "config"):
            model = getattr(self._rerank_instance.config, "model", None)
        if not model:
            model = "qwen3-reranker-0.6b"
        provider = getattr(self._rerank_instance, "provider", None) or "openai"
        return [
            {
                "Model": model,
                "Provider": provider,
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }
        ]

    def _get_compressor_usage(self) -> Optional[list]:
        """Get Compressor (e.g. LLMLingua-2) token usage data."""
        if not self._compressor_instance:
            return None

        usage_data = None
        if hasattr(self._compressor_instance, "get_token_usage"):
            try:
                usage_data = self._compressor_instance.get_token_usage()
            except Exception as e:
                logger.debug(f"Failed to get_token_usage from compressor: {e}")
        elif hasattr(self._compressor_instance, "_token_tracker"):
            try:
                usage_data = self._compressor_instance._token_tracker.to_dict()
            except Exception as e:
                logger.debug(f"Failed to get _token_tracker from compressor: {e}")

        if usage_data and usage_data.get("usage_by_model"):
            data = []
            for model_name, model_data in usage_data["usage_by_model"].items():
                for provider_name, provider_data in model_data.get("usage_by_provider", {}).items():
                    data.append(
                        {
                            "Model": model_name,
                            "Provider": provider_name,
                            "Calls": provider_data.get("call_count", 0),
                            "Prompt": provider_data.get("prompt_tokens", 0),
                            "Completion": provider_data.get("completion_tokens", 0),
                            "Total": provider_data.get("total_tokens", 0),
                            "Last Updated": provider_data.get("last_updated", ""),
                        }
                    )
            if data:
                return data

        # Default configured compressor identity
        model_name = getattr(
            self._compressor_instance,
            "model_name",
            getattr(self._compressor_instance, "model", "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"),
        )
        provider = getattr(self._compressor_instance, "provider", "local")
        return [
            {
                "Model": model_name,
                "Provider": provider,
                "Calls": 0,
                "Prompt": 0,
                "Completion": 0,
                "Total": 0,
                "Last Updated": "--",
            }
        ]

    def __str__(self) -> str:
        return self.get_status_table()

    def is_healthy(self) -> bool:
        """
        Check if model system is healthy.

        For ModelsObserver, healthy means at least one model is available and token tracking is working.

        Returns:
            True if system is healthy, False otherwise
        """
        return (
            self._vlm_instance is not None
            or self._embedding_instance is not None
            or self._rerank_instance is not None
            or self._compressor_instance is not None
        )

    def has_errors(self) -> bool:
        """
        Check if model system has any errors.

        For ModelsObserver, errors are not tracked in token usage.

        Returns:
            False (no error tracking in token usage)
        """
        return False
