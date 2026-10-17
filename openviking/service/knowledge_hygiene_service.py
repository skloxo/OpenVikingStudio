# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Knowledge Hygiene Async Audit Service (知识卫生全量异步巡检服务).
(Card-Hygiene-AsyncAuditTaskCenter / v1.5.56)

Provides full-scale (100% coverage, no LIMIT 200) asynchronous knowledge hygiene auditing,
progress tracking, audit trail persistence in TaskCenter, and real-time snapshot caching for cockpits.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from openviking.retrieve.asymmetric_decay import AsymmetricDecayEngine
from openviking.retrieve.knowledge_hygiene import KnowledgeHygieneEngine, HygieneReport
from openviking.service.task_tracker import TaskRecord, TaskStatus, get_task_tracker
from openviking.storage.bm25_fts_index import BM25FTSIndex

logger = logging.getLogger("openviking.service.knowledge_hygiene_service")

TASK_TYPE_HYGIENE_AUDIT = "knowledge_hygiene_audit"


class KnowledgeHygieneService:
    """Singleton service orchestrating full-scale async knowledge hygiene audits."""

    _instance: Optional[KnowledgeHygieneService] = None

    def __init__(self) -> None:
        self.decay_engine = AsymmetricDecayEngine()
        self.hygiene_engine = KnowledgeHygieneEngine(self.decay_engine)
        self._latest_report: Optional[HygieneReport] = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> KnowledgeHygieneService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _collect_all_fts_items(self) -> List[Dict[str, Any]]:
        """Fetch all documents from BM25 FTS index joined with real lifecycle states and timestamps."""
        # 1. Fetch lifecycle status map from memory_lifecycle.db
        lifecycle_status_map = {}
        try:
            lc_path = os.path.expanduser("~/.openviking/data/memory_lifecycle.db")
            if os.path.exists(lc_path):
                lc_conn = sqlite3.connect(lc_path, timeout=5.0)
                try:
                    cur = lc_conn.execute("SELECT uri, status, disputed_reason, updated_at FROM memory_lifecycle")
                    for u, s, reason, upd in cur.fetchall():
                        lifecycle_status_map[u.strip()] = {
                            "status": s,
                            "reason": reason,
                            "updated_at": upd,
                        }
                finally:
                    lc_conn.close()
        except Exception as e:
            logger.warning("[KnowledgeHygieneService] Error querying memory_lifecycle: %s", e)

        # 2. Query FTS documents joined with fts_meta timestamps
        bm25 = BM25FTSIndex.get_instance()
        conn = bm25._get_connection()
        items: List[Dict[str, Any]] = []
        fts_uris = set()
        base_disk_path = os.path.expanduser("~/.openviking/data/viking/default/resources")

        try:
            cursor = conn.execute("""
                SELECT d.uri, d.title, d.level, d.context_type, 
                       COALESCE(strftime('%s', m.updated_at), 0)
                FROM fts_documents d
                LEFT JOIN fts_meta m ON d.uri = m.uri
            """)
            rows = cursor.fetchall()
            now_ts = time.time()
            for r in rows:
                uri = r[0]
                fts_uris.add(uri)
                meta_ts = float(r[4]) if r[4] else 0.0

                # Check physical disk mtime
                disk_path = uri.replace("viking://resources", base_disk_path)
                if os.path.exists(disk_path):
                    file_mtime = os.path.getmtime(disk_path)
                else:
                    file_mtime = meta_ts if meta_ts > 0 else (now_ts - 86400 * 20)

                lc_info = lifecycle_status_map.get(uri.strip())
                if lc_info:
                    status = lc_info["status"]
                    updated_ts = lc_info.get("updated_at") or file_mtime
                else:
                    status = "active"
                    updated_ts = file_mtime

                is_staging = "staging" in uri or "session" in uri
                # Axioms and rules have frequent active usage; staging/tmp buffers have lower initial calls
                call_count = 10 if "rules" in uri or "master_memory" in uri else (2 if not is_staging else 0)

                items.append({
                    "uri": uri,
                    "title": r[1],
                    "level": r[2],
                    "context_type": r[3],
                    "updated_ts": updated_ts,
                    "call_count": call_count,
                    "status": status,
                    "is_staging": is_staging,
                    "has_relations": not is_staging or "master_memory" in uri,
                })

            # 3. Ensure all items in memory_lifecycle are represented in the audit
            for u, lc in lifecycle_status_map.items():
                if u not in fts_uris:
                    items.append({
                        "uri": u,
                        "title": u.split("/")[-1].replace(".md", ""),
                        "level": 2,
                        "context_type": "resource",
                        "updated_ts": lc.get("updated_at") or (now_ts - 86400 * 20),
                        "call_count": 0 if lc["status"] == "superseded" else 1,
                        "status": lc["status"],
                        "is_staging": "staging" in u,
                        "has_relations": True,
                    })
        except Exception as e:
            logger.warning("[KnowledgeHygieneService] Error querying fts_documents: %s", e)
        finally:
            conn.close()
        return items

    def get_latest_report(self) -> HygieneReport:
        """Return the latest cached hygiene report, or perform a fast baseline scan if none exists."""
        if self._latest_report is not None:
            return self._latest_report

        # First run: compute full-scale baseline immediately
        items = self._collect_all_fts_items()
        report = self.hygiene_engine.inspect_items(items)
        report.total_in_store = len(items)
        self._latest_report = report
        return report

    async def dispatch_audit(
        self,
        *,
        account_id: str = "default",
        user_id: str = "root",
        trigger: str = "manual",
    ) -> TaskRecord:
        """Create and start a background full-scale knowledge hygiene audit task."""
        tracker = get_task_tracker()
        items = self._collect_all_fts_items()
        total_docs = len(items)

        task = await tracker.create(
            task_type=TASK_TYPE_HYGIENE_AUDIT,
            resource_id="viking://default",
            account_id=account_id,
            user_id=user_id,
            meta={
                "is_business": True,
                "human_title": "知识卫生全量巡检",
                "initiator": f"User ({trigger})" if trigger == "manual" else "Scheduler",
                "task_type_label": "知识卫生全量巡检",
                "total_documents": total_docs,
                "progress": {"completed": 0, "total": total_docs},
            },
        )

        asyncio.create_task(
            self._execute_audit(
                task_id=task.task_id,
                account_id=account_id,
                user_id=user_id,
                items=items,
            )
        )
        return task

    async def _execute_audit(
        self,
        task_id: str,
        account_id: str,
        user_id: str,
        items: List[Dict[str, Any]],
    ) -> None:
        """Execute full-scale inspection, update progress, and record audit trail."""
        tracker = get_task_tracker()
        total = len(items)
        t0 = time.monotonic()

        try:
            await tracker.start(task_id, stage="scanning_fts_documents")
            # Step 1: Scanning progress
            await tracker.update_stage(
                task_id,
                stage=f"全库在籍文档遍历扫描 ({total}/{total})",
                account_id=account_id,
                user_id=user_id,
                meta_patch={"progress": {"completed": total, "total": total}},
            )

            # Yield briefly to ensure UI sees running status and progress
            await asyncio.sleep(0.05)

            # Step 2: Multi-dimensional hygiene inspection
            await tracker.update_stage(
                task_id,
                stage="多维卫生健康度诊断与冲突排查",
                account_id=account_id,
                user_id=user_id,
            )

            report = self.hygiene_engine.inspect_items(items)
            report.task_id = task_id
            report.total_in_store = total
            report.latency_ms = round((time.monotonic() - t0) * 1000.0, 2)

            # Update cached singleton report for instant cockpit reading
            self._latest_report = report

            deliverable_text = (
                f"已全量巡检 {report.total_inspected:,} 篇记忆 · "
                f"综合健康评分 {report.health_score} · "
                f"历史替代 {report.superseded_count} · "
                f"冲突条目 {report.disputed_count} · 休眠条目 {report.dormant_count}"
            )

            result_payload = {
                **report.model_dump(),
                "deliverable": {
                    "title": "知识卫生全量巡检报告",
                    "deliverableText": deliverable_text,
                    "expectedText": "全库记忆冲突、休眠死重与孤儿碎片多维全量健康诊断",
                },
            }

            await tracker.complete(
                task_id,
                result=result_payload,
                account_id=account_id,
                user_id=user_id,
            )
            logger.info(
                "[KnowledgeHygieneService] Completed audit task %s in %.2f ms (Score: %d, Total: %d)",
                task_id,
                report.latency_ms,
                report.health_score,
                report.total_inspected,
            )

        except Exception as e:
            logger.exception("[KnowledgeHygieneService] Failed audit task %s: %s", task_id, e)
            await tracker.fail(
                task_id,
                error=f"Knowledge hygiene audit failed: {e}",
                account_id=account_id,
                user_id=user_id,
            )
