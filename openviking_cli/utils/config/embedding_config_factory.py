# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from typing import Any, Dict, List, Optional, Tuple

from openviking_cli.utils.logger import get_logger

from .embedding_config_helpers import EmbeddingCredential
from .embedding_config_models import EmbeddingModelConfig

logger = get_logger(__name__)


class _EmbeddingFactoryMixin:
    """Runtime embedder instantiation and failover helpers for EmbeddingConfig."""

    def _create_embedder(
        self,
        provider: str,
        embedder_type: str,
        config: EmbeddingModelConfig,
    ):
        """Factory method to create embedder instance based on provider and type.

        Args:
            provider: Provider type ('openai', 'volcengine', 'vikingdb', 'jina', 'ollama', 'gemini', 'voyage', 'litellm')
            embedder_type: Embedder type ('dense', 'sparse', 'hybrid')
            config: EmbeddingModelConfig instance

        Returns:
            Embedder instance

        Raises:
            ValueError: If provider/type combination is not supported
        """
        from openviking.models.embedder import (
            CohereDenseEmbedder,
            DashScopeDenseEmbedder,
            GeminiDenseEmbedder,
            JinaDenseEmbedder,
            LiteLLMDenseEmbedder,
            LocalDenseEmbedder,
            MinimaxDenseEmbedder,
            OpenAIDenseEmbedder,
            RetryEmbedder,
            VikingDBDenseEmbedder,
            VikingDBHybridEmbedder,
            VikingDBSparseEmbedder,
            VolcengineDenseEmbedder,
            VolcengineHybridEmbedder,
            VolcengineSparseEmbedder,
            VoyageDenseEmbedder,
        )

        if provider == "litellm" and LiteLLMDenseEmbedder is None:
            raise ValueError("LiteLLM is not installed. Install it with: pip install litellm")

        # Factory registry: (provider, type) -> (embedder_class, param_builder)
        runtime_config = {
            "max_retries": self.max_retries,
            "max_concurrent": self.max_concurrent,
            "max_input_tokens": self.max_input_tokens,
        }

        factory_registry = {
            ("openai", "dense"): (
                OpenAIDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key
                    or "no-key",  # Placeholder for local OpenAI-compatible servers
                    "api_base": cfg.api_base,
                    "api_version": cfg.api_version,
            **({"max_tokens": cfg.max_tokens} if cfg.max_tokens is not None else {}),
                    "dimension": cfg.dimension,
                    "provider": "openai",
                    "configured_provider": "openai",
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                    **(
                        {"encoding_format": cfg.encoding_format}
                        if cfg.encoding_format is not None
                        else {}
                    ),
                    **(
                        {"input_type": "multimodal"}
                        if "input" in cfg.model_fields_set and cfg.input == "multimodal"
                        else {}
                    ),
                    **({"extra_body": cfg.extra_body} if cfg.extra_body else {}),
                },
            ),
            ("azure", "dense"): (
                OpenAIDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "api_version": cfg.api_version,
            **({"max_tokens": cfg.max_tokens} if cfg.max_tokens is not None else {}),
                    "dimension": cfg.dimension,
                    "provider": "azure",
                    "configured_provider": "azure",
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                    **(
                        {"encoding_format": cfg.encoding_format}
                        if cfg.encoding_format is not None
                        else {}
                    ),
                    **({"extra_body": cfg.extra_body} if cfg.extra_body else {}),
                },
            ),
            ("volcengine", "dense"): (
                VolcengineDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "input_type": cfg.input,
                    "config": dict(runtime_config),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                },
            ),
            ("volcengine", "sparse"): (
                VolcengineSparseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "config": dict(runtime_config),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                },
            ),
            ("volcengine", "hybrid"): (
                VolcengineHybridEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "input_type": cfg.input,
                    "config": dict(runtime_config),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                },
            ),
            ("vikingdb", "dense"): (
                VikingDBDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "model_version": cfg.version,
                    "ak": cfg.ak,
                    "sk": cfg.sk,
                    "region": cfg.region,
                    "host": cfg.host,
                    "dimension": cfg.dimension,
                    "input_type": cfg.input,
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                },
            ),
            ("vikingdb", "sparse"): (
                VikingDBSparseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "model_version": cfg.version,
                    "ak": cfg.ak,
                    "sk": cfg.sk,
                    "region": cfg.region,
                    "host": cfg.host,
                    "config": dict(runtime_config),
                },
            ),
            ("vikingdb", "hybrid"): (
                VikingDBHybridEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "model_version": cfg.version,
                    "ak": cfg.ak,
                    "sk": cfg.sk,
                    "region": cfg.region,
                    "host": cfg.host,
                    "dimension": cfg.dimension,
                    "input_type": cfg.input,
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                },
            ),
            ("jina", "dense"): (
                JinaDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                },
            ),
            ("gemini", "dense"): (
                GeminiDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                },
            ),
            # Ollama: local OpenAI-compatible embedding server, no real API key needed
            ("ollama", "dense"): (
                OpenAIDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key
                    or "no-key",  # Ollama ignores the key, but client requires non-empty
                    "api_base": cfg.api_base or "http://localhost:11434/v1",
                    "dimension": cfg.dimension,
                    "configured_provider": "ollama",
                    "config": dict(runtime_config),
                },
            ),
            ("voyage", "dense"): (
                VoyageDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                },
            ),
            ("minimax", "dense"): (
                MinimaxDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                },
            ),
            ("dashscope", "dense"): (
                DashScopeDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "input_type": cfg.input,
                    "config": dict(runtime_config),
                    **(
                        {"enable_fusion": cfg.enable_fusion}
                        if cfg.enable_fusion is not None
                        else {}
                    ),
                    **({"res_level": cfg.res_level} if cfg.res_level is not None else {}),
                    **(
                        {"max_video_frames": cfg.max_video_frames}
                        if cfg.max_video_frames is not None
                        else {}
                    ),
                },
            ),
            ("cohere", "dense"): (
                CohereDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                },
            ),
            ("litellm", "dense"): (
                LiteLLMDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "api_key": cfg.api_key,
                    "api_base": cfg.api_base,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                    **({"query_param": cfg.query_param} if cfg.query_param else {}),
                    **({"document_param": cfg.document_param} if cfg.document_param else {}),
                    **({"extra_headers": cfg.extra_headers} if cfg.extra_headers else {}),
                },
            ),
            ("local", "dense"): (
                LocalDenseEmbedder,
                lambda cfg: {
                    "model_name": cfg.model,
                    "model_path": cfg.model_path,
                    "cache_dir": cfg.cache_dir,
                    "dimension": cfg.dimension,
                    "config": dict(runtime_config),
                },
            ),
        }

        key = (provider, embedder_type)
        if key not in factory_registry:
            raise ValueError(
                f"Unsupported combination: provider='{provider}', type='{embedder_type}'. "
                f"Supported combinations: {list(factory_registry.keys())}"
            )

        embedder_class, param_builder = factory_registry[key]
        if embedder_class is None and key == ("gemini", "dense"):
            raise ValueError(
                "google-genai is not installed. Install it with: pip install openviking[gemini]"
            )
        params = param_builder(config)
        embedder = embedder_class(**params)
        if provider == "local":
            return embedder
        if isinstance(embedder, RetryEmbedder):
            return embedder
        return RetryEmbedder(embedder)

    def get_embedder(self):
        """Get embedder instance based on configuration.

        Returns:
            Embedder instance (Dense, Sparse, Hybrid, or Composite)

        Raises:
            ValueError: If configuration is invalid or unsupported
        """
        from openviking.models.embedder import CompositeHybridEmbedder
        from openviking.models.embedder.base import DenseEmbedderBase, SparseEmbedderBase

        if self.hybrid:
            if self.hybrid.credentials:
                return self._create_failover_embedder("hybrid", self.hybrid)
            provider = self._require_provider(self.hybrid.provider)
            return self._create_embedder(provider, "hybrid", self.hybrid)

        if self.dense and self.sparse:
            # Handle failover for both dense and sparse if credentials are configured
            dense_embedder = self._create_single_or_failover_embedder("dense", self.dense)
            sparse_embedder = self._create_single_or_failover_embedder("sparse", self.sparse)
            return CompositeHybridEmbedder(
                cast(DenseEmbedderBase, dense_embedder),
                cast(SparseEmbedderBase, sparse_embedder),
            )

        if self.dense:
            return self._create_single_or_failover_embedder("dense", self.dense)

        if self.sparse:
            return self._create_single_or_failover_embedder("sparse", self.sparse)

        raise ValueError("No embedding configuration found (dense, sparse, or hybrid)")

    def _create_single_or_failover_embedder(
        self, embedder_type: str, config: "EmbeddingModelConfig"
    ):
        """Create either a single embedder or a FailoverEmbedder based on credentials config."""
        if config.credentials:
            return self._create_failover_embedder(embedder_type, config)
        provider = self._require_provider(config.provider)
        return self._create_embedder(provider, embedder_type, config)

    def _create_failover_embedder(self, embedder_type: str, config: "EmbeddingModelConfig"):
        """Create a FailoverEmbedder with multiple credentials."""
        from openviking.models.embedder import FailoverEmbedder

        embedders = []
        credential_ids = []

        for cred in config.credentials:
            # Preserve whether `input` was explicitly set; the default multimodal
            # value must not opt OpenAI-compatible failover configs into image input.
            merged_config = EmbeddingModelConfig(
                model=cred.model or config.model,
                dimension=config.dimension,
                batch_size=config.batch_size,
                query_param=config.query_param,
                document_param=config.document_param,
                provider=cred.provider or config.provider,
                version=config.version,
                ak=cred.ak or config.ak,
                sk=cred.sk or config.sk,
                region=cred.region or config.region,
                host=cred.host or config.host,
                api_key=cred.api_key or config.api_key,
                api_base=cred.api_base or config.api_base,
                api_version=cred.api_version or config.api_version,
                extra_headers=cred.extra_headers or config.extra_headers,
                # Model-behavior fields are shared by all credentials of the
                # same model and live only on the parent config.
                encoding_format=config.encoding_format,
                extra_body=config.extra_body,
                model_path=config.model_path,
                cache_dir=config.cache_dir,
                enable_fusion=config.enable_fusion,
                res_level=config.res_level,
                max_video_frames=config.max_video_frames,
                **({"input": config.input} if "input" in config.model_fields_set else {}),
            )
            provider = self._require_provider(merged_config.provider)
            embedder = self._create_embedder(provider, embedder_type, merged_config)
            # Retry wrappers delegate the actual provider request to their child.
            # Each failover candidate keeps its own owner, including failed calls.
            if cred.cost_bearer is not None:
                current = embedder
                seen = set()
                while current is not None and id(current) not in seen:
                    seen.add(id(current))
                    current.cost_bearer = cred.cost_bearer
                    current = getattr(current, "inner", None)
            embedders.append(embedder)
            credential_ids.append(cred.id or f"credential-{len(credential_ids)}")

        if len(embedders) == 1:
            return embedders[0]

        return FailoverEmbedder(
            embedders=embedders,
            credential_ids=credential_ids,
            failback_timeout_seconds=config.failback_timeout_seconds,
            failback_request_count=config.failback_request_count,
        )

    @property
    def dimension(self) -> int:
        """Get dimension from active config."""
        return self.get_dimension()

    def get_dimension(self) -> int:
        """Helper to get dimension from active config"""
        if self.hybrid:
            return self.hybrid.get_effective_dimension()
        if self.dense:
            return self.dense.get_effective_dimension()
        if self.sparse:
            return self.sparse.get_effective_dimension()
        return 2048

    @staticmethod
    def _require_provider(provider: Optional[str]) -> str:
        if not provider:
            raise ValueError("Embedding provider is required")
        return provider.lower()
