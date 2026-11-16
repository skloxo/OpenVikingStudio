# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Pydantic request schemas for sessions router."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator

from openviking.core.peer_id import normalize_peer_id
from openviking.session.auto_commit_policy import validate_idle_timeout_input
from openviking.telemetry import TelemetryRequest


class TextPartRequest(BaseModel):
    """Text part request model."""

    type: Literal["text"] = "text"
    text: str


class ContextPartRequest(BaseModel):
    """Context part request model."""

    type: Literal["context"] = "context"
    uri: str = ""
    context_type: Literal["memory", "resource", "skill"] = "memory"
    abstract: str = ""


class ToolPartRequest(BaseModel):
    """Tool part request model."""

    type: Literal["tool"] = "tool"
    tool_id: str = ""
    tool_name: str = ""
    tool_uri: str = ""
    skill_uri: str = ""
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: str = ""
    tool_status: str = "pending"
    duration_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    tool_output_ref: str = ""
    tool_output_truncated: bool = False
    tool_output_original_chars: Optional[int] = None
    tool_output_preview_chars: Optional[int] = None
    tool_output_sha256: str = ""
    tool_output_storage_uri: str = ""
    tool_output_mime_type: str = "text/plain"
    tool_output_source_ref: str = ""
    tool_output_source_offset: Optional[int] = None
    tool_output_source_limit: Optional[int] = None
    tool_output_externalization_error: str = ""
    tool_output_group_id: str = ""
    tool_output_externalized_reason: str = ""
    tool_output_group_original_chars: Optional[int] = None
    tool_output_group_budget_chars: Optional[int] = None


PartRequest = TextPartRequest | ContextPartRequest | ToolPartRequest


class AutoCommitPolicyRequest(BaseModel):
    """Session-level auto-commit policy overrides."""

    pending_token_threshold: Optional[int] = None
    message_count_threshold: Optional[int] = None
    idle_timeout_seconds: Optional[int] = None
    keep_recent_count: Optional[int] = None
    min_commit_interval_seconds: Optional[int] = None

    model_config = {"extra": "forbid"}

    @field_validator("idle_timeout_seconds")
    @classmethod
    def validate_idle_timeout_seconds(cls, value: Optional[int]) -> Optional[int]:
        return None if value is None else validate_idle_timeout_input(value)

    @model_validator(mode="after")
    def reject_explicit_null_fields(self) -> "AutoCommitPolicyRequest":
        null_fields = [field for field in self.model_fields_set if getattr(self, field) is None]
        if null_fields:
            raise ValueError(
                "auto_commit_policy fields must be integers; use "
                "auto_commit_policy=null to disable automatic commits"
            )
        return self


class EventExtractionConfigRequest(BaseModel):
    """Default event-memory extraction settings for a session."""

    tags: Optional[List[str]] = Field(
        default=None,
        description=(
            "Default custom scalar tags applied to event memories extracted from "
            "this session. Each element is a strict 'key=value' string. Commit-time "
            "tags override this default; an empty list clears it."
        ),
    )

    model_config = {"extra": "forbid"}


class MemoryExtractionConfigRequest(BaseModel):
    """Per-memory-type extraction configuration."""

    events: Optional[EventExtractionConfigRequest] = None

    model_config = {"extra": "forbid"}


class AddMessageRequest(BaseModel):
    """Request model for adding a message."""

    role: str
    peer_id: Optional[str] = None
    content: Optional[str] = None
    parts: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None
    turn_id: Optional[str] = None
    message_kind: Optional[
        Literal["user_query", "assistant_step", "tool_transport", "checkpoint"]
    ] = None
    source_message_ids: Optional[List[str]] = None
    telemetry: TelemetryRequest = False

    @field_validator("peer_id")
    @classmethod
    def validate_peer_id(cls, value: Optional[str]) -> Optional[str]:
        return normalize_peer_id(value)

    @model_validator(mode="after")
    def validate_content_or_parts(self) -> "AddMessageRequest":
        if self.content is None and self.parts is None:
            raise ValueError("Either 'content' or 'parts' must be provided")
        return self


