# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Task Card Manager for Autonomous Issue Filing and Lifecycle Governance.

Implements the Charlie Munger Inversion & Occam's Razor System:
1. Decentralized Ingestion: Any satellite or local agent can file bug reports via MCP.
2. Anti-Card-Storm: Semantic fingerprint deduplication collapses cascades into single cards.
3. Blame-Shift Defense: 4xx client parameter errors are rejected at the gate.
4. Clean Inbox Decoupling: Avoids concurrent Git mutation on REFACTORING_PLAN.md.
5. Structured Lifecyle: Pending -> Triaged -> Resolved with commit and tag traceability.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("openviking.service.task_card_manager")


@dataclass
class IssueTaskCard:
    """Strongly-typed DTO for issue task card filing."""
    title: str
    module: str
    symptom: str
    hypothesis: str = ""
    reproduce_steps: str = ""
    suggested_action: str = ""
    reporting_agent: str = "agent"
    priority: str = "P1"


class TaskCardManager:
    """Singleton manager for autonomous issue filing, deduplication, and lifecycle tracking."""

    _instance: Optional["TaskCardManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        base_dir = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "task_cards"
        self._inbox_dir = base_dir / "inbox"
        self._resolved_dir = base_dir / "resolved"
        self._inbox_dir.mkdir(parents=True, exist_ok=True)
        self._resolved_dir.mkdir(parents=True, exist_ok=True)
        self._rw_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "TaskCardManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _compute_fingerprint(self, module: str, symptom: str) -> str:
        """Compute 12-char deterministic fingerprint from module and normalized symptom core."""
        norm_mod = module.strip().lower()
        # Strip timestamps, dynamic numbers, and hex IDs from symptom signature
        norm_sym = symptom.strip().lower()
        norm_sym = re.sub(r"0x[0-9a-f]+", "", norm_sym)
        norm_sym = re.sub(r"\d{4}-\d{2}-\d{2}[t\s]\d{2}:\d{2}:\d{2}", "", norm_sym)
        norm_sym = re.sub(r"\d+\.\d+ms", "", norm_sym)
        signature = f"{norm_mod}::{norm_sym[:120]}"
        return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:12]

    def _validate_blame_shift(self, symptom: str) -> None:
        """Reject obvious 4xx client bad requests to avoid blaming server for caller bugs."""
        lower = symptom.lower()
        if any(term in lower for term in ["400 bad request", "422 unprocessable", "missing required query parameter", "invalid argument", "客户端错误"]):
            raise ValueError(
                f"[Blame-Shift Defense] 拒绝立为系统缺陷工单: 检测到调用方传参错误 (4xx Bad Request)。"
                f"此为客户端代码/参数不合规，请检查调用方输入，严禁转嫁为服务端缺陷。"
            )

    async def file_issue_card(
        self,
        title: str,
        priority: str,
        module: str,
        symptom: str,
        initiator: str = "agent",
        root_cause_hypothesis: str = "",
        reproduce_steps: str = "",
        suggested_action: str = "",
    ) -> Dict[str, Any]:
        """Ingest bug report, deduplicate via fingerprint, and persist to inbox."""
        self._validate_blame_shift(symptom)

        valid_priorities = ("P0", "P1", "P2", "P3")
        norm_prio = priority.upper() if priority.upper() in valid_priorities else "P1"
        fingerprint = self._compute_fingerprint(module, symptom)

        with self._rw_lock:
            # Check existing pending cards for deduplication
            for json_path in self._inbox_dir.glob("*.json"):
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                    if data.get("fingerprint") == fingerprint and data.get("status") == "pending":
                        # Existing issue found: Atomic Increment to prevent card flooding!
                        data["occurrence_count"] = data.get("occurrence_count", 1) + 1
                        data["last_seen_at"] = time.time()
                        agents = set(data.get("affected_agents", []))
                        agents.add(initiator)
                        data["affected_agents"] = sorted(list(agents))

                        # Bump priority if new report has higher severity
                        if valid_priorities.index(norm_prio) < valid_priorities.index(data.get("priority", "P1")):
                            data["priority"] = norm_prio

                        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                        self._write_markdown_card(data, json_path.with_suffix(".md"))
                        logger.info("[TaskCardManager] Collapsed recurring bug into %s (count: %d)", data["card_id"], data["occurrence_count"])
                        return {
                            "status": "aggregated",
                            "action": "count_incremented",
                            "card_id": data["card_id"],
                            "occurrence_count": data["occurrence_count"],
                            "affected_agents": data["affected_agents"],
                            "priority": data["priority"],
                        }
                except Exception as e:
                    logger.debug("Failed to read card %s: %s", json_path, e)

            # New Issue Card creation
            date_prefix = time.strftime("%Y%m%d")
            clean_title = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fa5]+", "-", title).strip("-")[:40] or "Issue"
            card_id = f"Card-Issue-{date_prefix}-{fingerprint}"
            now = time.time()

            card_record = {
                "card_id": card_id,
                "fingerprint": fingerprint,
                "title": title,
                "clean_title": clean_title,
                "priority": norm_prio,
                "module": module,
                "symptom": symptom,
                "initiator": initiator,
                "affected_agents": [initiator],
                "occurrence_count": 1,
                "root_cause_hypothesis": root_cause_hypothesis,
                "reproduce_steps": reproduce_steps,
                "suggested_action": suggested_action,
                "status": "pending",
                "created_at": now,
                "last_seen_at": now,
                "resolved_at": None,
                "resolution_metadata": None,
            }

            json_file = self._inbox_dir / f"{card_id}.json"
            md_file = self._inbox_dir / f"{card_id}.md"

            json_file.write_text(json.dumps(card_record, ensure_ascii=False, indent=2), encoding="utf-8")
            self._write_markdown_card(card_record, md_file)

            # Best-effort task tracker registration
            try:
                from openviking.service.task_tracker import get_task_tracker
                tracker = get_task_tracker()
                if tracker:
                    asyncio.create_task(
                        tracker.create(
                            task_type="agent_issue_card",
                            task_id=card_id,
                            resource_id=f"viking://resources/task_cards/inbox/{card_id}.md",
                            account_id="default",
                            user_id="default",
                            meta={"title": title, "priority": norm_prio, "initiator": initiator},
                        )
                    )
            except Exception:
                pass

            logger.info("[TaskCardManager] Filed new autonomous task card %s (priority: %s)", card_id, norm_prio)
            return {
                "status": "created",
                "action": "new_card",
                "card_id": card_id,
                "occurrence_count": 1,
                "affected_agents": [initiator],
                "priority": norm_prio,
                "inbox_uri": f"viking://resources/task_cards/inbox/{card_id}.md",
            }

    def _write_markdown_card(self, data: Dict[str, Any], path: Path) -> None:
        """Format card data as human-readable and AI-friendly Markdown."""
        agents_str = ", ".join(f"`{a}`" for a in data.get("affected_agents", []))
        created_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data["created_at"]))
        last_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data["last_seen_at"]))
        md = f"""# 📋 {data['card_id']}: {data['title']}

- **Priority**: `{data['priority']}` | **Module**: `{data['module']}` | **Status**: `{data['status']}`
- **Initiator**: `{data['initiator']}` | **Affected Agents**: {agents_str}
- **Occurrence Count**: `{data['occurrence_count']}` | **Fingerprint**: `{data['fingerprint']}`
- **First Seen**: {created_str} | **Last Seen**: {last_str}

## 🔍 Phenomenon & Physical Symptom
{data['symptom']}

## 💡 Root Cause Hypothesis
{data.get('root_cause_hypothesis', 'N/A')}

## 🧪 Reproduce Steps / Context
{data.get('reproduce_steps', 'N/A')}

## 🛠️ Suggested Fix / Workaround
{data.get('suggested_action', 'N/A')}
"""
        path.write_text(md, encoding="utf-8")

    async def list_pending_cards(self) -> List[Dict[str, Any]]:
        """Retrieve all active pending cards sorted by priority (P0 first) then recency."""
        cards = []
        prio_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        with self._rw_lock:
            for json_path in self._inbox_dir.glob("*.json"):
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                    if data.get("status") == "pending":
                        cards.append(data)
                except Exception:
                    continue

        cards.sort(key=lambda c: (prio_order.get(c.get("priority", "P1"), 9), -c.get("last_seen_at", 0)))
        return cards

    async def resolve_card(
        self,
        card_id: str,
        resolution_tag: str,
        commit_hash: str = "",
        summary: str = "",
    ) -> Dict[str, Any]:
        """Move card from pending inbox to resolved archive with closure metadata."""
        with self._rw_lock:
            src_json = self._inbox_dir / f"{card_id}.json"
            src_md = self._inbox_dir / f"{card_id}.md"
            if not src_json.exists():
                raise FileNotFoundError(f"Card {card_id} not found in inbox")

            data = json.loads(src_json.read_text(encoding="utf-8"))
            data["status"] = "resolved"
            data["resolved_at"] = time.time()
            data["resolution_metadata"] = {
                "resolution_tag": resolution_tag,
                "commit_hash": commit_hash,
                "summary": summary,
            }

            dest_json = self._resolved_dir / f"{card_id}.json"
            dest_md = self._resolved_dir / f"{card_id}.md"

            dest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._write_markdown_card(data, dest_md)

            src_json.unlink(missing_ok=True)
            src_md.unlink(missing_ok=True)

            logger.info("[TaskCardManager] Resolved card %s under tag %s", card_id, resolution_tag)
            return {
                "status": "resolved",
                "card_id": card_id,
                "resolution_tag": resolution_tag,
                "commit_hash": commit_hash,
            }

    async def list_resolved_cards(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve resolved task cards sorted by resolved_at descending."""
        cards = []
        with self._rw_lock:
            for json_path in self._resolved_dir.glob("*.json"):
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                    if data.get("status") == "resolved":
                        cards.append(data)
                except Exception:
                    continue

        cards.sort(key=lambda c: -c.get("resolved_at", 0))
        return cards[:limit]

    async def get_card_detail(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full details for a task card from either inbox or resolved archives."""
        with self._rw_lock:
            inbox_file = self._inbox_dir / f"{card_id}.json"
            if inbox_file.exists():
                try:
                    return json.loads(inbox_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            resolved_file = self._resolved_dir / f"{card_id}.json"
            if resolved_file.exists():
                try:
                    return json.loads(resolved_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return None

    async def get_card_summary_stats(self) -> Dict[str, Any]:
        """Aggregate high-density operational metrics across pending and resolved cards."""
        pending_cards = await self.list_pending_cards()
        resolved_cards = await self.list_resolved_cards(limit=500)

        p0_count = sum(1 for c in pending_cards if c.get("priority") == "P0")
        p1_count = sum(1 for c in pending_cards if c.get("priority") == "P1")
        p2_count = sum(1 for c in pending_cards if c.get("priority") == "P2")
        p3_count = sum(1 for c in pending_cards if c.get("priority") == "P3")

        affected_agents = set()
        total_occurrences = 0
        for c in pending_cards:
            total_occurrences += c.get("occurrence_count", 1)
            for a in c.get("affected_agents", []):
                affected_agents.add(a)

        # Anti-card-storm compression ratio
        raw_events = total_occurrences
        deduped_cards = len(pending_cards)
        storm_suppression_pct = 0.0
        if raw_events > 0:
            storm_suppression_pct = round((1.0 - (deduped_cards / raw_events)) * 100.0, 1)

        return {
            "pending_count": len(pending_cards),
            "resolved_count": len(resolved_cards),
            "p0_count": p0_count,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "p3_count": p3_count,
            "total_occurrences": total_occurrences,
            "storm_suppression_pct": storm_suppression_pct,
            "affected_agents_count": len(affected_agents),
            "affected_agents": sorted(list(affected_agents)),
        }

