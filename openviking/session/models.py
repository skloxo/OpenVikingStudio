# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Session data models, DTOs, and protocol specifications.

Extracts core session metadata, compression statistics, archive states,
and Working Memory v2 tool/schema definitions into a clean domain seam.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from openviking.core.peer_id import safe_peer_id
from openviking.message import Message
from openviking.server.identity import RequestContext
from openviking.session.memory_policy import MemoryPolicy
from openviking.utils import get_current_timestamp


class _ArchiveMessagesCorruptError(ValueError):
    """Raised when an archive messages file cannot be deserialized."""


@dataclass(frozen=True)
class _MemoryExtractionScope:
    allow_self_memory: bool
    peer_memory_enabled: bool
    allowed_peer_ids: set[str]
    include_session_skills: bool
    memory_types: Optional[set[str]]


def _default_memory_counts() -> Dict[str, int]:
    return {"total": 0}


def _message_peer_ids(messages: List[Message]) -> set[str]:
    return {
        peer_id
        for message in messages
        if (peer_id := safe_peer_id(getattr(message, "peer_id", None)))
    }


def _resolve_memory_extraction_scope(
    ctx: RequestContext,
    policy: MemoryPolicy,
    messages: List[Message],
    *,
    config_session_skill_extraction_enabled: bool,
) -> _MemoryExtractionScope:
    allow_self_memory = policy.self_enabled
    allowed_peer_ids = _message_peer_ids(messages) if policy.peer_enabled else set()

    return _MemoryExtractionScope(
        allow_self_memory=allow_self_memory,
        peer_memory_enabled=policy.peer_enabled,
        allowed_peer_ids=allowed_peer_ids,
        include_session_skills=config_session_skill_extraction_enabled and allow_self_memory,
        memory_types=policy.memory_types,
    )


def _resolve_event_search_tags(
    commit_tags: Optional[List[str]],
    session_default_tags: Optional[List[str]],
) -> List[str]:
    """Resolve the event tags for a commit against the session default."""
    from openviking.utils.tags import normalize_search_tags

    chosen = commit_tags if commit_tags is not None else session_default_tags
    return normalize_search_tags(chosen)


# =====================================================================
# Working Memory v2 Tool Schemas & Section Names
# =====================================================================

WM_SEVEN_SECTIONS: List[str] = [
    "Session Title",
    "Current State",
    "Task & Goals",
    "Key Facts & Decisions",
    "Files & Context",
    "Errors & Corrections",
    "Open Issues",
]

_WM_SECTION_OP_SCHEMA: Dict[str, Any] = {
    "oneOf": [
        {
            "type": "object",
            "required": ["op"],
            "additionalProperties": False,
            "properties": {"op": {"type": "string", "enum": ["KEEP"]}},
        },
        {
            "type": "object",
            "required": ["op", "content"],
            "additionalProperties": False,
            "properties": {
                "op": {"type": "string", "enum": ["UPDATE"]},
                "content": {
                    "type": "string",
                    "description": (
                        "FULL replacement content for this section, markdown, "
                        "WITHOUT the '## <section>' header line."
                    ),
                },
            },
        },
        {
            "type": "object",
            "required": ["op", "items"],
            "additionalProperties": False,
            "properties": {
                "op": {"type": "string", "enum": ["APPEND"]},
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "New bullet-style items to append under the existing "
                        "section body. Omit heading / bullet markers; the "
                        "server renders each item as '- <item>'."
                    ),
                },
            },
        },
    ]
}

WM_UPDATE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "update_working_memory",
        "description": (
            "Emit a per-section decision (KEEP / UPDATE / APPEND) for the "
            "7-section Working Memory document."
        ),
        "parameters": {
            "type": "object",
            "required": ["sections"],
            "additionalProperties": False,
            "properties": {
                "sections": {
                    "type": "object",
                    "required": list(WM_SEVEN_SECTIONS),
                    "additionalProperties": False,
                    "properties": dict.fromkeys(WM_SEVEN_SECTIONS, _WM_SECTION_OP_SCHEMA),
                },
                "checkpoint_summaries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "When checkpoint sources are present, one bounded cumulative "
                        "continuation summary per checkpoint_source index, in ascending "
                        "index order."
                    ),
                },
            },
        },
    },
}

