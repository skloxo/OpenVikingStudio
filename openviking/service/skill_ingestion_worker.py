# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VikingFS Skill Ingestion Background Worker (Card-95).

核心物理公理:
  1. 单线程顺序消费: 从 SQLite 暂存表中原子认领 PENDING 记录，防止并发竞态；
  2. 纯算法门禁驱动: 调用 Card-94 Validator 校验 Frontmatter v2.0 与 AST 安全；
  3. 确定性状态流转: 合规 ➔ STAGED（待归包与查重），违规 ➔ REJECTED（附带错误清单），异常 ➔ ERROR。
"""

from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any, Dict, List, Optional

from openviking.service.skill_ingestion_validator import SkillIngestionValidator
from openviking.service.skill_package_router import SkillPackageRouter
from openviking.storage.skill_ingestion_store import (
    IngestionRecord,
    IngestionStatus,
    SkillIngestionStore,
)

logger = logging.getLogger(__name__)


class SkillIngestionWorker:
    """技能准入后台异步处理器。"""

    def __init__(
        self,
        store: Optional[SkillIngestionStore] = None,
        validator: Optional[SkillIngestionValidator] = None,
        router: Optional[SkillPackageRouter] = None,
    ):
        self._store = store or SkillIngestionStore.get_instance()
        self._validator = validator or SkillIngestionValidator()
        self._router = router or SkillPackageRouter()

    def process_next_batch(self, batch_size: int = 1) -> List[IngestionRecord]:
        """批量原子认领并执行准入校验与路由流水线。"""
        claimed_records = self._store.fetch_and_claim_pending(batch_size=batch_size)
        if not claimed_records:
            return []

        processed: List[IngestionRecord] = []
        for record in claimed_records:
            try:
                receipt = self._validator.validate(
                    content=record.raw_content,
                    filename=f"{record.skill_name}.md",
                )
                report_dict = receipt.to_dict()

                if receipt.is_valid:
                    status = IngestionStatus.STAGED
                    # Dynamic routing analysis
                    decision = self._router.analyze_routing(
                        skill_name=record.skill_name,
                        content=record.raw_content,
                        existing_skills=[],
                    )
                    report_dict["routing"] = asdict(decision)
                    msg = f"Passed static checks. Routed to '{decision.target_package}' ({decision.action.value})"
                else:
                    status = IngestionStatus.REJECTED
                    error_details = "; ".join(v.message for v in (receipt.critical_violations or receipt.violations))
                    msg = f"Rejected by gatekeeper: {error_details}" if error_details else "Static checks failed"

                self._store.update_status(
                    receipt_id=record.receipt_id,
                    status=status,
                    status_message=msg,
                    validation_report=report_dict,
                )
                record.status = status
                record.status_message = msg
                record.validation_report = report_dict
                processed.append(record)

            except Exception as exc:
                logger.exception("Error processing skill ingestion record %s", record.receipt_id)
                err_msg = f"Worker internal exception: {exc}"
                self._store.update_status(
                    receipt_id=record.receipt_id,
                    status=IngestionStatus.ERROR,
                    status_message=err_msg,
                )
                record.status = IngestionStatus.ERROR
                record.status_message = err_msg
                processed.append(record)

        return processed

    def run_worker_tick(self, batch_size: int = 5) -> Dict[str, Any]:
        """执行单次轮询滴答，返回处理统一度量。"""
        processed = self.process_next_batch(batch_size=batch_size)
        staged_cnt = sum(1 for r in processed if r.status == IngestionStatus.STAGED)
        rejected_cnt = sum(1 for r in processed if r.status == IngestionStatus.REJECTED)
        error_cnt = sum(1 for r in processed if r.status == IngestionStatus.ERROR)

        return {
            "processed_count": len(processed),
            "staged_count": staged_cnt,
            "rejected_count": rejected_cnt,
            "error_count": error_cnt,
            "queue_depth": self._store.get_queue_depth(),
        }
