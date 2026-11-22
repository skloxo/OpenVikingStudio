# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Autonomous Memory Purity Sentinel for archiving low-value process noise."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from openviking.storage.bm25_fts_index import BM25FTSIndex

logger = logging.getLogger("openviking.service.memory_purity_sentinel")

PROTECTED_SEGMENTS = frozenset(
    {
        "master_memory",
        "archive",
        "_system",
        "skills",
        "crystals",
        "recipes",
        "evolution_lessons",
    }
)
NOISE_DIR_SEGMENTS = frozenset({"scratch", "tmp", "drafts", "debug_logs"})
_NOISE_NAME_RE = re.compile(
    r"(?:^|[_\-.])(scratch|draft|tmp|temp|debug|process_log|trace_dump)(?:[_\-.]|$)",
    re.IGNORECASE,
)
_NOISE_MARKERS = ("[DRAFT]", "[PROCESS_LOG]", "status: draft")
_SCANNABLE_EXTS = frozenset({".md", ".txt", ".log", ".json", ".jsonl"})


class PuritySweepReport(BaseModel):
    """Structured result of one MemoryPuritySentinel patrol cycle."""

    scanned_files: int = 0
    noise_detected: int = 0
    archived_count: int = 0
    bm25_deleted: int = 0
    bm25_pruned: int = 0
    active_snr_before: float = 1.0
    active_snr_after: float = 1.0
    archived_uris: List[str] = Field(default_factory=list)
    dry_run: bool = False
    ran_at: float = Field(default_factory=time.time)
    status: str = "ok"


