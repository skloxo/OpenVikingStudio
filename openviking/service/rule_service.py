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
from openviking.service.rule_apply import _RuleApplyMixin
from openviking.service.rule_compiler import _RuleCompilerMixin
from openviking.service.rule_models import (
    RULE_SCHEMA,
    SCENARIO_SCHEMA,
    RuleCarriedOver,
    RuleCompilePlan,
    RuleCompileRequest,
    RuleDroppedRequirement,
    RuleMutation,
    RuleRecord,
    RuleResourceReference,
    RuleScenarioRef,
    RuleSearchRequest,
    StoredRule,
    StoredScenario,
    _build_material_batches,
    _render_markdown,
)
from openviking.service.rule_prompts import _RulePromptsMixin
from openviking.service.rule_render import _render_rule_block, _render_rules
from openviking.service.rule_search import _RuleSearchMixin
from openviking.service.rule_storage import _RuleStorageMixin


class RuleService(
    _RuleStorageMixin,
    _RuleCompilerMixin,
    _RulePromptsMixin,
    _RuleApplyMixin,
    _RuleSearchMixin,
):
    """Compile durable rules and retrieve applicable complete rule documents."""

    task_type = "rule_compile"
    task_id_prefix = "rul_"

    def __init__(self) -> None:
        self._fs: FSService | None = None
        self._resources: ResourceService | None = None
        self._search: SearchService | None = None
        self._vlm_resolver: Any = None
        self._rules_config: Any = None
        self._config: Any = None
        self._running: set[asyncio.Task[None]] = set()
        self._compile_locks: dict[tuple[str, str], asyncio.Lock] = {}

    def set_dependencies(
        self,
        *,
        fs: FSService,
        resources: ResourceService,
        search: SearchService,
        vlm_resolver: Any,
        rules_config: Any = None,
        config: Any = None,
    ) -> None:
        self._fs = fs
        self._resources = resources
        self._search = search
        self._vlm_resolver = vlm_resolver
        self._rules_config = rules_config
        self._config = config

    def _dependencies(self) -> tuple[FSService, ResourceService, SearchService]:
        if self._fs is None or self._resources is None or self._search is None:
            raise UnavailableError("rule service", "service dependencies are not initialized")
        return self._fs, self._resources, self._search
