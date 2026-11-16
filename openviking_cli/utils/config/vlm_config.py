# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from __future__ import annotations

import threading
import weakref
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr, ValidationInfo, model_validator

from openviking_cli.utils.config.runtime_field import RuntimeField

from .vlm_config_models import (
    VLMCredential,
    VLMMediaConfig,
    _bind_token_usage_tracker,
    _has_codex_auth_available,
    _load_codex_auth_module,
    _normalize_provider_name,
)
from .vlm_config_runtime import _VLMInstanceMixin

class VLMConfig(_VLMInstanceMixin, BaseModel):
    """VLM configuration with multi-provider and multi-credential failover.

    Compatibility contract: top-level fields added here must describe common
    runtime behavior that is safe for Account VLM configurations to inherit
    from Cluster configuration. Fields that select a model service, credential,
    endpoint, or provider-specific request identity must instead be represented
    by ``AccountVLMConfig`` (normally ``model`` or ``VLMCredential``) and excluded by
    ``AccountVLMConfig._ACCOUNT_OWNED_MODEL_SERVICE_FIELDS``.
    """

    backup: Optional["VLMConfig"] = Field(
        default=None, description="Backup VLM configuration for failover (legacy)"
    )
    model: Optional[str] = Field(default=None, description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    forward_api_key: Optional[bool] = Field(
        default=None,
        description=(
            "Whether to pass api_key through to LiteLLM. None uses provider-aware defaults."
        ),
    )
    api_base: Optional[str] = Field(default=None, description="API base URL")
    temperature: Optional[float] = Field(
        default=None, description="Generation temperature; None uses the provider default"
    )
    stream: bool = Field(
        default=False, description="Enable streaming mode for OpenAI-compatible providers"
    )
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout: float = Field(
        default=600.0,
        gt=0.0,
        description=(
            "Per-request HTTP timeout in seconds for VLM API calls. Applied to "
            "the underlying OpenAI/Azure/LiteLLM clients. Increase for slow or "
            "high-latency endpoints (e.g., DashScope, local inference servers)."
        ),
    )
    keepalive_expiry: Optional[float] = Field(
        default=None,
        ge=0.0,
        description=(
            "Idle HTTP connection lifetime in seconds for OpenAI-compatible VLM clients. "
            "Set to 0 to disable connection reuse; None uses the provider SDK default."
        ),
    )

    provider: Optional[str] = Field(default=None, description="Provider type")
    backend: Optional[str] = Field(
        default=None, description="Backend provider (Deprecated, use 'provider' instead)"
    )

    providers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Multi-provider configuration, e.g. {'openai': {'api_key': 'xxx', 'api_base': 'xxx'}}",
    )

    default_provider: Optional[str] = Field(default=None, description="Default provider name")

    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens for VLM completion output (None = provider default)",
    )

    thinking: bool = Field(default=False, description="Enable thinking mode for VolcEngine models")

    max_concurrent: int = Field(
        default=32, description="Maximum number of concurrent LLM calls for semantic processing"
    )

    media: VLMMediaConfig = Field(
        default_factory=VLMMediaConfig,
        description="Audio/video runtime controls for the configured VLM",
    )

    api_version: Optional[str] = Field(
        default=None,
        description="API version for Azure OpenAI (e.g., '2025-01-01-preview').",
    )

    extra_headers: Optional[Dict[str, str]] = Field(
        default=None, description="Extra HTTP headers for OpenAI-compatible providers"
    )

    extra_request_body: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Extra JSON body fields passed to OpenAI-compatible VLM completion requests. "
            "Useful for provider-specific options such as Ollama's {'think': false}."
        ),
    )

    reasoning_effort: Optional[str] = Field(
        default=None,
        description="Reasoning effort for OpenAI-compatible reasoning models",
    )

    # New multi-credential configuration
    credentials: List[VLMCredential] = Field(
        default_factory=list,
        description="Ordered list of credentials for failover. Call order matches array index (0 is highest priority).",
    )

    failback_timeout_seconds: float = Field(
        default=600.0, description="Time in seconds after which to attempt failback to primary"
    )
    failback_request_count: int = Field(
        default=50, description="Number of backup requests after which to attempt failback"
    )

    _vlm_instance: Optional[Any] = None
    _token_usage_tracker: Any = PrivateAttr(default=None)
    _media_semaphores: weakref.WeakKeyDictionary[
        asyncio.AbstractEventLoop,
        weakref.ReferenceType[asyncio.Semaphore],
    ] = PrivateAttr(default_factory=weakref.WeakKeyDictionary)
    _media_semaphore_lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="before")
    @classmethod
    def sync_provider_backend(cls, data: Any) -> Any:
        if isinstance(data, dict):
            provider = data.get("provider")
            backend = data.get("backend")

            if backend is not None and provider is None:
                data["provider"] = backend
            data["provider"] = _normalize_provider_name(data.get("provider"))
            data["backend"] = _normalize_provider_name(data.get("backend"))
            data["default_provider"] = _normalize_provider_name(data.get("default_provider"))
            providers = data.get("providers")
            if isinstance(providers, dict):
                normalized: Dict[str, Dict[str, Any]] = {}
                provider_sources: Dict[str, str] = {}
                for name, config in providers.items():
                    normalized_name = _normalize_provider_name(name) or str(name)
                    existing_name = provider_sources.get(normalized_name)
                    if existing_name is not None and existing_name != str(name):
                        raise ValueError(
                            "Duplicate VLM provider config after normalization: "
                            f"{existing_name} and {name}"
                        )
                    normalized[normalized_name] = config
                    provider_sources[normalized_name] = str(name)
                data["providers"] = normalized
        return data

    @model_validator(mode="after")
    def validate_config(self, info: ValidationInfo):
        """Validate configuration completeness and consistency"""
        # Validate recursive backup BEFORE normalizing credentials (which clears backup)
        self._validate_no_recursive_backup()

        self._migrate_legacy_config()
        self._normalize_credentials()

        skip_codex_auth_availability = bool(
            info.context and info.context.get("skip_codex_auth_availability")
        )

        if self._has_any_config():
            if not self.model:
                raise ValueError("VLM configuration requires 'model' to be set")
            # When credentials are configured, validate each credential
            if self.credentials:
                for i, cred in enumerate(self.credentials):
                    provider_name = cred.provider or self.provider
                    if provider_name == "openai-codex":
                        has_codex_auth_available = (
                            _load_codex_auth_module().has_codex_auth_available
                        )
                        if (
                            not cred.api_key
                            and not skip_codex_auth_availability
                            and not has_codex_auth_available()
                        ):
                            raise ValueError(
                                f"Credential {i} ({cred.id or 'unnamed'}): requires Codex OAuth credentials in ~/.openviking/codex_auth.json"
                            )
                    elif provider_name not in ("litellm", None) and not cred.api_key:
                        # Also check providers dict for fallback
                        if not self._get_credential_api_key(cred):
                            raise ValueError(
                                f"Credential {i} ({cred.id or 'unnamed'}): requires 'api_key' to be set"
                            )
            else:
                # Legacy validation
                provider_name = self._resolve_provider_name()
                if provider_name == "openai-codex":
                    has_codex_auth_available = _load_codex_auth_module().has_codex_auth_available
                    if (
                        not self._get_effective_api_key()
                        and not skip_codex_auth_availability
                        and not has_codex_auth_available()
                    ):
                        raise ValueError(
                            "VLM configuration requires Codex OAuth credentials in ~/.openviking/codex_auth.json or an importable Codex CLI auth file"
                        )
                elif provider_name != "litellm" and not self._get_effective_api_key():
                    raise ValueError("VLM configuration requires 'api_key' to be set")
        return self

    def _validate_no_recursive_backup(self):
        """Prevent recursive backup configurations"""
        if self.backup is not None:
            if self.backup.backup is not None:
                raise ValueError(
                    "Backup VLM configuration cannot have its own backup (recursive backups are not allowed)"
                )

    def _migrate_legacy_config(self):
        """Migrate legacy config to providers structure."""
        if self.provider and (
            self.api_key
            or self.api_base
            or self.extra_headers
            or self.extra_request_body
            or self.reasoning_effort
            or self.keepalive_expiry is not None
            or self.forward_api_key is not None
        ):
            if self.provider not in self.providers:
                self.providers[self.provider] = {}
            if self.api_key and "api_key" not in self.providers[self.provider]:
                self.providers[self.provider]["api_key"] = self.api_key
            if (
                self.forward_api_key is not None
                and "forward_api_key" not in self.providers[self.provider]
            ):
                self.providers[self.provider]["forward_api_key"] = self.forward_api_key
            if self.api_base and "api_base" not in self.providers[self.provider]:
                self.providers[self.provider]["api_base"] = self.api_base
            if self.extra_headers and "extra_headers" not in self.providers[self.provider]:
                self.providers[self.provider]["extra_headers"] = self.extra_headers
            if (
                self.extra_request_body
                and "extra_request_body" not in self.providers[self.provider]
            ):
                self.providers[self.provider]["extra_request_body"] = self.extra_request_body
            if self.reasoning_effort and "reasoning_effort" not in self.providers[self.provider]:
                self.providers[self.provider]["reasoning_effort"] = self.reasoning_effort
            if (
                self.keepalive_expiry is not None
                and "keepalive_expiry" not in self.providers[self.provider]
            ):
                self.providers[self.provider]["keepalive_expiry"] = self.keepalive_expiry

    def _normalize_credentials(self):
        """Normalize credentials configuration:
        1. Migrate legacy backup config to credentials
        2. Migrate top-level credentials to credentials list
        3. Assign default IDs to credentials without IDs
        4. Apply top-level defaults to credentials
        """
        migrated_credentials = []

        # Step 1: Migrate legacy backup config
        if self.backup is not None and self.backup._has_any_config():
            # Primary credential: resolve via _match_provider() so legacy
            # ``providers: {openai: {...}}`` configs (without top-level
            # provider/api_key) are migrated correctly.
            primary_cfg, primary_provider = self._match_provider()
            primary_cfg = primary_cfg or {}
            primary_cred = VLMCredential(
                id="legacy-primary",
                provider=primary_provider or self.provider,
                model=self.model,
                api_key=primary_cfg.get("api_key") or self.api_key,
                api_base=primary_cfg.get("api_base") or self.api_base,
                api_version=primary_cfg.get("api_version") or self.api_version,
                forward_api_key=(
                    primary_cfg.get("forward_api_key")
                    if primary_cfg.get("forward_api_key") is not None
                    else self.forward_api_key
                ),
                extra_headers=primary_cfg.get("extra_headers") or self.extra_headers,
                extra_request_body=(
                    primary_cfg.get("extra_request_body") or self.extra_request_body
                ),
                reasoning_effort=(primary_cfg.get("reasoning_effort") or self.reasoning_effort),
                keepalive_expiry=(
                    primary_cfg.get("keepalive_expiry")
                    if primary_cfg.get("keepalive_expiry") is not None
                    else self.keepalive_expiry
                ),
                max_tokens=self.max_tokens,
            )
            migrated_credentials.append(primary_cred)

            # Backup credential: same resolution rules so backup using
            # providers/default_provider also gets a usable api_key/provider.
            backup_cfg, backup_provider = self.backup._match_provider()
            backup_cfg = backup_cfg or {}
            backup_cred = VLMCredential(
                id="legacy-backup",
                provider=backup_provider or self.backup.provider,
                model=self.backup.model,
                api_key=backup_cfg.get("api_key") or self.backup.api_key,
                api_base=backup_cfg.get("api_base") or self.backup.api_base,
                api_version=backup_cfg.get("api_version") or self.backup.api_version,
                forward_api_key=(
                    backup_cfg.get("forward_api_key")
                    if backup_cfg.get("forward_api_key") is not None
                    else self.backup.forward_api_key
                ),
                extra_headers=backup_cfg.get("extra_headers") or self.backup.extra_headers,
                extra_request_body=(
                    backup_cfg.get("extra_request_body") or self.backup.extra_request_body
                ),
                reasoning_effort=(
                    backup_cfg.get("reasoning_effort") or self.backup.reasoning_effort
                ),
                keepalive_expiry=(
                    backup_cfg.get("keepalive_expiry")
                    if backup_cfg.get("keepalive_expiry") is not None
                    else self.backup.keepalive_expiry
                ),
                max_tokens=self.backup.max_tokens,
            )
            migrated_credentials.append(backup_cred)

            # Clear backup to avoid double processing
            self.backup = None

        # Step 2: If no credentials from backup migration and no explicit credentials,
        # create credentials from top-level config. We resolve the effective provider
        # config first (via _match_provider) so legacy ``providers: {openai: {...}}``
        # configurations - where the api_key/api_base live inside the providers dict
        # rather than at the top level - are migrated correctly. Otherwise the
        # generated credential would be missing provider/api_key and is_available()
        # would return False.
        if not migrated_credentials and not self.credentials:
            if self._has_legacy_provider_config():
                provider_cfg, provider_name = self._match_provider()
                provider_cfg = provider_cfg or {}
                migrated_credentials.append(
                    VLMCredential(
                        id="default",
                        provider=provider_name or self.provider,
                        model=self.model,
                        api_key=provider_cfg.get("api_key") or self.api_key,
                        api_base=provider_cfg.get("api_base") or self.api_base,
                        api_version=provider_cfg.get("api_version") or self.api_version,
                        forward_api_key=(
                            provider_cfg.get("forward_api_key")
                            if provider_cfg.get("forward_api_key") is not None
                            else self.forward_api_key
                        ),
                        extra_headers=provider_cfg.get("extra_headers") or self.extra_headers,
                        extra_request_body=(
                            provider_cfg.get("extra_request_body") or self.extra_request_body
                        ),
                        reasoning_effort=(
                            provider_cfg.get("reasoning_effort") or self.reasoning_effort
                        ),
                        keepalive_expiry=(
                            provider_cfg.get("keepalive_expiry")
                            if provider_cfg.get("keepalive_expiry") is not None
                            else self.keepalive_expiry
                        ),
                    )
                )

        # Step 3: Merge migrated credentials with existing credentials
        if migrated_credentials:
            # Only use migrated if no explicit credentials exist
            if not self.credentials:
                self.credentials = migrated_credentials

        # Step 4: Assign default IDs and apply top-level defaults
        for i, cred in enumerate(self.credentials):
            if not cred.id:
                cred.id = f"credential-{i}"
            # Apply top-level defaults where credential doesn't specify
            if not cred.provider:
                cred.provider = self.provider
            if not cred.api_key:
                cred.api_key = self._get_credential_api_key(cred)
            if not cred.api_base:
                cred.api_base = self.api_base
            if not cred.api_version:
                cred.api_version = self.api_version
            if cred.forward_api_key is None:
                cred.forward_api_key = self.forward_api_key
            if not cred.extra_headers:
                cred.extra_headers = self.extra_headers
            if not cred.extra_request_body:
                cred.extra_request_body = self.extra_request_body
            if not cred.reasoning_effort:
                cred.reasoning_effort = self.reasoning_effort
            if cred.stream is None:
                cred.stream = self.stream
            if cred.keepalive_expiry is None:
                cred.keepalive_expiry = self.keepalive_expiry


# Resolve forward reference for backup field
VLMConfig.model_rebuild()

