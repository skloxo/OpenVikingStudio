# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, Optional

from openviking_cli.session.user_id import UserIdentifier

from .config_loader import expand_config_environment, resolve_config_path
from .consts import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_OV_CONF,
    OPENVIKING_CONFIG_ENV,
    SYSTEM_CONFIG_DIR,
)

if TYPE_CHECKING:
    from .open_viking_config import OpenVikingConfig

_config_logger: Optional[logging.Logger] = None


def _get_config_logger() -> logging.Logger:
    global _config_logger
    if _config_logger is None:
        from openviking_cli.utils.logger import get_logger

        _config_logger = get_logger(__name__)
    return _config_logger


class OpenVikingConfigSingleton:
    """Global singleton for OpenVikingConfig.

    Resolution chain for ov.conf:
      1. Explicit path passed to initialize()
      2. OPENVIKING_CONFIG_FILE environment variable
      3. ~/.openviking/ov.conf
      4. /etc/openviking/ov.conf
      5. Error with clear guidance

    ``_initializing`` prevents a same-thread deadlock: loading the config
    triggers pydantic validation which can import modules whose module-level
    ``get_logger()`` calls ``get_instance()`` again *before* the lock is
    released.  The flag is checked **before** ``_lock.acquire()`` so the
    re-entrant call raises immediately, letting ``_load_log_config()``
    fall back to default logging.
    """

    _instance: Optional[OpenVikingConfig] = None
    _lock: Lock = Lock()
    _initializing: bool = False
    _config_file: Optional[Path] = None
    _config_file_revision: Optional[str] = None
    _config_file_content: Optional[bytes] = None

    @classmethod
    def get_instance(cls) -> OpenVikingConfig:
        """Get the global singleton instance.

        Raises FileNotFoundError if no config file is found.
        Raises RuntimeError if called re-entrantly during initialization.
        """
        if cls._initializing:
            raise RuntimeError(
                "OpenVikingConfigSingleton is still initializing "
                "(re-entrant call detected, falling back to defaults)"
            )
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._initializing = True
                    try:
                        config_path = resolve_config_path(
                            None, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF
                        )
                        if config_path is not None:
                            cls._instance = cls._load_from_file(str(config_path))
                        else:
                            cfg_mod = sys.modules.get("openviking_cli.utils.config.open_viking_config")
                            default_user_dir = getattr(cfg_mod, "DEFAULT_CONFIG_DIR", DEFAULT_CONFIG_DIR)
                            default_sys_dir = getattr(cfg_mod, "SYSTEM_CONFIG_DIR", SYSTEM_CONFIG_DIR)
                            default_path_user = default_user_dir / DEFAULT_OV_CONF
                            default_path_system = default_sys_dir / DEFAULT_OV_CONF
                            raise FileNotFoundError(
                                f"OpenViking configuration file not found.\n"
                                f"Please create {default_path_user} or {default_path_system}, "
                                f"or set {OPENVIKING_CONFIG_ENV}.\n"
                                f"See: https://openviking.ai/docs"
                            )
                    finally:
                        cls._initializing = False
                    from openviking_cli.utils.logger import reconfigure_logging

                    reconfigure_logging()
        return cls._instance

    @classmethod
    def initialize(
        cls,
        config_dict: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> OpenVikingConfig:
        """Initialize the global singleton.

        Args:
            config_dict: Direct config dictionary (highest priority).
            config_path: Explicit path to ov.conf file.
        """
        with cls._lock:
            cls._initializing = True
            try:
                if config_dict is not None:
                    cls._instance = _load_model_cls().from_dict(config_dict)
                    cls._config_file = None
                    cls._config_file_revision = None
                    cls._config_file_content = None
                else:
                    path = resolve_config_path(config_path, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF)
                    if path is not None:
                        cls._instance = cls._load_from_file(str(path))
                    else:
                        cfg_mod = sys.modules.get("openviking_cli.utils.config.open_viking_config")
                        default_user_dir = getattr(cfg_mod, "DEFAULT_CONFIG_DIR", DEFAULT_CONFIG_DIR)
                        default_sys_dir = getattr(cfg_mod, "SYSTEM_CONFIG_DIR", SYSTEM_CONFIG_DIR)
                        default_path_user = default_user_dir / DEFAULT_OV_CONF
                        default_path_system = default_sys_dir / DEFAULT_OV_CONF
                        raise FileNotFoundError(
                            f"OpenViking configuration file not found.\n"
                            f"Please create {default_path_user} or {default_path_system}, "
                            f"or set {OPENVIKING_CONFIG_ENV}.\n"
                            f"See: https://openviking.ai/docs"
                        )
            finally:
                cls._initializing = False
        from openviking_cli.utils.logger import reconfigure_logging

        reconfigure_logging()
        return cls._instance

    @classmethod
    def _load_from_file(cls, config_file: str) -> "OpenVikingConfig":
        """Load configuration from JSON config file."""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file does not exist: {config_file}")

            data = config_path.read_bytes()
            raw = data.decode("utf-8-sig")

            raw = expand_config_environment(raw)
            config_data = json.loads(raw)

            config = _load_model_cls().from_dict(config_data)
            cls._config_file = config_path.resolve()
            cls._config_file_revision = hashlib.sha256(data).hexdigest()
            cls._config_file_content = data
            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Config file JSON format error: {e}")
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to load config file: {e}")

    @classmethod
    def set_instance(cls, config: "OpenVikingConfig") -> None:
        """Atomically publish an already-built validated configuration."""
        with cls._lock:
            cls._instance = config

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            cls._instance = None
            cls._config_file = None
            cls._config_file_revision = None
            cls._config_file_content = None

    @classmethod
    def get_config_file_content(cls) -> Optional[bytes]:
        """Return the exact startup bytes for recovery, even after subsequent saves."""
        return cls._config_file_content

    @classmethod
    def get_config_file_revision(cls) -> Optional[str]:
        """Return the revision of the complete file read at startup."""
        return cls._config_file_revision

    @classmethod
    def get_config_file(cls) -> Optional[Path]:
        """Return the actual startup file, not a newly resolved default path."""
        return cls._config_file


# Global convenience function
def _load_model_cls():
    from .open_viking_config import OpenVikingConfig
    return OpenVikingConfig

def _singleton_get_openviking_config() -> "OpenVikingConfig":
    return OpenVikingConfigSingleton.get_instance()


def set_openviking_config(config: OpenVikingConfig) -> None:
    """Atomically publish an already-built OpenVikingConfig."""
    OpenVikingConfigSingleton.set_instance(config)


def is_valid_openviking_config(config: OpenVikingConfig) -> bool:
    """
    Check if OpenVikingConfig is valid.

    Note: Most validation is now handled by Pydantic validators in individual config classes.
    This function only validates cross-config consistency.

    Raises:
        ValueError: If configuration is invalid with detailed error messages

    Returns:
        bool: True if configuration is valid
    """
    errors = []

    # Validate account identifier
    if not config.default_account or not config.default_account.strip():
        errors.append("Default account identifier cannot be empty")

    if errors:
        error_message = "Invalid OpenViking configuration:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        raise ValueError(error_message)

    return True


def initialize_openviking_config(
    user: Optional[UserIdentifier] = None,
    path: Optional[str] = None,
) -> OpenVikingConfig:
    """
    Initialize OpenViking configuration with provided parameters.

    Loads ov.conf from the standard resolution chain, then applies
    parameter overrides.

    Args:
        user: UserIdentifier for session management
        path: Optional local workspace override for the service

    Returns:
        Configured OpenVikingConfig instance

    Raises:
        ValueError: If the resulting configuration is invalid
        FileNotFoundError: If no config file is found
    """
    from .open_viking_config import get_openviking_config
    config = get_openviking_config()

    if user:
        # Set user if provided, like a email address or a account_id
        config.default_account = user._account_id
        config.default_user = user._user_id

    # Configure storage based on provided parameters
    if path:
        # Explicit local workspace override
        config.storage.agfs.backend = config.storage.agfs.backend or "local"
        config.storage.vectordb.backend = config.storage.vectordb.backend or "local"
        # Resolve and update workspace + dependent paths (model_validator won't
        # re-run on attribute assignment, so sync agfs.path / vectordb.path here).
        workspace_path = Path(path).expanduser().resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)
        resolved = str(workspace_path)
        config.storage.workspace = resolved
        config.storage.agfs.path = resolved
        config.storage.vectordb.path = resolved

    config.storage.vectordb.apply_resolved_dimension(config.embedding.dimension)

    # Validate configuration
    if not is_valid_openviking_config(config):
        raise ValueError("Invalid OpenViking configuration")

    return config
