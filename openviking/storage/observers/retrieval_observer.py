# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
RetrievalObserver: Retrieval system observability tool.

Provides retrieval diagnostics accumulated by the HierarchicalRetriever.
"""

from openviking.storage.observers.base_observer import BaseObserver
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalObserver(BaseObserver):
    """
    RetrievalObserver: System observability tool for retrieval quality.

    Empty retrievals are valid outcomes. Result counts and scores are
    diagnostics only and do not determine component health.
    """

    @staticmethod
    def _get_collector():
        """Lazy import to avoid circular dependency with storage module."""
        from openviking.retrieve.retrieval_stats import get_stats_collector

        return get_stats_collector()

    def get_status_table(self) -> str:
        """Format retrieval statistics as a string table."""
        return self._format_status_as_table()

    def _format_status_as_table(self) -> str:
        """Format retrieval stats as a table using tabulate from TelemetryStore (SSOT)."""
        from tabulate import tabulate

        # 1. Fetch SQLite baseline
        baseline = None
        try:
            from openviking.telemetry.telemetry_store import TelemetryStore

            ts = TelemetryStore()
            baseline = ts.get_retrieval_baseline()
        except Exception as e:
            logger.debug(f"Failed to query retrieval baseline from TelemetryStore: {e}")

        # 2. Fetch memory stats snapshot
        stats = self._get_collector().snapshot()

        # Combine TelemetryStore SQLite with memory snapshot
        total_queries = stats.total_queries
        total_results = stats.total_results
        zero_result_queries = stats.zero_result_queries
        total_score_sum = stats.total_score_sum
        max_score = stats.max_score
        min_score = stats.min_score
        rerank_used = stats.rerank_used
        rerank_fallback = stats.rerank_fallback
        total_latency_ms = stats.total_latency_ms
        max_latency_ms = stats.max_latency_ms
        queries_by_type = dict(stats.queries_by_type)

        if baseline and baseline.get("total_queries", 0) > 0:
            b_q = baseline.get("total_queries", 0)
            if b_q > total_queries:
                total_queries = b_q
                total_results = baseline.get("total_results", 0)
                zero_result_queries = baseline.get("zero_result_queries", 0)
                total_score_sum = baseline.get("total_score_sum", 0.0)
                max_score = max(max_score, baseline.get("max_score", 0.0))
                b_min = baseline.get("min_score", 1.0)
                min_score = min(min_score, b_min) if b_min > 0 else min_score
                rerank_used = baseline.get("rerank_used", 0)
                rerank_fallback = baseline.get("rerank_fallback", 0)
                total_latency_ms = baseline.get("total_latency_ms", 0.0)
                max_latency_ms = max(max_latency_ms, baseline.get("max_latency_ms", 0.0))
                for ctype, cnt in baseline.get("queries_by_type", {}).items():
                    queries_by_type[ctype] = max(queries_by_type.get(ctype, 0), cnt)

        if total_queries == 0:
            return "No retrieval queries recorded."

        avg_results_per_query = total_results / total_queries if total_queries > 0 else 0.0
        zero_result_rate = zero_result_queries / total_queries if total_queries > 0 else 0.0
        avg_score = total_score_sum / total_results if total_results > 0 else 0.0
        avg_latency_ms = total_latency_ms / total_queries if total_queries > 0 else 0.0

        summary = [
            {"Metric": "Total Queries", "Value": total_queries},
            {"Metric": "Total Results", "Value": total_results},
            {"Metric": "Avg Results/Query", "Value": f"{avg_results_per_query:.1f}"},
            {"Metric": "Zero-Result Queries", "Value": zero_result_queries},
            {
                "Metric": "Zero-Result Rate",
                "Value": f"{zero_result_rate:.1%}",
            },
            {"Metric": "Avg Score", "Value": f"{avg_score:.4f}"},
            {
                "Metric": "Score Range",
                "Value": f"{min_score:.4f} - {max_score:.4f}"
                if total_results > 0
                else "N/A",
            },
            {"Metric": "Rerank Used", "Value": rerank_used},
            {"Metric": "Rerank Fallback", "Value": rerank_fallback},
            {"Metric": "Avg Latency (ms)", "Value": f"{avg_latency_ms:.1f}"},
            {"Metric": "Max Latency (ms)", "Value": f"{max_latency_ms:.1f}"},
        ]

        lines = [tabulate(summary, headers="keys", tablefmt="pretty")]

        # Query breakdown by context type
        if queries_by_type:
            type_data = [
                {"Context Type": ctype, "Queries": count}
                for ctype, count in sorted(
                    queries_by_type.items(), key=lambda x: x[1], reverse=True
                )
            ]
            lines.append("")
            lines.append(tabulate(type_data, headers="keys", tablefmt="pretty"))

        return "\n".join(lines)

    def __str__(self) -> str:
        return self.get_status_table()

    def is_healthy(self) -> bool:
        """Retrieval result diagnostics do not indicate component availability."""
        return True

    def has_errors(self) -> bool:
        """Empty retrieval results are valid outcomes, not errors."""
        return False
