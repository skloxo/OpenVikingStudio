# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
QueueObserver: Queue system observability tool.

Provides methods to observe and report queue status in various formats.
"""

from typing import Dict, Optional

from openviking.storage.observers.base_observer import BaseObserver
from openviking.storage.queuefs.named_queue import QueueStatus
from openviking.storage.queuefs.queue_manager import QueueManager
from openviking_cli.utils import run_async
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class QueueObserver(BaseObserver):
    """
    QueueObserver: System observability tool for queue management.

    Provides methods to query queue status and format output.
    """

    def __init__(self, queue_manager: QueueManager):
        self._queue_manager = queue_manager

    PERSISTENCE_PATH = "~/.openviking/queue_stats.json"

    def _load_persisted_stats(self) -> dict:
        import json
        import os
        path = os.path.expanduser(self.PERSISTENCE_PATH)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_persisted_stats(self, snapshot: dict) -> None:
        import json
        import os
        if not snapshot:
            return
        path = os.path.expanduser(self.PERSISTENCE_PATH)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = f"{path}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    async def get_status_table_async(self) -> str:
        statuses = await self._queue_manager.check_status()
        dag_stats = self._get_semantic_dag_stats()
        table_str = self._format_status_as_table(statuses, dag_stats)
        self._save_persisted_stats({"status_table": table_str})
        return table_str

    def get_status_table(self) -> str:
        try:
            import asyncio
            import concurrent.futures
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(lambda: asyncio.run(self.get_status_table_async())).result(timeout=2.0)
            except (RuntimeError, Exception):
                return run_async(self.get_status_table_async())
        except Exception as e:
            logger.debug(f"Error getting live queue table: {e}")
            persisted = self._load_persisted_stats()
            if persisted and "status_table" in persisted:
                return persisted["status_table"]
            return "No queue status data available."

    def __str__(self) -> str:
        return self.get_status_table()

    def _format_status_as_table(
        self, statuses: Dict[str, QueueStatus], dag_stats: Optional[object]
    ) -> str:
        """
        Format queue statuses as a table using tabulate.

        Args:
            statuses: Dict mapping queue names to QueueStatus

        Returns:
            Formatted table string
        """
        from tabulate import tabulate

        if not statuses:
            return "No queue status data available."

        data = []
        total_pending = 0
        total_in_progress = 0
        total_processed = 0
        total_requeues = 0
        total_errors = 0

        for queue_name, status in statuses.items():
            total = status.pending + status.in_progress + status.processed
            data.append(
                {
                    "Queue": queue_name,
                    "Pending": status.pending,
                    "In Progress": status.in_progress,
                    "Processed": status.processed,
                    "Requeued": status.requeue_count,
                    "Errors": status.error_count,
                    "Total": total,
                }
            )
            total_pending += status.pending
            total_in_progress += status.in_progress
            total_processed += status.processed
            total_requeues += status.requeue_count
            total_errors += status.error_count

        data.append(
            {
                "Queue": "Semantic-Nodes",
                "Pending": getattr(dag_stats, "pending_nodes", 0) if dag_stats else 0,
                "In Progress": getattr(dag_stats, "in_progress_nodes", 0) if dag_stats else 0,
                "Processed": getattr(dag_stats, "done_nodes", 0) if dag_stats else 0,
                "Requeued": 0,
                "Errors": 0,
                "Total": getattr(dag_stats, "total_nodes", 0) if dag_stats else 0,
            }
        )

        # Add total row
        total_total = total_pending + total_in_progress + total_processed
        data.append(
            {
                "Queue": "TOTAL",
                "Pending": total_pending,
                "In Progress": total_in_progress,
                "Processed": total_processed,
                "Requeued": total_requeues,
                "Errors": total_errors,
                "Total": total_total,
            }
        )

        return tabulate(data, headers="keys", tablefmt="pretty")

    def _get_semantic_dag_stats(self) -> Optional[object]:
        semantic_queue = self._queue_manager._queues.get(self._queue_manager.SEMANTIC)
        if not semantic_queue:
            return None
        handler = getattr(semantic_queue, "_dequeue_handler", None)
        if handler and hasattr(handler, "get_dag_stats"):
            return handler.get_dag_stats()
        return None

    def is_healthy(self) -> bool:
        return not self.has_errors()

    def has_errors(self) -> bool:
        return self._queue_manager.has_errors()
