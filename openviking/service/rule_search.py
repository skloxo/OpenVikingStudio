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

class _RuleSearchMixin:

    async def search_rules(
        self,
        request: RuleSearchRequest,
        *,
        ctx: RequestContext,
    ) -> dict[str, Any]:
        matches = await self._find_relevant_rules(
            request.task_context,
            ctx=ctx,
            rule_probability_threshold=request.rule_probability_threshold,
            allowed_statuses=frozenset({"active"}),
            strict_rule_loading=True,
            filter_scenarios_with_jev=True,
            scenario_limit=None,
        )
        rendered = _render_rules(matches.selected)
        result = {
            "rules": [
                {
                    "atomic_id": rule.atomic_id,
                    "revision": rule.revision,
                    "scenario_id": rule.scenario_id,
                    "probability": score,
                    "uri": rule.uri,
                    "content": rule.content,
                }
                for rule, score in matches.selected
            ],
            "scenarios": [scenario.scenario_id for scenario in matches.scenarios],
            "rendered": rendered,
            "delivery": {
                "complete": True,
                "rule_count": len(matches.selected),
                "rendered_chars": len(rendered),
            },
            "scenario_selection": matches.scenario_selection,
        }
        if matches.judge is not None:
            result["judge"] = matches.judge
        if matches.warning:
            result["warning"] = matches.warning
        return result

    async def _find_relevant_rules(
        self,
        query: str,
        *,
        ctx: RequestContext,
        rule_probability_threshold: float,
        allowed_statuses: frozenset[str] | None,
        strict_rule_loading: bool,
        filter_scenarios_with_jev: bool,
        scenario_limit: int | None = DEFAULT_RULE_SCENARIO_LIMIT,
        scenario_score_threshold: float | None = DEFAULT_RULE_SCENARIO_SCORE_THRESHOLD,
    ) -> _RelevantRules:
        try:
            scenarios = await self._recall_scenarios(
                query,
                ctx=ctx,
                limit=scenario_limit,
                score_threshold=scenario_score_threshold,
            )
            scenario_selection = None
            if filter_scenarios_with_jev and scenarios:
                scenarios, scenario_selection = await self._filter_unrelated_scenarios_with_jev(
                    query, scenarios
                )
            rules = (
                await self._load_rules_for_scenarios(
                    scenarios,
                    ctx,
                    strict=strict_rule_loading,
                )
                if scenarios
                else []
            )
        except NotFoundError:
            return _RelevantRules(
                scenarios=[],
                selected=[],
                warning="rule library is empty",
            )
        if not scenarios:
            return _RelevantRules(
                scenarios=[],
                selected=[],
                scenario_selection=scenario_selection,
            )

        rules = [
            rule for rule in rules if allowed_statuses is None or rule.status in allowed_statuses
        ]
        if not rules:
            return _RelevantRules(
                scenarios=scenarios,
                selected=[],
                scenario_selection=scenario_selection,
            )

        scores, judge, warning = await self._score_rules(
            query,
            rules,
            rule_probability_threshold=rule_probability_threshold,
        )
        vetoed_indices = scores.vetoed_indices if isinstance(scores, _RuleScores) else frozenset()
        selected = sorted(
            (
                (rule, score)
                for index, (rule, score) in enumerate(zip(rules, scores, strict=True))
                if index not in vetoed_indices and score >= rule_probability_threshold
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        return _RelevantRules(
            scenarios=scenarios,
            selected=selected,
            judge=judge,
            warning=warning,
            scenario_selection=scenario_selection,
        )

    async def _recall_scenarios(
        self,
        query: str,
        *,
        ctx: RequestContext,
        limit: int | None,
        score_threshold: float | None,
    ) -> list[StoredScenario]:
        fs, _, search = self._dependencies()
        root = _rules_root(ctx)
        await fs.stat(root, ctx, skip_count=True)
        page = await fs.glob("*/abstract.md", ctx=ctx, uri=root)
        scenario_uris = {
            item if isinstance(item, str) else str(item.get("uri") or "")
            for item in page.get("matches", [])
        }
        scenario_uris = {
            uri
            for uri in scenario_uris
            if uri.startswith(f"{root}/")
            and uri[len(root) + 1 :].count("/") == 1
            and uri.endswith("/abstract.md")
        }
        if not scenario_uris:
            return []
        limit = len(scenario_uris) if limit is None else min(limit, len(scenario_uris))
        result = await search.find(
            query=query,
            ctx=ctx,
            target_uri=root,
            limit=limit,
            score_threshold=score_threshold,
            level=[2],
            filter={
                "op": "or",
                "conds": [
                    {"op": "must", "field": "uri", "conds": [uri], "para": "-d=0"}
                    for uri in sorted(scenario_uris)
                ],
            },
        )
        contexts = (
            list(result) if hasattr(result, "__iter__") and not isinstance(result, dict) else []
        )
        if isinstance(result, dict):
            contexts = [
                item
                for category in ("memories", "resources", "skills")
                for item in result.get(category, [])
            ]
        uris: list[str] = []
        for context in contexts:
            uri = context.get("uri") if isinstance(context, dict) else getattr(context, "uri", None)
            if isinstance(uri, str) and uri in scenario_uris and uri not in uris:
                uris.append(uri)
        loaded = await asyncio.gather(
            *(self._load_scenario(uri, ctx) for uri in uris),
            return_exceptions=True,
        )
        failures = [str(item) for item in loaded if isinstance(item, Exception)]
        if failures:
            raise ProcessingError("Unreadable recalled Scenario: " + "; ".join(failures))
        return [scenario for scenario in loaded if isinstance(scenario, StoredScenario)]

    async def _filter_unrelated_scenarios_with_jev(
        self,
        task_context: str,
        scenarios: list[StoredScenario],
    ) -> tuple[list[StoredScenario], dict[str, Any]]:
        threshold = float(
            getattr(self._rules_config, "scenario_irrelevance_threshold", 0.9)
            if self._rules_config is not None
            else 0.9
        )
        config = self._rules_config.jev_rule_matcher if self._rules_config is not None else None
        base_report: dict[str, Any] = {
            "backend": "disabled",
            "irrelevance_threshold": threshold,
            "recalled_scenario_count": len(scenarios),
            "passed_scenario_ids": [scenario.scenario_id for scenario in scenarios],
            "skipped_scenario_ids": [],
            "decisions": [],
        }
        if config is None or not config.is_available():
            base_report["decisions"] = [
                {
                    "scenario_id": scenario.scenario_id,
                    "decision": "pass",
                    "reason": "jev_not_configured",
                }
                for scenario in scenarios
            ]
            return scenarios, base_report

        try:
            client = _rs_dep("ScenarioJevClient", ScenarioJevClient).from_config(config)
        except Exception as exc:  # noqa: BLE001 - an unavailable judge must pass
            logger.warning("Jev Scenario filter unavailable: %s", exc)
            client = None
        if client is None:
            base_report.update(
                {
                    "backend": "unavailable",
                    "warning": "Jev Scenario filter was unavailable; every recalled Scenario was passed.",
                    "decisions": [
                        {
                            "scenario_id": scenario.scenario_id,
                            "decision": "pass",
                            "reason": "jev_unavailable_or_invalid",
                        }
                        for scenario in scenarios
                    ],
                }
            )
            return scenarios, base_report

        passed: list[StoredScenario] = []
        skipped_ids: list[str] = []
        decisions: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            for start in range(0, len(scenarios), MAX_SCENARIOS_PER_MATCHER_BATCH):
                batch = scenarios[start : start + MAX_SCENARIOS_PER_MATCHER_BATCH]
                try:
                    scores = await asyncio.to_thread(
                        client.judge_scenarios,
                        task_context,
                        [_render_scenario_for_judge(scenario) for scenario in batch],
                    )
                except Exception as exc:  # noqa: BLE001 - uncertainty must pass
                    logger.warning("Jev Scenario filter failed: %s", exc)
                    scores = None
                if not isinstance(scores, (list, tuple)) or len(scores) != len(batch):
                    warnings.append(
                        f"Jev did not return a valid score for Scenario batch starting at {start}; "
                        "the entire batch was passed."
                    )
                    for scenario in batch:
                        passed.append(scenario)
                        decisions.append(
                            {
                                "scenario_id": scenario.scenario_id,
                                "decision": "pass",
                                "reason": "jev_unavailable_or_invalid",
                            }
                        )
                    continue

                for scenario, score in zip(batch, scores, strict=True):
                    if (
                        isinstance(score, bool)
                        or not isinstance(score, (int, float))
                        or not 0 <= score <= 1
                    ):
                        passed.append(scenario)
                        decisions.append(
                            {
                                "scenario_id": scenario.scenario_id,
                                "decision": "pass",
                                "reason": "invalid_jev_score",
                            }
                        )
                    elif float(score) >= threshold:
                        skipped_ids.append(scenario.scenario_id)
                        decisions.append(
                            {
                                "scenario_id": scenario.scenario_id,
                                "decision": "skip",
                                "reason": "high_confidence_completely_unrelated",
                                "irrelevance_probability": float(score),
                            }
                        )
                    else:
                        passed.append(scenario)
                        decisions.append(
                            {
                                "scenario_id": scenario.scenario_id,
                                "decision": "pass",
                                "reason": "not_high_confidence_unrelated",
                                "irrelevance_probability": float(score),
                            }
                        )
        finally:
            try:
                client.close()
            except Exception as exc:  # noqa: BLE001 - closing must not change filter decisions
                logger.warning("Failed to close Jev Scenario filter: %s", exc)

        report = {
            "backend": "jev_noul",
            "irrelevance_threshold": threshold,
            "recalled_scenario_count": len(scenarios),
            "passed_scenario_ids": [scenario.scenario_id for scenario in passed],
            "skipped_scenario_ids": skipped_ids,
            "decisions": decisions,
        }
        if warnings:
            report["warning"] = " ".join(warnings)
        return passed, report

    async def _score_rules_with_jev(
        self,
        task_context: str,
        rules: list[StoredRule],
        config: Any,
        *,
        exception_veto_threshold: float,
    ) -> list[float]:
        inputs = [
            RuleJevInput(
                name=rule.record.name,
                content=rule.record.content,
                applies_when=_meaningful_applicability_clause(rule.record.applies_when),
                exception=_meaningful_applicability_clause(rule.record.exception),
            )
            for rule in rules
        ]
        client = _rs_dep("RuleJevClient", RuleJevClient).from_config(config)
        if client is None:
            raise RuntimeError("Rule Jev judge is unavailable")
        try:
            scores = await asyncio.to_thread(client.judge_rules, task_context, inputs)
        finally:
            client.close()
        if scores is None or len(scores) != len(rules):
            raise ValueError("Rule Jev returned incomplete scores")
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
            for score in scores
            for value in (score.applies_when, score.exception)
        ):
            raise ValueError("Rule Jev returned invalid probabilities")

        vetoed_indices = frozenset(
            index
            for index, (rule, score) in enumerate(zip(inputs, scores, strict=True))
            if rule.exception
            # A zero probability is evidence that the exception does not apply,
            # including when the caller selects a zero retrieval threshold.
            and score.exception > 0.0
            and score.exception >= exception_veto_threshold
            and (not rule.applies_when or score.exception > score.applies_when)
        )
        return _RuleScores(
            [
                0.0 if index in vetoed_indices else score.applies_when
                for index, score in enumerate(scores)
            ],
            vetoed_indices,
        )

    async def _score_rules(
        self,
        task_context: str,
        rules: list[StoredRule],
        *,
        rule_probability_threshold: float = DEFAULT_RULE_PROBABILITY_THRESHOLD,
    ) -> tuple[list[float], str, str | None]:
        config = self._rules_config.jev_rule_matcher if self._rules_config is not None else None
        if config is not None:
            try:
                scores = await self._score_rules_with_jev(
                    task_context,
                    rules,
                    config,
                    exception_veto_threshold=rule_probability_threshold,
                )
            except Exception as exc:  # noqa: BLE001 - an unavailable judge must pass
                logger.warning("Jev rule matcher unavailable: %s", exc)
            else:
                return scores, "jev_noul", None

        return (
            [1.0] * len(rules),
            "pass",
            "Jev Noul was unavailable; all candidate Rules were passed without judgment.",
        )
