# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from typing import Any, ClassVar, List, Literal, Optional, Tuple, cast

from pydantic import BaseModel, Field, model_validator

from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

from .embedding_config_factory import _EmbeddingFactoryMixin
from .embedding_config_helpers import (
    SUMMARY_TEXT_SOURCES,
    TEXT_SOURCE_CONTENT_ONLY,
    TEXT_SOURCE_SUMMARY_FIRST,
    TEXT_SOURCE_SUMMARY_ONLY,
    TEXT_SOURCES,
    EmbeddingCircuitBreakerConfig,
    EmbeddingCredential,
)
from .embedding_config_models import EmbeddingModelConfig

logger = get_logger(__name__)

class EmbeddingConfig(_EmbeddingFactoryMixin, BaseModel):
    """
    Embedding configuration, supports OpenAI, VolcEngine, VikingDB, Jina, Gemini, Voyage, or LiteLLM APIs.

    Structure:
    - dense: Configuration for dense embedder
    - sparse: Configuration for sparse embedder
    - hybrid: Configuration for hybrid embedder (single model returning both)

    Environment variables are mapped to these configurations.
    """

    dense: Optional[EmbeddingModelConfig] = Field(default=None)
    sparse: Optional[EmbeddingModelConfig] = Field(default=None)
    hybrid: Optional[EmbeddingModelConfig] = Field(default=None)
    circuit_breaker: EmbeddingCircuitBreakerConfig = Field(
        default_factory=EmbeddingCircuitBreakerConfig
    )

    max_concurrent: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent document embedding requests; retrieval queries bypass this limit",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for embedding provider calls (0 disables retry)",
    )
    text_source: str = Field(
        default=TEXT_SOURCE_CONTENT_ONLY,
        description="Text source for file vectorization: summary_first|content_only",
    )
    max_input_tokens: int = Field(
        default=4096,
        ge=100,
        description="Maximum estimated tokens sent to embeddings when raw text fallback is used",
    )
    allow_metadata_override: bool = Field(
        default=False,
        description=(
            "When true, allow starting up against an existing collection whose "
            "embedding metadata (provider/model) differs from the current config, "
            "as long as dimension is unchanged. The collection metadata will be "
            "rewritten to the new config and a warning will be logged. "
            "Useful when migrating an existing index to a new model deployment "
            "(e.g. switching ARK endpoint id) while keeping previously indexed "
            "vectors. Note: vector semantics may drift if the underlying model "
            "actually changed; only enable when you understand the implication."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def apply_default_local_dense(cls, data: Any) -> Any:
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return data

        if not data.get("dense") and not data.get("sparse") and not data.get("hybrid"):
            data = dict(data)
            data["dense"] = {
                "provider": "local",
                "model": "bge-small-zh-v1.5-f16",
            }
        return data

    @model_validator(mode="after")
    def validate_config(self):
        """Validate configuration completeness and consistency"""
        if not self.dense and not self.sparse and not self.hybrid:
            raise ValueError(
                "At least one embedding configuration (dense, sparse, or hybrid) is required"
            )
        if self.text_source == "summary_only":
            logger.warning(
                "embedding.text_source=summary_only is deprecated; use summary_first instead. "
                "Files without a summary still fall back to content for vectorization."
            )
            self.text_source = TEXT_SOURCE_SUMMARY_FIRST
        if self.text_source not in TEXT_SOURCES:
            raise ValueError("embedding.text_source must be one of: summary_first, content_only")
        return self

