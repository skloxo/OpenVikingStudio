# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Autonomous Skill Pipeline Orchestrator (Card-2).

7x24h Unattended Autonomous Conveyor Belt:
1. SQLite Ingestion Queue atomic claim (PENDING -> VALIDATING -> STAGED -> COMMITTED)
2. SkillOpt 4-factor Quality Gate (Threshold >= 70.0)
3. SkillZip 0-Rollout 6-tuple contractual compression (40%~60% Token reduction)
4. B6 Stage 0 Ante-Gate adaptive routing (MERGE_INTO_EXISTING vs SPAWN_NEW_BUNDLE)
5. Zero-breaking physical scenario landing & Aliasing Router refresh
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import yaml

from openviking.storage.skill_ingestion_store import (
    IngestionRecord,
    IngestionStatus,
    SkillIngestionStore,
)
from openviking.service.skill_ingestion_validator import SkillIngestionValidator
from openviking.service.skill_opt_judge import SkillOptJudge
from openviking.service.skill_zip_engine import SkillZipEngine
from openviking.service.auto_crystallizer_b5 import (
    SeamDecisionGateB5,
    GENERIC_STOP_WORDS,
)
from openviking.service.skill_aliasing_router import SkillAliasingRouter

logger = logging.getLogger(__name__)

DEFAULT_SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")


