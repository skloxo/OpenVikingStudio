# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Rule compilation and retrieval backed by Markdown in VikingFS."""

from __future__ import annotations

import asyncio
import inspect
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

class _RuleCompilerMixin:

    async def create_compile(
        self,
        request: RuleCompileRequest,
        *,
        ctx: RequestContext,
    ) -> TaskRecord:
        self._dependencies()
        root = _rules_root(ctx)
        tracker = _rs_dep("get_task_tracker", get_task_tracker)()
        task = await tracker.create(
            self.task_type,
            task_id=f"{self.task_id_prefix}{uuid4().hex}",
            resource_id=root,
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
            meta={
                "request": {
                    "instruction": request.instruction,
                    "source_count": len(request.sources),
                }
            },
        )
        await tracker.patch_task(
            task.task_id,
            TaskPatch(stage="queued"),
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
        )
        background = asyncio.create_task(
            self._run_compile(task_id=task.task_id, request=request, ctx=ctx)
        )
        self._running.add(background)
        background.add_done_callback(self._running.discard)
        current = await tracker.get(
            task.task_id,
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
        )
        return current or task

    async def _run_compile(
        self,
        *,
        task_id: str,
        request: RuleCompileRequest,
        ctx: RequestContext,
    ) -> None:
        tracker = _rs_dep("get_task_tracker", get_task_tracker)()
        if hasattr(tracker, "register_running_work"):
            running_work_id = await tracker.register_running_work(
                task_id,
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
        else:
            res = tracker.register_running_task(
                task_id,
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
            running_work_id = await res if inspect.isawaitable(res) else None
        try:
            await tracker.start(
                task_id,
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
                stage="ingesting_sources",
            )
            with bind_task_context(
                task_id,
                ctx.account_id,
                ctx.user.user_id,
                enqueued_work=[],
                work_id=running_work_id,
            ):
                lock = self._compile_locks.setdefault(
                    (ctx.account_id, ctx.user.user_id), asyncio.Lock()
                )
                async with lock:
                    result = await self._compile(
                        request,
                        ctx=ctx,
                        task_id=task_id,
                    )
            await tracker.complete(
                task_id,
                result,
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
        except asyncio.CancelledError:
            return
        except Exception as exc:  # noqa: BLE001 - task failures must be persisted
            logger.exception("Rule compile task %s failed", task_id)
            await tracker.fail(
                task_id,
                f"RULE_COMPILE_FAILED: {exc}",
                account_id=ctx.account_id,
                user_id=ctx.user.user_id,
            )
        finally:
            await tracker.unregister_running_task(task_id)

    async def _compile(
        self,
        request: RuleCompileRequest,
        *,
        ctx: RequestContext,
        task_id: str,
    ) -> dict[str, Any]:
        self._dependencies()
        await self._ensure_rule_directories(ctx)
        source_text, source_uris = await self._collect_sources(request, ctx)
        tracker = _rs_dep("get_task_tracker", get_task_tracker)()
        await tracker.patch_task(
            task_id,
            TaskPatch(stage="recalling_rules"),
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
        )
        compiler = await self._compiler_vlm(ctx)
        prompt_token_limit = self._compiler_prompt_token_limit(compiler)
        fixed_prompt_tokens = estimate_text_tokens(
            self._render_compile_prompt(
                instruction="",
                source_text="",
                scenario_data=[],
                rule_data=[],
            )
        )
        available_material_tokens = prompt_token_limit - fixed_prompt_tokens
        if available_material_tokens < MIN_COMPILE_BATCH_TOKENS:
            raise InvalidArgumentError(
                "rule compiler context window cannot fit the compiler prompt"
            )
        material_token_limit = max(
            MIN_COMPILE_BATCH_TOKENS,
            available_material_tokens // 2,
        )
        batches = _rs_dep("_build_material_batches", _build_material_batches)(
            request.instruction or "",
            source_text,
            max_tokens=material_token_limit,
        )
        await tracker.patch_task(
            task_id,
            TaskPatch(stage="planning_operations"),
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
        )

        working_scenarios: dict[str, StoredScenario] = {}
        working_rules: dict[str, StoredRule] = {}
        accumulated_writes: dict[str, str] = {}
        operations: list[dict[str, Any]] = []
        plan_reasons: list[str] = []
        for batch_instruction, batch_source in batches:
            query = "\n\n".join(part for part in (batch_instruction, batch_source[:24_000]) if part)
            matches = await self._find_relevant_rules(
                query,
                ctx=ctx,
                scenario_limit=DEFAULT_RULE_SCENARIO_LIMIT,
                scenario_score_threshold=DEFAULT_RULE_SCENARIO_SCORE_THRESHOLD,
                rule_probability_threshold=DEFAULT_RULE_PROBABILITY_THRESHOLD,
                allowed_statuses=COMPILER_RULE_STATUSES,
                strict_rule_loading=False,
                filter_scenarios_with_jev=False,
            )
            recalled_scenarios = matches.scenarios
            recalled_rules = [rule for rule, _ in matches.selected]
            scenarios_by_id = {
                **{scenario.scenario_id: scenario for scenario in recalled_scenarios},
                **working_scenarios,
            }
            rules_by_id = {
                **{rule.atomic_id: rule for rule in recalled_rules},
                **working_rules,
            }
            plan = await self._build_compile_plan(
                instruction=batch_instruction,
                source_text=batch_source,
                scenarios=list(working_scenarios.values())
                + [
                    scenario
                    for scenario_id, scenario in scenarios_by_id.items()
                    if scenario_id not in working_scenarios
                ],
                rules=list(working_rules.values())
                + [
                    rule
                    for atomic_id, rule in rules_by_id.items()
                    if atomic_id not in working_rules
                ],
                ctx=ctx,
                vlm=compiler,
                prompt_token_limit=prompt_token_limit,
            )
            self._validate_plan_evidence(
                plan,
                material="\n".join((batch_instruction, batch_source)),
            )
            applied = await self._apply_plan(
                plan,
                existing_scenarios=list(scenarios_by_id.values()),
                existing_rules=list(rules_by_id.values()),
                source_uris=source_uris,
                ctx=ctx,
                persist=False,
            )
            batch_scenarios = applied.pop("_scenarios")
            batch_rules = applied.pop("_rules")
            batch_writes = applied.pop("_writes")
            accumulated_writes.update(batch_writes)
            written_uris = set(accumulated_writes)
            working_rules = {
                rule.atomic_id: rule
                for rule in batch_rules
                if rule.uri in written_uris and rule.status in COMPILER_RULE_STATUSES
            }
            working_rule_scenario_ids = {rule.scenario_id for rule in working_rules.values()}
            working_scenarios = {
                scenario.scenario_id: scenario
                for scenario in batch_scenarios
                if scenario.uri in written_uris
                or scenario.scenario_id in working_rule_scenario_ids
                or scenario.scenario_id in working_scenarios
            }
            operations.extend(applied["operations"])
            if plan.reason:
                plan_reasons.append(plan.reason)

        await tracker.patch_task(
            task_id,
            TaskPatch(stage="writing_rules"),
            account_id=ctx.account_id,
            user_id=ctx.user.user_id,
        )
        fs, _, _ = self._dependencies()
        if accumulated_writes:
            # Detach the compile Task context so the file-write background work is
            # owned and finalized by its own content_batch_write Task. Otherwise it
            # inherits this compile Task's id, the ContentWriteProcessor overwrites
            # the compile result with the file-write result, and the content-write
            # Task created by batch_write never receives its work and stays pending.
            with detach_task_context():
                write_result = await fs.batch_write(
                    root_uri=_rules_root(ctx),
                    operations=[
                        {"uri": uri, "content": content, "mode": "upsert"}
                        for uri, content in accumulated_writes.items()
                    ],
                    ctx=ctx,
                    wait=False,
                )
        else:
            write_result = {"created": [], "updated": [], "unchanged": []}
        return {
            "rules_root": _rules_root(ctx),
            "source_uris": source_uris,
            "plan_reason": "\n".join(plan_reasons),
            "batch_count": len(batches),
            "operations": operations,
            "written_uris": sorted(accumulated_writes),
            "write_result": write_result,
        }

    async def _default_vlm(self, ctx: RequestContext) -> Any:
        if self._vlm_resolver is not None:
            return await self._vlm_resolver.get_vlm(ctx.account_id)
        from openviking_cli.utils.config import get_openviking_config

        vlm = get_openviking_config().vlm.get_vlm_instance()
        if vlm is not None:
            return vlm
        raise UnavailableError("rule VLM", "account VLM resolver is not configured")

    async def _compiler_vlm(self, ctx: RequestContext) -> Any:
        config = self._rules_config
        if config is not None:
            compiler = config.get_compiler()
            if compiler is not None:
                return compiler
        return await self._default_vlm(ctx)

    def _compiler_prompt_token_limit(self, vlm: Any) -> int:
        configured_window = _positive_int(
            getattr(self._rules_config, "compiler_context_window", None)
        )
        extra_request_body = _vlm_setting(vlm, "extra_request_body")
        num_ctx = (
            _positive_int(extra_request_body.get("num_ctx"))
            if isinstance(extra_request_body, dict)
            else None
        )
        model_info: dict[str, Any] = {}
        model = _vlm_setting(vlm, "model")
        if configured_window is None and num_ctx is None and isinstance(model, str) and model:
            try:
                from litellm import model_cost

                loaded = model_cost.get(model)
                if loaded is None and "/" in model:
                    loaded = model_cost.get(model.split("/", 1)[1])
                if isinstance(loaded, dict):
                    model_info = {str(key): value for key, value in loaded.items()}
            except Exception as exc:  # noqa: BLE001 - unknown/custom models use fallback
                logger.debug("No context metadata for rule compiler model %s: %s", model, exc)

        context_window = (
            configured_window
            or num_ctx
            or _positive_int(model_info.get("max_input_tokens"))
            or DEFAULT_COMPILER_CONTEXT_WINDOW
        )
        if context_window < MIN_COMPILER_CONTEXT_WINDOW:
            raise InvalidArgumentError(
                f"rule compiler context window must be at least {MIN_COMPILER_CONTEXT_WINDOW}"
            )

        configured_output = _positive_int(_vlm_setting(vlm, "max_tokens"))
        discovered_output = _positive_int(model_info.get("max_output_tokens"))
        output_reserve = (
            configured_output
            or discovered_output
            or min(DEFAULT_COMPILER_OUTPUT_TOKENS, context_window // 4)
        )
        safety_reserve = max(256, context_window // 20)
        prompt_limit = context_window - output_reserve - safety_reserve
        if prompt_limit < 1024:
            raise InvalidArgumentError(
                "rule compiler context window is too small after reserving output tokens"
            )
        return prompt_limit
