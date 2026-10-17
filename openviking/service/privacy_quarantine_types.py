"""Strongly-typed DTOs for Privacy Compliance Audit & Quarantine Engine (SSOT).

Defines immutable records, enum states, and report data transfer objects
for quarantine isolation, data purging, and audit logging.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class QuarantineStatus(str, Enum):
    """Lifecycle status of an isolated quarantined item."""

    QUARANTINED = "QUARANTINED"
    RESTORED = "RESTORED"
    PURGED = "PURGED"


class AuditAction(str, Enum):
    """Operation action recorded in the compliance audit ledger."""

    MASK = "MASK"
    SCAN = "SCAN"
    QUARANTINE = "QUARANTINE"
    RESTORE = "RESTORE"
    PURGE = "PURGE"


@dataclass(frozen=True)
class QuarantineItem:
    """Strongly-typed immutable record of a quarantined asset."""

    quarantine_id: str
    target_uri: str
    category: str
    reason: str
    actor: str
    content_sha256: str
    created_at: str
    status: QuarantineStatus = QuarantineStatus.QUARANTINED
    metadata: Mapping[str, Any] = field(default_factory=dict)
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes the quarantine item into a JSON-friendly dict."""
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class ComplianceAuditEntry:
    """Immutable entry recorded in the compliance audit ledger (compliance_audit.jsonl)."""

    audit_id: str
    timestamp: str
    action: AuditAction
    actor: str
    target: str
    details: Mapping[str, Any]
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        """Serializes the audit entry into a JSON-friendly dict."""
        data = asdict(self)
        data["action"] = self.action.value
        return data


@dataclass(frozen=True)
class AuditReportSummary:
    """Aggregated compliance audit summary report."""

    total_events: int
    quarantined_count: int
    restored_count: int
    purged_count: int
    active_quarantine_count: int
    actions_breakdown: Mapping[str, int]
    categories_breakdown: Mapping[str, int]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializes the report summary into a JSON-friendly dict."""
        return asdict(self)