class BatchAddMessageRequest(BaseModel):
    """Request model for adding multiple messages in a single request."""

    messages: List[AddMessageRequest] = Field(..., max_length=100)
    telemetry: TelemetryRequest = False


class UsedRequest(BaseModel):
    """Request model for recording usage."""

    contexts: Optional[List[str]] = None
    skill: Optional[Dict[str, Any]] = None


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    session_id: Optional[str] = None
    memory_policy: Optional[Dict[str, Any]] = None
    auto_commit_policy: Optional[AutoCommitPolicyRequest] = None
    memory_extraction_config: Optional[MemoryExtractionConfigRequest] = None
    telemetry: TelemetryRequest = False


class UpdateSessionConfigRequest(BaseModel):
    """Request body for PATCH /sessions/{id}/config."""

    memory_extraction_config: Optional[MemoryExtractionConfigRequest] = None
    auto_commit_policy: Optional[AutoCommitPolicyRequest] = None
    telemetry: TelemetryRequest = False

    model_config = {"extra": "forbid"}


class EventExtractionMetadataRequest(BaseModel):
    """Commit-time event-memory tag override."""

    tags: Optional[List[str]] = Field(
        default=None,
        description=(
            "Custom scalar tags applied to event memories from this commit. Each "
            "element is a strict 'key=value' string. Overrides the session default; "
            "an empty list disables default-tag injection for this commit."
        ),
    )

    model_config = {"extra": "forbid"}


class ExtractionMetadataRequest(BaseModel):
    """Per-memory-type extraction overrides for a single commit."""

    event: Optional[EventExtractionMetadataRequest] = None

    model_config = {"extra": "forbid"}


class CommitRequest(BaseModel):
    """Commit request body."""

    enable_working_memory: Optional[StrictBool] = Field(
        default=None,
        description="Override only Working Memory generation for this commit; null inherits policy.",
    )
    keep_recent_count: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description=(
            "Number of most-recent messages to keep live after commit. "
            "compact path passes 0 to archive everything."
        ),
    )
    retention_mode: Optional[Literal["turn_budget"]] = Field(
        default=None,
        description="Opt in to logical Turn retention. Omit to preserve keep_recent_count semantics.",
    )
    keep_recent_turn_count: Optional[int] = Field(
        default=None,
        ge=0,
        le=10_000,
        description="Maximum number of newest logical user Turns to retain.",
    )
    retained_message_token_budget: Optional[int] = Field(
        default=None,
        ge=1,
        description="Token budget for retained raw messages and checkpoint.",
    )
    min_raw_tail_steps: Optional[int] = Field(
        default=None,
        ge=0,
        le=10_000,
        description="Minimum number of latest atomic assistant Steps kept raw.",
    )
    session_window_context: Optional[int] = Field(
        default=None,
        ge=1,
        description="Caller context window tokens used to size Working Memory summary budgets.",
    )
    summary_token_ratio: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Fraction of session_window_context allowed for Working Memory summary output.",
    )
    retained_token_ratio: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Fraction of session_window_context used as default retained token budget.",
    )
    reasoning_effort: Optional[str] = Field(
        default=None,
        description="Optional reasoning effort override forwarded to Working Memory VLM calls.",
    )
    extraction_metadata: Optional[ExtractionMetadataRequest] = Field(
        default=None,
        description="Per-commit memory extraction overrides.",
    )
    telemetry: TelemetryRequest = False

    @model_validator(mode="after")
    def validate_turn_retention_opt_in(self) -> "CommitRequest":
        if self.retention_mode is None and any(
            value is not None
            for value in (
                self.keep_recent_turn_count,
                self.retained_message_token_budget,
                self.min_raw_tail_steps,
                self.retained_token_ratio,
            )
        ):
            raise ValueError(
                "retention_mode='turn_budget' is required when Turn retention fields are set"
            )
        return self
