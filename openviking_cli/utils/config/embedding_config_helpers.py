# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from typing import Any, ClassVar, List, Literal, Optional, Tuple, cast

from pydantic import BaseModel, Field, model_validator

from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

TEXT_SOURCE_CONTENT_ONLY = "content_only"
TEXT_SOURCE_SUMMARY_FIRST = "summary_first"
TEXT_SOURCE_SUMMARY_ONLY = "summary_only"
SUMMARY_TEXT_SOURCES = frozenset({TEXT_SOURCE_SUMMARY_FIRST, TEXT_SOURCE_SUMMARY_ONLY})
TEXT_SOURCES = frozenset({TEXT_SOURCE_SUMMARY_FIRST, TEXT_SOURCE_CONTENT_ONLY})


class EmbeddingCredential(BaseModel):
    """Single embedding credential configuration for multi-credential failover."""

    cost_bearer: Optional[Literal["ov", "customer", "unknown"]] = Field(
        default=None, description="Billing owner supplied by the credential provisioner"
    )

    id: Optional[str] = Field(default=None, description="Unique identifier for this credential")
    provider: Optional[str] = Field(default=None, description="Provider type")
    model: Optional[str] = Field(
        default=None,
        description=(
            "Model name (or endpoint id) for this credential. "
            "Overrides the parent EmbeddingModelConfig.model when set, allowing "
            "each credential to point to a different deployment / endpoint."
        ),
    )
    api_key: Optional[str] = Field(default=None, description="API key")
    api_base: Optional[str] = Field(default=None, description="API base URL")
    api_version: Optional[str] = Field(default=None, description="API version")
    ak: Optional[str] = Field(default=None, description="Access Key ID for VikingDB API")
    sk: Optional[str] = Field(default=None, description="Access Key Secret for VikingDB API")
    region: Optional[str] = Field(default=None, description="Region for VikingDB API")
    host: Optional[str] = Field(default=None, description="Host for VikingDB API")
    extra_headers: Optional[dict[str, str]] = Field(default=None, description="Extra HTTP headers")



class EmbeddingCircuitBreakerConfig(BaseModel):
    failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Consecutive failures required to open the embedding circuit breaker",
    )
    reset_timeout: float = Field(
        default=60.0,
        gt=0,
        description="Base circuit breaker reset timeout in seconds",
    )
    max_reset_timeout: float = Field(
        default=600.0,
        gt=0,
        description="Maximum circuit breaker reset timeout in seconds",
    )

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.max_reset_timeout < self.reset_timeout:
            raise ValueError("embedding.circuit_breaker.max_reset_timeout must be >= reset_timeout")
        return self



def resolve_embedding_dimension_for(
    model_cfg: Any, provider: Optional[str], model: Optional[str]
) -> Optional[int]:
    """Resolve dimension for a (provider, model) pair using the same
    rules as ``get_effective_dimension``. The explicit parent dimension,
    when set, always wins."""
    if model_cfg.dimension is not None:
        return model_cfg.dimension

    provider = (provider or "").lower()
    if provider in {"openai", "azure"}:
        mapping = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return mapping.get((model or "").lower())

    if provider == "voyage":
        from openviking.models.embedder.voyage_embedders import (
            get_voyage_model_default_dimension,
        )

        return get_voyage_model_default_dimension(model)

    if provider == "cohere":
        from openviking.models.embedder.cohere_embedders import (
            get_cohere_model_default_dimension,
        )

        return get_cohere_model_default_dimension(model)

    if provider == "jina":
        from openviking.models.embedder.jina_embedders import (
            get_jina_model_default_dimension,
        )

        return get_jina_model_default_dimension(model)

    if provider == "gemini":
        from openviking.models.embedder.gemini_embedders import GeminiDenseEmbedder

        return GeminiDenseEmbedder._default_dimension(model)

    if provider == "local":
        from openviking.models.embedder.local_embedders import (
            get_local_model_default_dimension,
        )

        return get_local_model_default_dimension(model)

    if provider == "dashscope":
        try:
            from openviking.models.embedder.dashscope_embedders import (
                get_dashscope_model_default_dimension,
            )

            return get_dashscope_model_default_dimension(model)
        except ImportError:
            return 1024

    # Providers without a known dimension lookup (volcengine,
    # vikingdb, ollama for unlisted models, etc.) cannot be cross-checked
    # here without an explicit dimension. Return None so validation skips
    # them; same-provider credentials are typically dimension-compatible
    # by construction, and any real mismatch will surface at write time.
    return None

def compute_effective_dimension(self: Any) -> int:
    """Resolve the dimension used for schema creation and validation."""
    if self.dimension is not None:
        return self.dimension

    provider = (self._effective_provider() or "").lower()
    effective_model = self._effective_model()
    if provider in {"openai", "azure"}:
        openai_model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        model_lower = (effective_model or "").lower()
        if model_lower in openai_model_dimensions:
            return openai_model_dimensions[model_lower]

    if provider == "voyage":
        from openviking.models.embedder.voyage_embedders import (
            get_voyage_model_default_dimension,
        )

        return get_voyage_model_default_dimension(effective_model)

    if provider == "cohere":
        from openviking.models.embedder.cohere_embedders import (
            get_cohere_model_default_dimension,
        )

        return get_cohere_model_default_dimension(effective_model)

    if provider == "jina":
        from openviking.models.embedder.jina_embedders import (
            get_jina_model_default_dimension,
        )

        return get_jina_model_default_dimension(effective_model)

    if provider == "gemini":
        from openviking.models.embedder.gemini_embedders import GeminiDenseEmbedder

        return GeminiDenseEmbedder._default_dimension(effective_model)

    if provider == "ollama":
        # Common Ollama embedding models and their dimensions
        # Users should set dimension explicitly for other models
        ollama_model_dimensions = {
            "nomic-embed-text": 768,
            "nomic-embed-text-v1": 768,
            "nomic-embed-text-v1.5": 768,
            "mxbai-embed-large": 1024,
            "mxbai-embed-large-v1": 1024,
            "all-minilm": 384,
            "all-minilm-l6-v2": 384,
            "snowflake-arctic-embed": 1024,
            "snowflake-arctic-embed-l": 1024,
            "qwen3-embedding": 1024,
            "qwen3-embedding:0.6b": 1024,
            "qwen3-embedding:4b": 1024,
            "qwen3-embedding:8b": 1024,
            "embeddinggemma": 768,
            "embeddinggemma:300m": 768,
        }
        model_lower = (effective_model or "").lower()
        if model_lower in ollama_model_dimensions:
            return ollama_model_dimensions[model_lower]
        # For unknown Ollama models, require explicit dimension
        raise ValueError(
            f"Unknown dimension for Ollama model '{effective_model}'. "
            f"Please set 'dimension' explicitly in your embedding config. "
            f"Known models: {list(ollama_model_dimensions.keys())}"
        )

    if provider == "local":
        from openviking.models.embedder.local_embedders import get_local_model_default_dimension

        return get_local_model_default_dimension(effective_model)

    if provider == "dashscope":
        try:
            from openviking.models.embedder.dashscope_embedders import (
                get_dashscope_model_default_dimension,
            )

            return get_dashscope_model_default_dimension(effective_model)
        except ImportError:
            # Fallback dimension if dashscope_embedders module doesn't exist yet
            return 1024

    return 2048

