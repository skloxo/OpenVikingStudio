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
    _positive_int, _render_markdown, _rules_root, _slug, _take_text_prefix,
    _validate_text_source, _vlm_setting, logger,
)
from openviking.service.rule_render import (
    _RULE_APPLICATION_GUIDANCE, _meaningful_applicability_clause,
    _render_rule_block, _render_rules, _render_scenario_for_judge,
)

class _RuleApplyMixin:

    async def _apply_plan(
        self,
        plan: RuleCompilePlan,
        *,
        existing_scenarios: list[StoredScenario],
        existing_rules: list[StoredRule],
        source_uris: list[str],
        ctx: RequestContext,
        persist: bool = True,
    ) -> dict[str, Any]:
        fs, _, _ = self._dependencies()
        root = _rules_root(ctx)
        scenarios = {scenario.scenario_id: scenario for scenario in existing_scenarios}
        rules = {rule.atomic_id: rule for rule in existing_rules}
        writes: dict[str, str] = {}
        outcomes: list[dict[str, Any]] = []
        scenarios_to_write: set[str] = set()
        reserved_ids = set(rules) | {"abstract"}
        if any(mutation.operation in {"NEW", "REPLACE"} for mutation in plan.mutations):
            inventory = await fs.glob("*/*.md", ctx=ctx, uri=root)
            reserved_ids.update(
                (item if isinstance(item, str) else str(item.get("uri") or ""))
                .rsplit("/", 1)[-1]
                .removesuffix(".md")
                for item in inventory.get("matches", [])
            )

        def require_rule(atomic_id: str, allowed: set[str]) -> StoredRule:
            rule = rules.get(atomic_id)
            if rule is None:
                raise InvalidArgumentError(f"rule operation targets unknown rule: {atomic_id}")
            if rule.status not in allowed:
                raise InvalidArgumentError(
                    f"rule {atomic_id} has status {rule.status}, expected {sorted(allowed)}"
                )
            return rule

        def store_rule(
            *,
            atomic_id: str,
            revision: int,
            status: Literal["active", "paused", "archived"],
            scenario_id: str,
            record: RuleRecord,
            evidence: list[str],
            archived_at: str | None = None,
            uri: str | None = None,
            prior_sources: list[str] | None = None,
        ) -> StoredRule:
            rule_uri = uri or f"{root}/{scenario_id}/{atomic_id}.md"
            merged_sources = list(dict.fromkeys([*(prior_sources or []), *source_uris]))
            updated_at = get_current_timestamp()
            metadata = {
                "schema": RULE_SCHEMA,
                "atomic_id": atomic_id,
                "revision": revision,
                "status": status,
                "scenario_id": scenario_id,
                "source_uris": merged_sources,
                "evidence": evidence,
                "updated_at": updated_at,
                **record.model_dump(exclude={"body"}),
            }
            if status == "archived":
                metadata["archived_at"] = archived_at or updated_at
            content = _render_markdown(
                metadata, record.body or f"# {record.name}\n\n{record.content}"
            )
            stored = StoredRule.model_validate(
                {
                    **metadata,
                    "record": record,
                    "uri": rule_uri,
                    "content": content,
                }
            )
            rules[atomic_id] = stored
            writes[rule_uri] = content
            return stored

        async def resolve_scenario(ref: RuleScenarioRef) -> StoredScenario:
            if ref.scenario_id and ref.scenario_id in scenarios:
                return scenarios[ref.scenario_id]
            requested = _slug(ref.scenario_id or ref.name, "scenario")
            if requested in scenarios:
                return scenarios[requested]
            scenario_id = requested
            uri = f"{root}/{scenario_id}/abstract.md"
            try:
                existing = await self._load_scenario(uri, ctx)
            except NotFoundError:
                pass
            else:
                scenarios[scenario_id] = existing
                return existing
            scenario = StoredScenario(
                schema=SCENARIO_SCHEMA,
                scenario_id=scenario_id,
                name=ref.name.strip(),
                description=ref.description.strip(),
                uri=uri,
                content="",
            )
            scenarios[scenario_id] = scenario
            scenarios_to_write.add(scenario_id)
            return scenario

        def new_id(record: RuleRecord) -> str:
            base = _slug(record.name, "rule")
            candidate = base
            while candidate in reserved_ids:
                candidate = f"{base}-{uuid4().hex[:8]}"
            reserved_ids.add(candidate)
            return candidate

        async def apply(mutation: RuleMutation) -> None:
            operation = mutation.operation
            if operation in {"UNCERTAIN", "REJECT"}:
                outcomes.append(
                    {
                        "operation": operation,
                        "reason_code": mutation.reason_code,
                        "reason": mutation.reason,
                    }
                )
                return
            if operation == "NOOP":
                for target in mutation.target_ids:
                    require_rule(target, {"active"})
                outcomes.append({"operation": operation, "target_ids": mutation.target_ids})
                return
            if operation in {"PAUSE", "ARCHIVE", "RESTORE"}:
                if operation == "PAUSE":
                    expected = {"active"}
                    status: Literal["active", "paused", "archived"] = "paused"
                elif operation == "RESTORE":
                    expected = {"paused"}
                    status = "active"
                else:
                    expected = {"active", "paused", "archived"}
                    status = "archived"
                for target in mutation.target_ids:
                    current = require_rule(target, expected)
                    if operation == "ARCHIVE" and current.status == "archived":
                        continue
                    store_rule(
                        atomic_id=current.atomic_id,
                        revision=current.revision + 1,
                        status=status,
                        scenario_id=current.scenario_id,
                        record=current.record,
                        evidence=mutation.evidence_spans,
                        archived_at=current.archived_at,
                        uri=current.uri,
                        prior_sources=current.source_uris,
                    )
                outcomes.append({"operation": operation, "target_ids": mutation.target_ids})
                return
            assert mutation.record is not None
            if operation == "NEW":
                assert mutation.scenario is not None
                scenario = await resolve_scenario(mutation.scenario)
                atomic_id = new_id(mutation.record)
                created = store_rule(
                    atomic_id=atomic_id,
                    revision=1,
                    status="active",
                    scenario_id=scenario.scenario_id,
                    record=mutation.record,
                    evidence=mutation.evidence_spans,
                )
                outcomes.append(
                    {"operation": operation, "atomic_id": atomic_id, "uri": created.uri}
                )
                return

            primary = require_rule(mutation.target_ids[0], {"active", "paused"})
            if operation == "UPDATE":
                updated = store_rule(
                    atomic_id=primary.atomic_id,
                    revision=primary.revision + 1,
                    status=primary.status,
                    scenario_id=primary.scenario_id,
                    record=mutation.record,
                    evidence=mutation.evidence_spans,
                    uri=primary.uri,
                    prior_sources=primary.source_uris,
                )
                outcomes.append(
                    {
                        "operation": operation,
                        "atomic_id": updated.atomic_id,
                        "uri": updated.uri,
                    }
                )
                return

            assert operation == "REPLACE"
            replacement_id = new_id(mutation.record)
            replacement = store_rule(
                atomic_id=replacement_id,
                revision=1,
                status="active",
                scenario_id=primary.scenario_id,
                record=mutation.record,
                evidence=mutation.evidence_spans,
            )
            store_rule(
                atomic_id=primary.atomic_id,
                revision=primary.revision + 1,
                status="archived",
                scenario_id=primary.scenario_id,
                record=primary.record,
                evidence=mutation.evidence_spans,
                uri=primary.uri,
                prior_sources=primary.source_uris,
            )
            outcomes.append(
                {
                    "operation": operation,
                    "atomic_id": replacement_id,
                    "uri": replacement.uri,
                    "target_ids": mutation.target_ids,
                }
            )

        for mutation in plan.mutations:
            await apply(mutation)

        for scenario_id in scenarios_to_write:
            scenario = scenarios[scenario_id]
            metadata = {
                "schema": SCENARIO_SCHEMA,
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "description": scenario.description,
                "updated_at": get_current_timestamp(),
            }
            lines = [f"# {scenario.name}", "", scenario.description]
            content = _render_markdown(metadata, "\n".join(lines))
            writes[scenario.uri] = content
            scenarios[scenario_id] = scenario.model_copy(
                update={
                    "content": content,
                }
            )

        if persist and writes:
            write_result = await fs.batch_write(
                root_uri=root,
                operations=[
                    {"uri": uri, "content": content, "mode": "upsert"}
                    for uri, content in writes.items()
                ],
                ctx=ctx,
                wait=False,
            )
        else:
            write_result = {"created": [], "updated": [], "unchanged": []}
        result = {
            "operations": outcomes,
            "written_uris": sorted(writes),
            "write_result": write_result,
        }
        if not persist:
            result["_scenarios"] = list(scenarios.values())
            result["_rules"] = list(rules.values())
            result["_writes"] = writes
        return result