WM_CREATE_WITH_CHECKPOINTS_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_working_memory",
        "description": (
            "Create the complete Working Memory and the requested checkpoint summaries "
            "from the same model pass."
        ),
        "parameters": {
            "type": "object",
            "required": ["working_memory", "checkpoint_summaries"],
            "additionalProperties": False,
            "properties": {
                "working_memory": {
                    "type": "string",
                    "description": "Complete 7-section Working Memory markdown.",
                },
                "checkpoint_summaries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One bounded cumulative continuation summary per checkpoint_source "
                        "index, in ascending index order."
                    ),
                },
            },
        },
    },
}


@dataclass(frozen=True)
class _CheckpointRequest:
    """Server-owned mapping for one checkpoint summary requested from Phase 2."""

    turn_anchor_message_id: str
    source_message_ids: tuple[str, ...]
    retained_message_token_budget: int
    estimated_active_tokens: int
    previous_checkpoint_abstract: str = ""
    previous_checkpoint_source_message_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CheckpointSnapshot:
    """Effective completed checkpoint state for one retained User Turn."""

    turn_anchor_message_id: str
    source_message_ids: tuple[str, ...]
    abstract: str
    archive_id: str
    archive_uri: str


@dataclass(frozen=True)
class _ArchiveSummaryResult:
    """The two products emitted by the existing Working-Memory model call."""

    overview: str
    checkpoint_summaries: tuple[str, ...] = ()


@dataclass
class SessionCompression:
    """Session compression information."""

    summary: str = ""
    original_count: int = 0
    compressed_count: int = 0
    compression_index: int = 0


@dataclass
class SessionStats:
    """Session statistics information."""

    total_turns: int = 0
    total_tokens: int = 0
    compression_count: int = 0
    contexts_used: int = 0
    skills_used: int = 0
    memories_extracted: int = 0


@dataclass
class ArchiveState:
    """Filesystem-derived state for one archive directory."""

    archive_id: str
    archive_uri: str
    index: int
    state: Literal["pending", "completed", "failed"]
    overview: str = ""
    done: Dict[str, Any] = field(default_factory=dict)
    failed: Dict[str, Any] = field(default_factory=dict)

    @property
    def coverage_start_index(self) -> int:
        raw = self.done.get("coverage_start_archive")
        if isinstance(raw, str):
            match = re.fullmatch(r"archive_(\d+)", raw)
            if match:
                return int(match.group(1))
        return self.index

    @property
    def coverage_end_index(self) -> int:
        raw = self.done.get("coverage_end_archive")
        if isinstance(raw, str):
            match = re.fullmatch(r"archive_(\d+)", raw)
            if match:
                return int(match.group(1))
        return self.index


