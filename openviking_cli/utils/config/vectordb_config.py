# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, StrictInt, model_validator

from openviking_cli.utils.logger import get_logger

COLLECTION_NAME = "context"
DEFAULT_PROJECT_NAME = "default"
DEFAULT_INDEX_NAME = "default"
logger = get_logger(__name__)


class VolcengineConfig(BaseModel):
    """Configuration for Volcengine VikingDB."""

    ak: Optional[str] = Field(default=None, description="Volcengine Access Key")
    sk: Optional[str] = Field(default=None, description="Volcengine Secret Key")
    api_key: Optional[str] = Field(
        default=None,
        description="Optional VikingDB Data API key for data-plane-only access",
    )
    session_token: Optional[str] = Field(
        default=None,
        description="Optional Volcengine STS security token for temporary credentials",
    )
    region: Optional[str] = Field(
        default=None, description="Volcengine region (e.g., 'cn-beijing')"
    )
    host: Optional[str] = Field(
        default=None,
        description=(
            "Optional VikingDB data API host. "
            "Used together with `api_key` for data-plane-only access."
        ),
    )


class VikingDBConfig(BaseModel):
    """Configuration for VikingDB private deployment."""

    host: Optional[str] = Field(default=None, description="VikingDB service host")
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Custom headers for requests"
    )


from .opengauss_config import (
    _OPENGAUSS_BUILD_PARAMS,
    _OPENGAUSS_COMMON_QUANT_BUILD_PARAMS,
    _OPENGAUSS_DISTANCE_METRICS,
    _OPENGAUSS_INDEX_TYPES,
    _OPENGAUSS_INDEX_TYPE_ALIASES,
    _OPENGAUSS_MODES,
    _OPENGAUSS_SEARCH_ALIASES,
    _OPENGAUSS_SEARCH_PARAMS,
    CuVSConfig,
    OpenGaussConfig,
    OpenGaussIndexConfig,
    PgvectorConfig,
    normalize_opengauss_index_type,
    resolve_opengauss_index_spec,
)

