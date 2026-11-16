# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
import hashlib
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError, model_validator

from openviking_cli.session.user_id import UserIdentifier

from .agent_evolution_config import AgentEvolutionConfig
from .cache_config import CacheConfig
from .config_loader import expand_config_environment, resolve_config_path
from .config_utils import (
    DEFAULT_SERVICE_NAME,
    format_validation_error,
    normalize_service_name,
    warn_unknown_config_fields,
    warn_unknown_fields,
)
from .consts import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_OV_CONF,
    OPENVIKING_CONFIG_ENV,
    SYSTEM_CONFIG_DIR,
)
from .embedding_config import EmbeddingConfig
from .encryption_config import EncryptionConfig
from .expiry_config import ExpiryConfig
from .git_config import GitConfig
from .glob_config import GlobConfig
from .grep_config import GrepConfig
from .ingest_config import IngestConfig
from .log_config import LogConfig
from .memory_config import MemoryConfig
from .oauth_config import OAuthConfig
from .openviking_gateway_config import EmbeddedGatewayConfig
from .parser_config import (
    AnydocConfig,
    AudioConfig,
    CodeConfig,
    DirectoryConfig,
    FeishuConfig,
    HTMLConfig,
    ImageConfig,
    MarkdownConfig,
    PDFConfig,
    SemanticConfig,
    TextConfig,
    VideoConfig,
    WebFeedConfig,
)
from .prompts_config import PromptsConfig
from .queue_worker_config import QueueWorkersConfig
from .reindex_config import ReindexConfig
from .rerank_config import RerankConfig
from .retrieval_config import RetrievalConfig
from .rules_config import RulesConfig
from .runtime_field import RuntimeField
from .storage_config import StorageConfig
from .telemetry_config import TelemetryConfig
from .ttl_config import TTLConfig
from .vlm_config import VLMConfig


def _get_config_logger():
    """Use stdlib logging during config bootstrap to avoid early logger side effects."""
    return logging.getLogger(__name__)


class ConnectorConfig(BaseModel):
    """Configuration for external Connector service."""

    enable: bool = False
    connector: str = ""
    tracker: str = ""
    auth: str = ""
    timeout_seconds: int = 3600
    poll_interval_ms: int = 5000
    allowed_add_types: List[str] = Field(default_factory=lambda: ["tos"])

    @model_validator(mode="after")
    def _validate(self) -> "ConnectorConfig":
        self.auth = self.auth.strip()
        if self.auth:
            url = urlsplit(self.auth)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
                or url.fragment
            ):
                raise ValueError(
                    "connector.auth must be an HTTP(S) endpoint URL without credentials or fragment"
                )
        if self.enable:
            for name, url in (("connector", self.connector), ("tracker", self.tracker)):
                if not url.strip():
                    raise ValueError(f"connector.{name} is required when connector.enable=true")
                if "://" not in url:
                    raise ValueError(
                        f"connector.{name} must be a full endpoint URL including scheme "
                        "(e.g., http://...)"
                    )
        if self.timeout_seconds <= 0:
            raise ValueError("connector.timeout_seconds must be > 0")
        if self.poll_interval_ms <= 0:
            raise ValueError("connector.poll_interval_ms must be > 0")
        return self

    def credential_resolve_url(self) -> str:
        """Derive the unified credential-resolve endpoint from ``auth``.

        The Feishu compatibility endpoint (``.../oauth/access_token``) and the
        unified resolver (``.../credential/resolve``) are two fixed paths on the
        same KernelAPI inner entry, so the resolver URL is derived from the
        configured ``auth`` rather than adding a second endpoint setting; this
        keeps existing Feishu deployments unchanged. Returns an empty string
        when ``auth`` is unset or uses an unrecognized path.
        """
        auth = self.auth.strip()
        if not auth:
            return ""
        compat_suffix = "/oauth/access_token"
        resolve_suffix = "/credential/resolve"
        if auth.endswith(compat_suffix):
            return auth[: -len(compat_suffix)] + resolve_suffix
        if auth.endswith(resolve_suffix):
            return auth
        return ""


class ParserApiConfig(BaseModel):
    """Configuration for the Understanding files/responses API."""

    enable: bool = False
    extensions: List[str] = Field(default_factory=list)
    host: str = ""
    api_key: str = ""
    enable_feishu_url: bool = False
    enable_resumable_upload: bool = False
    upload_simple_max_bytes: int = 512 * 1024 * 1024
    upload_part_size_bytes: int = 8 * 1024 * 1024
    http_timeout_seconds: float = 10.0
    response_timeout_seconds: int = 1800
    poll_interval_ms: int = 3000

    @model_validator(mode="after")
    def _normalize_and_validate(self) -> "ParserApiConfig":
        normalized_extensions: List[str] = []
        for ext in self.extensions or []:
            s = str(ext).strip().lower()
            if not s:
                continue
            if s.startswith("."):
                s = s[1:]
            normalized_extensions.append(s)
        self.extensions = normalized_extensions

        if self.enable:
            if not self.host.strip():
                raise ValueError("parser_api.host is required when parser_api.enable=true")
            # The credential may be supplied by Account runtime configuration.
            # UnderstandingAPI validates it when an operation starts.
        if self.host and "://" not in self.host:
            raise ValueError("parser_api.host must include scheme (e.g., https://...)")
        if self.upload_simple_max_bytes <= 0:
            raise ValueError("parser_api.upload_simple_max_bytes must be > 0")
        if self.upload_part_size_bytes <= 0:
            raise ValueError("parser_api.upload_part_size_bytes must be > 0")
        if self.http_timeout_seconds <= 0:
            raise ValueError("parser_api.http_timeout_seconds must be > 0")
        if self.response_timeout_seconds <= 0:
            raise ValueError("parser_api.response_timeout_seconds must be > 0")
        if self.poll_interval_ms <= 0:
            raise ValueError("parser_api.poll_interval_ms must be > 0")
        return self


class ParserRuntimeConfig(BaseModel):
    """Runtime directories used by built-in parser download/extraction paths."""

    download_temp_dir: Optional[str] = Field(
        default=None,
        description=(
            "Directory for parser-owned downloads, Git checkouts, and archive extraction. "
            "Defaults to the system temporary directory."
        ),
    )


class CompileApiConfig(BaseModel):
    """Configuration for the external Compile task API."""

    base_url: str = ""
    gateway_token: str = ""
    http_timeout_seconds: float = 10.0
    poll_interval_ms: int = 30000
    # Run Redis-backed Compile scheduling on this instance.
    scheduler_enabled: bool = False
    scheduler_backend: Literal["redis"] = "redis"

    @model_validator(mode="after")
    def _validate(self) -> "CompileApiConfig":
        if self.base_url and "://" not in self.base_url:
            raise ValueError("compile_api.base_url must include scheme (e.g., https://...)")
        if self.http_timeout_seconds <= 0:
            raise ValueError("compile_api.http_timeout_seconds must be > 0")
        if self.poll_interval_ms <= 0:
            raise ValueError("compile_api.poll_interval_ms must be > 0")
        self.base_url = self.base_url.rstrip("/")
        return self


class RuntimeConfigSettings(BaseModel):
    """Startup selection of the runtime config source."""

    source: str = "file"
    module: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


