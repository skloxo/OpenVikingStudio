# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
import asyncio
import importlib
import threading
import weakref
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr, ValidationInfo, model_validator

from openviking_cli.utils.config.runtime_field import RuntimeField


def _load_codex_auth_module():
    importlib.import_module("openviking.models.vlm")
    return importlib.import_module("openviking.models.vlm.backends.codex_auth")


def _normalize_provider_name(name: Optional[str]) -> Optional[str]:
    if not isinstance(name, str):
        return name
    cleaned = name.strip().lower()
    return cleaned or None


def _has_codex_auth_available() -> bool:
    try:
        return bool(_load_codex_auth_module().has_codex_auth_available())
    except Exception:
        return False


def _bind_token_usage_tracker(instance: Any, tracker: Any) -> None:
    """Bind one Account tracker to all concrete VLM instances in a wrapper."""
    if instance is None:
        return
    if hasattr(instance, "_token_tracker"):
        instance._token_tracker = tracker
    inner = getattr(instance, "inner", None)
    if inner is not None:
        _bind_token_usage_tracker(inner, tracker)
        return
    if hasattr(instance, "_vlm_instances"):
        for child in instance._vlm_instances:
            _bind_token_usage_tracker(child, tracker)
    else:
        for name in ("primary", "backup"):
            child = getattr(instance, name, None)
            if child is not None:
                _bind_token_usage_tracker(child, tracker)


class VLMCredential(BaseModel):
    """Single VLM credential configuration for multi-credential failover."""

    cost_bearer: Optional[Literal["ov", "customer", "unknown"]] = RuntimeField(
        default=None, description="Billing owner supplied by the credential provisioner"
    )

    id: Optional[str] = RuntimeField(
        default=None, description="Unique identifier for this credential"
    )
    provider: Optional[str] = RuntimeField(default=None, description="Provider type")
    model: Optional[str] = RuntimeField(
        default=None,
        description=(
            "Model name (or endpoint id) for this credential. "
            "Overrides the parent VLMConfig.model when set, allowing each credential "
            "to point to a different deployment / endpoint."
        ),
    )
    api_key: Optional[str] = RuntimeField(default=None, description="API key")
    api_base: Optional[str] = RuntimeField(default=None, description="API base URL")
    api_version: Optional[str] = RuntimeField(default=None, description="API version")
    forward_api_key: Optional[bool] = RuntimeField(
        default=None, description="Whether to pass api_key through to LiteLLM"
    )
    extra_headers: Optional[Dict[str, str]] = RuntimeField(
        default=None, description="Extra HTTP headers"
    )
    extra_request_body: Optional[Dict[str, Any]] = RuntimeField(
        default=None, description="Extra JSON body fields"
    )
    reasoning_effort: Optional[str] = RuntimeField(
        default=None,
        description="Reasoning effort for OpenAI-compatible reasoning models",
    )
    keepalive_expiry: Optional[float] = RuntimeField(
        default=None,
        ge=0.0,
        description="Idle HTTP connection lifetime for OpenAI-compatible providers",
    )
    stream: Optional[bool] = RuntimeField(default=None, description="Enable streaming mode")
    max_tokens: Optional[int] = RuntimeField(
        default=None,
        gt=0,
        description=(
            "Maximum completion output tokens for this credential. "
            "Overrides the parent max_tokens when set."
        ),
    )


class VLMMediaConfig(BaseModel):
    """Runtime controls for audio and video inputs handled by the configured VLM."""

    enabled: bool = Field(default=False, description="Enable VLM audio/video understanding")
    max_concurrent: int = Field(
        default=2,
        ge=1,
        description="Maximum concurrent audio/video VLM calls",
    )
    file_processing_timeout: float = Field(
        default=1800.0,
        gt=0.0,
        description="Maximum provider-side media preprocessing wait in seconds",
    )
    file_poll_interval: float = Field(
        default=3.0,
        gt=0.0,
        description="Provider-side media preprocessing poll interval in seconds",
    )
    video_fps: float = Field(
        default=1.0,
        ge=0.2,
        le=5.0,
        description="Video frame sampling rate for providers that support preprocessing",
    )