@dataclass
class SessionMeta:
    """Session metadata persisted in .meta.json."""

    session_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    created_by_account_id: str = ""
    created_by_user_id: str = ""
    message_count: int = 0
    total_message_count: Optional[int] = 0
    commit_count: int = 0
    memories_extracted: Dict[str, int] = field(default_factory=_default_memory_counts)
    last_commit_at: str = ""
    llm_token_usage: Dict[str, int] = field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
        }
    )
    embedding_token_usage: Dict[str, int] = field(
        default_factory=lambda: {
            "total_tokens": 0,
        }
    )
    pending_tokens: int = 0
    keep_recent_count: int = 0
    retention_mode: str = ""
    keep_recent_turn_count: int = 0
    retained_message_token_budget: int = 0
    min_raw_tail_steps: int = 1
    memory_policy: Optional[Dict[str, Any]] = None
    auto_commit_policy: Optional[Dict[str, Any]] = None
    last_message_at: str = ""
    last_auto_commit_at: str = ""
    event_search_tags: Optional[List[str]] = None
    category: str = "interactive"
    is_heartbeat: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by_account_id": self.created_by_account_id,
            "created_by_user_id": self.created_by_user_id,
            "message_count": self.message_count,
            "commit_count": self.commit_count,
            "memories_extracted": dict(self.memories_extracted),
            "last_commit_at": self.last_commit_at,
            "llm_token_usage": dict(self.llm_token_usage),
            "embedding_token_usage": dict(self.embedding_token_usage),
            "pending_tokens": self.pending_tokens,
            "keep_recent_count": self.keep_recent_count,
            "retention_mode": self.retention_mode,
            "keep_recent_turn_count": self.keep_recent_turn_count,
            "retained_message_token_budget": self.retained_message_token_budget,
            "min_raw_tail_steps": self.min_raw_tail_steps,
            "memory_policy": dict(self.memory_policy) if self.memory_policy is not None else None,
            "auto_commit_policy": (
                dict(self.auto_commit_policy) if self.auto_commit_policy is not None else None
            ),
            "last_message_at": self.last_message_at,
            "last_auto_commit_at": self.last_auto_commit_at,
            "category": self.category,
            "is_heartbeat": self.is_heartbeat,
        }
        if self.total_message_count is not None:
            data["total_message_count"] = self.total_message_count
        if self.event_search_tags is not None:
            data["event_search_tags"] = list(self.event_search_tags)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMeta":
        llm_token_usage = data.get("llm_token_usage", {})
        embedding_token_usage = data.get("embedding_token_usage", {})
        memories = data.get("memories_extracted", {})

        memory_counts = _default_memory_counts()
        for key, value in memories.items():
            try:
                memory_counts[key] = int(value or 0)
            except (TypeError, ValueError):
                memory_counts[key] = 0

        return cls(
            session_id=data.get("session_id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            created_by_account_id=data.get("created_by_account_id", "")
            or data.get("account_id", ""),
            created_by_user_id=data.get("created_by_user_id", ""),
            message_count=data.get("message_count", 0),
            total_message_count=data.get("total_message_count"),
            commit_count=data.get("commit_count", 0),
            memories_extracted=memory_counts,
            last_commit_at=data.get("last_commit_at", ""),
            llm_token_usage={
                "prompt_tokens": llm_token_usage.get("prompt_tokens", 0),
                "completion_tokens": llm_token_usage.get("completion_tokens", 0),
                "total_tokens": llm_token_usage.get("total_tokens", 0),
                "cached_tokens": llm_token_usage.get("cached_tokens", 0),
                "reasoning_tokens": llm_token_usage.get("reasoning_tokens", 0),
            },
            embedding_token_usage={
                "total_tokens": embedding_token_usage.get("total_tokens", 0),
            },
            pending_tokens=max(0, int(data.get("pending_tokens", 0) or 0)),
            keep_recent_count=max(0, int(data.get("keep_recent_count", 0) or 0)),
            retention_mode=str(data.get("retention_mode", "") or ""),
            keep_recent_turn_count=max(0, int(data.get("keep_recent_turn_count", 0) or 0)),
            retained_message_token_budget=max(
                0, int(data.get("retained_message_token_budget", 0) or 0)
            ),
            min_raw_tail_steps=max(0, int(data.get("min_raw_tail_steps", 1) or 0)),
            memory_policy=data.get("memory_policy"),
            auto_commit_policy=data.get("auto_commit_policy"),
            last_message_at=data.get("last_message_at", ""),
            last_auto_commit_at=data.get("last_auto_commit_at", ""),
            event_search_tags=data.get("event_search_tags"),
            category=data.get("category", "interactive"),
            is_heartbeat=bool(data.get("is_heartbeat", False)),
        )


@dataclass
class Usage:
    """Usage record."""

    uri: str
    type: str  # "context" | "skill"
    contribution: float = 0.0
    input: str = ""
    output: str = ""
    success: bool = True
    timestamp: str = field(default_factory=get_current_timestamp)
