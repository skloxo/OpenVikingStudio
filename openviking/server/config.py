# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Server configuration for OpenViking HTTP Server."""

import sys
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from openviking.server.auth.ldap_config import LDAPConfig
from openviking.server.auth.oidc_config import OIDCConfig
from openviking.server.auth.registry import get_registry
from openviking.server.config_models import (
    AccountStoreConfig,
    AddTargetsConfig,
    DeprecatedUserAgentEvolutionConfig,
    EventReportingConfig,
    MetricsAccountDimensionConfig,
    MetricsConfig,
    MetricsExportersConfig,
    ObservabilityConfig,
    OTelExporterConfig,
    PrometheusExporterConfig,
    TTLAdapterConfig,
    TempUploadConfig,
    ToolOutputExternalizationConfig,
    TraceDumpBodyConfig,
    UsageAuditConfig,
    UsageReporterConfig,
    UsageReporterSinkConfig,
    UserConfig,
    UserConfigDefaults,
    UserMemoryPolicy,
    UserSettingsPatch,
    _normalize_config_uri,
    _normalize_user_memory_policy,
    _rewrite_legacy_current_user_uri,
    validate_config_input,
)
from openviking.server.identity import AuthMode
from openviking_cli.utils import get_logger
from openviking_cli.utils.config.agent_evolution_config import AgentEvolutionConfig
from openviking_cli.utils.config.config_loader import load_json_config, resolve_config_path
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

logger = get_logger(__name__)

class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 1933
    workers: int = 1
    executor_threads: int = Field(
        default=0,
        ge=0,
        description=(
            "Maximum number of threads in each server process's default asyncio "
            "executor. Zero keeps Python's default sizing policy."
        ),
    )
    # Seconds an idle HTTP keep-alive connection is kept open before the server
    # closes it. Defaults to 5 to match uvicorn's built-in default and preserve
    # the existing service behavior. Raise it above the idle-connection lifetime
    # of any upstream client or load balancer that reuses connections (e.g. the
    # serverless VKE forwarder keeps idle connections for up to 60s via
    # WithMaxIdleConnDuration(1*time.Minute)); otherwise the server may close
    # connections the client still believes are reusable, causing sporadic
    # connection-reset / EOF errors.
    timeout_keep_alive: int = 5
    auth_mode: Optional[str] = None  # If None, auto-detect based on root_api_key
    root_api_key: Optional[str] = None
    # OIDC/LDAP authentication configuration
    oidc: Optional[OIDCConfig] = None
    ldap: Optional[LDAPConfig] = None
    profile_enabled: bool = False
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    with_bot: bool = False  # Enable Bot API proxy to Vikingbot
    bot_api_url: str = "http://localhost:18790"  # Vikingbot OpenAPIChannel URL (default port)
    encryption_enabled: bool = False  # Whether file-level AES encryption is enabled
    api_key_hashing_enabled: bool = False  # Whether API key Argon2id hashing is enabled (default: false, rely on file encryption)
    # When true, poll the shared key store and reload the in-memory index on change so
    # read replicas pick up writer-side user add/rotate/remove. Default off (single writer).
    api_key_watch_enabled: bool = False
    # Poll interval; each check only stats registry files and reads fully on change.
    api_key_watch_interval_seconds: float = 30.0
    account_store: AccountStoreConfig = Field(default_factory=AccountStoreConfig)
    # Trusted-mode identity registration is batched in memory; 0 disables it.
    trusted_identity_flush_interval_seconds: float = Field(300.0, ge=0)
    trusted_identity_pending_max_size: int = Field(10_000, gt=0)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    usage_reporter: UsageReporterConfig = Field(default_factory=UsageReporterConfig)
    # Built-in Redis TTL; disabled unless explicitly configured.
    ttl_adapter: Optional[TTLAdapterConfig] = None
    # Public-facing base URL emitted in MCP-issued upload instructions. See
    # ``openviking.server.mcp_endpoint._resolve_public_base_url`` for the full
    # resolution chain: env var > this field > X-Forwarded-Host/Proto > Host header
    # > listen-address fallback. Set this (or the env var) when the server runs
    # behind a reverse proxy that does not forward X-Forwarded-* headers.
    public_base_url: Optional[str] = None
    upload_signed_ttl_seconds: int = 600
    temp_upload: TempUploadConfig = Field(default_factory=TempUploadConfig)
    user_config_defaults: UserConfigDefaults = Field(default_factory=UserConfigDefaults)
    agent_evolution: AgentEvolutionConfig = Field(default_factory=AgentEvolutionConfig)
    tool_output_externalization: ToolOutputExternalizationConfig = Field(
        default_factory=ToolOutputExternalizationConfig
    )

    @field_validator("user_config_defaults", mode="before")
    @classmethod
    def normalize_user_config_defaults(cls, value: Any) -> Any:
        return value.model_dump() if isinstance(value, UserConfig) else value

    def get_effective_auth_mode(self) -> str:
        """Get effective auth mode, auto-detecting if not explicitly set.

        - If root_api_key is configured (non-empty) and auth_mode is None: api_key
        - If root_api_key is not configured and auth_mode is None: dev
        """
        auth_mode_text = str(self.auth_mode).strip() if self.auth_mode is not None else ""
        if auth_mode_text:
            return auth_mode_text

        if self.root_api_key is not None and str(self.root_api_key).strip():
            return AuthMode.API_KEY.value
        return AuthMode.DEV.value


