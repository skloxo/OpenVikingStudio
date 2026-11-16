# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Connector delegation for resource imports.

ResourceService hands an add_resource request to :class:`ConnectorDelegate`
when the source belongs to the external Connector integration; the native
service keeps only that hand-off. This module owns the whole delegation
lifecycle:

- the routing decision (:meth:`ConnectorDelegate.should_delegate`): a
  three-state verdict — delegate, degrade to the standard pipeline, or raise;
- payload construction and queue publication (:meth:`ConnectorDelegate.create`);
- synchronous submission followed by durable monitoring in the ExternalTask queue.
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import replace
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Set, Tuple
from urllib.parse import urlsplit

import httpx

from openviking.connector.auth import (
    OAUTH_REF_ARG,
    confluence_auth_config,
    document_auth_config,
    extract_credential_reference,
    project_auth_config,
    resolve_connector_auth_config,
)
from openviking.connector.client import ConnectorClient
from openviking.connector.routing import (
    CONNECTOR_ARGS_AUTH_CONFIG_KEY,
    CONNECTOR_CREDENTIAL_ARGS,
    CONNECTOR_SUPPORTED_ARGS,
    credential_arg_names,
    detect_connector_add_type,
    is_full_commit_sha,
)
from openviking.core.namespace import NamespaceShapeError
from openviking.core.uri_validation import matches_content_kind
from openviking.crypto.encryptor import MAGIC as ENCRYPTED_ENVELOPE_MAGIC
from openviking.crypto.encryptor import build_credential_encryptor
from openviking.metrics.datasources.resource import ResourceIngestionEventDataSource
from openviking.observability.http_error_context import (
    sanitize_public_error_details,
    sanitize_public_http_error,
)
from openviking.parse.mode import ParseMode
from openviking.resource.processing_mode import (
    DEFAULT_PROCESSING_MODE,
    VECTORS_ONLY,
    ProcessingMode,
)
from openviking.server.identity import RequestContext
from openviking.service.external_task_service import (
    ExternalTaskCancellation,
    ExternalTaskError,
    ExternalTaskSnapshot,
    get_external_task_service,
)
from openviking.service.task_domain import TaskPatch
from openviking.service.task_tracker import TaskRecord, TaskStatus, get_task_tracker
from openviking.service.task_tracker_concurrency import run_to_completion
from openviking.storage.acl import AclUpdate
from openviking.utils.tags import normalize_search_tags
from openviking_cli.exceptions import InternalError, InvalidArgumentError
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.utils import get_logger
from openviking_cli.utils.config.open_viking_config import get_openviking_config

logger = get_logger(__name__)

_TOS_BUCKET_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")
CONNECTOR_DISPLAY_RESOURCE_CONFIG_ARG = "resource_config"
from openviking.connector.delegate_helpers import _is_resource_target, _safe_http_response, _validate_tos_uri


