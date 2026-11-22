# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Request schemas and validation helpers for search router."""

from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openviking.retrieve.context_assembler import (
    CATEGORY_KEYS,
    DEFAULT_LIMIT,
    DEFAULT_MAX_TOKENS,
    MAX_EXCLUDE_URIS,
    REPORTED_CATEGORY_KEYS,
    DetailRequest,
)
from openviking.retrieve.context_assembler.recall_preset import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_SCORE,
)
from openviking.telemetry import TelemetryRequest
from openviking.utils.time_decay import validate_event_time_decay_request

TimeField = Literal["updated_at", "created_at"]


def _reject_unknown_categories(value: Any, label: str, allowed: Sequence[str]) -> None:
    if not isinstance(value, dict):
        return
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise ValueError(
            f"unknown {label} keys: {', '.join(unknown)}; allowed: {', '.join(allowed)}"
        )


def _reject_unknown_quota_and_detail(quotas: Any, detail: Any) -> None:
    _reject_unknown_categories(quotas, "quota", CATEGORY_KEYS)
    _reject_unknown_categories(detail, "detail", REPORTED_CATEGORY_KEYS)


CONTEXT_ONLY_FIELDS = (
    "query_expansion",
    "max_tokens",
    "quotas",
    "purpose",
    "detail",
    "dedup_turns",
    "exclude_uris",
    "peer_scope",
    "other_peer_penalty",
    "rewrite",
    "rewrite_max_bullets",
    "evidence_hops",
    "dpp_diversity",
)


def context_only_fields_error(supplied_fields, as_named_by_caller=None) -> Optional[str]:
    """Refusal for context-only arguments in list mode, shared across HTTP and MCP."""
    used = sorted(set(CONTEXT_ONLY_FIELDS) & set(supplied_fields))
    if not used:
        return None
    names = sorted(
        {name for field in used for name in ((as_named_by_caller or {}).get(field) or {field})}
    )
    return f"{', '.join(names)} require mode='context'; set mode='context' or drop these fields"


class FindRequest(BaseModel):
    """Request model for find."""

    model_config = ConfigDict(extra="forbid")

    query: str = ""
    image_url: str | list[str] | None = None
    target_uri: Union[str, List[str]] = ""
    context_type: Optional[Union[str, List[str]]] = None
    limit: int = Field(default=DEFAULT_LIMIT, ge=1)
    node_limit: Optional[int] = Field(default=None, ge=1)
    score_threshold: Optional[float] = None
    filter: Optional[Dict[str, Any]] = None
    include_provenance: bool = False
    tags: Optional[List[str]] = None
    since: Optional[str] = None
    until: Optional[str] = None
    time_field: Optional[TimeField] = None
    level: Optional[Union[int, str, List[int]]] = None
    read_content: bool = False
    telemetry: TelemetryRequest = False
    mode: Optional[str] = None
    events_time_decay_protection: Optional[str] = None

    @model_validator(mode="after")
    def _validate_time_decay(self) -> "FindRequest":
        validate_event_time_decay_request(self.events_time_decay_protection)
        if self.events_time_decay_protection is not None:
            if not self.query.strip() and not self.image_url:
                raise ValueError("events_time_decay_protection requires a semantic query or image")
        return self


class SearchRequest(BaseModel):
    """Request model for search with session."""

    model_config = ConfigDict(extra="forbid")

    query: str = ""
    image_url: str | list[str] | None = None
    target_uri: Union[str, List[str]] = ""
    context_type: Optional[Union[str, List[str]]] = None
    session_id: Optional[str] = None
    limit: int = Field(default=DEFAULT_LIMIT, ge=1)
    node_limit: Optional[int] = Field(default=None, ge=1)
    score_threshold: Optional[float] = None
    filter: Optional[Dict[str, Any]] = None
    include_provenance: bool = False
    tags: Optional[List[str]] = None

    since: Optional[str] = None
    until: Optional[str] = None
    time_field: Optional[TimeField] = None
    level: Optional[Union[int, str, List[int]]] = None
    read_content: bool = False
    telemetry: TelemetryRequest = False
    events_time_decay_protection: Optional[str] = None

    mode: Literal["list", "context"] = "list"

    query_expansion: Literal["off", "auto"] = "auto"
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=64, le=32000)
    quotas: Optional[Dict[str, int]] = None
    purpose: Optional[Literal["chat", "coding"]] = None
    detail: Optional[DetailRequest] = None
    dedup_turns: int = Field(default=0, ge=0, le=100)
    exclude_uris: List[str] = Field(default_factory=list, max_length=MAX_EXCLUDE_URIS)
    peer_scope: Literal["actor", "all"] = "all"
    other_peer_penalty: Optional[Union[float, Dict[str, float]]] = None
    rewrite: Union[bool, Literal["auto"]] = False
    rewrite_max_bullets: int = Field(default=6, ge=1, le=20)
    evidence_hops: int = Field(default=0, ge=0, le=2)
    dpp_diversity: bool = False

    @model_validator(mode="after")
    def _validate_mode(self) -> "SearchRequest":
        validate_event_time_decay_request(self.events_time_decay_protection)
        if self.mode == "list":
            error = context_only_fields_error(self.model_fields_set)
            if error:
                raise ValueError(error)
            return self

        if self.read_content:
            raise ValueError("read_content is only supported in mode='list'")
        if self.target_uri:
            raise ValueError("target_uri is not supported in mode='context'")
        _reject_unknown_quota_and_detail(self.quotas, self.detail)
        return self


class GrepRequest(BaseModel):
    """Request model for grep."""

    uri: str
    exclude_uri: Optional[str] = None
    pattern: str
    case_insensitive: bool = False
    node_limit: Optional[int] = 256
    level_limit: int = 10
    tags: Optional[List[str]] = None
    include_tags: bool = False
    before_context: int = Field(default=0, ge=0)
    after_context: int = Field(default=0, ge=0)


class GlobRequest(BaseModel):
    """Request model for glob."""

    pattern: str
    uri: str = "viking://"
    node_limit: Optional[int] = 256
    extra_fields: Optional[list[str]] = None
    tags: Optional[List[str]] = None
    include_tags: bool = False