def map_bind_host_to_loopback(host: str) -> str:
    """Map a server *bind* host to a client-connectable *loopback* host.

    ``server.host`` configures the address the server binds/listens on. A
    wildcard bind address such as ``0.0.0.0`` (or IPv6 ``::``) is valid to
    listen on but is *not* a destination a client can connect to. Clients that
    derive a connect URL from the configured host (the bot proxy, the bot's
    own config loader, ``doctor``) must translate the wildcard to loopback:

    - ``"0.0.0.0"``, ``""``, ``"*"``   -> ``"127.0.0.1"``
    - ``"::"``, ``"::0"``, ``"[::]"``  -> ``"[::1]"``
    - bare IPv6 literals (e.g. ``"::1"``) are bracketed for URL syntax
    - everything else passes through unchanged
    """
    host = str(host or "").strip()
    if host in ("0.0.0.0", "", "*"):
        return "127.0.0.1"
    if host in ("::", "::0", "[::]"):
        return "[::1]"
    if ":" in host and not (host.startswith("[") and host.endswith("]")):
        return f"[{host}]"
    return host


def get_server_url_from_server_data(server_data: object) -> str:
    """Return the loopback URL clients use for the configured OpenViking server."""
    if isinstance(server_data, dict):
        host_value = server_data.get("host")
        port_value = server_data.get("port")
    else:
        host_value = getattr(server_data, "host", None)
        port_value = getattr(server_data, "port", None)
    host = map_bind_host_to_loopback(str(host_value or "127.0.0.1"))
    port = str(port_value or "1933").strip()
    return f"http://{host}:{port}"


def _inherit_otel_service_names(server_data: Dict[str, Any], service_name: str) -> None:
    """Fill omitted OTel service_name fields from the top-level service name."""
    if "observability" not in server_data:
        server_data["observability"] = {}
    observability = server_data["observability"]
    if not isinstance(observability, dict):
        return

    for key in ("traces", "logs"):
        if key not in observability:
            observability[key] = {"service_name": service_name}
        elif isinstance(observability[key], dict) and "service_name" not in observability[key]:
            observability[key]["service_name"] = service_name

    if "metrics" not in observability:
        observability["metrics"] = {}
    metrics = observability["metrics"]
    if not isinstance(metrics, dict):
        return
    if "exporters" not in metrics:
        metrics["exporters"] = {}
    exporters = metrics["exporters"]
    if not isinstance(exporters, dict):
        return
    if "otel" not in exporters:
        exporters["otel"] = {"service_name": service_name}
    elif isinstance(exporters["otel"], dict) and "service_name" not in exporters["otel"]:
        exporters["otel"]["service_name"] = service_name


