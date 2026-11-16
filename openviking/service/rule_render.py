# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Rule compilation and retrieval backed by Markdown in VikingFS."""

from __future__ import annotations

import asyncio
import json
import re
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
from openviking.service.rule_models import (
    MAX_SCENARIO_CHARS_FOR_JUDGE, StoredRule, StoredScenario, _parse_markdown,
)


_RULE_APPLICATION_GUIDANCE = """# Applicable OpenViking Rules

These Rules are behavioral constraints.

Application protocol:
1. Evaluate every Rule independently against concrete facts from the current task.
2. Check the applicability boundary and exception before applying a Rule. An empty
   applies_when means the Rule applies in every situation except its exception.
   For a non-empty applies_when, topic similarity alone does not establish applicability.
3. Do not infer facts that are absent.
4. Before acting or answering, validate the planned action or answer against every
   returned Rule. Returned Rules are mandatory when their applicability conditions hold.
5. When quoting a Rule, copy an unchanged contiguous excerpt from the returned text.
   Preserve its punctuation and qualifiers. Do not combine or rewrite Constraint and
   Summary text into a quotation."""


def _render_rule_block(rule: StoredRule) -> str:
    record = rule.record
    body = strip_memory_fields_trailer(record.body).strip()
    generated_body = f"# {record.name}\n\n{record.content}".strip()
    if body in {record.content.strip(), generated_body}:
        body = ""

    lines = [
        f"## [{rule.atomic_id}] {record.name}",
        "",
        "Constraint:",
        record.content.strip(),
        "",
        f"Applies when: {record.applies_when.strip() or 'Every situation, except as stated below.'}",
    ]
    exception = _meaningful_applicability_clause(record.exception)
    if exception:
        lines.append(f"Exception: {exception}")
    description = record.description.strip()
    if description and description != record.content.strip():
        lines.extend(["", f"Summary: {description}"])
    if body:
        lines.extend(["", "Additional guidance:", body])
    lines.extend(["", f"Compiled Rule URI: {rule.uri}"])
    if rule.source_uris:
        lines.extend(
            [
                "Policy sources:",
                *(f"- {source_uri}" for source_uri in rule.source_uris),
            ]
        )
    return "\n".join(lines)


def _meaningful_applicability_clause(value: str) -> str:
    stripped = value.strip()
    return "" if stripped.casefold() in {"", "none", "(none)", "[]", "[ ]"} else stripped


def _render_rules(selected: list[tuple[StoredRule, float]]) -> str:
    total = len(selected)
    header = f"{_RULE_APPLICATION_GUIDANCE}\n\nMatched {total} active Rule(s)."

    if not selected:
        return f"{header}\n\nNo active compiled Rule met the current retrieval thresholds."
    return "\n\n".join([header, *(_render_rule_block(rule) for rule, _ in selected)])


def _render_scenario_for_judge(scenario: StoredScenario) -> str:
    try:
        _, body = _parse_markdown(scenario.content)
    except ValueError:
        body = scenario.content
    parts = [
        f"Scenario ID: {scenario.scenario_id}",
        f"Scenario name: {scenario.name}",
        f"Scenario description: {scenario.description}",
    ]
    if body.strip():
        parts.extend(["Scenario details:", body.strip()])
    return "\n".join(parts)[:MAX_SCENARIO_CHARS_FOR_JUDGE]


