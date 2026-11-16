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


def _safe_http_response(response: httpx.Response) -> Any:
    """Return a bounded, credential-redacted response body for logs."""
    try:
        payload = response.json()
    except (TypeError, ValueError):
        payload = response.text
    if isinstance(payload, dict):
        return sanitize_public_error_details(payload)
    return sanitize_public_http_error(code="CONNECTOR_HTTP_ERROR", message=payload).message


def _validate_tos_uri(
    value: Any,
    field: str,
    *,
    allow_bucket_without_slash: bool = False,
) -> None:
    """Validate a Connector TOS URI without exposing it in client errors."""
    error = InvalidArgumentError(f"{field} must be a valid TOS URI.")
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not value.startswith("tos://")
        or any(char in "?#%" or ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    ):
        raise error

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise error from None
    if (
        parsed.scheme != "tos"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or not hostname
        or hostname != parsed.netloc
        or not _TOS_BUCKET_PATTERN.fullmatch(hostname)
        or (not parsed.path and not allow_bucket_without_slash)
        or (parsed.path and not parsed.path.startswith("/"))
        or parsed.path.startswith("//")
        or parsed.query
        or parsed.fragment
    ):
        raise error


def _is_resource_target(to: str) -> bool:
    """True when *to* lies in a resources tree: the public root or a user's own."""
    try:
        return matches_content_kind(to, "resource")
    except (ValueError, NamespaceShapeError):
        return False