class MemoryPuritySentinel:
    """Resident watchdog that archives transient noise and hot-prunes BM25."""

    _instance: Optional["MemoryPuritySentinel"] = None
    _singleton_lock = threading.Lock()

    def __init__(
        self,
        *,
        active_root: Optional[Path] = None,
        archive_root: Optional[Path] = None,
        audit_log_path: Optional[Path] = None,
        bm25_index: Optional[BM25FTSIndex] = None,
    ) -> None:
        default_root = Path.home() / ".openviking" / "data" / "viking" / "default"
        self.active_root = active_root or default_root
        self.archive_root = archive_root or (self.active_root / "archive")
        self.audit_log_path = audit_log_path or (
            Path.home() / ".openviking" / "data" / "purity_sentinel.jsonl"
        )
        self._bm25_index = bm25_index
        self._sweep_lock = threading.Lock()
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._interval_seconds = 300.0
        self._sweep_count = 0
        self._last_report: Optional[PuritySweepReport] = None

    @classmethod
    def get_instance(cls) -> "MemoryPuritySentinel":
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._singleton_lock:
            cls._instance = None

    def _get_bm25(self) -> Optional[BM25FTSIndex]:
        if self._bm25_index is not None:
            return self._bm25_index
        try:
            return BM25FTSIndex.get_instance()
        except Exception as exc:
            logger.debug("[PuritySentinel] BM25 index unavailable: %s", exc)
            return None

    def _to_viking_uri(self, file_path: Path) -> str:
        rel = file_path.relative_to(self.active_root).as_posix()
        return f"viking://user/default/{rel}"

    def _is_protected(self, rel_parts: tuple[str, ...]) -> bool:
        return any(part in PROTECTED_SEGMENTS for part in rel_parts)

    def _classify_noise_reason(self, file_path: Path, rel_parts: tuple[str, ...]) -> Optional[str]:
        if any(part in NOISE_DIR_SEGMENTS for part in rel_parts[:-1]):
            return "noise_directory"
        if _NOISE_NAME_RE.search(file_path.stem):
            return "noise_filename"
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        stripped = text.strip()
        if not stripped:
            return "empty_file"
        head = stripped[:512]
        if any(marker in head for marker in _NOISE_MARKERS):
            return "draft_marker"
        return None

    def _archive_destination(self, rel_path: Path, day_tag: str) -> Path:
        dest = self.archive_root / "purity" / day_tag / rel_path
        if not dest.exists():
            return dest
        stamp = int(time.time() * 1000)
        return dest.with_name(f"{dest.stem}_{stamp}{dest.suffix}")

    def _append_audit(self, entries: List[Dict[str, Any]]) -> None:
        if not entries:
            return
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.audit_log_path, "a", encoding="utf-8") as fh:
            for item in entries:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    def run_once(self, *, dry_run: bool = False) -> PuritySweepReport:
        """Scan active_root, archive low-value noise, and hot-prune BM25 index."""
        with self._sweep_lock:
            if not self.active_root.is_dir():
                report = PuritySweepReport(dry_run=dry_run, status="missing_root")
                self._last_report = report
                return report

            scanned = 0
            noise_items: List[tuple[Path, Path, str, str]] = []
            valid_uris: set[str] = set()

            for path in sorted(self.active_root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in _SCANNABLE_EXTS:
                    continue
                rel = path.relative_to(self.active_root)
                if self._is_protected(rel.parts):
                    valid_uris.add(self._to_viking_uri(path))
                    continue
                scanned += 1
                uri = self._to_viking_uri(path)
                reason = self._classify_noise_reason(path, rel.parts)
                if reason is not None:
                    noise_items.append((path, rel, uri, reason))
                else:
                    valid_uris.add(uri)

            snr_before = (
                round((scanned - len(noise_items)) / scanned, 4) if scanned > 0 else 1.0
            )
            archived_uris: List[str] = []
            audit_entries: List[Dict[str, Any]] = []
            bm25 = self._get_bm25()
            bm25_deleted = 0
            bm25_pruned = 0

            if not dry_run and noise_items:
                day_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
                for src, rel, uri, reason in noise_items:
                    dest = self._archive_destination(rel, day_tag)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest))
                    archived_uris.append(uri)
                    if bm25 is not None and bm25.delete_document(uri):
                        bm25_deleted += 1
                    audit_entries.append(
                        {
                            "ts": time.time(),
                            "action": "archive_noise",
                            "reason": reason,
                            "uri": uri,
                            "dest": str(dest),
                        }
                    )
                self._append_audit(audit_entries)
                if bm25 is not None and valid_uris:
                    bm25_pruned = bm25.prune_orphans(
                        valid_uris, prefix="viking://user/default/"
                    )
            else:
                archived_uris = [uri for _, _, uri, _ in noise_items]

            remaining = scanned - (0 if dry_run else len(archived_uris))
            remaining_noise = len(noise_items) if dry_run else 0
            snr_after = (
                round((remaining - remaining_noise) / remaining, 4) if remaining > 0 else 1.0
            )

            self._sweep_count += 1
            report = PuritySweepReport(
                scanned_files=scanned,
                noise_detected=len(noise_items),
                archived_count=0 if dry_run else len(archived_uris),
                bm25_deleted=bm25_deleted,
                bm25_pruned=bm25_pruned,
                active_snr_before=snr_before,
                active_snr_after=snr_after,
                archived_uris=archived_uris,
                dry_run=dry_run,
            )
            self._last_report = report
            return report

    async def run_once_async(self, *, dry_run: bool = False) -> PuritySweepReport:
        return await asyncio.to_thread(self.run_once, dry_run=dry_run)

    async def _patrol_loop(self) -> None:
        while self._running:
            try:
                await self.run_once_async(dry_run=False)
            except Exception as exc:
                logger.warning("[PuritySentinel] Patrol cycle failed: %s", exc)
            await asyncio.sleep(self._interval_seconds)

    def start(self, *, interval_seconds: float = 300.0) -> bool:
        """Start the resident background patrol loop if not already running."""
        if self._running:
            return False
        self._interval_seconds = max(5.0, float(interval_seconds))
        self._running = True
        self._task = asyncio.create_task(self._patrol_loop())
        return True

    async def stop(self) -> None:
        """Gracefully stop the background patrol loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "interval_seconds": self._interval_seconds,
            "sweep_count": self._sweep_count,
            "active_root": str(self.active_root),
            "archive_root": str(self.archive_root),
            "last_report": self._last_report.model_dump() if self._last_report else None,
        }
