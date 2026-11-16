# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Rule compilation and retrieval backed by Markdown in VikingFS."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from openviking.core.namespace import classify_uri
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.models.vlm.llm import parse_json_from_response
from openviking.parse.parsers.media.constants import MEDIA_EXTENSIONS
from openviking.server.identity import RequestContext
from openviking.server.resource_ingest import (
    AddResourceRequest,
    ingest_resource_request,
)
from openviking.service.fs_service import FSService
from openviking.service.resource_service import ResourceService
from openviking.service.rule_jev import (
    RuleJevClient,
    RuleJevInput,
    ScenarioJevClient,
)
from openviking.service.search_service import SearchService
from openviking.service.task_domain import TaskPatch
from openviking.service.task_tracker import TaskRecord, TaskStatus, get_task_tracker
from openviking.service.task_work_index import bind_task_context, detach_task_context
from openviking.session.memory.utils.memory_fields import strip_memory_fields_trailer
from openviking.utils.time_utils import get_current_timestamp, parse_iso_datetime
from openviking.utils.token_estimation import estimate_text_tokens
from openviking_cli.exceptions import (
    InvalidArgumentError,
    NotFoundError,
    ProcessingError,
    UnavailableError,
    VLMFailedError,
)
from openviking_cli.utils import get_logger

logger = get_logger(__name__)


def _rs_dep(name: str, fallback: Any) -> Any:
    """Resolve symbols monkeypatched on openviking.service.rule_service first."""
    mod = sys.modules.get("openviking.service.rule_service")
    return getattr(mod, name, fallback) if mod is not None else fallback

RULE_SCHEMA = "openviking.rule/v1"
SCENARIO_SCHEMA = "openviking.rule.scenario/v1"
RULE_OPERATIONS = frozenset(
    {
        "NOOP",
        "UPDATE",
        "REPLACE",
        "NEW",
        "UNCERTAIN",
        "REJECT",
        "PAUSE",
        "ARCHIVE",
        "RESTORE",
    }
)
MAX_SOURCE_CHARS = 128_000
MAX_SOURCE_FILES = 128
MAX_SCENARIO_CHARS_FOR_JUDGE = 16_000
MAX_SCENARIOS_PER_MATCHER_BATCH = 20
DEFAULT_COMPILER_CONTEXT_WINDOW = 16_384
DEFAULT_COMPILER_OUTPUT_TOKENS = 4_096
MIN_COMPILER_CONTEXT_WINDOW = 2_048
MIN_COMPILE_BATCH_TOKENS = 256
DEFAULT_RULE_SCENARIO_LIMIT = 5
DEFAULT_RULE_SCENARIO_SCORE_THRESHOLD = 0.1
DEFAULT_RULE_PROBABILITY_THRESHOLD = 0.65
DEFAULT_ARCHIVED_RETENTION_DAYS = 30
MAX_COMPILE_REPAIR_ATTEMPTS = 2
COMPILER_RULE_STATUSES = frozenset({"active", "paused"})