class _ConnectorEnqueueMixin:

    async def _enqueue(
        self,
        path: str,
        ctx: RequestContext,
        to: Optional[str],
        reason: str = "",
        declared_add_type: Optional[str] = None,
        connector_args: Optional[Dict[str, Any]] = None,
        connector_auth_config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        tag_mode: str = "replace",
        connector_states: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        on_task_created: Optional[Callable[[TaskRecord], Awaitable[None]]] = None,
        acl_update: Optional[AclUpdate] = None,
        **kwargs: Any,
    ) -> TaskRecord:
        """Persist the request and submit before publishing its monitoring Work."""
        config = get_openviking_config().connector
        if not ctx.api_key:
            raise InvalidArgumentError("Connector import requires an API key in the request.")

        resolved = self.resolve_add_type(path, declared_add_type)
        if resolved is None:
            raise InvalidArgumentError(f"'{path}' does not match any Connector source type.")
        add_type, _ = resolved
        if add_type == "tos":
            _validate_tos_uri(path, "path", allow_bucket_without_slash=True)

        task_resource_id = to or ""
        if not task_resource_id:
            raise InvalidArgumentError("Connector import requires an exact 'to' target.")

        if not kwargs.get("create_parent", False):
            # Match the native pipeline default: unless create_parent=true is
            # given, the parent of the exact target must pre-exist.
            parent_uri, _, _ = task_resource_id.rpartition("/")
            if parent_uri.startswith("viking://") and not await self._viking_fs.exists(
                parent_uri, ctx
            ):
                raise InvalidArgumentError(
                    f"Parent directory '{parent_uri}' does not exist; "
                    "pass create_parent=true to create it."
                )

        # Credentials are separated into the dedicated auth_config field before
        # forwarding: Connector and plugin logs redact auth_config while logging
        # param_config verbatim. The incoming OpenViking HTTP body may still be
        # captured when the explicitly unsafe observability body dump is enabled.
        if add_type in CONNECTOR_SUPPORTED_ARGS:
            forwarded_args = {
                key: value
                for key, value in (connector_args or {}).items()
                if key in CONNECTOR_SUPPORTED_ARGS.get(add_type, frozenset()) and value
            }
            auth_config = {
                key: str(value)
                for key, value in (connector_args or {}).items()
                if key in CONNECTOR_CREDENTIAL_ARGS.get(add_type, frozenset()) and value
            }
        else:
            # Declared add_type outside the registry: the plugin owns the args
            # semantics, so they travel wholesale through param_config. The
            # caller supplies credentials under the reserved args.auth_config
            # key, lifted into the top-level auth_config field.
            display_only_args = {
                CONNECTOR_ARGS_AUTH_CONFIG_KEY,
                CONNECTOR_DISPLAY_RESOURCE_CONFIG_ARG,
            }
            forwarded_args = {
                key: value
                for key, value in (connector_args or {}).items()
                if key not in display_only_args and value is not None
            }
            declared_auth = (connector_args or {}).get(CONNECTOR_ARGS_AUTH_CONFIG_KEY)
            if declared_auth is not None and not isinstance(declared_auth, dict):
                raise InvalidArgumentError(
                    "args.auth_config must be an object of credential fields."
                )
            auth_config = {
                str(key): str(value) for key, value in (declared_auth or {}).items() if value
            }

        if add_type in {"meego", "feishu_project"} and OAUTH_REF_ARG in (connector_args or {}):
            auth_config = await project_auth_config(connector_args or {}, ctx)
            forwarded_args.pop(OAUTH_REF_ARG, None)
        if add_type == "feishu_doc" and OAUTH_REF_ARG in (connector_args or {}):
            auth_config = await document_auth_config(connector_args or {}, ctx)
            forwarded_args.pop(OAUTH_REF_ARG, None)
        if add_type == "confluence" and OAUTH_REF_ARG in (connector_args or {}):
            auth_config = await confluence_auth_config(connector_args or {}, ctx)
            forwarded_args.pop(OAUTH_REF_ARG, None)

        # Imports carrying an OpenViking-managed credential reference resolve the
        # full auth_config through the unified resolver just before forwarding,
        # so a refreshed token is always current. This is platform-agnostic:
        # the kernel forwards whatever auth_config the resolver assembled for the
        # target Connector without inspecting its fields.
        credential_reference = extract_credential_reference(connector_auth_config)
        if credential_reference is not None:
            if add_type in CONNECTOR_SUPPORTED_ARGS:
                raise InvalidArgumentError(
                    f"add_type '{add_type}' does not accept a managed credential reference."
                )
            auth_config = await resolve_connector_auth_config(credential_reference, ctx)

        tos_path: Optional[str] = None
        param_config: Optional[Dict[str, Any]] = None
        if add_type == "tos":
            tos_args = connector_args or {}
            if "tos_prefix" not in tos_args:
                if "exclude" in tos_args:
                    raise InvalidArgumentError("args.exclude requires args.tos_prefix.")
                source_path = path[len("tos://") :].strip()
                if not source_path:
                    raise InvalidArgumentError(
                        "Connector TOS import requires path='tos://<bucket>/<path>'."
                    )
                tos_path = source_path
            else:
                tos_prefix = tos_args["tos_prefix"]
                if not isinstance(tos_prefix, list) or not tos_prefix:
                    raise InvalidArgumentError(
                        "args.tos_prefix must be a non-empty list of TOS URIs."
                    )
                for index, source in enumerate(tos_prefix):
                    _validate_tos_uri(source, f"args.tos_prefix[{index}]")
                if tos_prefix[0] != path:
                    raise InvalidArgumentError("path must equal the first item in args.tos_prefix.")
                exclude = tos_args.get("exclude", [])
                if not isinstance(exclude, list):
                    raise InvalidArgumentError("args.exclude must be a list of TOS URIs.")
                for index, source in enumerate(exclude):
                    _validate_tos_uri(source, f"args.exclude[{index}]")
                param_config = {"tos_prefix": tos_prefix}
                if exclude:
                    param_config["exclude"] = exclude
        elif add_type == "git":
            from openviking.parse.accessors.git_accessor import GitAccessor

            # Source-specific settings stay in param_config. The exact target
            # is transported separately as the top-level ``to`` field.
            repo_url, branch, commit = GitAccessor()._parse_repo_source(
                path.strip(), **forwarded_args
            )
            param_config = {"repo_url": repo_url}
            if commit:
                # Routing already degraded abbreviated SHAs to the standard
                # pipeline. Preserve the native accessor's historical precedence:
                # when both commit and branch/ref are present, send only the full
                # commit SHA so the plugin receives an unambiguous pinned request.
                param_config["commit"] = str(commit)
            elif branch:
                param_config["branch"] = str(branch)
        else:
            # Declared add_type outside the registry: the plugin owns the
            # source semantics. The top-level path travels under the agreed
            # param_config["path"] key -- args can never carry "path", it is
            # a reserved core add_resource field.
            param_config = dict(forwarded_args)
            param_config["path"] = path

        extra_params: Optional[Dict[str, Any]] = None
        if tag_mode == "clear":
            extra_params = {"tag_mode": tag_mode}
        elif tags is not None:
            normalized_tags = normalize_search_tags(tags)
            if normalized_tags:
                extra_params = {
                    "tags": normalized_tags,
                    "tag_mode": tag_mode,
                }

        submit_kwargs: Dict[str, Any] = {
            "add_type": add_type,
            "tos_path": tos_path,
            "to": task_resource_id,
            "include_child": True,
            "param_config": param_config,
            "extra_params": extra_params,
        }
        if connector_states is not None:
            submit_kwargs["stream_states"] = connector_states
        payload = {
            "submit": submit_kwargs,
            "reason": reason,
            "acl_update": (
                acl_update.model_dump(mode="json", exclude_none=True)
                if acl_update is not None
                else None
            ),
            "identity": {
                "role": str(ctx.role),
                "group_ids": list(ctx.group_ids),
                "actor_peer_id": ctx.actor_peer_id,
                "bypass_acl": ctx.bypass_acl,
            },
            "deadline": None,
            "timeout_seconds": config.timeout_seconds,
        }
        private_payload = {"api_key": ctx.api_key, "auth_config": auth_config}

        async def submit_before_enqueue(task: TaskRecord) -> None:
            # Register the Watch/run before Connector can call back into OV.
            if on_task_created is not None:
                await on_task_created(task)
            if task.meta.get("connector_task_key"):
                return
            tracker = get_task_tracker()
            owner = {"account_id": task.account_id, "user_id": task.user_id}
            try:
                await tracker.start(task.task_id, stage="submitting", **owner)
                current = await tracker.get(task.task_id, **owner)
                if (
                    current is None
                    or current.is_terminal()
                    or current.status == TaskStatus.CANCELLING
                    or current.error
                ):
                    raise InternalError("Connector Task ended before submission")
                key = await self.submit(
                    task.task_id, payload, private_payload, {"account_id": ctx.account_id}
                )
                request = {**payload, "deadline": time.time() + config.timeout_seconds}
                patched = await tracker.patch_task(
                    task.task_id,
                    TaskPatch(
                        auth={"external_task_id": key},
                        meta={**self.submission_meta(key), "request": request},
                    ),
                    **owner,
                )
                if not patched.is_applied:
                    raise InternalError("Connector Task ended before submission was persisted")
            except BaseException as exc:
                await tracker.fail(
                    task.task_id,
                    sanitize_public_http_error(
                        code="CONNECTOR_SUBMISSION_FAILED",
                        message=str(exc) or "connector task submission cancelled",
                    ).message,
                    **owner,
                )
                raise

        return await get_external_task_service().create(
            self.task_type,
            resource_id=task_resource_id,
            payload=payload,
            private_payload=private_payload,
            ctx=ctx,
            task_id=task_id,
            on_task_created=submit_before_enqueue,
        )