class _ConnectorProviderMixin:

    @property
    def poll_interval_seconds(self) -> float:
        return get_openviking_config().connector.poll_interval_ms / 1000.0

    def serialization_key(self, payload: Mapping[str, Any]) -> None:
        return None

    @staticmethod
    def submission_meta(external_task_id: str) -> Dict[str, Any]:
        return {"connector_task_key": external_task_id}

    @staticmethod
    def _client(account_id: str) -> ConnectorClient:
        config = get_openviking_config().connector
        return ConnectorClient(
            doc_add_url=config.connector, task_info_url=config.tracker, account_id=account_id
        )

    @staticmethod
    def _timeout(payload: Mapping[str, Any]) -> ExternalTaskSnapshot:
        return ExternalTaskSnapshot(
            status="failed",
            error_code="DEADLINE_EXCEEDED",
            error_message=f"connector task timed out after {payload['timeout_seconds']}s",
        )

    async def on_start(self, task: TaskRecord) -> ExternalTaskSnapshot | None:
        if task.auth.get("external_terminal_snapshot") is not None:
            return None
        return None

    async def submit(
        self,
        ov_task_id: str,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        connection: Mapping[str, Any],
    ) -> str:
        """Submit an import; the caller persists the returned key before monitoring."""
        request = {
            **payload["submit"],
            "api_key": private_payload["api_key"],
            "auth_config": private_payload.get("auth_config") or None,
        }
        safe_request = {**request, "api_key": "[REDACTED]"}
        if safe_request["auth_config"] is not None:
            safe_request["auth_config"] = "[REDACTED]"
        logger.info(
            "[ConnectorDelegate] Connector task add request: ov_task_id=%s request=%s",
            ov_task_id,
            sanitize_public_error_details(safe_request),
        )
        try:
            result = await self._client(connection["account_id"]).submit_doc_add(**request)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[ConnectorDelegate] Connector task add response: ov_task_id=%s status=%s "
                "response=%s",
                ov_task_id,
                exc.response.status_code,
                _safe_http_response(exc.response),
            )
            raise ExternalTaskError(
                "CONNECTOR_SUBMISSION_FAILED",
                sanitize_public_http_error(code="CONNECTOR_SUBMISSION_FAILED", message=exc).message,
                transient=exc.response.status_code in {408, 429} or exc.response.status_code >= 500,
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalTaskError(
                "CONNECTOR_SUBMISSION_FAILED",
                "Connector submission transport failed",
                transient=True,
            ) from exc
        logger.info(
            "[ConnectorDelegate] Connector task add response: ov_task_id=%s response=%s",
            ov_task_id,
            sanitize_public_error_details(result),
        )
        key = result.get("task_key") or result.get("TaskKey")
        if not isinstance(key, str) or not key.strip():
            raise ExternalTaskError(
                "INVALID_RESPONSE",
                "Connector accepted the import but returned no task key",
                transient=False,
            )
        ResourceIngestionEventDataSource.record_import(
            pipeline="connector",
            source_type="repository" if request["add_type"] == "git" else "document",
            account_id=connection["account_id"],
        )
        return key.strip()

    async def get(
        self,
        external_task_id: str,
        connection: Mapping[str, Any],
        *,
        payload: Mapping[str, Any] | None = None,
        private_payload: Mapping[str, Any] | None = None,
    ) -> ExternalTaskSnapshot:
        assert payload is not None and private_payload is not None

        def active(status: str, *, stage: str | None = None) -> ExternalTaskSnapshot:
            if time.time() >= payload["deadline"]:
                return self._timeout(payload)
            return ExternalTaskSnapshot(status=status, stage=stage)

        try:
            info = await self._client(connection["account_id"]).get_task_info(
                external_task_id, private_payload["api_key"]
            )
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            retrying = code in {408, 429} or code >= 500
            logger.warning(
                "[ConnectorDelegate] Connector task info error response: "
                "connector_task_key=%s status=%s response=%s retrying=%s",
                external_task_id,
                code,
                _safe_http_response(exc.response),
                retrying,
            )
            if retrying:
                return active("running")
            raise ExternalTaskError(
                "CONNECTOR_POLL_FAILED", "connector task monitoring failed", transient=False
            ) from exc
        except httpx.RequestError:
            return active("running")
        status = str(info.get("Status") or info.get("status") or "").lower()
        if status in {"pending", "running"}:
            return active(status, stage=f"connector:{status}")
        if status == "succeeded":
            result: Dict[str, Any] = {
                "connector_status": status,
                "connector_task_key": external_task_id,
            }
            states = info.get("StreamStates")
            if states is None:
                states = info.get("stream_states")
            if states is not None:
                if not isinstance(states, dict):
                    raise ExternalTaskError(
                        "INVALID_RESPONSE",
                        "Connector task response contains invalid stream states",
                        transient=False,
                    )
                result["connector_states"] = states
            return ExternalTaskSnapshot(
                status="completed", stage="connector:succeeded", result=result
            )
        if status in {"failed", "cancelled"}:
            error = sanitize_public_http_error(
                code="CONNECTOR_TASK_FAILED",
                message=info.get("ErrorMessage") or info.get("error_message") or status,
            ).message
            return ExternalTaskSnapshot(
                status=status,
                stage=f"connector:{status}",
                error_code="CONNECTOR_TASK_FAILED",
                error_message=f"connector task {status}: {error}",
            )
        raise ExternalTaskError(
            "INVALID_RESPONSE", f"Unknown Connector task status: {status}", transient=False
        )

    async def on_finish(
        self, task: TaskRecord, snapshot: ExternalTaskSnapshot
    ) -> ExternalTaskSnapshot:
        """Apply resource effects before the framework records the outcome."""
        if task.status == TaskStatus.CANCELLING and snapshot.status == "completed":
            # Cancellation may be persisted before this worker receives its notification.
            return ExternalTaskSnapshot(status="cancelled")
        request = task.meta["request"]
        assert task.account_id is not None and task.user_id is not None
        private = task.auth["external_request_private"]
        identity = request["identity"]
        ctx = RequestContext(
            user=UserIdentifier(task.account_id, task.user_id),
            role=identity["role"],
            group_ids=tuple(identity["group_ids"]),
            actor_peer_id=identity["actor_peer_id"],
            bypass_acl=identity["bypass_acl"],
            api_key=private["api_key"],
        )
        result = dict(snapshot.result or {})
        if snapshot.status == "completed":
            if request["acl_update"] is not None:
                update = AclUpdate.model_validate(request["acl_update"])
                await self._viking_fs.set_acl(
                    update.uri, update.acl.entries, ctx=ctx, acl_mode=update.acl.acl_mode
                )
            if request["reason"].strip() and self._resource_memory_link_service is not None:
                linked = task.meta.get("connector_reason_result")
                if linked is None:
                    try:
                        linked = {
                            "memory_linking": await self._resource_memory_link_service.on_resource_added(
                                ctx=ctx,
                                resource_uri=task.resource_id,
                                reason=request["reason"],
                                source_name=None,
                            )
                        }
                    except Exception as exc:
                        linked = {"warnings": [f"Memory linking failed: {exc}"]}
                    await get_task_tracker().patch_task(
                        task.task_id,
                        TaskPatch(meta={"connector_reason_result": linked}),
                        account_id=task.account_id,
                        user_id=task.user_id,
                    )
                result.update(linked)
        return replace(snapshot, result=result)

    async def on_cancel(
        self,
        task: TaskRecord,
        *,
        external_task_id: str | None,
        payload: Mapping[str, Any],
        private_payload: Mapping[str, Any],
        connection: Mapping[str, Any],
        failure: Exception | None,
    ) -> ExternalTaskCancellation:
        """Stop local monitoring; Connector currently has no remote cancellation API."""
        snapshot = (
            ExternalTaskSnapshot(
                status="failed",
                error_code=getattr(failure, "code", None) or "INTERNAL",
                error_message=sanitize_public_http_error(
                    code="CONNECTOR_TASK_FAILED",
                    message=str(failure) or type(failure).__name__,
                ).message,
            )
            if failure is not None
            else ExternalTaskSnapshot(status="cancelled")
        )
        return ExternalTaskCancellation(external_task_id, snapshot)
