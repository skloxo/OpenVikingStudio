"""Privacy Compliance Audit & Quarantine Engine (SSOT).

Provides physical isolation (Quarantine Vault) for sensitive data leaks,
secure destruction (Purge) capabilities, and immutable compliance audit
logging (compliance_audit.jsonl) for multi-agent clusters.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Mapping, Sequence
import uuid

from openviking.service.privacy_quarantine_types import (
    AuditAction,
    AuditReportSummary,
    ComplianceAuditEntry,
    QuarantineItem,
    QuarantineStatus,
)


class PrivacyQuarantineEngine:
    """Synchronous, thread-safe privacy quarantine and compliance audit engine."""

    _instance: PrivacyQuarantineEngine | None = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        *,
        storage_dir: Path | str | None = None,
        audit_ledger_path: Path | str | None = None,
    ) -> None:
        """Initializes the quarantine vault and compliance audit ledger paths."""
        base_data_dir = (
            Path(storage_dir)
            if storage_dir
            else Path.home() / ".openviking" / "data" / "quarantine"
        )
        self._vault_dir = base_data_dir / "vault"
        self._index_file = base_data_dir / "quarantine_index.json"
        self._audit_ledger_file = (
            Path(audit_ledger_path)
            if audit_ledger_path
            else Path.home() / ".openviking" / "data" / "compliance_audit.jsonl"
        )

        self._lock = threading.Lock()
        self._items: dict[str, QuarantineItem] = {}
        self._ensure_storage()
        self._load_index()

    @classmethod
    def get_instance(cls) -> PrivacyQuarantineEngine:
        """Returns the process-wide thread-safe singleton instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_storage(self) -> None:
        """Ensures that required vault and data directories exist on disk."""
        self._vault_dir.mkdir(parents=True, exist_ok=True)
        self._audit_ledger_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """Loads existing quarantine items from disk index into memory."""
        if not self._index_file.exists():
            return
        try:
            with open(self._index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for raw in data:
                item = QuarantineItem(
                    quarantine_id=raw["quarantine_id"],
                    target_uri=raw["target_uri"],
                    category=raw["category"],
                    reason=raw["reason"],
                    actor=raw["actor"],
                    content_sha256=raw["content_sha256"],
                    created_at=raw["created_at"],
                    status=QuarantineStatus(raw.get("status", "QUARANTINED")),
                    metadata=raw.get("metadata", {}),
                    resolved_at=raw.get("resolved_at"),
                )
                self._items[item.quarantine_id] = item
        except Exception:
            # Fallback gracefully if index file is empty or corrupted
            self._items = {}

    def _save_index(self) -> None:
        """Persists all in-memory quarantine items to disk index file."""
        data = [item.to_dict() for item in self._items.values()]
        temp_file = self._index_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(self._index_file)

    def quarantine(
        self,
        *,
        target_uri: str,
        raw_content: str,
        reason: str,
        category: str = "credential",
        actor: str = "system",
        metadata: Mapping[str, Any] | None = None,
    ) -> QuarantineItem:
        """Isolates high-risk content into the Quarantine Vault and registers audit."""
        content_bytes = raw_content.encode("utf-8")
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()
        quarantine_id = f"qnt_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        item = QuarantineItem(
            quarantine_id=quarantine_id,
            target_uri=target_uri,
            category=category,
            reason=reason,
            actor=actor,
            content_sha256=content_sha256,
            created_at=now_iso,
            status=QuarantineStatus.QUARANTINED,
            metadata=dict(metadata or {}),
        )

        with self._lock:
            # Write raw content to isolated physical vault file
            vault_file = self._vault_dir / f"{quarantine_id}.vault"
            vault_file.write_bytes(content_bytes)

            self._items[quarantine_id] = item
            self._save_index()

        self.record_audit(
            action=AuditAction.QUARANTINE,
            actor=actor,
            target=target_uri,
            details={
                "quarantine_id": quarantine_id,
                "category": category,
                "reason": reason,
                "content_sha256": content_sha256,
            },
        )
        return item

    def restore(
        self,
        quarantine_id: str,
        *,
        actor: str = "admin",
        reason: str = "verified_safe",
    ) -> QuarantineItem:
        """Unfreezes a quarantined item after security verification."""
        with self._lock:
            if quarantine_id not in self._items:
                raise KeyError(f"Quarantine item not found: {quarantine_id}")
            current = self._items[quarantine_id]
            if current.status != QuarantineStatus.QUARANTINED:
                raise ValueError(f"Item is already in terminal state: {current.status}")

            now_iso = datetime.now(timezone.utc).isoformat()
            updated = QuarantineItem(
                quarantine_id=current.quarantine_id,
                target_uri=current.target_uri,
                category=current.category,
                reason=current.reason,
                actor=current.actor,
                content_sha256=current.content_sha256,
                created_at=current.created_at,
                status=QuarantineStatus.RESTORED,
                metadata={**current.metadata, "restore_reason": reason},
                resolved_at=now_iso,
            )
            self._items[quarantine_id] = updated
            self._save_index()

        self.record_audit(
            action=AuditAction.RESTORE,
            actor=actor,
            target=current.target_uri,
            details={"quarantine_id": quarantine_id, "reason": reason},
        )
        return updated

    def purge(
        self,
        quarantine_id: str,
        *,
        actor: str = "admin",
        reason: str = "permanent_destruction",
    ) -> bool:
        """Securely erases quarantined content from physical disk and seals record."""
        with self._lock:
            if quarantine_id not in self._items:
                raise KeyError(f"Quarantine item not found: {quarantine_id}")
            current = self._items[quarantine_id]

            # Secure shredding: zero-fill before deletion
            vault_file = self._vault_dir / f"{quarantine_id}.vault"
            if vault_file.exists():
                file_size = vault_file.stat().st_size
                vault_file.write_bytes(b"\x00" * file_size)
                vault_file.unlink()

            now_iso = datetime.now(timezone.utc).isoformat()
            updated = QuarantineItem(
                quarantine_id=current.quarantine_id,
                target_uri=current.target_uri,
                category=current.category,
                reason=current.reason,
                actor=current.actor,
                content_sha256=current.content_sha256,
                created_at=current.created_at,
                status=QuarantineStatus.PURGED,
                metadata={**current.metadata, "purge_reason": reason},
                resolved_at=now_iso,
            )
            self._items[quarantine_id] = updated
            self._save_index()

        self.record_audit(
            action=AuditAction.PURGE,
            actor=actor,
            target=current.target_uri,
            details={"quarantine_id": quarantine_id, "reason": reason},
        )
        return True

    def list_quarantined(
        self,
        *,
        status: QuarantineStatus | str | None = None,
        category: str | None = None,
    ) -> Sequence[QuarantineItem]:
        """Lists quarantined items matching optional status or category filter."""
        target_status: QuarantineStatus | None = None
        if isinstance(status, QuarantineStatus):
            target_status = status
        elif isinstance(status, str):
            try:
                target_status = QuarantineStatus(status)
            except ValueError:
                target_status = None

        with self._lock:
            items = list(self._items.values())

        filtered: list[QuarantineItem] = []
        for item in items:
            if target_status and item.status != target_status:
                continue
            if category and item.category != category:
                continue
            filtered.append(item)
        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    def get_quarantined(self, quarantine_id: str) -> QuarantineItem | None:
        """Retrieves a single quarantine item by ID."""
        with self._lock:
            return self._items.get(quarantine_id)

    def record_audit(
        self,
        *,
        action: AuditAction | str,
        actor: str,
        target: str,
        details: Mapping[str, Any] | None = None,
    ) -> ComplianceAuditEntry:
        """Appends an immutable audit entry to compliance_audit.jsonl."""
        audit_action = AuditAction(action) if isinstance(action, str) else action
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_details = dict(details or {})

        payload_bytes = f"{audit_id}:{now_iso}:{audit_action.value}:{actor}:{target}".encode(
            "utf-8"
        )
        fingerprint = hashlib.sha256(payload_bytes).hexdigest()[:16]

        entry = ComplianceAuditEntry(
            audit_id=audit_id,
            timestamp=now_iso,
            action=audit_action,
            actor=actor,
            target=target,
            details=clean_details,
            fingerprint=fingerprint,
        )

        with self._lock:
            with open(self._audit_ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        return entry

    def list_audit_entries(
        self,
        *,
        limit: int = 50,
        action: AuditAction | str | None = None,
    ) -> Sequence[ComplianceAuditEntry]:
        """Reads recent compliance audit events from the immutable ledger file."""
        target_action: AuditAction | None = None
        if isinstance(action, AuditAction):
            target_action = action
        elif isinstance(action, str):
            try:
                target_action = AuditAction(action)
            except ValueError:
                target_action = None

        entries: list[ComplianceAuditEntry] = []
        if not self._audit_ledger_file.exists():
            return entries

        with self._lock:
            try:
                with open(self._audit_ledger_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        raw = json.loads(line)
                        act = AuditAction(raw["action"])
                        if target_action and act != target_action:
                            continue
                        entries.append(
                            ComplianceAuditEntry(
                                audit_id=raw["audit_id"],
                                timestamp=raw["timestamp"],
                                action=act,
                                actor=raw["actor"],
                                target=raw["target"],
                                details=raw.get("details", {}),
                                fingerprint=raw.get("fingerprint", ""),
                            )
                        )
            except Exception:
                pass

        entries.reverse()
        return entries[:limit]

    def get_compliance_report(self) -> AuditReportSummary:
        """Generates an aggregated compliance audit summary report."""
        with self._lock:
            all_items = list(self._items.values())

        quarantined = sum(
            1 for i in all_items if i.status == QuarantineStatus.QUARANTINED
        )
        restored = sum(
            1 for i in all_items if i.status == QuarantineStatus.RESTORED
        )
        purged = sum(1 for i in all_items if i.status == QuarantineStatus.PURGED)

        actions_breakdown: dict[str, int] = {}
        for entry in self.list_audit_entries(limit=1000):
            actions_breakdown[entry.action.value] = (
                actions_breakdown.get(entry.action.value, 0) + 1
            )

        categories_breakdown: dict[str, int] = {}
        for item in all_items:
            categories_breakdown[item.category] = (
                categories_breakdown.get(item.category, 0) + 1
            )

        return AuditReportSummary(
            total_events=sum(actions_breakdown.values()),
            quarantined_count=quarantined + restored + purged,
            restored_count=restored,
            purged_count=purged,
            active_quarantine_count=quarantined,
            actions_breakdown=actions_breakdown,
            categories_breakdown=categories_breakdown,
        )