def _media_extension(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    path = unquote(parsed.path or value).lower().rstrip("/")
    return next((extension for extension in MEDIA_EXTENSIONS if path.endswith(extension)), None)


def _validate_text_source(source: AddResourceRequest) -> None:
    for value in (source.source_name, source.path, source.temp_file_id):
        extension = _media_extension(value)
        if extension:
            raise InvalidArgumentError(
                "rules/compile only supports text sources that can be parsed into readable "
                f"text; multimodal {extension} sources are not supported"
            )


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parse_iso_datetime(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _slug(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return (normalized[:64].rstrip("-") or fallback).strip("-")


def _rules_root(ctx: RequestContext) -> str:
    return f"viking://user/{ctx.user.user_id}/memories/rules"


def _parse_markdown(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---\n"):
        raise ValueError("rule Markdown is missing YAML frontmatter")
    closing = content.find("\n---\n", 4)
    if closing < 0:
        raise ValueError("rule Markdown has unclosed YAML frontmatter")
    loaded = yaml.safe_load(content[4:closing]) or {}
    if not isinstance(loaded, dict):
        raise ValueError("rule Markdown frontmatter must be an object")
    return loaded, content[closing + 5 :].strip()


def _render_markdown(metadata: dict[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    return f"---\n{frontmatter}\n---\n\n{body.strip()}\n"


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


def _vlm_setting(vlm: Any, name: str) -> Any:
    value = getattr(vlm, name, None)
    if value is not None:
        return value
    config = getattr(vlm, "config", None)
    return config.get(name) if isinstance(config, dict) else None


def _take_text_prefix(text: str, max_tokens: int) -> tuple[str, str]:
    """Take a budgeted prefix, preferring paragraph, line, or sentence boundaries."""
    if not text or estimate_text_tokens(text) <= max_tokens:
        return text, ""
    if max_tokens <= 0:
        return "", text

    low = 1
    high = len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if estimate_text_tokens(text[:mid]) <= max_tokens:
            low = mid
        else:
            high = mid - 1
    hard_end = low
    minimum_end = hard_end // 2
    preferred_end = -1
    for separator in ("\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "; "):
        position = text.rfind(separator, minimum_end, hard_end)
        if position >= 0:
            preferred_end = max(preferred_end, position + len(separator))
    end = preferred_end if preferred_end > 0 else hard_end
    return text[:end], text[end:]


def _build_material_batches(
    instruction: str,
    source_text: str,
    *,
    max_tokens: int,
) -> list[tuple[str, str]]:
    if instruction and source_text:
        # Instructions can restrict the authorized source scope, so every source batch needs it.
        source_budget = max_tokens - estimate_text_tokens(instruction)
        if source_budget <= 0:
            raise InvalidArgumentError(
                "rule compiler instruction leaves no room for source material"
            )
        batches: list[tuple[str, str]] = []
        remaining_source = source_text
        while remaining_source:
            chunk, remaining_source = _take_text_prefix(remaining_source, source_budget)
            if not chunk:
                raise InvalidArgumentError("rule compiler input budget is too small")
            batches.append((instruction, chunk))
        return batches

    pending = [
        [kind, text]
        for kind, text in (("instruction", instruction), ("source", source_text))
        if text
    ]
    batches: list[tuple[str, str]] = []
    while pending:
        remaining = max_tokens
        parts = {"instruction": [], "source": []}
        while pending and remaining > 0:
            kind, text = pending[0]
            chunk, rest = _take_text_prefix(text, remaining)
            if not chunk:
                break
            parts[kind].append(chunk)
            remaining -= estimate_text_tokens(chunk)
            if rest:
                pending[0][1] = rest
                break
            pending.pop(0)
        if not parts["instruction"] and not parts["source"]:
            raise InvalidArgumentError("rule compiler input budget is too small")
        batches.append(("".join(parts["instruction"]), "".join(parts["source"])))
    return batches


class RuleResourceReference(BaseModel):
    """Reference a resource that has already been ingested."""

    model_config = ConfigDict(extra="forbid")

    resource_uri: str = Field(min_length=1)

    @model_validator(mode="after")
    def _normalize_uri(self) -> "RuleResourceReference":
        self.resource_uri = self.resource_uri.strip()
        if not self.resource_uri:
            raise ValueError("resource_uri must not be empty")
        return self


RuleSource = RuleResourceReference | AddResourceRequest


class RuleCompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str | None = Field(default=None, max_length=64_000)
    sources: list[RuleSource] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def _has_input(self) -> "RuleCompileRequest":
        self.instruction = self.instruction.strip() if self.instruction else None
        if not self.instruction and not self.sources:
            raise ValueError("instruction or sources is required")
        return self


class RuleSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_context: str = Field(min_length=1, max_length=64_000)
    rule_probability_threshold: float = Field(
        default=DEFAULT_RULE_PROBABILITY_THRESHOLD, ge=0, le=1
    )

    @model_validator(mode="after")
    def _normalize_context(self) -> "RuleSearchRequest":
        self.task_context = self.task_context.strip()
        if not self.task_context:
            raise ValueError("task_context must not be empty")
        return self


class RuleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2_000)
    confidence: Literal["user", "high", "medium", "low"] = "user"
    content: str = Field(min_length=1, max_length=16_000)
    applies_when: str = Field(default="", max_length=4_000)
    exception: str = Field(default="", max_length=4_000)
    body: str = Field(default="", max_length=32_000)

    @field_validator("applies_when")
    @classmethod
    def validate_applies_when(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.casefold() in {"none", "(none)", "[]", "[ ]"}:
            raise ValueError("applies_when must define a concrete applicability condition")
        return normalized


class RuleScenarioRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2_000)


class RuleDroppedRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str = Field(min_length=1, max_length=2_000)
    user_quote: str = Field(min_length=1, max_length=2_000)


class RuleCarriedOver(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing_requirements: list[str] = Field(min_length=1, max_length=64)
    dropped: list[RuleDroppedRequirement] = Field(default_factory=list, max_length=64)


class RuleMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str
    target_ids: list[str] = Field(default_factory=list, max_length=32)
    record: RuleRecord | None = None
    scenario: RuleScenarioRef | None = None
    evidence_spans: list[str] = Field(default_factory=list, max_length=32)
    applicability_evidence: str = Field(default="", max_length=4_000)
    carried_over: RuleCarriedOver | None = None
    reason_code: str = Field(default="", max_length=128)
    reason: str = Field(default="", max_length=2_000)

    @model_validator(mode="after")
    def _validate_operation(self) -> "RuleMutation":
        self.operation = self.operation.strip().upper()
        if self.operation not in RULE_OPERATIONS:
            raise ValueError(f"unsupported rule operation: {self.operation}")
        needs_record = self.operation in {"NEW", "UPDATE", "REPLACE"}
        if needs_record != (self.record is not None):
            raise ValueError(f"{self.operation} record requirement is invalid")
        if self.operation == "NEW" and self.scenario is None:
            raise ValueError("NEW requires scenario")
        if self.operation != "NEW" and self.scenario is not None:
            raise ValueError(f"{self.operation} must not include scenario")
        if self.operation in {
            "UPDATE",
            "REPLACE",
            "PAUSE",
            "ARCHIVE",
            "RESTORE",
            "NOOP",
        }:
            if not self.target_ids:
                raise ValueError(f"{self.operation} requires target_ids")
        elif self.target_ids:
            raise ValueError(f"{self.operation} must not have target_ids")
        if self.operation in {"UPDATE", "REPLACE"} and len(self.target_ids) != 1:
            raise ValueError(f"{self.operation} requires exactly one target_id")
        if self.operation != "UPDATE" and self.carried_over is not None:
            raise ValueError("carried_over is valid only for UPDATE")
        return self


class RuleCompilePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mutations: list[RuleMutation] = Field(default_factory=list, max_length=64)
    reason: str = Field(default="", max_length=2_000)


class StoredRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_: str = Field(alias="schema")
    atomic_id: str
    revision: int = Field(ge=1)
    status: Literal["active", "paused", "archived"]
    scenario_id: str
    source_uris: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    archived_at: str | None = None
    updated_at: str = ""
    record: RuleRecord
    uri: str
    content: str


class StoredScenario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_: str = Field(alias="schema")
    scenario_id: str
    name: str
    description: str
    uri: str
    content: str


class _RuleScores(list[float]):
    """Probabilities with exception vetoes preserved through threshold selection."""

    def __init__(self, probabilities: list[float], vetoed_indices: frozenset[int]):
        super().__init__(probabilities)
        self.vetoed_indices = vetoed_indices


@dataclass(frozen=True)
class _RelevantRules:
    scenarios: list[StoredScenario]
    selected: list[tuple[StoredRule, float]]
    judge: str | None = None
    warning: str | None = None
    scenario_selection: dict[str, Any] | None = None

