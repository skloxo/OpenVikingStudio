# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Compile API models and external task provider."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Mapping

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from openviking.core.namespace import classify_uri, uri_parts
from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.identity import RequestContext
from openviking.service.compile_targets import CompileLifecycle, UpdateSchedule, split_control_args
from openviking.service.external_task_service import (
    ExternalTaskCancellation,
    ExternalTaskError,
    ExternalTaskRetryExhaustedError,
    ExternalTaskService,
    ExternalTaskSnapshot,
)
from openviking.service.fs_service import FSService
from openviking.service.memory_compile import MemoryCompileRunner
from openviking.service.task_tracker import SENSITIVE_TASK_KEYS, TaskRecord
from openviking.session.memory.utils.memory_fields import strip_memory_fields_trailer
from openviking.storage.acl import AclAction
from openviking_cli.exceptions import (
    ConflictError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
    UnavailableError,
)
from openviking_cli.utils.config.open_viking_config import CompileApiConfig
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_ACTIVE_STATUSES = frozenset({"accepted", "pending", "running", "committing"})
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

# Sentinel --skill value that routes a Compile request to in-process memory
# consolidation instead of the VikingBot agent path. It is not a real Skill URI.
MEMORY_COMPILE_SKILL = "memory"


class CompileConfigUpdate(BaseModel):
    """Whole update settings for one Compile target (POST /compile/config/update)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    to: str = Field(min_length=1)
    from_: list[str] = Field(alias="from", min_length=1)
    skill: str = Field(min_length=1)
    instruction: str | None = None
    auto_update: bool
    update_schedule: UpdateSchedule | None = None

    @property
    def instruction_sent(self) -> bool:
        return "instruction" in self.model_fields_set


class CompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: list[str] = Field(default_factory=list, alias="from")
    to: str = Field(min_length=1)
    skill: str = Field(min_length=1)
    instruction: str | None = None
    args: dict[str, Any] | None = None
    # Explicit instruction/reason updates the saved instruction only when the
    # request also configures scheduling; ordinary manual instructions are per-run.
    _instruction_sent: bool = PrivateAttr(default=False)

    @property
    def is_memory_mode(self) -> bool:
        return self.skill == MEMORY_COMPILE_SKILL

    @model_validator(mode="before")
    @classmethod
    def _accept_reason(cls, data: Any) -> Any:
        if isinstance(data, dict) and "reason" in data:
            data = dict(data)
            data.setdefault("instruction", data.pop("reason"))
        return data

    @model_validator(mode="wrap")
    @classmethod
    def _track_instruction(cls, data: Any, handler: Any) -> "CompileRequest":
        model = handler(data)
        if isinstance(data, dict):
            model._instruction_sent = "instruction" in data or "reason" in data
        return model

    @model_validator(mode="after")
    def _normalize(self) -> "CompileRequest":
        sources: list[str] = []
        for source in self.from_:
            normalized = source.strip().rstrip("/")
            if not normalized:
                raise ValueError("from must not contain empty values")
            if normalized not in sources:
                sources.append(normalized)
        self.from_ = sources
        self.to = self.to.strip().rstrip("/")
        self.skill = self.skill.strip().rstrip("/")
        self.instruction = (
            self.instruction.strip() if self.instruction and self.instruction.strip() else None
        )
        self.args = dict(self.args) if self.args else None
        if not self.to:
            raise ValueError("to must not be empty")
        if not self.skill:
            raise ValueError("skill must not be empty")
        # Memory mode consolidates the --to space in place and takes no sources;
        # every other skill still requires at least one --from directory.
        if not self.is_memory_mode and not self.from_:
            raise ValueError("from must contain at least one directory")
        if self.is_memory_mode and self.from_:
            raise ValueError("--skill memory consolidates --to in place and takes no --from")
        return self


class CompileErrorInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    message: str


class CompileSessionAccepted(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str


class CompileSessionStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str | None = None
    stage: str
    error: CompileErrorInfo | str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None


@dataclass(frozen=True)
class _CompileEndpoint:
    base_url: str
    gateway_token: str
    http_timeout_seconds: float
    poll_interval_ms: int
    local: bool = False


class CompileAPIClient:
    """Client for submitting Compile tasks through the Runtime API."""

    def __init__(self, endpoint: _CompileEndpoint) -> None:
        self._endpoint = endpoint

    def _headers(
        self,
        connection: Mapping[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, str]:
        """Build Runtime headers from saved identity, optional request ID, and retry key."""
        headers = {
            "Content-Type": "application/json",
        }
        if self._endpoint.gateway_token:
            headers["X-Gateway-Token"] = self._endpoint.gateway_token
        for field, header in (
            ("api_key", "X-API-Key"),
            ("account_id", "X-OpenViking-Account"),
            ("user_id", "X-OpenViking-User"),
            ("actor_peer_id", "X-OpenViking-Actor-Peer"),
        ):
            value = str(connection.get(field) or "").strip()
            if value:
                headers[header] = value
        request_id = connection.get("request_id")
        if request_id:
            headers["X-Tt-Logid"] = request_id
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def create(
        self,
        payload: Mapping[str, Any],
        *,
        connection: Mapping[str, Any],
        idempotency_key: str,
    ) -> CompileSessionAccepted:
        response = await self._request(
            "POST",
            "/runtime/v1/tasks",
            json=payload,
            headers=self._headers(connection, idempotency_key=idempotency_key),
        )
        return self._validate(CompileSessionAccepted, response)

    async def get(
        self,
        session_id: str,
        *,
        connection: Mapping[str, Any],
        args: Mapping[str, Any] | None = None,
    ) -> CompileSessionStatus:
        """Query a session with its original args; omit args for legacy tasks."""
        body = await self._request(
            "POST",
            "/runtime/v1/tasks/status",
            json={"session_id": session_id, **({"args": dict(args)} if args is not None else {})},
            headers=self._headers(connection),
        )
        return self._validate(CompileSessionStatus, body)

    async def cancel(
        self,
        session_id: str,
        *,
        connection: Mapping[str, Any],
        args: Mapping[str, Any] | None = None,
    ) -> CompileSessionStatus:
        """Cancel a session with its original args; omit args for legacy tasks."""
        body = await self._request(
            "POST",
            "/runtime/v1/tasks/cancel",
            json={"session_id": session_id, **({"args": dict(args)} if args is not None else {})},
            headers=self._headers(connection),
        )
        return self._validate(CompileSessionStatus, body)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
    ) -> Any:
        try:
            async with httpx.AsyncClient(
                timeout=self._endpoint.http_timeout_seconds,
                trust_env=not self._endpoint.local,
                follow_redirects=False,
            ) as client:
                response = await client.request(
                    method,
                    f"{self._endpoint.base_url}{path}",
                    headers=dict(headers),
                    json=dict(json),
                )
        except httpx.RequestError as exc:
            reason = str(exc).strip() or type(exc).__name__
            message = f"Failed to reach the compile kernel service: {reason}"
            raise ExternalTaskError("UNAVAILABLE", message, transient=True) from exc

        try:
            body = response.json()
        except ValueError as exc:
            if not response.is_success:
                raise ExternalTaskError(
                    "UNAVAILABLE" if response.status_code >= 500 else "INVALID_ARGUMENT",
                    "Compile API request failed",
                    transient=response.status_code in {408, 425, 429}
                    or response.status_code >= 500,
                ) from exc
            raise ExternalTaskError(
                "INVALID_RESPONSE",
                "Compile API returned a non-JSON response",
                transient=False,
            ) from exc
        if response.is_success:
            return body

        detail = body.get("detail") if isinstance(body, dict) else None
        error = body.get("error") if isinstance(body, dict) else None
        source = detail if isinstance(detail, dict) else error if isinstance(error, dict) else {}
        default_code = "UNAVAILABLE" if response.status_code >= 500 else "INVALID_ARGUMENT"
        code = str(source.get("code") or default_code)
        message = str(source.get("message") or detail or error or "Compile API request failed")
        raise ExternalTaskError(
            code,
            message,
            transient=response.status_code in {408, 425, 429} or response.status_code >= 500,
        )

    @staticmethod
    def _validate(model: type[BaseModel], body: Any) -> Any:
        try:
            return model.model_validate(body)
        except ValidationError as exc:
            raise ExternalTaskError(
                "INVALID_RESPONSE",
                f"Compile API returned an invalid response: {exc}",
                transient=False,
            ) from exc

