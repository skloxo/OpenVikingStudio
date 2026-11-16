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
    COMPILER_RULE_STATUSES, DEFAULT_ARCHIVED_RETENTION_DAYS, DEFAULT_COMPILER_CONTEXT_WINDOW,
    DEFAULT_COMPILER_OUTPUT_TOKENS, DEFAULT_RULE_PROBABILITY_THRESHOLD,
    DEFAULT_RULE_SCENARIO_LIMIT, DEFAULT_RULE_SCENARIO_SCORE_THRESHOLD,
    MAX_COMPILE_REPAIR_ATTEMPTS, MAX_SCENARIOS_PER_MATCHER_BATCH, MAX_SOURCE_CHARS,
    MAX_SOURCE_FILES, MIN_COMPILE_BATCH_TOKENS, MIN_COMPILER_CONTEXT_WINDOW,
    RULE_OPERATIONS, RULE_SCHEMA, SCENARIO_SCHEMA,
    RuleCarriedOver, RuleCompilePlan, RuleCompileRequest, RuleDroppedRequirement,
    RuleMutation, RuleRecord, RuleResourceReference, RuleScenarioRef, RuleSearchRequest,
    StoredRule, StoredScenario, _RelevantRules, _RuleScores,
    _build_material_batches, _media_extension, _parse_markdown, _parse_timestamp,
    _positive_int, _render_markdown, _rs_dep, _rules_root, _slug, _take_text_prefix,
    _validate_text_source, _vlm_setting, logger,
)
from openviking.service.rule_render import (
    _RULE_APPLICATION_GUIDANCE, _meaningful_applicability_clause,
    _render_rule_block, _render_rules, _render_scenario_for_judge,
)