class SkillAutonomousPipeline:
    """End-to-end autonomous pipeline orchestrator for unattended skill operations."""

    def __init__(
        self,
        skills_root: Optional[Path | str] = None,
        store: Optional[SkillIngestionStore] = None,
    ) -> None:
        self.skills_root = Path(skills_root) if skills_root else DEFAULT_SKILLS_DIR
        self.store = store or SkillIngestionStore.get_instance()
        self.validator = SkillIngestionValidator()
        self.zip_engine = SkillZipEngine.get_instance()
        self.aliasing_router = SkillAliasingRouter(skills_root=self.skills_root)
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

    def process_one_cycle(self, batch_size: int = 5) -> Dict[str, Any]:
        """Claim and process next batch of pending records through the 5-stage pipeline."""
        claimed = self.store.fetch_and_claim_pending(batch_size=batch_size)
        if not claimed:
            return {"processed_count": 0, "results": []}

        results: List[Dict[str, Any]] = []

        for record in claimed:
            res = self._process_single_record(record)
            results.append(res)

        # Refresh alias router cache after batch
        self.aliasing_router.get_alias_map(force_refresh=True)

        return {"processed_count": len(results), "results": results}

    def _process_single_record(self, record: IngestionRecord) -> Dict[str, Any]:
        receipt_id = record.receipt_id
        skill_name = record.skill_name
        raw_content = record.raw_content

        summary: Dict[str, Any] = {
            "receipt_id": receipt_id,
            "skill_name": skill_name,
            "status": "FAILED",
            "quality_score": 0.0,
            "compressed": False,
            "decision": "NONE",
            "target_bundle": None,
            "error": None,
        }

        try:
            # Stage 1: AST / Frontmatter Validation
            v_receipt = self.validator.validate(content=raw_content, filename=f"{skill_name}.md")
            if not v_receipt.is_valid:
                msg = f"AST Validation failed: {v_receipt.errors}"
                self.store.update_status(receipt_id, IngestionStatus.REJECTED, msg, v_receipt.to_dict())
                summary["error"] = msg
                return summary

            # Stage 2: SkillOpt 4-factor Quality Gate
            opt_report = SkillOptJudge.evaluate_skill(raw_content, passing_score=70.0)
            summary["quality_score"] = opt_report.total_score
            if not opt_report.passed:
                msg = f"SkillOpt rejected with score {opt_report.total_score} < 70.0: {opt_report.recommendations}"
                self.store.update_status(receipt_id, IngestionStatus.REJECTED, msg, opt_report.to_dict())
                summary["error"] = msg
                return summary

            # Stage 3: SkillZip 6-tuple contractual compression
            zip_res = self.zip_engine.compress(raw_content)
            compressed_content = zip_res.compressed_content if zip_res.compressed_length > 0 else raw_content
            summary["compressed"] = True

            # Extract triggers & tools for Ante-Gate
            triggers, tools = self._extract_metadata(raw_content)

            # Stage 4: B6 Ante-Gate Adaptive Routing
            ante_gate_res = SeamDecisionGateB5.route_incremental_skill(
                skill_name=skill_name,
                keywords=triggers,
                toolchain=tools,
                existing_bundles_dir=self.skills_root,
            )

            decision = ante_gate_res.get("decision", "MERGE_INTO_EXISTING")
            target = ante_gate_res.get("target") or "system-fleet-ops"
            summary["decision"] = decision
            summary["target_bundle"] = target

            # Stage 5: Physical Landing
            if decision == "MERGE_INTO_EXISTING" and target:
                self._land_scenario(target, skill_name, compressed_content)
            else:
                self._land_new_bundle(skill_name, compressed_content, triggers)

            # Mark COMMITTED
            self.store.update_status(
                receipt_id=receipt_id,
                status=IngestionStatus.COMMITTED,
                status_message=f"Autonomous pipeline committed into {target} via {decision}",
                validation_report={"opt_score": opt_report.total_score, "ante_gate": ante_gate_res},
            )
            summary["status"] = "COMMITTED"
            return summary

        except Exception as exc:
            logger.exception("Error in autonomous pipeline processing %s: %s", skill_name, exc)
            self.store.update_status(receipt_id, IngestionStatus.ERROR, str(exc))
            summary["error"] = str(exc)
            return summary

    def _extract_metadata(self, content: str) -> tuple[list[str], list[str]]:
        triggers: list[str] = []
        tools: list[str] = []
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                    triggers = fm.get("triggers") or fm.get("tags") or []
                    tools = fm.get("allowed-tools") or fm.get("tools") or []
                except Exception:
                    pass
        return list(triggers), list(tools)

    def _land_scenario(self, bundle_name: str, skill_name: str, content: str) -> None:
        bundle_dir = self.skills_root / bundle_name
        scenarios_dir = bundle_dir / "scenarios"
        scenarios_dir.mkdir(parents=True, exist_ok=True)

        sc_file = scenarios_dir / f"{skill_name}.md"
        sc_file.write_text(content, encoding="utf-8")

        # Update provenance absorption tracking
        prov_file = bundle_dir / "ABSORPTION_PROVENANCE.json"
        if prov_file.exists():
            try:
                data = json.loads(prov_file.read_text(encoding="utf-8"))
                absorbed = data.get("absorbed_skills", [])
                if skill_name not in absorbed:
                    absorbed.append(skill_name)
                    data["absorbed_skills"] = absorbed
                    data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    prov_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    def _land_new_bundle(self, bundle_name: str, content: str, triggers: list[str]) -> None:
        bundle_dir = self.skills_root / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "scenarios").mkdir(parents=True, exist_ok=True)
        (bundle_dir / "modules").mkdir(parents=True, exist_ok=True)

        # Write scenario
        (bundle_dir / "scenarios" / f"{bundle_name}.md").write_text(content, encoding="utf-8")

        # Write Master SKILL.md (<= 100 lines)
        master_yaml = {
            "name": bundle_name,
            "version": "1.0.0",
            "domain": bundle_name,
            "description": f"Autonomous spawned capability bundle for {bundle_name}.",
            "triggers": [t for t in triggers if t.lower() not in GENERIC_STOP_WORDS][:8],
        }
        master_content = (
            f"---\n{yaml.dump(master_yaml, allow_unicode=True)}---\n\n"
            f"# {bundle_name.title()} Capability Bundle\n\n"
            f"Autonomous spawned domain bundle managed by B6 pipeline.\n\n"
            f"## Scenarios\n- [{bundle_name}](scenarios/{bundle_name}.md)\n"
        )
        (bundle_dir / "SKILL.md").write_text(master_content, encoding="utf-8")

    async def start_background_daemon(self, interval_seconds: int = 30) -> None:
        """7x24h background worker loop polling and draining pending ingestion records."""
        self._is_running = True
        logger.info("[AutonomousPipeline] Background daemon started (polling every %ds).", interval_seconds)
        while self._is_running:
            try:
                res = self.process_one_cycle(batch_size=5)
                if res["processed_count"] > 0:
                    logger.info("[AutonomousPipeline] Processed %d records autonomously.", res["processed_count"])
            except Exception as e:
                logger.error("[AutonomousPipeline] Error in background cycle: %s", e)

            await asyncio.sleep(interval_seconds)

    def start(self, interval_seconds: int = 30) -> Optional[asyncio.Task]:
        """Start background daemon task if not already running."""
        if self._is_running and self._task and not self._task.done():
            return self._task
        self._is_running = True
        self._task = asyncio.create_task(self.start_background_daemon(interval_seconds=interval_seconds))
        return self._task

    def stop(self) -> None:
        """Stop background daemon gracefully."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def stop_daemon(self) -> None:
        """Alias for stop()."""
        self.stop()


_pipeline_instance: Optional[SkillAutonomousPipeline] = None


def get_skill_autonomous_pipeline(skills_root: Optional[Path | str] = None) -> SkillAutonomousPipeline:
    """Global accessor for SkillAutonomousPipeline singleton."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = SkillAutonomousPipeline(skills_root=skills_root)
    return _pipeline_instance

