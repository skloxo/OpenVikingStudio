# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from .agfs_config import AGFSConfig
from .cache_config import CacheConfig
from .consts import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_OV_CONF,
    OPENVIKING_CONFIG_ENV,
    SYSTEM_CONFIG_DIR,
)
from .config_utils import (
    DEFAULT_SERVICE_NAME,
    format_validation_error,
    normalize_service_name,
    warn_unknown_config_fields,
    warn_unknown_fields,
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
from .open_viking_config_models import (
    CompileApiConfig,
    ConnectorConfig,
    ParserApiConfig,
    ParserRuntimeConfig,
    RuntimeConfigSettings,
    WebFeedConfig,
)
from .open_viking_config_singleton import (
    OpenVikingConfigSingleton,
    _get_config_logger,
    initialize_openviking_config,
    is_valid_openviking_config,
    set_openviking_config,
)
from .openviking_gateway_config import EmbeddedGatewayConfig
from .agent_evolution_config import AgentEvolutionConfig
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


def get_openviking_config() -> "OpenVikingConfig":
    """Get the global OpenVikingConfig instance."""
    return OpenVikingConfigSingleton.get_instance()


from .open_viking_config_serde import _OpenVikingConfigSerdeMixin

class OpenVikingConfig(_OpenVikingConfigSerdeMixin, BaseModel):
    """Main configuration for OpenViking."""

    default_account: Optional[str] = Field(
        default="default", description="Default account identifier"
    )
    default_user: Optional[str] = Field(default="default", description="Default user identifier")
    default_agent: Optional[str] = Field(
        default=None,
        description="Deprecated and ignored. User is the only data-plane identity.",
    )
    service_name: str = Field(
        default=DEFAULT_SERVICE_NAME,
        description="OpenViking deployment name shared by cache namespaces and OTel defaults",
    )

    cache: Optional[CacheConfig] = Field(
        default=None,
        description="Global cache Provider configuration",
    )

    storage: StorageConfig = Field(
        default_factory=StorageConfig, description="Storage configuration"
    )

    parser: ParserRuntimeConfig = Field(
        default_factory=ParserRuntimeConfig,
        description="Runtime directories used by built-in parsers",
    )

    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig, description="Embedding configuration"
    )

    vlm: VLMConfig = Field(default_factory=VLMConfig, description="VLM configuration")

    query_planner: Optional[VLMConfig] = Field(
        default=None,
        description=(
            "Optional lightweight model configuration for retrieval intent analysis and query "
            "planning. Falls back to vlm when unset or empty."
        ),
    )

    rerank: RerankConfig = Field(default_factory=RerankConfig, description="Rerank configuration")

    rules: RulesConfig = Field(
        default_factory=RulesConfig,
        description="Rule compilation and applicability model configuration",
    )

    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval behavior configuration",
    )

    grep: GrepConfig = Field(
        default_factory=GrepConfig,
        description="Grep engine configuration",
    )

    glob: GlobConfig = Field(
        default_factory=GlobConfig,
        description="Glob engine configuration",
    )

    # Encryption configuration
    encryption: EncryptionConfig = Field(
        default_factory=EncryptionConfig, description="Encryption configuration"
    )

    git: GitConfig = Field(
        default_factory=GitConfig, description="Git version control configuration"
    )

    pdf: PDFConfig = Field(default_factory=PDFConfig, description="PDF parsing configuration")

    code: CodeConfig = Field(default_factory=CodeConfig, description="Code parsing configuration")

    image: ImageConfig = Field(
        default_factory=ImageConfig, description="Image parsing configuration"
    )

    audio: AudioConfig = Field(
        default_factory=AudioConfig, description="Audio parsing configuration"
    )

    video: VideoConfig = Field(
        default_factory=VideoConfig, description="Video parsing configuration"
    )

    markdown: MarkdownConfig = Field(
        default_factory=MarkdownConfig, description="Markdown parsing configuration"
    )

    anydoc: AnydocConfig = Field(
        default_factory=AnydocConfig,
        description="Shared anydoc Office conversion configuration",
    )

    html: HTMLConfig = Field(default_factory=HTMLConfig, description="HTML parsing configuration")

    text: TextConfig = Field(default_factory=TextConfig, description="Text parsing configuration")

    directory: DirectoryConfig = Field(
        default_factory=DirectoryConfig, description="Directory parsing configuration"
    )

    feishu: FeishuConfig = Field(
        default_factory=FeishuConfig,
        description="Feishu/Lark document parsing configuration",
    )

    webfeed: WebFeedConfig = Field(
        default_factory=WebFeedConfig,
        description="Whole-site ingestion via sitemap / RSS / Atom feeds",
    )

    semantic: SemanticConfig = Field(
        default_factory=SemanticConfig,
        description="Semantic processing configuration (overview/abstract limits)",
    )

    queue_workers: QueueWorkersConfig = Field(
        default_factory=QueueWorkersConfig,
        description="Queue worker runtime configuration",
    )

    reindex: ReindexConfig = Field(
        default_factory=ReindexConfig,
        description="Admin reindex runtime configuration",
    )

    parser_api: ParserApiConfig = Field(
        default_factory=ParserApiConfig,
        description="Third-party parser API configuration (files/responses)",
    )

    compile_api: CompileApiConfig = Field(
        default_factory=CompileApiConfig,
        description="External Compile task API configuration",
    )

    connector: ConnectorConfig = Field(
        default_factory=ConnectorConfig,
        description="External Connector service configuration for data import",
    )

    gateway: EmbeddedGatewayConfig = Field(default_factory=EmbeddedGatewayConfig)

    enable_watch_scheduler: bool = Field(
        default=True,
        description=(
            "Whether this node may become the Watch scheduler leader that polls due "
            "watches and settles their runs. Every node serves the Watch API either way; "
            "disable on nodes that should never run the background watch/refresh loop."
        ),
    )
    watch_leader_provider: Literal["auto", "local", "cache"] = Field(
        default="auto",
        description=(
            "Deprecated; will be removed in the next version. Use "
            "storage.agfs.coordination.provider instead; explicit coordination takes precedence."
        ),
        json_schema_extra={"deprecated": True},
    )
    reconcile_system_assets_on_startup: bool = Field(
        default=True,
        description=(
            "Whether to reconcile packaged system assets for active accounts during startup. "
            "Disable on read-only replicas that share a writer's data."
        ),
    )

    auto_generate_l0: bool = Field(
        default=True, description="Automatically generate L0 (abstract) if not provided"
    )

    auto_generate_l1: bool = Field(
        default=True, description="Automatically generate L1 (overview) if not provided"
    )

    default_search_mode: str = Field(
        default="thinking",
        description="Default search mode: 'fast' (vector only) or 'thinking' (vector + LLM rerank)",
    )

    default_search_limit: int = Field(default=3, description="Default number of results to return")

    language_fallback: str = Field(
        default="en",
        description=(
            "Deprecated. No longer used — detection falls back to 'en' when no language can be "
            "inferred. Set output_language_override instead to pin an explicit language."
        ),
    )

    output_language_override: str = Field(
        default="",
        description=(
            "When non-empty, bypasses content-based language detection for memory extraction "
            "and semantic summaries/overviews and forces this language instead. Use when your "
            "corpus is mixed-language but you want summaries pinned to a single language "
            "(e.g., 'en', 'zh-CN', 'ja'). Leave empty (default) to auto-detect per content."
        ),
    )

    @model_validator(mode="after")
    def _warn_on_deprecated_language_fallback(self) -> "OpenVikingConfig":
        if self.language_fallback and self.language_fallback != "en":
            _get_config_logger().warning(
                "Config field 'language_fallback=%s' is deprecated and has no effect; "
                "remove it, or set 'output_language_override' to pin an explicit language.",
                self.language_fallback,
            )
        return self

    @model_validator(mode="after")
    def _validate_service_name(self) -> "OpenVikingConfig":
        """Validate and normalize the top-level service name."""
        self.service_name = normalize_service_name(self.service_name)
        return self

    @model_validator(mode="after")
    def _normalize_watch_leader_provider(self) -> "OpenVikingConfig":
        if "watch_leader_provider" in self.model_fields_set:
            _get_config_logger().warning(
                "Config field 'watch_leader_provider' is deprecated and will be removed "
                "in the next version; use 'storage.agfs.coordination.provider' instead."
            )
        coordination = self.storage.agfs.coordination
        uses_cache = self.watch_leader_provider == "cache" or (
            self.watch_leader_provider == "auto" and self.storage.watch_store.provider != "file"
        )
        if uses_cache and "provider" not in coordination.model_fields_set:
            self.storage.agfs.coordination = coordination.model_copy(update={"provider": "cache"})
        return self

    @model_validator(mode="after")
    def _validate_cache_runtime_config(self) -> "OpenVikingConfig":
        """Require the shared cache Provider whenever AGFS selects a cache-backed runtime."""
        agfs = self.storage.agfs
        backups = agfs.backups or {}
        uses_canonical_cache = (
            agfs.cachefs.backend == "cache"
            or agfs.queuefs.backend == "cache"
            or agfs.pathlock.provider == "cache"
            or agfs.coordination.provider == "cache"
            or backups.get("provider", "filesystem") == "cache"
        )
        if uses_canonical_cache and self.cache is None:
            raise ValueError("top-level cache config is required when an AGFS backend uses cache")
        return self

    @model_validator(mode="before")
    @classmethod
    def _inherit_git_defaults_from_agfs(cls, data: Any) -> Any:
        """Let the `git` section inherit unset defaults from `storage.agfs`.

        - `git.backend` defaults to `storage.agfs.backend` (a 'memory' storage
          backend maps to 'local') when not set explicitly.
        - When the effective git backend is 's3', the `git.s3` fields
          bucket/region/endpoint/access_key/secret_key default to the matching
          `storage.agfs.s3` values when not set explicitly and the source value
          is non-empty.

        Injecting into the raw dict keeps GitConfig's own validation intact.
        """
        if not isinstance(data, dict):
            return data

        storage = data.get("storage")
        agfs = storage.get("agfs", {}) if isinstance(storage, dict) else {}
        if not isinstance(agfs, dict):
            agfs = {}

        git = data.get("git")
        if not isinstance(git, dict):
            if git is not None:
                # git provided as a model instance; respect it as-is.
                return data
            git = {}
        git = dict(git)

        if "backend" not in git:
            agfs_backend = agfs.get("backend", "local")
            if agfs_backend == "memory":
                agfs_backend = "local"
            if agfs_backend in ("local", "s3"):
                git["backend"] = agfs_backend

        if git.get("backend", "local") == "s3":
            agfs_s3 = agfs.get("s3", {})
            if not isinstance(agfs_s3, dict):
                agfs_s3 = {}
            git_s3 = git.get("s3")
            git_s3 = dict(git_s3) if isinstance(git_s3, dict) else {}
            for field in ("bucket", "region", "endpoint", "access_key", "secret_key"):
                if field not in git_s3 and agfs_s3.get(field):
                    git_s3[field] = agfs_s3[field]
            git["s3"] = git_s3

        data = dict(data)
        data["git"] = git
        return data

    allow_private_networks: bool = Field(
        default=False,
        description=(
            "Allow fetching resources from private/non-public network addresses. "
            "Configured code hosts may also use private networks. Loopback, link-local, "
            "unspecified, multicast, reserved and known metadata addresses are always rejected."
        ),
    )

    log: LogConfig = Field(default_factory=LogConfig, description="Logging configuration")

    memory: MemoryConfig = Field(default_factory=MemoryConfig, description="Memory configuration")

    expiry: ExpiryConfig = Field(
        default_factory=ExpiryConfig,
        description="Distributed expiry scheduling configuration",
    )

    ttl: TTLConfig = RuntimeField(
        default_factory=TTLConfig,
        description=(
            "Directory TTL recycling policy. Default-off; requires the enabled Redis TTL runtime."
        ),
    )

    @model_validator(mode="after")
    def _validate_expiry_backend(self) -> "OpenVikingConfig":
        self._check_expiry_backend()
        return self

    @model_validator(mode="after")
    def _validate_watch_store(self) -> "OpenVikingConfig":
        if self.storage.watch_store.provider == "mysql":
            if not self.storage.watch_store.params.get("credential_encryption_key"):
                raise ValueError(
                    "storage.watch_store.provider='mysql' requires "
                    "storage.watch_store.params.credential_encryption_key"
                )
        return self

    def _check_expiry_backend(self) -> None:
        if self.uses_redis_expiry():
            self.expiry.validate_for_runtime()

    def uses_redis_session_expiry(self) -> bool:
        idle = self.memory.session_auto_commit
        return idle.enabled and idle.idle_backend == "redis"

    def uses_redis_compile_schedule(self) -> bool:
        return self.compile_api.scheduler_enabled

    def uses_redis_expiry(self) -> bool:
        """Whether any feature needs the distributed ExpiryScheduler."""
        return self.uses_redis_session_expiry() or self.uses_redis_compile_schedule()

    agent_evolution: AgentEvolutionConfig = RuntimeField(
        default_factory=AgentEvolutionConfig,
        description="Dynamic cluster default for Agent Evolution.",
    )

    oauth: OAuthConfig = Field(
        default_factory=OAuthConfig,
        description="OAuth 2.1 (MCP) configuration",
    )

    telemetry: "TelemetryConfig" = Field(
        default_factory=TelemetryConfig, description="Telemetry configuration"
    )
    prompts: PromptsConfig = Field(
        default_factory=PromptsConfig,
        description="Prompt template configuration",
    )

    ingest: IngestConfig = Field(
        default_factory=IngestConfig,
        description="Conversation-log ingest (openviking-server ingest) configuration",
    )

    runtime_config: RuntimeConfigSettings = Field(
        default_factory=RuntimeConfigSettings,
        description=(
            "Boot-level selection of the runtime config source. "
            "Read once at startup and never mutated by the dynamic config API."
        ),
    )

    model_config = {"arbitrary_types_allowed": True, "hide_input_in_errors": True}

