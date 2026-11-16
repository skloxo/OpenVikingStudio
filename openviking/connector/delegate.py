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
from openviking.connector.delegate_helpers import _ConnectorEnqueueMixin, _is_resource_target, _safe_http_response, _validate_tos_uri
from openviking.connector.delegate_provider import _ConnectorProviderMixin


class ConnectorDelegate(_ConnectorEnqueueMixin, _ConnectorProviderMixin):
    """Delegate supported imports to an external Connector service."""

    task_type = "connector_import"
    task_id_prefix = ""
    poll_max_attempts = 3
    _WATCH_AUTH_PROVIDER = "connector_encrypted"
    _WATCH_PLAINTEXT_AUTH_PROVIDER = "connector_plaintext"

    def __init__(
        self,
        *,
        viking_fs: Any,
        resource_memory_link_service: Any = None,
    ) -> None:
        self._viking_fs = viking_fs
        self._resource_memory_link_service = resource_memory_link_service
        self._watch_credential_encryptor: Any = None

    def _watch_encryptor(self) -> Any:
        encryptor = getattr(self._viking_fs, "_encryptor", None)
        if encryptor is None:
            if self._watch_credential_encryptor is None:
                self._watch_credential_encryptor = build_credential_encryptor(
                    get_openviking_config().encryption
                )
            encryptor = self._watch_credential_encryptor
        return encryptor

    async def create_watch_auth_state(
        self,
        *,
        api_key: str,
        account_id: str,
        add_type: str,
        path: str,
        connector_args: Optional[Dict[str, Any]],
        connector_auth_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the private request state needed to replay a Connector watch."""
        if not api_key:
            raise InvalidArgumentError("Connector watch requires an API key.")
        payload = {
            "api_key": api_key,
            "account_id": account_id,
            "add_type": add_type,
            "path": path,
            "connector_args": dict(connector_args or {}),
        }
        # Watches persist only the secret-free credential reference; the actual
        # auth_config is resolved anew each round so refreshed tokens stay current.
        if connector_auth_config:
            payload["connector_auth_config"] = dict(connector_auth_config)
        try:
            plaintext = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            ciphertext = await self._watch_encryptor().encrypt(account_id, plaintext)
        except InvalidArgumentError:
            raise
        except Exception as exc:
            raise InvalidArgumentError("Failed to encrypt Connector watch credentials.") from exc
        return {
            "provider": self._WATCH_AUTH_PROVIDER,
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

    @classmethod
    def is_watch_auth_state(cls, auth_state: Optional[Dict[str, Any]]) -> bool:
        return isinstance(auth_state, dict) and auth_state.get("provider") in {
            cls._WATCH_AUTH_PROVIDER,
            cls._WATCH_PLAINTEXT_AUTH_PROVIDER,
        }

    async def restore_watch_request(
        self,
        auth_state: Dict[str, Any],
        *,
        account_id: str,
        path: str,
    ) -> Tuple[str, str, Dict[str, Any], Optional[Dict[str, Any]]]:
        """Restore and validate a source-bound Connector watch request.

        Returns ``(api_key, add_type, connector_args, connector_auth_config)``;
        ``connector_auth_config`` is the secret-free credential reference and is
        None for watches that predate it or use the legacy args channel.
        """
        try:
            provider = auth_state.get("provider")
            if provider == self._WATCH_PLAINTEXT_AUTH_PROVIDER:
                payload = auth_state.get("request")
            elif provider == self._WATCH_AUTH_PROVIDER:
                encoded = auth_state.get("ciphertext")
                if not isinstance(encoded, str) or not encoded:
                    raise ValueError("missing ciphertext")
                ciphertext = base64.b64decode(encoded, validate=True)
                if not ciphertext.startswith(ENCRYPTED_ENVELOPE_MAGIC):
                    raise ValueError("invalid encrypted envelope")
                plaintext = await self._watch_encryptor().decrypt(account_id, ciphertext)
                payload = json.loads(plaintext.decode("utf-8"))
            else:
                raise ValueError("unknown Connector watch provider")
            if (
                not isinstance(payload, dict)
                or payload.get("account_id") != account_id
                or payload.get("path") != path
            ):
                raise ValueError("watch binding mismatch")
            api_key = payload.get("api_key")
            add_type = payload.get("add_type")
            connector_args = payload.get("connector_args")
            connector_auth_config = payload.get("connector_auth_config")
            if (
                not isinstance(api_key, str)
                or not api_key
                or not isinstance(add_type, str)
                or not add_type
                or not isinstance(connector_args, dict)
                or (
                    connector_auth_config is not None
                    and not isinstance(connector_auth_config, dict)
                )
            ):
                raise ValueError("invalid watch request")
            return (
                api_key,
                add_type,
                dict(connector_args),
                dict(connector_auth_config) if connector_auth_config else None,
            )
        except InvalidArgumentError:
            raise
        except Exception as exc:
            raise InvalidArgumentError("Stored Connector watch credentials are invalid.") from exc

    @staticmethod
    def resolve_add_type(path: str, declared_add_type: Optional[str]) -> Optional[Tuple[str, bool]]:
        """Resolve the Connector ``(add_type, connector_only)`` for *path*.

        Probes the path when no add_type is declared. A declared add_type is
        validated against the probe: registry types (tos/git) must match it
        exactly, and other types must not claim a path that probes as a
        registry type. A declared request is an explicit routing instruction,
        so it is always connector-only: it never degrades to the standard
        pipeline.
        """
        detected = detect_connector_add_type(path)
        if declared_add_type is None:
            return detected
        probed = detected[0] if detected else None
        if declared_add_type in CONNECTOR_SUPPORTED_ARGS:
            if probed != declared_add_type:
                raise InvalidArgumentError(
                    f"add_type '{declared_add_type}' does not match the source path"
                    + (f", which is a '{probed}' source" if probed else "")
                    + "."
                )
        elif probed is not None:
            raise InvalidArgumentError(
                f"add_type '{declared_add_type}' does not match the source path, "
                f"which is a '{probed}' source."
            )
        return (declared_add_type, True)

    @classmethod
    def supported_args(cls, path: str, declared_add_type: Optional[str]) -> Set[str]:
        """Connector-owned ``args`` fields for the resolved source type."""
        resolved = cls.resolve_add_type(path, declared_add_type)
        if resolved is None:
            return set()
        return set(CONNECTOR_SUPPORTED_ARGS.get(resolved[0], frozenset()))

    def should_delegate(
        self,
        path: str,
        *,
        ctx: Optional[RequestContext] = None,
        declared_add_type: Optional[str] = None,
        to: Optional[str] = None,
        parent: Optional[str] = None,
        wait: bool = False,
        instruction: str = "",
        build_index: bool = True,
        summarize: bool = False,
        processing_mode: ProcessingMode = DEFAULT_PROCESSING_MODE,
        parse_mode: ParseMode = ParseMode.DEFAULT,
        watch_interval: float = 0,
        connector_args: Optional[Dict[str, Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Decide whether a top-level resource path belongs to Connector.

        Returns True to delegate to the Connector, False to route to the
        standard pipeline. Source types are detected the same way the
        standard pipeline routes them (see connector.routing), not by raw
        URL scheme. A source type only the Connector can import (tos)
        raises InvalidArgumentError when the Connector is disabled, does
        not allow the type, or cannot honor the request parameters —
        degrading such a request would only fail later with a misleading
        parse error. Source types the standard pipeline can also handle
        degrade to it instead when parameters are unsupported, unless the
        request carries Connector-only credentials; credentialed requests
        fail closed so secrets never enter a durable native job.
        """
        from openviking_cli.utils.config.open_viking_config import get_openviking_config

        resolved = self.resolve_add_type(path, declared_add_type)
        if resolved is None:
            return False
        add_type, connector_only = resolved
        connector_args = connector_args or {}
        credential_args = credential_arg_names(add_type, connector_args)

        config = get_openviking_config().connector
        if not config.enable or add_type not in config.allowed_add_types:
            if declared_add_type is not None:
                raise InvalidArgumentError(
                    f"add_type '{add_type}' requires the Connector integration, "
                    "which is disabled or does not allow this source type."
                )
            if credential_args:
                raise InvalidArgumentError(
                    f"Credential args {credential_args} for '{add_type}' require Connector "
                    "import, but the Connector is disabled or does not allow this source type."
                )
            if connector_only:
                raise InvalidArgumentError(
                    f"'{path}' can only be imported through the Connector integration, "
                    "which is disabled or does not allow this source type."
                )
            return False

        if add_type == "git":
            from openviking.parse.accessors.git_accessor import GitAccessor

            _, _, commit = GitAccessor()._parse_repo_source(path, **connector_args)
            if commit and not is_full_commit_sha(str(commit)):
                # The plugin fetches pinned commits by SHA over the wire and
                # cannot resolve abbreviated forms; the standard pipeline
                # resolves them locally after a full clone.
                if declared_add_type is not None:
                    raise InvalidArgumentError(
                        "Connector git import cannot resolve an abbreviated commit SHA; "
                        "pass a full 40-character SHA or drop add_type to use the "
                        "standard pipeline."
                    )
                if credential_args:
                    raise InvalidArgumentError(
                        f"Credential args {credential_args} for 'git' cannot fall back to the "
                        "standard import pipeline; pass a full 40-character commit SHA."
                    )
                logger.info(
                    "Connector git import degrades to the standard pipeline: "
                    "abbreviated commit SHA %r needs a local clone to resolve.",
                    commit,
                )
                return False

        unsupported = self._unsupported_params(
            add_type=add_type,
            wait=wait,
            instruction=instruction,
            build_index=build_index,
            summarize=summarize,
            processing_mode=processing_mode,
            parse_mode=parse_mode,
            watch_interval=watch_interval,
            connector_args=connector_args,
            kwargs=kwargs or {},
            to=to,
            parent=parent,
        )
        if not unsupported:
            return True
        detail = "; ".join(unsupported)
        if connector_only:
            raise InvalidArgumentError(f"Connector import does not support: {detail}")
        if credential_args:
            raise InvalidArgumentError(
                f"Credential args {credential_args} for '{add_type}' cannot fall back to the "
                f"standard import pipeline. Connector import does not support: {detail}"
            )
        logger.info(
            f"[ConnectorDelegate] Connector does not support {detail}; "
            "falling back to the standard import pipeline"
        )
        return False

    @staticmethod
    def _unsupported_params(
        *,
        add_type: str,
        wait: bool,
        instruction: str,
        build_index: bool,
        summarize: bool,
        processing_mode: ProcessingMode,
        parse_mode: ParseMode,
        watch_interval: float,
        connector_args: Dict[str, Any],
        kwargs: Dict[str, Any],
        to: Optional[str] = None,
        parent: Optional[str] = None,
    ) -> List[str]:
        """add_resource params the Connector delegation cannot honor.

        Returns an empty list when the request is fully supported.
        """
        unsupported: List[str] = []
        if parse_mode is ParseMode.NO_SPLIT:
            unsupported.append("parse_mode=no_split")
        if wait:
            unsupported.append("wait=true (Connector imports run asynchronously)")
        if parent:
            unsupported.append("parent targets (Connector imports require an exact 'to' target)")
        if not to:
            unsupported.append("missing exact 'to' target")
        elif not _is_resource_target(to):
            unsupported.append(
                "to outside a resources tree (viking://resources/... or "
                "viking://user/<user_id>/resources/...)"
            )
        if instruction:
            unsupported.append("instruction")
        if not build_index:
            unsupported.append("build_index=false")
        if summarize:
            unsupported.append("summarize=true")
        if processing_mode == VECTORS_ONLY:
            unsupported.append("processing_mode=vectors_only")
        if kwargs.get("strict"):
            unsupported.append("strict=true (Connector imports fail per file, not all-or-nothing)")
        for field in ("ignore_dirs", "include", "exclude"):
            if field == "exclude" and add_type == "tos" and field in connector_args:
                continue
            if kwargs.get(field):
                unsupported.append(f"{field} (Connector imports cannot filter the source tree)")
        if kwargs.get("preserve_structure") is False:
            unsupported.append(
                "preserve_structure=false (Connector always mirrors the source directory tree)"
            )
        if not kwargs.get("directly_upload_media", True):
            unsupported.append("directly_upload_media=false")
        if kwargs.get("source_name"):
            unsupported.append("source_name")
        if add_type in CONNECTOR_SUPPORTED_ARGS:
            supported_args = CONNECTOR_SUPPORTED_ARGS.get(
                add_type, frozenset()
            ) | CONNECTOR_CREDENTIAL_ARGS.get(add_type, frozenset())
            unknown_args = sorted(
                set(connector_args) - supported_args - {CONNECTOR_DISPLAY_RESOURCE_CONFIG_ARG}
            )
            if unknown_args:
                supported_hint = (
                    f"supported: {sorted(supported_args)}"
                    if supported_args
                    else "no args supported"
                )
                unsupported.append(f"args keys {unknown_args} ({supported_hint} for '{add_type}')")
        else:
            # Declared add_types outside the registry forward args wholesale
            # to the plugin via param_config; only the reserved credentials
            # key is inspected here.
            declared_auth = connector_args.get(CONNECTOR_ARGS_AUTH_CONFIG_KEY)
            if declared_auth is not None and not isinstance(declared_auth, dict):
                unsupported.append("args.auth_config that is not an object of credential fields")
        return unsupported

    async def create(
        self,
        path: str,
        ctx: RequestContext,
        to: Optional[str],
        *,
        wait_for_completion: bool = False,
        task_id: Optional[str] = None,
        on_task_created: Optional[Callable[[TaskRecord], Awaitable[None]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Submit an import, enqueue monitoring, and return its durable receipt."""
        task = await run_to_completion(
            lambda: self._enqueue(
                path,
                ctx,
                to,
                task_id=task_id,
                on_task_created=on_task_created,
                **kwargs,
            )
        )
        tracker = get_task_tracker()
        owner = {"account_id": task.account_id, "user_id": task.user_id}
        key = task.meta.get("connector_task_key")
        if not key:
            raise InternalError("Connector submission did not persist its task key")
        response = {
            "status": "accepted",
            "task_id": task.task_id,
            "connector_task_key": key,
            "resource_id": task.resource_id,
        }
        if wait_for_completion:
            completed = await tracker.wait(task.task_id, **owner, timeout=None)
            response.update(completed.result or {})
            response["status"] = completed.status.value
            if completed.error:
                response["error"] = completed.error
        return response
