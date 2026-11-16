# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from __future__ import annotations

import math
import os
from enum import Enum
from typing import Any, List, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator

from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


class DirectoryMarkerMode(str, Enum):
    """How S3 directory markers should be persisted."""

    NONE = "none"
    EMPTY = "empty"
    NONEMPTY = "nonempty"


class S3Config(BaseModel):
    """Configuration for S3 backend."""

    bucket: Optional[str] = Field(default=None, description="S3 bucket name")

    region: Optional[str] = Field(
        default=None,
        description="AWS region where the bucket is located (e.g., us-east-1, cn-beijing)",
    )

    access_key: Optional[str] = Field(
        default=None,
        description="S3 access key ID. If not provided, RAGFS may attempt to use environment variables or IAM roles.",
    )

    secret_key: Optional[str] = Field(
        default=None,
        description="S3 secret access key corresponding to the access key ID.",
    )

    endpoint: Optional[str] = Field(
        default=None,
        description="Custom S3 endpoint URL. Required for S3-compatible services like MinIO or LocalStack. "
        "Leave empty for standard AWS S3.",
    )

    prefix: Optional[str] = Field(
        default="",
        description="Optional key prefix for namespace isolation. All objects will be stored under this prefix.",
    )

    use_ssl: bool = Field(
        default=True,
        description="Enable/Disable SSL (HTTPS) for S3 connections. Set to False for local testing without HTTPS.",
    )

    use_path_style: bool = Field(
        default=True,
        description="true represent UsePathStyle for MinIO and some S3-compatible services; false represent VirtualHostStyle for TOS  and some S3-compatible services.",
    )

    s3_vendor: Literal["standard", "aliyun_oss"] = Field(
        default="standard",
        description="S3 vendor behavior. Use 'aliyun_oss' for Alibaba Cloud OSS.",
    )

    directory_marker_mode: DirectoryMarkerMode = Field(
        default=DirectoryMarkerMode.EMPTY,
        description="How to persist S3 directory markers: 'none' skips marker creation, 'empty' writes a zero-byte marker, and 'nonempty' writes a non-empty marker payload. Defaults to 'empty'.",
    )

    disable_batch_delete: bool = Field(
        default=False,
        description="Disable batch delete (DeleteObjects) and use sequential single-object deletes instead. "
        "Required for S3-compatible services like Alibaba Cloud OSS that require a Content-MD5 header "
        "for DeleteObjects but AWS SDK v2 does not send it by default. Defaults to False.",
    )

    normalize_encoding_chars: str = Field(
        default="?#%+@",
        description="Characters to escape in S3 object keys as !HH hexadecimal bytes. "
        "Set to an empty string to disable key normalization. Defaults to ?#%+@.",
    )

    auto_detect_content_type: bool = Field(
        default=False,
        description="Automatically infer S3 object Content-Type from the object key filename extension "
        "during uploads. Disabled by default for backward compatibility.",
    )

    def validate_config(self):
        """Validate S3 configuration completeness"""
        missing = []
        if not self.bucket:
            missing.append("bucket")
        if not self.endpoint:
            missing.append("endpoint")
        if not self.region:
            missing.append("region")
        if not self.access_key:
            missing.append("access_key")
        if not self.secret_key:
            missing.append("secret_key")

        if missing:
            raise ValueError(f"S3 backend requires the following fields: {', '.join(missing)}")

        return self


class QueueFSConfig(BaseModel):
    """Configuration for QueueFS backend."""

    mode: str = Field(
        default="shared",
        description="QueueFS namespace mode: 'shared' | 'worker'",
    )

    backend: str = Field(
        default="sqlite",
        description="QueueFS backend: 'memory' | 'sqlite' | 'sqlite3' | 'cache'",
    )

    db_path: Optional[str] = Field(
        default=None,
        description="SQLite database path for QueueFS when backend is 'sqlite' or 'sqlite3'.",
    )

    recover_stale_sec: int = Field(
        default=0,
        description="Recover processing messages older than this many seconds on startup (0 = recover all).",
    )

    busy_timeout_ms: int = Field(
        default=5000,
        description="SQLite busy timeout for QueueFS in milliseconds.",
    )

    cache_key_prefix: str = Field(
        default="default",
        description="Queue key namespace when backend is 'cache'.",
    )

    @model_validator(mode="after")
    def validate_config(self):
        """Validate QueueFS mode and backend choices."""
        valid_modes = {"shared", "worker"}
        if self.mode not in valid_modes:
            raise ValueError("queuefs mode must be one of: 'shared', 'worker'")

        valid_backends = {"memory", "sqlite", "sqlite3", "cache"}
        if self.backend not in valid_backends:
            raise ValueError(
                "queuefs backend must be one of: 'memory', 'sqlite', 'sqlite3', 'cache'; "
                "backend='redis' was removed, use backend='cache' with top-level cache.provider/cache.params"
            )
        if self.recover_stale_sec < 0:
            raise ValueError("queuefs recover_stale_sec must be >= 0")
        if self.busy_timeout_ms < 0:
            raise ValueError("queuefs busy_timeout_ms must be >= 0")
        return self