class _RuleStorageMixin:

    async def _ensure_rule_directories(self, ctx: RequestContext) -> None:
        fs, _, _ = self._dependencies()
        root = _rules_root(ctx)
        for uri, description in (
            (root, "Durable rules compiled from explicit user or agent instructions."),
        ):
            try:
                stat = await fs.stat(uri, ctx, skip_count=True)
            except NotFoundError:
                await fs.mkdir(uri, ctx, description=description)
            else:
                if not stat.get("isDir"):
                    raise InvalidArgumentError(f"rule library path is occupied by a file: {uri}")
                continue

    async def _collect_sources(
        self,
        request: RuleCompileRequest,
        ctx: RequestContext,
    ) -> tuple[str, list[str]]:
        _, resources, _ = self._dependencies()
        source_uris: list[str] = []
        for source in request.sources:
            if isinstance(source, RuleResourceReference):
                uri = validate_request_viking_uri(
                    source.resource_uri,
                    ctx,
                    field_name="resource_uri",
                ).rstrip("/")
                if classify_uri(uri).context_type != "resource":
                    raise InvalidArgumentError("resource_uri must point to the resource namespace")
            else:
                _validate_text_source(source)
                declared_connector = source.add_type is not None
                updates = {
                    "reason": source.reason or "Rule compile source",
                }
                if declared_connector:
                    updates["instruction"] = ""
                add_request = source.model_copy(
                    update=updates,
                )
                result = await _rs_dep("ingest_resource_request", ingest_resource_request)(
                    add_request,
                    ctx,
                    resources=resources,
                    config=self._config,
                    wait=False if declared_connector else True,
                    internal_task=True,
                )
                terminal: TaskRecord | None = None
                if result.get("status") == "accepted":
                    task_id = str(result.get("task_id") or "")
                    if not task_id:
                        raise ProcessingError(
                            "Rule source ingestion was accepted without a task ID"
                        )
                    terminal = await _rs_dep("get_task_tracker", get_task_tracker)().wait(
                        task_id,
                        account_id=ctx.account_id,
                        user_id=ctx.user.user_id,
                        timeout=None,
                    )
                    if terminal.status == TaskStatus.FAILED:
                        raise ProcessingError(
                            f"Rule source ingestion failed: {terminal.error or 'unknown error'}"
                        )
                    if terminal.status == TaskStatus.CANCELLED:
                        raise ProcessingError("Rule source ingestion was cancelled")
                uri = str(
                    result.get("root_uri")
                    or result.get("resource_id")
                    or (terminal.resource_id if terminal else "")
                    or ((terminal.result or {}).get("root_uri") if terminal else "")
                    or ((terminal.result or {}).get("resource_id") if terminal else "")
                ).rstrip("/")
                if not uri:
                    raise ProcessingError("add_resource did not return a parsed resource URI")
            if uri not in source_uris:
                source_uris.append(uri)

        chunks: list[str] = []
        remaining = MAX_SOURCE_CHARS
        for uri in source_uris:
            text = await self._read_source(uri, ctx, max(remaining, 1))
            if not text.strip():
                raise InvalidArgumentError(
                    "rules/compile only supports sources that contain readable text after "
                    f"resource parsing: {uri}"
                )
            if remaining <= 0:
                continue
            chunks.append(text)
            remaining -= len(text)
        return "\n\n".join(chunks), source_uris

    async def _read_source(
        self,
        uri: str,
        ctx: RequestContext,
        limit: int,
    ) -> str:
        fs, _, _ = self._dependencies()
        stat = await fs.stat(uri, ctx, skip_count=True)
        if not stat.get("isDir"):
            try:
                content = await fs.read_visible(uri, ctx)
            except UnicodeError:
                return ""
            if not content.strip():
                return ""
            return f"## Source: {uri}\n{content}"[:limit]

        page = await fs.ls(
            uri,
            ctx,
            recursive=True,
            simple=True,
            node_limit=MAX_SOURCE_FILES,
            level_limit=12,
        )
        chunks: list[str] = []
        used = 0
        for entry in page.entries:
            child_uri = entry if isinstance(entry, str) else str(entry.get("uri") or "")
            if not child_uri or used >= limit:
                continue
            try:
                child_stat = await fs.stat(child_uri, ctx, skip_count=True)
                if child_stat.get("isDir"):
                    continue
                content = await fs.read_visible(child_uri, ctx)
            except (NotFoundError, UnicodeError):
                continue
            if not content.strip():
                continue
            chunk = f"## Source: {child_uri}\n{content}"
            chunk = chunk[: limit - used]
            chunks.append(chunk)
            used += len(chunk)
        return "\n\n".join(chunks)

    async def _load_scenario(self, uri: str, ctx: RequestContext) -> StoredScenario:
        fs, _, _ = self._dependencies()
        content = await fs.read(uri, ctx)
        metadata, _ = _parse_markdown(content)
        if metadata.get("schema") != SCENARIO_SCHEMA:
            raise ValueError(f"unsupported rule scenario schema at {uri}")
        scenario = StoredScenario.model_validate({**metadata, "uri": uri, "content": content})
        if uri != f"{_rules_root(ctx)}/{scenario.scenario_id}/abstract.md":
            raise ValueError(f"scenario_id does not match its directory at {uri}")
        return scenario

    async def _load_rule(self, uri: str, ctx: RequestContext) -> StoredRule:
        fs, _, _ = self._dependencies()
        content = await fs.read(uri, ctx)
        metadata, body = _parse_markdown(content)
        if metadata.get("schema") != RULE_SCHEMA:
            raise ValueError(f"unsupported rule schema at {uri}")
        if (
            uri
            != f"{_rules_root(ctx)}/{metadata.get('scenario_id')}/{metadata.get('atomic_id')}.md"
        ):
            raise ValueError(f"Rule identity does not match its Scenario directory at {uri}")
        record_data = {
            field: metadata.get(field, "") for field in RuleRecord.model_fields if field != "body"
        }
        record_data["body"] = strip_memory_fields_trailer(body)
        return StoredRule.model_validate(
            {
                **metadata,
                "record": record_data,
                "uri": uri,
                "content": content,
            }
        )

    async def _load_rules_for_scenarios(
        self,
        scenarios: list[StoredScenario],
        ctx: RequestContext,
        *,
        strict: bool = False,
    ) -> list[StoredRule]:
        fs, _, _ = self._dependencies()
        uris: list[str] = []
        for scenario in scenarios:
            directory = scenario.uri.rsplit("/", 1)[0]
            try:
                page = await fs.glob("*.md", ctx=ctx, uri=directory)
            except Exception as exc:
                raise ProcessingError(f"Cannot list Scenario rules at {directory}: {exc}") from exc
            for item in page.get("matches", []):
                uri = item if isinstance(item, str) else str(item.get("uri") or "")
                if (
                    uri.startswith(f"{directory}/")
                    and "/" not in uri[len(directory) + 1 :]
                    and not uri.endswith("/abstract.md")
                    and uri not in uris
                ):
                    uris.append(uri)
        loaded = await asyncio.gather(
            *(self._load_rule(uri, ctx) for uri in uris),
            return_exceptions=True,
        )
        failures = [
            f"{uri}: {type(item).__name__}: {item}"
            for uri, item in zip(uris, loaded, strict=True)
            if isinstance(item, Exception)
        ]
        if failures and strict:
            raise ProcessingError(
                "Rule search cannot guarantee complete validation because a recalled Scenario "
                "contains an unreadable Rule: " + "; ".join(failures)
            )
        for failure in failures:
            logger.warning("Ignoring unreadable rule document: %s", failure)
        return [rule for rule in loaded if isinstance(rule, StoredRule)]

    async def cleanup_archived_rules(
        self,
        *,
        ctx: RequestContext,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Permanently remove rules continuously marked archived past retention."""
        self._dependencies()
        lock = self._compile_locks.setdefault((ctx.account_id, ctx.user.user_id), asyncio.Lock())
        async with lock:
            return await self._cleanup_archived_rules_locked(ctx=ctx, now=now)

    async def _cleanup_archived_rules_locked(
        self,
        *,
        ctx: RequestContext,
        now: datetime | None,
    ) -> dict[str, Any]:
        fs, _, _ = self._dependencies()
        root = _rules_root(ctx)
        try:
            result = await fs.glob(
                "*/*.md",
                ctx=ctx,
                uri=root,
            )
        except NotFoundError:
            return {"scanned": 0, "deleted": [], "failed": []}

        uris = [
            item if isinstance(item, str) else str(item.get("uri") or "")
            for item in result.get("matches", [])
        ]
        loaded = await asyncio.gather(
            *(
                self._load_rule(uri, ctx)
                for uri in uris
                if uri and not uri.endswith("/abstract.md")
            ),
            return_exceptions=True,
        )
        rules = [item for item in loaded if isinstance(item, StoredRule)]
        retention_days = int(
            getattr(
                self._rules_config,
                "archived_retention_days",
                DEFAULT_ARCHIVED_RETENTION_DAYS,
            )
        )
        reference_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        cutoff = reference_time - timedelta(days=retention_days)
        eligible: list[StoredRule] = []
        for rule in rules:
            if rule.status != "archived":
                continue
            archived_at = _parse_timestamp(rule.archived_at or "")
            if archived_at is None:
                logger.warning(
                    "Skipping archived rule with invalid archived_at: %s",
                    rule.uri,
                )
                continue
            if archived_at <= cutoff:
                eligible.append(rule)

        if not eligible:
            return {"scanned": len(rules), "deleted": [], "failed": []}

        failures: list[dict[str, str]] = []
        deleted: list[str] = []
        for rule in eligible:
            try:
                await fs.rm(rule.uri, ctx, wait=True)
            except Exception as exc:  # noqa: BLE001 - continue cleanup for independent rules
                logger.warning("Failed to clean up archived rule: %s", rule.uri)
                failures.append({"uri": rule.uri, "error": str(exc)})
            else:
                deleted.append(rule.uri)
        return {
            "scanned": len(rules),
            "deleted": deleted,
            "failed": failures,
        }
