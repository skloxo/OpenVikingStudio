# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Knowledge Deficit Capture, Reflection Scaffolding & Dual-Track Fulfillment Engine.

Spec: docs/architecture/KNOWLEDGE_DEFICIT_SCAFFOLDING_SPEC.md (Card-207).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from openviking.service.knowledge_deficit_scaffolder import (
    classify_deficit_route,
    compute_query_similarity,
    extract_entity_and_category,
    normalize_query,
    render_scaffold_markdown,
)

logger = logging.getLogger("openviking.service.knowledge_deficit")

DEFAULT_MISS_THRESHOLD = 3
DEFAULT_SIMILARITY_THRESHOLD = 0.72
IGNORED_PING_QUERIES = {"health", "ping", "test", "ok", "hello"}

__all__ = [
    "BlindspotLedger",
    "DEFAULT_MISS_THRESHOLD",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "classify_deficit_route",
    "compute_query_similarity",
    "extract_entity_and_category",
    "render_scaffold_markdown",
]


class BlindspotLedger:
    """SQLite-backed frequency funnel and two-stage remediation ledger."""

    _instance: Optional["BlindspotLedger"] = None
    _singleton_lock = threading.Lock()

    def __init__(
        self,
        db_path: Optional[Path] = None,
        deliverables_dir: Optional[Path] = None,
        miss_threshold: int = DEFAULT_MISS_THRESHOLD,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        base_resources = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources"
        self.db_path = Path(db_path) if db_path else (base_resources / "knowledge_deficits.db")
        self.deliverables_dir = Path(deliverables_dir) if deliverables_dir else (base_resources / "wiki_remediation")
        self.miss_threshold = max(1, int(miss_threshold))
        self.similarity_threshold = float(similarity_threshold)
        self._rw_lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def get_instance(cls) -> "BlindspotLedger":
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._singleton_lock:
            cls._instance = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blindspot_deficits (
                    deficit_id TEXT PRIMARY KEY,
                    canonical_query TEXT NOT NULL,
                    aliases_json TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    entity_category TEXT NOT NULL,
                    suggested_route TEXT NOT NULL,
                    miss_count INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'observing',
                    top_score REAL NOT NULL DEFAULT 0.0,
                    source_op TEXT NOT NULL DEFAULT 'search',
                    account_id TEXT NOT NULL DEFAULT 'default',
                    user_id TEXT NOT NULL DEFAULT 'default',
                    scaffold_markdown TEXT NOT NULL DEFAULT '',
                    fulfillment_content TEXT NOT NULL DEFAULT '',
                    deliverable_uri TEXT NOT NULL DEFAULT '',
                    fulfillment_track TEXT NOT NULL DEFAULT '',
                    stage_task_id TEXT NOT NULL DEFAULT '',
                    step_trace_json TEXT NOT NULL DEFAULT '[]',
                    embedding_json TEXT NOT NULL DEFAULT '[]',
                    dismiss_reason TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    promoted_at REAL,
                    fulfilled_at REAL
                )
                """
            )
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["aliases"] = json.loads(d.pop("aliases_json", "[]") or "[]")
        d["step_trace"] = json.loads(d.pop("step_trace_json", "[]") or "[]")
        d.pop("embedding_json", None)
        return d

    def _find_matching_row(
        self,
        conn: sqlite3.Connection,
        query: str,
        embedding: Optional[Sequence[float]] = None,
    ) -> Optional[sqlite3.Row]:
        rows = conn.execute(
            "SELECT * FROM blindspot_deficits WHERE status IN ('observing', 'pending_fulfillment') ORDER BY updated_at DESC LIMIT 200"
        ).fetchall()
        incoming_entity, _ = extract_entity_and_category(query)
        best_row: Optional[sqlite3.Row] = None
        best_sim = 0.0
        for row in rows:
            if len(incoming_entity) >= 2 and incoming_entity.lower() == str(row["entity_name"]).lower():
                return row
            emb_stored = json.loads(row["embedding_json"] or "[]")
            sim = compute_query_similarity(query, row["canonical_query"], embedding, emb_stored)
            if sim < self.similarity_threshold:
                for alias in json.loads(row["aliases_json"] or "[]"):
                    sim = max(sim, compute_query_similarity(query, alias, embedding, emb_stored))
            if sim >= self.similarity_threshold and sim > best_sim:
                best_sim = sim
                best_row = row
        return best_row

    def _build_stage1_trace(self, entity_name: str, route: str) -> List[Dict[str, Any]]:
        now = time.time()
        return [
            {"step": "step_miss_capture", "status": "completed", "detail": f"聚合缺失主题: {entity_name}", "ts": now},
            {"step": "step_reflection", "status": "completed", "detail": f"路由判断={route}，生成标准槽位骨架", "ts": now},
            {"step": "step_ticket_enqueue", "status": "completed", "detail": "阶段一知识补全卡挂牌完成", "ts": now},
        ]

    def _emit_stage1_task_record(self, deficit_id: str, entity_name: str, account_id: str, user_id: str) -> str:
        task_id = f"rem_{deficit_id.replace('scaf_', '')}"
        try:
            from openviking.service.task_tracker import get_task_tracker
            tracker = get_task_tracker(optional=True)
            if tracker is None:
                return task_id
            loop = asyncio.get_running_loop()

            async def _record() -> None:
                await tracker.create(
                    task_type="knowledge_remediation",
                    resource_id=f"knowledge_deficit://{deficit_id}",
                    account_id=account_id or "default",
                    user_id=user_id or "default",
                    task_id=task_id,
                    meta={"entity_name": entity_name, "deficit_id": deficit_id},
                )
                await tracker.complete(
                    task_id,
                    {"deficit_id": deficit_id, "stage": "stage1_scaffold_completed"},
                    account_id=account_id or "default",
                    user_id=user_id or "default",
                )

            loop.create_task(_record())
        except Exception:
            pass
        return task_id

    def record_miss(
        self,
        query: str,
        *,
        top_score: float = 0.0,
        operation: str = "search",
        account_id: str = "default",
        user_id: str = "default",
        embedding: Optional[Sequence[float]] = None,
        force_promote: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Record a retrieval zero-hit or low-score miss and promote when count >= threshold."""
        clean = normalize_query(query)
        if len(clean) < 2 or clean.lower() in IGNORED_PING_QUERIES:
            return None

        now = time.time()
        with self._rw_lock, self._connect() as conn:
            matched = self._find_matching_row(conn, clean, embedding=embedding)
            if matched is not None:
                record = self._row_to_dict(matched)
                aliases = list(record["aliases"])
                if clean not in aliases:
                    aliases.append(clean)
                new_count = int(record["miss_count"]) + 1
                if force_promote and new_count < self.miss_threshold:
                    new_count = self.miss_threshold
                status = record["status"]
                promoted_at = record.get("promoted_at")
                scaffold = record.get("scaffold_markdown") or ""
                step_trace = record.get("step_trace") or []
                stage_task_id = record.get("stage_task_id") or ""

                if status == "observing" and new_count >= self.miss_threshold:
                    status = "pending_fulfillment"
                    promoted_at = now
                    record["miss_count"] = new_count
                    record["status"] = status
                    scaffold = render_scaffold_markdown(record)
                    step_trace = self._build_stage1_trace(record["entity_name"], record["suggested_route"])
                    stage_task_id = self._emit_stage1_task_record(record["deficit_id"], record["entity_name"], account_id, user_id)

                conn.execute(
                    """
                    UPDATE blindspot_deficits
                    SET aliases_json=?, miss_count=?, status=?, top_score=?, updated_at=?,
                        promoted_at=?, scaffold_markdown=?, step_trace_json=?, stage_task_id=?
                    WHERE deficit_id=?
                    """,
                    (
                        json.dumps(aliases, ensure_ascii=False), new_count, status, float(top_score), now,
                        promoted_at, scaffold, json.dumps(step_trace, ensure_ascii=False), stage_task_id, record["deficit_id"],
                    ),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (record["deficit_id"],)).fetchone()
                return self._row_to_dict(row)

            entity, category = extract_entity_and_category(clean)
            route = classify_deficit_route(clean, entity_category=category)
            digest = hashlib.sha256(clean.lower().encode("utf-8")).hexdigest()[:8]
            deficit_id = f"scaf_{time.strftime('%Y%m%d')}_{digest}"
            if conn.execute("SELECT 1 FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone():
                deficit_id = f"{deficit_id}_{int(now * 1000) % 10000}"

            init_count = self.miss_threshold if force_promote else 1
            status = "pending_fulfillment" if init_count >= self.miss_threshold else "observing"
            promoted_at = now if status == "pending_fulfillment" else None
            draft = {
                "deficit_id": deficit_id, "entity_name": entity, "entity_category": category,
                "suggested_route": route, "miss_count": init_count, "status": status,
            }
            scaffold = render_scaffold_markdown(draft) if status == "pending_fulfillment" else ""
            step_trace = self._build_stage1_trace(entity, route) if status == "pending_fulfillment" else []
            stage_task_id = self._emit_stage1_task_record(deficit_id, entity, account_id, user_id) if status == "pending_fulfillment" else ""

            conn.execute(
                """
                INSERT INTO blindspot_deficits (
                    deficit_id, canonical_query, aliases_json, entity_name, entity_category,
                    suggested_route, miss_count, status, top_score, source_op, account_id, user_id,
                    scaffold_markdown, step_trace_json, stage_task_id, embedding_json,
                    created_at, updated_at, promoted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deficit_id, clean, json.dumps([clean], ensure_ascii=False), entity, category,
                    route, init_count, status, float(top_score), operation, account_id, user_id,
                    scaffold, json.dumps(step_trace, ensure_ascii=False), stage_task_id,
                    json.dumps(list(embedding) if embedding else []), now, now, promoted_at,
                ),
            )
            conn.commit()
            created = conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone()
            return self._row_to_dict(created)

    def cast_scaffold(self, deficit_id: str) -> Dict[str, Any]:
        """Explicitly promote an observing entry into Stage-1 scaffolded card (completed Stage-1)."""
        with self._rw_lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone()
            if row is None:
                raise KeyError(f"Deficit not found: {deficit_id}")
            record = self._row_to_dict(row)
            now = time.time()
            if record["status"] == "observing":
                record["status"] = "pending_fulfillment"
            scaffold = render_scaffold_markdown(record)
            trace = record["step_trace"] or self._build_stage1_trace(record["entity_name"], record["suggested_route"])
            stage_task_id = record["stage_task_id"] or self._emit_stage1_task_record(
                deficit_id, record["entity_name"], record["account_id"], record["user_id"]
            )
            conn.execute(
                """
                UPDATE blindspot_deficits
                SET status=?, scaffold_markdown=?, step_trace_json=?, stage_task_id=?,
                    promoted_at=COALESCE(promoted_at, ?), updated_at=?
                WHERE deficit_id=?
                """,
                (record["status"], scaffold, json.dumps(trace, ensure_ascii=False), stage_task_id, now, now, deficit_id),
            )
            conn.commit()
            return self._row_to_dict(conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone())

    def fulfill_deficit(
        self,
        deficit_id: str,
        *,
        content: str = "",
        fields: Optional[Dict[str, str]] = None,
        track: str = "",
    ) -> Dict[str, Any]:
        """Execute Stage-2 Dual-Track fulfillment, persist deliverable Markdown, and mark fulfilled."""
        body_parts: List[str] = []
        if fields:
            for k, v in fields.items():
                if str(v or "").strip():
                    body_parts.append(f"- **{str(k).strip()}**: {str(v).strip()}")
        if content and content.strip():
            body_parts.append(content.strip())
        resolved_content = "\n".join(body_parts).strip()
        if not resolved_content:
            raise ValueError("Fulfillment content or structured fields must not be empty")

        with self._rw_lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone()
            if row is None:
                raise KeyError(f"Deficit not found: {deficit_id}")
            record = self._row_to_dict(row)
            resolved_track = track.strip() or record["suggested_route"] or "human_assistance"
            now = time.time()

            self.deliverables_dir.mkdir(parents=True, exist_ok=True)
            deliverable_file = self.deliverables_dir / f"{deficit_id}.md"
            deliverable_md = (
                "---\n"
                f"deficit_id: \"{deficit_id}\"\n"
                f"entity_name: \"{record['entity_name']}\"\n"
                f"fulfillment_track: \"{resolved_track}\"\n"
                "status: \"fulfilled\"\n"
                "---\n\n"
                f"# {record['entity_name']}\n\n"
                f"{resolved_content}\n"
            )
            deliverable_file.write_text(deliverable_md, encoding="utf-8")
            deliverable_uri = f"viking://resources/wiki_remediation/{deficit_id}.md"

            conn.execute(
                """
                UPDATE blindspot_deficits
                SET status='fulfilled', fulfillment_content=?, deliverable_uri=?,
                    fulfillment_track=?, fulfilled_at=?, updated_at=?
                WHERE deficit_id=?
                """,
                (resolved_content, deliverable_uri, resolved_track, now, now, deficit_id),
            )
            conn.commit()
            return self._row_to_dict(conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone())

    def dismiss_deficit(self, deficit_id: str, reason: str = "") -> Dict[str, Any]:
        with self._rw_lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone()
            if row is None:
                raise KeyError(f"Deficit not found: {deficit_id}")
            now = time.time()
            conn.execute(
                "UPDATE blindspot_deficits SET status='dismissed', dismiss_reason=?, updated_at=? WHERE deficit_id=?",
                (reason.strip(), now, deficit_id),
            )
            conn.commit()
            return self._row_to_dict(conn.execute("SELECT * FROM blindspot_deficits WHERE deficit_id=?", (deficit_id,)).fetchone())

    def list_deficits(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status and status != "all":
                rows = conn.execute(
                    "SELECT * FROM blindspot_deficits WHERE status=? ORDER BY miss_count DESC, updated_at DESC LIMIT ?",
                    (status, max(1, min(limit, 500))),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM blindspot_deficits ORDER BY updated_at DESC LIMIT ?",
                    (max(1, min(limit, 500))),
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT status, suggested_route, miss_count FROM blindspot_deficits").fetchall()
        counts = {"observing": 0, "pending_fulfillment": 0, "fulfilled": 0, "dismissed": 0}
        routes = {"human_assistance": 0, "autonomous_researcher": 0}
        total_misses = 0
        for r in rows:
            st = r["status"]
            if st in counts:
                counts[st] += 1
            if st == "pending_fulfillment" and r["suggested_route"] in routes:
                routes[r["suggested_route"]] += 1
            total_misses += int(r["miss_count"] or 0)
        suppression_pct = round((1.0 - (counts["pending_fulfillment"] / total_misses)) * 100.0, 1) if total_misses > 0 else 100.0
        return {
            "total_tracked": len(rows),
            "total_misses": total_misses,
            "observing_count": counts["observing"],
            "pending_fulfillment_count": counts["pending_fulfillment"],
            "fulfilled_count": counts["fulfilled"],
            "dismissed_count": counts["dismissed"],
            "human_assistance_pending": routes["human_assistance"],
            "autonomous_researcher_pending": routes["autonomous_researcher"],
            "storm_suppression_pct": max(0.0, min(100.0, suppression_pct)),
            "miss_threshold": self.miss_threshold,
        }
