# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from __future__ import annotations

import os
from typing import Any, List, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator

from openviking_cli.utils.config.agfs_config_backends import (
    AGFSCacheFSConfig,
    AGFSCacheTraversalMode,
    AGFSCoordinationConfig,
    AGFSPathLockConfig,
    DirectoryMarkerMode,
    QueueFSConfig,
    RedisCacheConfig,
    S3Config,
)

class AGFSConfig(BaseModel):
    """Configuration for RAGFS (Rust-based AGFS)."""

    name: str = Field(
        default="primary",
        description="Logical backend name, globally unique across primary and all backups",
    )

    path: Optional[str] = Field(
        default=None,
        description="[Deprecated in favor of `storage.workspace`] RAGFS data storage path. This will be ignored if `storage.workspace` is set.",
    )

    port: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS service port. Ignored by RAGFS.",
    )

    log_level: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS log level. Ignored by RAGFS.",
    )

    url: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS service URL. Ignored by RAGFS.",
    )

    mode: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS client mode. Ignored by RAGFS.",
    )

    impl: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS binding implementation selector. Ignored by RAGFS.",
    )

    backend: str = Field(
        default="local", description="RAGFS storage backend: 'local' | 's3' | 'memory'"
    )

    timeout: int = Field(default=10, description="RAGFS request timeout (seconds)")

    queue_db_path: Optional[str] = Field(
        default=None,
        description="Override path of the queuefs sqlite database file. "
        "Defaults to '{storage.workspace}/_system/queue/queue.db' when not set. "
        "Useful when the workspace volume does not support sqlite (e.g. some network filesystems).",
    )

    queuefs: QueueFSConfig = Field(
        default_factory=QueueFSConfig,
        description="QueueFS configuration.",
    )

    cachefs: AGFSCacheFSConfig = Field(
        default_factory=AGFSCacheFSConfig,
        description="CacheFS configuration.",
    )

    pathlock: AGFSPathLockConfig = Field(
        default_factory=AGFSPathLockConfig,
        description="Native RAGFS path lock configuration.",
    )

    coordination: AGFSCoordinationConfig = Field(
        default_factory=AGFSCoordinationConfig,
        description="Native coordination for leader leases and revisions; defaults to memory.",
    )

    retry_times: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS retry count. Ignored by RAGFS.",
    )

    use_ssl: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS SSL switch. Ignored by RAGFS.",
    )

    lib_path: Any = Field(
        default=None,
        exclude=True,
        description="[Deprecated] Legacy AGFS binding library path. Ignored by RAGFS.",
    )

    # S3 backend configuration
    # These settings are used when backend is set to 's3'.
    # RAGFS will act as a gateway to the specified S3 bucket.
    s3: S3Config = Field(default_factory=lambda: S3Config(), description="S3 backend configuration")

    # Multi-write configuration
    backups: Optional[dict[str, Any]] = Field(
        default=None, description="Multi-write backups configuration. None = single backend mode."
    )
    redirects: Optional[List[dict[str, Any]]] = Field(
        default=None, description="[Deprecated] Primary redirect policies. Ignored by V2."
    )

    @model_validator(mode="after")
    def validate_config(self):
        """Validate configuration completeness and consistency"""
        deprecated_fields = (
            "port",
            "log_level",
            "url",
            "mode",
            "impl",
            "retry_times",
            "use_ssl",
            "lib_path",
        )
        for field_name in deprecated_fields:
            if field_name in self.model_fields_set:
                logger.warning(
                    "AGFSConfig: 'storage.agfs.%s' is deprecated and ignored after the RAGFS migration.",
                    field_name,
                )

        if self.backend not in ["local", "s3", "memory"]:
            raise ValueError(
                f"Invalid RAGFS backend: '{self.backend}'. Must be one of: 'local', 's3', 'memory'"
            )

        if self.backend == "local":
            pass

        elif self.backend == "s3":
            # Validate S3 configuration
            self.s3.validate_config()

        if self.queue_db_path is not None and self.queuefs.db_path is None:
            logger.warning(
                "AGFSConfig: 'storage.agfs.queue_db_path' is deprecated; "
                "prefer 'storage.agfs.queuefs.db_path'."
            )

        if self.queuefs.backend == "memory":
            if self.queuefs.db_path is not None or self.queue_db_path is not None:
                logger.warning(
                    "AGFSConfig: QueueFS backend is 'memory'; "
                    "db_path/queue_db_path will be ignored."
                )

        if self.backups is not None:
            initial_partitions = self.backups.get("initial_partitions", 16)
            if (
                not isinstance(initial_partitions, int)
                or isinstance(initial_partitions, bool)
                or not 1 <= initial_partitions <= 1024
            ):
                raise ValueError("backups initial_partitions must be between 1 and 1024")

            checkpoint_interval_secs = self.backups.get("checkpoint_interval_secs", 86400)
            if (
                not isinstance(checkpoint_interval_secs, int)
                or isinstance(checkpoint_interval_secs, bool)
                or checkpoint_interval_secs < 60
            ):
                raise ValueError("backups checkpoint_interval_secs must be at least 60")

            if self.backups.get("provider", "filesystem") not in {"filesystem", "cache"}:
                raise ValueError("backups provider must be 'filesystem' or 'cache'")

            names = set()
            for item in self.backups.get("items", []):
                if not isinstance(item, dict):
                    raise ValueError("backups items must be objects")
                name = item.get("name")
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("backup name must not be empty")
                name = name.strip()
                if name == "primary":
                    raise ValueError("backup name 'primary' is reserved")
                if name in names:
                    raise ValueError("backup names must be unique")
                names.add(name)

        return self