class VectorDBBackendConfig(BaseModel):
    """
    Configuration for VectorDB backend.

    This configuration class consolidates all settings related to the VectorDB backend,
    including type, connection details, and backend-specific parameters.
    """

    backend: str = Field(
        default="local",
        description=(
            "VectorDB backend type: 'local', 'cuvs', 'http', "
            "'volcengine' (AK/SK signed or API key data-plane only), "
            "'vikingdb' (private deployment), 'opengauss', or 'pgvector'"
        ),
    )

    enable_path_glob: Optional[bool] = Field(
        default=None,
        description=(
            "Enable remote PathGlob for this vector backend. "
            "True enables it, False disables it, and None uses the adapter's default. "
            "VikingDB and Volcengine adapters enable it by default."
        ),
    )

    name: Optional[str] = Field(default=COLLECTION_NAME, description="Collection name for VectorDB")

    path: Optional[str] = Field(
        default=None,
        description="[Deprecated in favor of `storage.workspace`] Local storage path for 'local' type. This will be ignored if `storage.workspace` is set.",
    )

    url: Optional[str] = Field(
        default=None,
        description="Remote service URL for 'http' type (e.g., 'http://localhost:5000')",
    )

    project_name: Optional[str] = Field(
        default=DEFAULT_PROJECT_NAME, description="project name", alias="project"
    )

    index_name: Optional[str] = Field(
        default=DEFAULT_INDEX_NAME,
        description="Default index name for VectorDB operations",
    )

    distance_metric: str = Field(
        default="cosine",
        description="Distance metric for vector similarity search (e.g., 'cosine', 'l2', 'ip')",
    )

    dimension: int = Field(
        default=0,
        description="Dimension of vector embeddings",
    )

    sparse_weight: float = Field(
        default=0.0,
        description=(
            "Sparse weight for hybrid vector search. "
            "When > 0, sparse vectors are used for index build and search."
        ),
    )

    volcengine: Optional[VolcengineConfig] = Field(
        default_factory=VolcengineConfig,
        description="Volcengine VikingDB configuration for 'volcengine' type",
    )

    # VikingDB private deployment mode
    vikingdb: Optional[VikingDBConfig] = Field(
        default_factory=VikingDBConfig,
        description="VikingDB private deployment configuration for 'vikingdb' type",
    )

    cuvs: Optional[CuVSConfig] = Field(
        default_factory=CuVSConfig,
        description="NVIDIA cuVS dense-vector search configuration for the 'cuvs' backend",
    )

    opengauss: Optional[OpenGaussConfig] = Field(
        default_factory=OpenGaussConfig,
        description="openGauss DataVec configuration for the 'opengauss' backend",
    )

    custom_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom parameters for custom backend adapters",
    )

    pgvector: Optional[PgvectorConfig] = Field(default=None)

    @model_validator(mode="after")
    def validate_config(self):
        """Validate configuration completeness and consistency"""
        standard_backends = [
            "local",
            "cuvs",
            "http",
            "volcengine",
            "vikingdb",
            "opengauss",
            "pgvector",
        ]

        # Allow custom backend classes (containing dot) without standard validation
        if "." in self.backend:
            logger.info("Using custom VectorDB backend: %s", self.backend)
            return self

        if self.backend not in standard_backends:
            raise ValueError(
                f"Invalid VectorDB backend: '{self.backend}'. Must be one of: {standard_backends} "
                "or a valid Python class path."
            )

        if self.backend in {"local", "cuvs"}:
            pass

        elif self.backend == "http":
            if not self.url:
                raise ValueError("VectorDB http backend requires 'url' to be set")

        elif self.backend == "volcengine":
            if self.volcengine and self.volcengine.host:
                self.volcengine.host = self.volcengine.host.strip().rstrip("/")

            uses_api_key = bool(self.volcengine and self.volcengine.api_key)
            if uses_api_key:
                if not self.volcengine or not (self.volcengine.host or self.volcengine.region):
                    raise ValueError(
                        "VectorDB volcengine backend with 'api_key' requires 'host' or 'region' to be set"
                    )
            else:
                if not self.volcengine or not self.volcengine.ak or not self.volcengine.sk:
                    raise ValueError(
                        "VectorDB volcengine backend requires 'ak' and 'sk' to be set "
                        "when 'api_key' is not configured"
                    )
                if not self.volcengine.region:
                    raise ValueError("VectorDB volcengine backend requires 'region' to be set")
            if self.volcengine and self.volcengine.host and not uses_api_key:
                logger.warning(
                    "VectorDB volcengine backend: 'volcengine.host' is ignored in AK/SK mode. "
                    "Using region-based console/data hosts for region='%s'.",
                    self.volcengine.region or "",
                )

        elif self.backend == "vikingdb":
            if not self.vikingdb or not self.vikingdb.host:
                raise ValueError("VectorDB vikingdb backend requires 'host' to be set")

        elif self.backend == "pgvector":
            if self.pgvector is None:
                raise ValueError("VectorDB pgvector backend requires 'pgvector' config")
            if self.distance_metric not in {"cosine", "l2", "ip", "l1"}:
                raise ValueError("pgvector distance_metric must be cosine, l2, ip or l1")
            if self.dimension > 16000:
                raise ValueError("pgvector vector supports at most 16000 dimensions")
            if self.dimension > 2000 and self.pgvector.index_type == "hnsw":
                raise ValueError("pgvector vector HNSW supports at most 2000 dimensions; use flat")
        elif self.backend == "opengauss":
            if not self.opengauss:
                raise ValueError("VectorDB opengauss backend requires 'opengauss' config")
            if not self.opengauss.host:
                raise ValueError("VectorDB opengauss backend requires 'opengauss.host' to be set")
            distance = (self.distance_metric or "cosine").lower()
            if distance not in _OPENGAUSS_DISTANCE_METRICS:
                raise ValueError(
                    "VectorDB opengauss backend supports distance_metric values: "
                    + ", ".join(sorted(_OPENGAUSS_DISTANCE_METRICS))
                )
            self.distance_metric = distance
            self.opengauss.validate_capabilities(
                distributed=self.opengauss.is_distributed, distance=distance
            )

        return self

    def apply_resolved_dimension(self, embedding_dimension: Any) -> None:
        """Resolve an unspecified collection dimension from the embedding configuration."""
        if int(self.dimension or 0) == 0 and embedding_dimension:
            self.dimension = int(embedding_dimension)
