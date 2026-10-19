# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""RNFV Pure Functional Planning Pipeline.

First Principles & Occam's Razor:
Zero Added Entity: Pure functional in-memory diffing pipeline.
RNFVSnapshot (R, N, F, V) -> ActionPlan (files, vectors, orphans).
No background daemons, no separate database tables, 100% idempotent.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("openviking.storage.transaction.rnfv_plan")


@dataclass(frozen=True)
class RequestIntent:
    """R: Normalized request intent."""
    action: str  # "write", "delete", "upsert", "patch"
    target_uri: str
    account_id: Optional[str] = None
    user_id: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FileEntry:
    """File representation for formal tree and new artifacts."""
    path: str
    md5: Optional[str] = None
    size: Optional[int] = None
    updated_at: Optional[float] = None


@dataclass(frozen=True)
class VectorEntry:
    """Vector representation for vector index snapshot and new vectors."""
    id: str
    uri: str
    md5: Optional[str] = None
    level: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RNFVSnapshot:
    """Validated immutable four-tuple snapshot across storage dimensions.

    R: Normalized request intent
    N: New artifact snapshot (parsed files from incoming content)
    F: Formal filesystem tree snapshot (currently persisted files)
    V: Vector index snapshot (currently persisted vectors)
    """
    intent: RequestIntent
    new_artifacts: List[FileEntry]
    formal_tree: List[FileEntry]
    vector_records: List[VectorEntry]
    new_vectors: List[VectorEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ActionPlan:
    """Deterministic, pure-memory diff output ready for atomic execution."""
    intent_action: str
    target_uri: str
    files_to_write: List[FileEntry]
    files_to_delete: List[str]
    vectors_to_upsert: List[VectorEntry]
    vectors_to_delete: List[str]
    orphans_detected: int = 0
    created_at: float = field(default_factory=time.time, compare=False)


def _matches_scope(path_or_uri: str, target: str) -> bool:
    """Return True if path_or_uri is target or a sub-resource/sidecar under target."""
    if path_or_uri == target:
        return True
    if path_or_uri.startswith(f"{target}/"):
        return True
    if path_or_uri.startswith(f"{target}."):
        return True
    return False


def plan_rnfv_actions(snapshot: RNFVSnapshot) -> ActionPlan:
    """Pure functional computation transforming RNFVSnapshot into ActionPlan.

    Complexity: O(|N| + |F| + |V|), zero I/O, completely deterministic.
    """
    intent = snapshot.intent
    target_uri = intent.target_uri
    action = intent.action.lower()

    if action == "delete":
        # Delete intent cascades: delete all matching formal files and vectors
        files_del: List[str] = [
            f.path for f in snapshot.formal_tree
            if _matches_scope(f.path, target_uri)
        ]
        vectors_del: List[str] = [
            v.id for v in snapshot.vector_records
            if _matches_scope(v.uri, target_uri)
        ]
        return ActionPlan(
            intent_action=action,
            target_uri=target_uri,
            files_to_write=[],
            files_to_delete=files_del,
            vectors_to_upsert=[],
            vectors_to_delete=vectors_del,
            orphans_detected=0,
        )

    # Write / Upsert / Patch: calculate file updates and detect vector orphans
    files_to_write: List[FileEntry] = list(snapshot.new_artifacts)
    vectors_to_upsert: List[VectorEntry] = list(snapshot.new_vectors)

    # Compute orphaned vectors: existing vectors under target_uri scope not present in new_vectors
    new_vector_ids: Set[str] = {v.id for v in snapshot.new_vectors}
    orphans: List[str] = []

    for existing_v in snapshot.vector_records:
        if _matches_scope(existing_v.uri, target_uri):
            if existing_v.id not in new_vector_ids:
                orphans.append(existing_v.id)

    return ActionPlan(
        intent_action=action,
        target_uri=target_uri,
        files_to_write=files_to_write,
        files_to_delete=[],
        vectors_to_upsert=vectors_to_upsert,
        vectors_to_delete=orphans,
        orphans_detected=len(orphans),
    )


def build_dlq_payload_from_error(
    intent: RequestIntent,
    error: BaseException,
    queue_name: str = "resource_transaction_dlq",
    retry_count: int = 0,
) -> Dict[str, Any]:
    """Helper formatting an unrecoverable planning or commit error into DLQManager DTO.

    Zero Added Entity: Directly integrates with existing QueueFS DLQManager.
    """
    import traceback

    return {
        "queue_name": queue_name,
        "msg_id": f"tx_err_{int(time.time() * 1000)}",
        "uri": intent.target_uri,
        "account_id": intent.account_id,
        "payload": {
            "action": intent.action,
            "target_uri": intent.target_uri,
            "meta": intent.meta,
        },
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "stack_trace": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        "retry_count": retry_count,
        "resolved": 0,
    }