class AGFSCacheTraversalMode(str, Enum):
    """Traversal strategy for cache-aware recursive RAGFS APIs."""

    BACKEND = "backend"
    CACHED_TRAVERSAL = "cached_traversal"


class AGFSCacheFSConfig(BaseModel):
    """CacheFS behavior independent from the selected global Provider."""

    backend: Literal["local", "cache"] = Field(
        default="local",
        description="CacheFS backend: 'local' | 'cache'",
    )
    shared_redis_ttl_seconds: int = Field(
        default=0,
        description="TTL override for cache query buckets on a shared Redis service; 0 keeps the provider default",
    )
    namespace: str = Field(default="openviking", description="RAGFS cache namespace")
    max_file_size_bytes: int = Field(
        default=1024 * 1024,
        description="Maximum full-file object size admitted to cache",
    )
    traversal_mode: AGFSCacheTraversalMode = Field(
        default=AGFSCacheTraversalMode.BACKEND,
        description="Traversal strategy for tree, glob, and grep",
    )
    bypass_prefixes: list[str] = Field(
        default_factory=list,
        description="Path prefixes that bypass cache",
    )

    @model_validator(mode="after")
    def validate_config(self):
        """Validate CacheFS query-cache settings."""
        if self.shared_redis_ttl_seconds < 0:
            raise ValueError("cachefs shared_redis_ttl_seconds must be >= 0")
        return self


class RedisCacheConfig(BaseModel):
    """Configuration for Redis cache provider."""

    mode: str = Field(default="standalone", description="Redis deployment mode")
    endpoints: list[str] = Field(
        default_factory=lambda: ["redis://127.0.0.1:6379"],
        description="Redis endpoint URLs",
    )
    username: str = Field(default="", description="Redis ACL username")
    password_env: str = Field(default="", description="Environment variable containing password")
    password: str = Field(
        default="",
        description="Legacy plaintext Redis password; prefer password_env",
        repr=False,
    )
    master_name: Optional[str] = Field(default=None, description="Sentinel master name")
    sentinel_username: str = Field(default="", description="Sentinel ACL username")
    sentinel_password_env: str = Field(
        default="", description="Environment variable containing Sentinel password"
    )
    sentinel_password: str = Field(
        default="",
        description="Legacy plaintext Sentinel password; prefer sentinel_password_env",
        repr=False,
    )
    db: int = Field(default=0, description="Redis database number")
    pool_size: int = Field(default=32, description="Redis command concurrency")
    connect_timeout_ms: int = Field(default=10000, description="Redis connect timeout")
    command_timeout_ms: int = Field(default=0, description="Redis command timeout; 0 disables command timeout")
    default_ttl_seconds: int = Field(default=300, description="Redis default cache TTL")
    tls_insecure_skip_verify: bool = Field(
        default=False, description="Skip Redis TLS certificate verification"
    )

    @model_validator(mode="after")
    def validate_config(self):
        if self.mode not in {"standalone", "cluster", "sentinel"}:
            raise ValueError("redis mode must be standalone, cluster, or sentinel")
        if not self.endpoints:
            raise ValueError("redis endpoints must not be empty")
        schemes = set()
        for endpoint in self.endpoints:
            parsed = urlparse(endpoint)
            if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
                raise ValueError("redis endpoints must use redis:// or rediss:// URLs")
            schemes.add(parsed.scheme)
            try:
                port = parsed.port
            except ValueError as error:
                raise ValueError("redis endpoint port is invalid") from error
            if port == 0:
                raise ValueError("redis endpoint port is invalid")
            if (
                parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "redis endpoints must not include credentials, database paths, "
                    "query parameters, or fragments; use dedicated redis fields"
                )
        if self.mode == "standalone" and len(self.endpoints) != 1:
            raise ValueError("redis standalone mode requires exactly one endpoint")
        if self.mode == "cluster" and self.db != 0:
            raise ValueError("redis cluster mode requires db=0")
        if self.mode == "sentinel" and not (self.master_name or "").strip():
            raise ValueError("redis sentinel mode requires master_name")
        if self.db < 0 or self.db > 255:
            raise ValueError("redis db must be between 0 and 255")
        if self.pool_size <= 0:
            raise ValueError("redis pool_size must be > 0")
        if self.connect_timeout_ms <= 0:
            raise ValueError("redis connect_timeout_ms must be > 0")
        if self.command_timeout_ms < 0:
            raise ValueError("redis command_timeout_ms must be >= 0")
        if self.default_ttl_seconds < 0:
            raise ValueError("redis default_ttl_seconds must be >= 0")
        if len(schemes) != 1:
            raise ValueError("redis endpoints must use the same URL scheme")
        if self.password_env and self.password:
            raise ValueError("redis password and password_env cannot both be configured")
        if self.sentinel_password_env and self.sentinel_password:
            raise ValueError(
                "redis sentinel_password and sentinel_password_env cannot both be configured"
            )
        if self.tls_insecure_skip_verify and schemes != {"rediss"}:
            raise ValueError("redis tls_insecure_skip_verify requires rediss:// endpoints")
        return self


