"""
Quarantine Manager module (Card-Observability-MemoryQuarantine-Dashboard / v1.5.10).

Manages cold archived memory drafts and staging sessions, providing:
1. Aggregate net entropy reduction metrics (targets, files, bytes freed).
2. Manifest listing, search, and pagination.
3. Safe dry-run restore validation probe.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QuarantineItem(BaseModel):
    """Metadata for a single quarantined draft or folder."""
    name: str
    source: str
    destination: str
    size_bytes: int = 0
    file_count: int = 0
    batch_id: str
    category: str
    created_at: str
    uri: Optional[str] = None


class QuarantineBatch(BaseModel):
    """Metadata for a quarantine batch run."""
    batch_id: str
    category: str
    created_at: str
    total_targets: int
    total_files: int
    total_bytes: int
    archive_dir: str


class QuarantineManifestSnapshot(BaseModel):
    """Aggregate snapshot of all quarantine archives and reduction metrics."""
    total_quarantined_targets: int
    total_quarantined_files: int
    total_quarantined_bytes: int
    total_quarantined_mb: float
    total_batches: int
    batches: List[QuarantineBatch]
    items: List[QuarantineItem]
    filtered_count: int
    cache_timestamp: float


class RestoreDryRunResult(BaseModel):
    """Result of a dry-run restoration validation probe."""
    success: bool
    item_name: str
    batch_id: str
    destination_exists: bool
    destination_files_count: int
    destination_size_bytes: int
    target_restore_path: str
    target_already_exists: bool
    safe_to_restore: bool
    message: str
    integrity_checked_at: float = Field(default_factory=time.time)


class QuarantineManager:
    """
    Thread-safe manager and audit provider for cold quarantine archives.
    Caches parsed manifests and monitors filesystem modifications.
    """

    _instance: Optional[QuarantineManager] = None
    _lock = threading.Lock()

    def __init__(self, archive_base: Optional[Path] = None) -> None:
        if archive_base is None:
            self.archive_base = Path.home() / ".openviking" / "data" / "archive"
        else:
            self.archive_base = Path(archive_base)
        self._cached_items: List[QuarantineItem] = []
        self._cached_batches: List[QuarantineBatch] = []
        self._cached_total_bytes: int = 0
        self._cached_total_files: int = 0
        self._last_scan_time: float = 0.0
        self._scan_ttl_seconds: float = 10.0

    @classmethod
    def get_instance(cls) -> QuarantineManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def refresh(self, force: bool = False) -> None:
        """Scan archive base directory and load all quarantine manifests."""
        now = time.monotonic()
        if not force and (now - self._last_scan_time) < self._scan_ttl_seconds:
            return

        with self._lock:
            if not force and (now - self._last_scan_time) < self._scan_ttl_seconds:
                return

            batches: List[QuarantineBatch] = []
            all_items: List[QuarantineItem] = []
            total_bytes = 0
            total_files = 0

            if self.archive_base.exists():
                manifest_files = sorted(
                    self.archive_base.glob("**/quarantine_manifest.json"),
                    reverse=True
                )
                for m_file in manifest_files:
                    try:
                        content = json.loads(m_file.read_text(encoding="utf-8"))
                        batch_dir = m_file.parent
                        category = batch_dir.parent.name if batch_dir.parent != self.archive_base else "archive"
                        batch_id = f"{category}/{batch_dir.name}"
                        created_at = content.get("created_at", "")
                        raw_items = content.get("items", [])

                        b_targets = len(raw_items)
                        b_files = 0
                        b_bytes = 0

                        for item in raw_items:
                            name = item.get("name", "")
                            source = item.get("source", "")
                            dest = item.get("destination", "")
                            s_bytes = int(item.get("size_bytes", 0))
                            f_count = int(item.get("file_count", 0))
                            uri = item.get("uri")

                            b_bytes += s_bytes
                            b_files += f_count

                            q_item = QuarantineItem(
                                name=name,
                                source=source,
                                destination=dest,
                                size_bytes=s_bytes,
                                file_count=f_count,
                                batch_id=batch_id,
                                category=category,
                                created_at=created_at,
                                uri=uri,
                            )
                            all_items.append(q_item)

                        batch = QuarantineBatch(
                            batch_id=batch_id,
                            category=category,
                            created_at=created_at,
                            total_targets=b_targets,
                            total_files=b_files,
                            total_bytes=b_bytes,
                            archive_dir=str(batch_dir),
                        )
                        batches.append(batch)
                        total_bytes += b_bytes
                        total_files += b_files
                    except Exception as e:
                        logger.warning("Failed to parse quarantine manifest %s: %s", m_file, e)

            self._cached_batches = batches
            self._cached_items = all_items
            self._cached_total_bytes = total_bytes
            self._cached_total_files = total_files
            self._last_scan_time = now

    def get_snapshot(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
        force_refresh: bool = False,
    ) -> QuarantineManifestSnapshot:
        """Return aggregate reduction metrics and paginated filtered items."""
        self.refresh(force=force_refresh)

        with self._lock:
            items = self._cached_items
            batches = list(self._cached_batches)
            total_targets = len(items)
            total_files = self._cached_total_files
            total_bytes = self._cached_total_bytes

        filtered = items
        if category and category.strip():
            c_lower = category.strip().lower()
            filtered = [it for it in filtered if it.category.lower() == c_lower]

        if search and search.strip():
            q = search.strip().lower()
            filtered = [
                it for it in filtered
                if q in it.name.lower() or q in it.source.lower() or (it.uri and q in it.uri.lower())
            ]

        filtered_count = len(filtered)
        paginated = filtered[offset : offset + limit]

        mb_freed = round(total_bytes / (1024.0 * 1024.0), 2)

        return QuarantineManifestSnapshot(
            total_quarantined_targets=total_targets,
            total_quarantined_files=total_files,
            total_quarantined_bytes=total_bytes,
            total_quarantined_mb=mb_freed,
            total_batches=len(batches),
            batches=batches,
            items=paginated,
            filtered_count=filtered_count,
            cache_timestamp=time.time(),
        )

    def dry_run_restore(self, batch_id: str, item_name: str) -> RestoreDryRunResult:
        """Perform a read-only integrity dry-run validation of a quarantined item."""
        self.refresh()

        matched: Optional[QuarantineItem] = None
        with self._lock:
            for it in self._cached_items:
                if it.name == item_name and (not batch_id or it.batch_id == batch_id):
                    matched = it
                    break

        if not matched:
            return RestoreDryRunResult(
                success=False,
                item_name=item_name,
                batch_id=batch_id,
                destination_exists=False,
                destination_files_count=0,
                destination_size_bytes=0,
                target_restore_path="",
                target_already_exists=False,
                safe_to_restore=False,
                message=f"Quarantined item '{item_name}' not found in batch '{batch_id}'.",
            )

        dest_path = Path(matched.destination)
        dest_exists = dest_path.exists()
        dest_files_count = 0
        dest_size = 0

        if dest_exists:
            if dest_path.is_file():
                dest_files_count = 1
                dest_size = dest_path.stat().st_size
            else:
                for f in dest_path.rglob("*"):
                    if f.is_file():
                        dest_files_count += 1
                        dest_size += f.stat().st_size

        target_path = Path(matched.source)
        target_already_exists = target_path.exists()

        safe = dest_exists and (dest_files_count > 0 or dest_size > 0)
        msg = (
            f"Dry-run verified: {dest_files_count} files ({dest_size} bytes) intact in archive. "
            f"Target location {'already has conflicting files' if target_already_exists else 'is ready for clean restore'}."
        )

        return RestoreDryRunResult(
            success=safe,
            item_name=matched.name,
            batch_id=matched.batch_id,
            destination_exists=dest_exists,
            destination_files_count=dest_files_count,
            destination_size_bytes=dest_size,
            target_restore_path=str(target_path),
            target_already_exists=target_already_exists,
            safe_to_restore=safe,
            message=msg,
        )
