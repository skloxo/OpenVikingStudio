# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Server configuration for OpenViking HTTP Server."""

import json
import sys
from collections.abc import Mapping
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, ValidationError, field_validator

# Import auth plugin registry for config validation
from openviking.server.auth.ldap_config import LDAPConfig
from openviking.server.auth.oidc_config import OIDCConfig
from openviking.server.auth.registry import get_registry
from openviking.server.identity import AuthMode
from openviking_cli.utils import get_logger
from openviking_cli.utils.config.agent_evolution_config import AgentEvolutionConfig
from openviking_cli.utils.config.config_loader import (
    load_json_config,
    resolve_config_path,
)
from openviking_cli.utils.config.config_utils import (
    DEFAULT_SERVICE_NAME,
    format_validation_error,
    normalize_service_name,
    warn_unknown_config_fields,
)
from openviking_cli.utils.config.consts import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_OV_CONF,
    OPENVIKING_CONFIG_ENV,
    SYSTEM_CONFIG_DIR,
)
from openviking_cli.utils.config.ttl_config import TTLConfig

logger = get_logger(__name__)


def _normalize_config_uri(value: Optional[str], field_name: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    uri = value.strip().rstrip("/")
    if not uri:
        raise ValueError(f"{field_name} must not be empty")
    # Preserve pre-home-alias add-target configurations when upgrading.
    if uri in {"viking://user/resources", "viking://user/skills"} or uri.startswith(
        "viking://user/resources/"
    ):
        uri = "viking://~/" + uri.removeprefix("viking://user/")
    return uri


def _rewrite_legacy_current_user_uri(uri: str, field_name: str) -> str:
    """Rewrite legacy uid-less current-user spellings to the ``~`` home alias."""
    from openviking.core.namespace import uri_parts

    try:
        parts = uri_parts(uri.rstrip("/"))
    except ValueError:
        return uri
    if parts[:2] not in (["user", "resources"], ["user", "skills"]):
        return uri
    rewritten = f"viking://~/{'/'.join(parts[1:])}"
    logger.info(
        "Rewrote legacy current-user %s %r to %r; use the viking://~ home alias instead.",
        field_name,
        uri,
        rewritten,
    )
    return rewritten


class AddTargetsConfig(BaseModel):
    """Add targets for resource and skill writes."""

    resource_uri: Optional[str] = None
    skill_uri: Optional[str] = None

    @field_validator("resource_uri")
    @classmethod
    def validate_resource_uri(cls, value: Optional[str]) -> Optional[str]:
        uri = _normalize_config_uri(value, "resource_uri")
        if uri is None:
            return None
        from openviking.core.namespace import uri_parts
        from openviking.core.peer_id import normalize_peer_id
        from openviking.core.uri_validation import validate_viking_uri

        validate_viking_uri(uri, field_name="resource_uri")
        normalized = uri.rstrip("/")
        parts = uri_parts(normalized)
        if (
            parts[:1] == ["resources"]
            or parts[:2] == ["~", "resources"]
            or (
                len(parts) >= 4
                and parts[:2] == ["~", "peers"]
                and parts[3] == "resources"
                and normalize_peer_id(parts[2]) is not None
            )
        ):
            return normalized
        raise ValueError(
            "resource_uri must be a resource directory URI: viking://resources/..., "
            "viking://~/resources[/...], or viking://~/peers/{peer_id}/resources[/...]. "
            "Explicit user IDs are not allowed in add-target configuration."
        )

    @field_validator("skill_uri")
    @classmethod
    def validate_skill_uri(cls, value: Optional[str]) -> Optional[str]:
        uri = _normalize_config_uri(value, "skill_uri")
        if uri is None:
            return None
        from openviking.core.namespace import uri_parts
        from openviking.core.uri_validation import validate_viking_uri

        validate_viking_uri(uri, field_name="skill_uri")
        normalized = uri.rstrip("/")
        parts = uri_parts(normalized)
        if parts in (["~", "skills"], ["agent", "skills"]):
            return normalized
        raise ValueError(
            "skill_uri must be viking://~/skills or viking://agent/skills. "
            "Explicit user IDs are not allowed in add-target configuration."
        )


def _normalize_user_memory_policy(value: Any) -> dict[str, Any]:
    from openviking.session.memory_policy import MemoryPolicy

    return MemoryPolicy.from_dict(value).to_dict()


UserMemoryPolicy = Annotated[Dict[str, Any], BeforeValidator(_normalize_user_memory_policy)]


class DeprecatedUserAgentEvolutionConfig(BaseModel):
    """Parse-only compatibility for legacy per-user configuration files."""

    enabled: Optional[bool] = None


class UserConfig(BaseModel):
    """User configuration values that can be defaulted or initialized."""

    add_targets: AddTargetsConfig = Field(default_factory=AddTargetsConfig)
    memory_policy: Optional[UserMemoryPolicy] = None
    ttl: Optional[TTLConfig] = None
    agent_evolution: DeprecatedUserAgentEvolutionConfig = Field(
        default_factory=DeprecatedUserAgentEvolutionConfig,
        exclude=True,
    )

    @classmethod
    def from_stored(cls, payload: dict[str, Any]) -> "UserConfig":
        """Restore persisted values without applying configuration input validators."""
        config = cls.model_construct(**payload)
        config.add_targets = AddTargetsConfig.model_construct(**payload.get("add_targets", {}))
        if config.ttl is not None:
            config.ttl = TTLConfig.model_construct(**payload["ttl"])
        return config


class UserSettingsPatch(BaseModel):
    """Validate only fields supplied by a user-settings PATCH."""

    model_config = {"extra": "forbid"}

    add_targets: Optional[AddTargetsConfig] = None
    memory_policy: Optional[UserMemoryPolicy] = None
    ttl: Optional[TTLConfig] = None


def validate_config_input(
    settings: Mapping[str, Any] | UserConfig | UserSettingsPatch | None = None,
    content: Optional[str] = None,
) -> None:
    """Check submitted configuration against the running server's capabilities."""
    from openviking.ttl.wiring import ttl_config_supported
    from openviking_cli.exceptions import UnimplementedError

    if isinstance(settings, (UserConfig, UserSettingsPatch)):
        settings = settings.model_dump(by_alias=True, exclude_unset=True)
        memory_types = (settings.get("memory_policy") or {}).get("memory_types")
        if memory_types is not None:
            from openviking.session.memory.memory_type_registry import get_default_registry
            from openviking.session.memory_policy import MemoryPolicy

            MemoryPolicy(memory_types=set(memory_types)).validate_memory_types(
                set(get_default_registry().list_names(include_disabled=False))
            )
    file_settings = None
    if content is not None:
        try:
            file_settings = json.loads(content.lstrip("\ufeff"))
        except (TypeError, ValueError):
            pass  # The startup-file parser reports malformed JSON.
    has_ttl = (settings is not None and "ttl" in settings) or (
        isinstance(file_settings, dict) and "ttl" in file_settings
    )
    if has_ttl and not ttl_config_supported():
        raise UnimplementedError("Redis-backed TTL is not enabled in this deployment.")


class UserConfigDefaults(UserConfig):
    """Deployment defaults for users without persisted overrides."""

    preset_global_policy: bool = Field(
        default=False,
        description="Create the packaged GLOBAL_POLICY.md during user initialization.",
    )
    auto_commit_policy: Optional[Dict[str, Any]] = None

    @field_validator("auto_commit_policy", mode="before")
    @classmethod
    def validate_auto_commit_policy(cls, value: Any) -> Optional[Dict[str, Any]]:
        from openviking.session.auto_commit_policy import (
            AutoCommitPolicy,
            validate_idle_timeout_input,
        )

        if value is None:
            return None
        if isinstance(value, dict) and "idle_timeout_seconds" in value:
            validate_idle_timeout_input(value["idle_timeout_seconds"])
        return AutoCommitPolicy.from_dict(value).to_dict()


class MetricsAccountDimensionConfig(BaseModel):
    """Account-dimension configuration for metrics label injection."""

    # Enabled by default, but still allowlist-gated to avoid accidental high-cardinality exposure.
    enabled: bool = True
    max_active_accounts: int = 100
    metric_allowlist: List[str] = Field(default_factory=list)


class PrometheusExporterConfig(BaseModel):
    """Prometheus exporter configuration."""

    enabled: bool = True


class OTelExporterConfig(BaseModel):
    """OpenTelemetry exporter configuration."""

    class TLSConfig(BaseModel):
        """TLS configuration for OTLP exporters."""

        insecure: bool = False

    enabled: bool = False
    protocol: str = "grpc"  # "grpc", "http", or "local" for traces
    tls: TLSConfig = Field(default_factory=TLSConfig)
    endpoint: str = "localhost:4317"  # gRPC default: 4317; HTTP default: 4318
    service_name: str = "openviking-server"
    export_interval_ms: int = 10000
    headers: Dict[str, str] = Field(default_factory=dict)
    local_path: str = "~/.openviking/logs/traces.jsonl"
    local_rotation_mb: int = Field(default=40, gt=0)
    local_backup_count: int = Field(default=2, ge=0)


class MetricsExportersConfig(BaseModel):
    """Metrics exporters configuration."""

    prometheus: PrometheusExporterConfig = Field(default_factory=PrometheusExporterConfig)
    otel: OTelExporterConfig = Field(default_factory=OTelExporterConfig)


class MetricsConfig(BaseModel):
    """Metrics subsystem configuration."""

    enabled: bool = False
    bot_data_path: Optional[str] = None
    account_dimension: MetricsAccountDimensionConfig = Field(
        default_factory=MetricsAccountDimensionConfig
    )
    exporters: MetricsExportersConfig = Field(default_factory=MetricsExportersConfig)


class UsageAuditConfig(BaseModel):
    """Product usage and audit projection configuration."""

    enabled: bool = True
    backend: Literal["sqlite"] = "sqlite"
    sqlite_path: Optional[str] = None
    queue_size: int = Field(10_000, gt=0)
    batch_size: int = Field(500, gt=0)
    flush_interval_seconds: float = Field(1.0, gt=0)
    shutdown_flush_timeout_seconds: float = Field(3.0, gt=0)
    usage_retention_days: int = Field(14, ge=0)
    audit_retention_days: int = Field(7, ge=0)
    audit_retention_per_account: int = Field(1000, ge=0)
    timezone: str = "local"
    inventory_ttl_seconds: float = Field(10.0, ge=0)


class UsageReporterSinkConfig(BaseModel):
    """Usage reporter sink configuration."""

    type: Literal["custom", "file_log"] = "custom"
    class_path: Optional[str] = None
    config: Dict[str, object] = Field(default_factory=dict)


class UsageReporterConfig(BaseModel):
    """Usage event reporter configuration."""

    enabled: bool = False
    extractors: List[Literal["memory_usage"]] = Field(default_factory=lambda: ["memory_usage"])
    sinks: List[UsageReporterSinkConfig] = Field(default_factory=list)


class TTLAdapterConfig(BaseModel):
    """Opt-in Redis-backed directory TTL configuration.

    Uses the built-in implementation, supplied with its ResourceID, Redis
    connection and writer/reader role through ``config``. No external Python
    package is required. Unset or disabled leaves all TTL hooks inactive.
    """

    enabled: bool = False
    config: Dict[str, object] = Field(default_factory=dict)

    @property
    def writer_enabled(self) -> bool:
        return self.enabled and bool(self.config.get("writer", True))


class TraceDumpBodyConfig(BaseModel):
    """HTTP body dump configuration.

    Attaches request/response bodies as attributes on the active trace span so
    they can be inspected in trace UIs. Off by default — bodies may contain
    secrets and high-cardinality content.
    """

    enabled: bool = False
    max_bytes: int = 4096


class EventReportingConfig(BaseModel):
    """Optional business-event exporter configured in ov.conf."""

    enabled: bool = False
    kafka: Dict[str, Any] = Field(default_factory=dict)
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class ObservabilityConfig(BaseModel):
    """Server-side observability configuration."""

    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    usage_audit: UsageAuditConfig = Field(default_factory=UsageAuditConfig)
    traces: OTelExporterConfig = Field(default_factory=OTelExporterConfig)
    logs: OTelExporterConfig = Field(default_factory=OTelExporterConfig)
    dump_body: TraceDumpBodyConfig = Field(default_factory=TraceDumpBodyConfig)
    reporting: EventReportingConfig = Field(default_factory=EventReportingConfig)


class TempUploadConfig(BaseModel):
    """Temporary upload configuration."""

    default_mode: Literal["local", "shared"] = "local"
    shared_max_size_bytes: int = 512 * 1024 * 1024
    ttl_seconds: int = Field(12 * 60 * 60, ge=0)
    # When True, shared-upload cleanup also removes directories whose names are
    # not valid upload ids (missing/garbled `<ms-ts>-<uuid>` format). Off by
    # default so a malformed entry never triggers an unexpected delete; enable
    # to reclaim junk directories that would otherwise be skipped forever.
    cleanup_invalid_dirs: bool = False


class ToolOutputExternalizationConfig(BaseModel):
    """External storage controls for oversized tool outputs."""

    enabled: bool = True
    threshold_chars: int = 20_000
    preview_chars: int = 2_000
    assistant_turn_inline_budget_chars: int = 100_000
    assistant_turn_preview_budget_chars: int = 10_000
    min_preview_chars: int = 1_000
    aggregate_selection_strategy: Literal["largest_first"] = "largest_first"
    failure_mode: Literal["reject", "preserve_raw", "preview_only"] = "preserve_raw"


class AccountStoreConfig(BaseModel):
    """Startup-only selection of the complete account store provider."""

    provider: str = "file"
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        supported = {"file", "mysql", "redis_mysql", "postgres"}
        if normalized not in supported:
            raise ValueError(
                "account_store.provider must be one of: " + ", ".join(sorted(supported))
            )
        return normalized