class AGFSPathLockConfig(BaseModel):
    """Configuration for the native RAGFS path lock service."""

    @model_validator(mode="after")
    def ignore_deprecated_lock_timeout(self):
        """Warn and force the deprecated timeout back to the fixed runtime value."""
        if "lock_timeout_secs" in self.model_fields_set:
            logger.warning(
                "AGFSPathLockConfig: 'storage.agfs.pathlock.lock_timeout_secs' is deprecated "
                "and ignored; the runtime wait timeout is fixed at 0.0 seconds."
            )
            self.lock_timeout_secs = 0.0
        return self

    provider: str = Field(
        default="filesystem",
        description="PathLock provider: 'filesystem' | 'memory' | 'sqlite' | 'postgres' | 'cache'",
    )
    postgres_dsn_env: Optional[str] = Field(
        default=None,
        description="Environment variable containing the PostgreSQL connection string.",
    )
    sqlite_path: Optional[str] = Field(
        default=None,
        description="Absolute local SQLite lock database file shared by all participating processes. "
        "Defaults to '{storage.workspace}/_system/pathlock/pathlock.db' when not set.",
    )
    lock_timeout_secs: float = Field(
        default=0.0,
        description="Deprecated internal field. Runtime auto-pathlock wait timeout is fixed at 0.0 seconds.",
    )
    lock_expire_secs: float = Field(
        default=30.0,
        description="Seconds before an unrefreshed lock token becomes stale.",
    )

    @model_validator(mode="after")
    def validate_config(self):
        """Validate provider and timeout/expiry ranges."""
        if self.provider not in {"filesystem", "memory", "sqlite", "postgres", "cache"}:
            raise ValueError(
                "pathlock provider must be one of: 'filesystem', 'memory', 'sqlite', 'postgres', 'cache'"
            )
        if self.postgres_dsn_env is not None and not self.postgres_dsn_env.strip():
            raise ValueError("pathlock postgres_dsn_env must be nonempty")
        if self.provider == "postgres" and self.postgres_dsn_env is None:
            raise ValueError("pathlock postgres_dsn_env is required for PostgreSQL")
        if (
            self.provider == "sqlite"
            and self.sqlite_path is not None
            and not os.path.isabs(self.sqlite_path)
        ):
            raise ValueError("pathlock sqlite_path must be an absolute local file path")
        if not math.isfinite(self.lock_expire_secs) or self.lock_expire_secs < 1.0:
            raise ValueError("pathlock lock_expire_secs must be finite and >= 1.0")
        return self


class AGFSCoordinationConfig(BaseModel):
    """Native coordination backend for leadership and revisions."""

    provider: Literal["memory", "sqlite", "cache"] = Field(
        default="memory",
        description="memory: process-wide; sqlite: local cross-process; cache: distributed.",
    )
    sqlite_path: Optional[str] = Field(
        default=None,
        description="Absolute local SQLite file shared by participating processes. Required "
        "for sqlite; independent of storage.workspace so it can stay off EFS/NFS.",
    )
    operation_timeout_ms: Optional[int] = Field(
        default=None,
        gt=0,
        description="Deadline for one cache coordination operation in milliseconds. Defaults "
        "to 5000 in Rust; independent of cache command timeouts and cannot be disabled.",
    )

    @model_validator(mode="after")
    def validate_config(self):
        if self.provider == "sqlite":
            if not self.sqlite_path or not os.path.isabs(self.sqlite_path):
                raise ValueError("coordination.sqlite_path must be an absolute local file path")
        elif self.sqlite_path is not None:
            raise ValueError("coordination.sqlite_path requires provider='sqlite'")
        if self.provider != "cache" and self.operation_timeout_ms is not None:
            raise ValueError("coordination.operation_timeout_ms requires provider='cache'")
        return self