def load_server_config(config_path: Optional[str] = None) -> ServerConfig:
    """Load server configuration from ov.conf.

    Reads the ``server`` section of ov.conf and also ensures the full
    ov.conf is loaded into the OpenVikingConfigSingleton so that model
    and storage settings are available.

    Resolution chain:
      1. Explicit ``config_path`` (from --config)
      2. OPENVIKING_CONFIG_FILE environment variable
      3. ~/.openviking/ov.conf

    Args:
        config_path: Explicit path to ov.conf.

    Returns:
        ServerConfig instance with defaults for missing fields.

    Raises:
        FileNotFoundError: If no config file is found.
    """
    path = resolve_config_path(config_path, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF)
    if path is None:
        default_path_user = DEFAULT_CONFIG_DIR / DEFAULT_OV_CONF
        default_path_system = SYSTEM_CONFIG_DIR / DEFAULT_OV_CONF
        raise FileNotFoundError(
            f"OpenViking configuration file not found.\n"
            f"Please create {default_path_user} or {default_path_system}, or set {OPENVIKING_CONFIG_ENV}.\n"
            f"See: https://openviking.ai/docs"
        )

    data = load_json_config(path)
    server_data = data.get("server", {})
    if server_data is None:
        server_data = {}
    if not isinstance(server_data, dict):
        raise ValueError(f"Invalid server config in {path}: 'server' section must be an object")
    server_data = dict(server_data)
    service_name = normalize_service_name(data.get("service_name", DEFAULT_SERVICE_NAME))
    _inherit_otel_service_names(server_data, service_name)

    # Convert auth_mode string — built-in enums are converted to their string
    # value; custom modes are kept as-is for plugin extensibility.
    if "auth_mode" in server_data and isinstance(server_data["auth_mode"], str):
        try:
            server_data["auth_mode"] = AuthMode(server_data["auth_mode"]).value
        except ValueError:
            # Custom auth mode — keep as string for plugin registration
            pass

    # Get encryption enabled from config data directly (for test compatibility)
    encryption_enabled = data.get("encryption", {}).get("enabled", False)
    # Get API key hashing enabled from config data directly (under encryption namespace)
    # Default: false - rely on file-level encryption for API key protection
    api_key_hashing_enabled = (
        data.get("encryption", {}).get("api_key_hashing", {}).get("enabled", False)
    )

    # BREAKING CHANGE: Previously, encryption.enabled=true implicitly enabled API key Argon2id hashing.
    # Now, you must explicitly configure encryption.api_key_hashing.enabled=true to enable hashing.
    # When encryption.enabled=true but api_key_hashing.enabled=false (default),
    # API keys will be stored in plaintext within AES-GCM encrypted files.
    if encryption_enabled and not api_key_hashing_enabled:
        logger.info(
            "API key hashing is disabled while file encryption is enabled. "
            "Previously, encryption.enabled=true implicitly enabled API key Argon2id hashing. "
            "Now, API keys will be stored in plaintext within AES-GCM encrypted files. "
            "To maintain the previous behavior, set encryption.api_key_hashing.enabled=true. "
            "See documentation for more details."
        )

    warn_unknown_config_fields(
        data=server_data,
        model=ServerConfig,
        path_prefix="server",
        logger=logger,
    )

    try:
        config = ServerConfig.model_validate(server_data)
    except ValidationError as e:
        raise ValueError(
            f"Invalid server config in {path}:\n"
            f"{format_validation_error(root_model=ServerConfig, error=e, path_prefix='server')}"
        ) from e

    return config.model_copy(
        update={
            "encryption_enabled": encryption_enabled,
            "api_key_hashing_enabled": api_key_hashing_enabled,
        }
    )


_LOCALHOST_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _is_localhost(host: str) -> bool:
    """Return True if *host* resolves to a loopback address."""
    return host in _LOCALHOST_HOSTS


def load_bot_gateway_token(config_path: Optional[str] = None) -> str:
    """Load bot gateway token from ov.conf bot.gateway.token."""
    path = resolve_config_path(config_path, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF)
    if path is None:
        return ""

    data = load_json_config(path)
    bot_config = data.get("bot", {})
    if not isinstance(bot_config, dict):
        return ""
    gateway_config = bot_config.get("gateway", {})
    if not isinstance(gateway_config, dict):
        return ""
    return gateway_config.get("token", "") or ""


def validate_server_config(config: ServerConfig) -> None:
    """Validate server config for safe startup.

    Validation is delegated to the auth plugin registered for the effective
    auth_mode. Built-in plugins (dev, api_key, trusted) preserve the original
    validation behaviour.

    If auth_mode is not explicitly configured:
    - If root_api_key is configured (non-empty): auto-select api_key mode
    - If root_api_key is not configured: auto-select dev mode

    Raises:
        SystemExit: If the configuration is unsafe.
    """
    # Check for empty root_api_key
    if config.root_api_key == "":
        logger.error(
            "Invalid server.root_api_key: empty string is not allowed. "
            "Set a non-empty server.root_api_key in ov.conf and restart. "
            "Only remove this setting if the selected auth mode does not require a root key; "
            "trusted and api_key modes require it even on localhost."
        )
        sys.exit(1)

    effective_auth_mode = config.get_effective_auth_mode()

    # Ensure built-in plugins are registered before validation.
    # If a non-built-in plugin has already claimed a built-in mode name,
    # log a security warning and forcefully override it.
    from openviking.server.auth.plugins import ApiKeyAuthPlugin, DevAuthPlugin, TrustedAuthPlugin

    registry = get_registry()
    _BUILTIN_PLUGINS = {
        "dev": DevAuthPlugin,
        "api_key": ApiKeyAuthPlugin,
        "trusted": TrustedAuthPlugin,
    }
    for mode, plugin_cls in _BUILTIN_PLUGINS.items():
        existing = registry.get(mode)
        if existing is None:
            registry.register(plugin_cls)
        elif existing is not plugin_cls:
            logger.warning(
                "SECURITY: Auth mode %r was registered by %s but is being "
                "overridden by the built-in %s.",
                mode,
                existing.__name__,
                plugin_cls.__name__,
            )
            registry._plugins[mode] = plugin_cls

    plugin_cls = registry.get(effective_auth_mode)
    if plugin_cls is None:
        logger.error(
            "Unknown auth_mode: %r. No auth plugin registered for this mode. Registered modes: %s.",
            effective_auth_mode,
            ", ".join(registry.list_modes()),
        )
        sys.exit(1)

    plugin_cls().validate_config(config)
