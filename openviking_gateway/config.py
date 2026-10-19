"""Gateway configuration module for OpenViking Gateway 2.0.

Provides strongly typed configuration with environment variable fallbacks
and sane defaults for port 1934 isolation.
"""

from __future__ import annotations

import os
from typing import List, Optional
from pydantic import BaseModel, Field


class GatewayConfig(BaseModel):
    """Runtime configuration for OpenViking Gateway 2.0."""

    host: str = Field(default="0.0.0.0", description="Host address to bind")
    port: int = Field(default=1934, description="Gateway port, isolated from 1933")
    upstream_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL of upstream LLM provider",
    )
    upstream_api_key: str = Field(
        default="",
        description="API key for upstream provider",
    )
    upstream_protocol: str = Field(
        default="openai",
        description="Protocol of upstream provider: 'openai' or 'anthropic'",
    )
    default_model: str = Field(
        default="gpt-4o",
        description="Fallback model if client specifies none or upstream overrides",
    )
    timeout_seconds: float = Field(
        default=120.0,
        description="HTTP timeout in seconds for upstream requests",
    )
    enable_dual_track_translation: bool = Field(
        default=True,
        description="Enable automatic Anthropic<->OpenAI translation",
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins",
    )
    debug: bool = Field(default=False, description="Enable debug logging")

    def __init__(self, **data):
        super().__init__(**data)
        # Strip trailing slash from upstream_base_url
        if self.upstream_base_url.endswith("/"):
            self.upstream_base_url = self.upstream_base_url.rstrip("/")


_GLOBAL_GATEWAY_CONFIG: Optional[GatewayConfig] = None


def get_gateway_config(reload: bool = False) -> GatewayConfig:
    """Retrieve global GatewayConfig singleton with environment overrides.

    Environment variables:
        OPENVIKING_GATEWAY_HOST (default: 0.0.0.0)
        OPENVIKING_GATEWAY_PORT (default: 1934)
        OPENVIKING_GATEWAY_UPSTREAM_URL or OPENAI_BASE_URL
        OPENVIKING_GATEWAY_UPSTREAM_KEY or OPENAI_API_KEY
        OPENVIKING_GATEWAY_UPSTREAM_PROTOCOL (default: openai)
        OPENVIKING_GATEWAY_DEFAULT_MODEL (default: gpt-4o)
        OPENVIKING_GATEWAY_TIMEOUT (default: 120.0)
    """
    global _GLOBAL_GATEWAY_CONFIG
    if _GLOBAL_GATEWAY_CONFIG is not None and not reload:
        return _GLOBAL_GATEWAY_CONFIG

    host = os.environ.get("OPENVIKING_GATEWAY_HOST", "0.0.0.0")
    port_str = os.environ.get("OPENVIKING_GATEWAY_PORT", "1934")
    try:
        port = int(port_str)
    except ValueError:
        port = 1934

    upstream_url = (
        os.environ.get("OPENVIKING_GATEWAY_UPSTREAM_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    upstream_key = (
        os.environ.get("OPENVIKING_GATEWAY_UPSTREAM_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    upstream_protocol = os.environ.get(
        "OPENVIKING_GATEWAY_UPSTREAM_PROTOCOL", "openai"
    ).lower()
    default_model = (
        os.environ.get("OPENVIKING_GATEWAY_DEFAULT_MODEL")
        or os.environ.get("DEFAULT_MODEL")
        or "gpt-4o"
    )
    timeout_str = os.environ.get("OPENVIKING_GATEWAY_TIMEOUT", "120.0")
    try:
        timeout = float(timeout_str)
    except ValueError:
        timeout = 120.0

    debug_val = os.environ.get("OPENVIKING_GATEWAY_DEBUG", "false").lower()
    debug = debug_val in ("1", "true", "yes", "on")

    _GLOBAL_GATEWAY_CONFIG = GatewayConfig(
        host=host,
        port=port,
        upstream_base_url=upstream_url,
        upstream_api_key=upstream_key,
        upstream_protocol=upstream_protocol,
        default_model=default_model,
        timeout_seconds=timeout,
        debug=debug,
    )
    return _GLOBAL_GATEWAY_CONFIG
