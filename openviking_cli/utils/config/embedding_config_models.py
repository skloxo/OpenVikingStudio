# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from typing import Any, ClassVar, Dict, List, Literal, Optional, Tuple, cast

from pydantic import BaseModel, Field, model_validator

from openviking_cli.utils.logger import get_logger

from .embedding_config_helpers import (
    SUMMARY_TEXT_SOURCES,
    TEXT_SOURCE_CONTENT_ONLY,
    TEXT_SOURCE_SUMMARY_FIRST,
    TEXT_SOURCES,
    EmbeddingCredential,
    compute_effective_dimension,
    resolve_embedding_dimension_for,
)

logger = get_logger(__name__)

class EmbeddingModelConfig(BaseModel):
    """Configuration for a specific embedding model"""

    model: Optional[str] = Field(default=None, description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    api_base: Optional[str] = Field(default=None, description="API base URL")
    dimension: Optional[int] = Field(default=None, description="Embedding dimension")
    max_tokens: Optional[int] = Field(
        default=None, description="Max token limit for embeddings input truncation"
    )
    batch_size: int = Field(default=32, description="Batch size for embedding generation")
    input: str = Field(default="multimodal", description="Input type: 'text' or 'multimodal'")
    query_param: Optional[str] = Field(
        default=None,
        description=(
            "Parameter value for query-side embeddings when calling embed(is_query=True). "
            "For OpenAI-compatible models, this maps to 'input_type' (e.g., 'query', 'search_query'). "
            "For Jina models, this maps to 'task' (e.g., 'retrieval.query'). "
            "Setting this or document_param activates non-symmetric mode. "
            "Leave both unset for symmetric models."
        ),
    )
    document_param: Optional[str] = Field(
        default=None,
        description=(
            "Parameter value for document-side embeddings when calling embed(is_query=False). "
            "For OpenAI-compatible models, this maps to 'input_type' (e.g., 'passage', 'document'). "
            "For Jina models, this maps to 'task' (e.g., 'retrieval.passage'). "
            "Setting this or query_param activates non-symmetric mode. "
            "Leave both unset for symmetric models."
        ),
    )
    provider: Optional[str] = Field(
        default="volcengine",
        description=(
            "Provider type: 'openai', 'volcengine', 'vikingdb', 'jina', 'ollama', 'gemini', 'voyage', 'dashscope', 'minimax', 'cohere', 'litellm', 'local'. "
            "For OpenRouter or other OpenAI-compatible providers, use 'litellm' with "
            "api_base and api_key, or 'openai' with api_base and extra_headers."
        ),
    )
    backend: Optional[str] = Field(
        default="volcengine",
        description="Backend type (Deprecated, use 'provider' instead): 'openai', 'volcengine', 'vikingdb', 'voyage', 'local'",
    )
    version: Optional[str] = Field(default=None, description="Model version")
    ak: Optional[str] = Field(default=None, description="Access Key ID for VikingDB API")
    sk: Optional[str] = Field(default=None, description="Access Key Secretfor VikingDB API")
    region: Optional[str] = Field(default=None, description="Region for VikingDB API")
    host: Optional[str] = Field(default=None, description="Host for VikingDB API")
    extra_headers: Optional[dict[str, str]] = Field(
        default=None,
        description=(
            "Extra HTTP headers for API requests. Passed as default_headers to the OpenAI client. "
            "Useful for OpenRouter (e.g., {'HTTP-Referer': '...', 'X-Title': '...'}) "
            "or other OpenAI-compatible providers that require custom headers."
        ),
    )
    encoding_format: Optional[Literal["float", "base64"]] = Field(
        default=None,
        description=(
            "Wire format for embedding values. Applies to OpenAI / Azure providers. "
            "Leave unset to use the OpenAI Python SDK default (currently 'base64', "
            "which is bandwidth-efficient and decoded client-side). Set to 'float' "
            "to send/receive plain JSON arrays. This is the recommended workaround "
            "when the upstream gateway cannot serialize base64 responses correctly."
        ),
    )
    extra_body: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Extra JSON body fields merged into every embeddings request. "
            "Applies to OpenAI / Azure providers. Useful for OpenAI-compatible "
            "gateways that accept vendor-specific fields, e.g. OpenRouter provider "
            "routing {'provider': {'sort': 'latency'}}. Explicit "
            "query_param/document_param keys take precedence on conflict."
        ),
    )
    api_version: Optional[str] = Field(
        default=None,
        description="API version for Azure OpenAI (e.g., '2025-01-01-preview').",
    )
    model_path: Optional[str] = Field(
        default=None,
        description="Explicit local GGUF model path for provider='local'.",
    )
    cache_dir: Optional[str] = Field(
        default=None,
        description="Local model cache directory for provider='local'.",
    )
    enable_fusion: Optional[bool] = Field(
        default=None,
        description="Enable multimodal fusion for DashScope provider (multimodal models only).",
    )
    res_level: Optional[int] = Field(
        default=None,
        description="Resolution level for DashScope multimodal models (multimodal models only).",
    )
    max_video_frames: Optional[int] = Field(
        default=None,
        description="Maximum video frames for DashScope multimodal models (multimodal models only).",
    )

    # New multi-credential configuration
    credentials: List[EmbeddingCredential] = Field(
        default_factory=list,
        description="Ordered list of credentials for failover. Call order matches array index (0 is highest priority).",
    )

    failback_timeout_seconds: float = Field(
        default=600.0, description="Time in seconds after which to attempt failback to primary"
    )
    failback_request_count: int = Field(
        default=50, description="Number of backup requests after which to attempt failback"
    )

    @model_validator(mode="before")
    @classmethod
    def sync_provider_backend(cls, data: Any) -> Any:
        if isinstance(data, dict):
            provider = data.get("provider")
            backend = data.get("backend")

            if backend is not None and provider is None:
                data["provider"] = backend
            for key in ("query_param", "document_param"):
                value = data.get(key)
                if isinstance(value, str):
                    data[key] = value.lower()
        return data

    _VALID_PROVIDERS: ClassVar[Tuple[str, ...]] = (
        "openai",
        "azure",
        "volcengine",
        "vikingdb",
        "jina",
        "ollama",
        "gemini",
        "voyage",
        "dashscope",
        "minimax",
        "cohere",
        "litellm",
        "local",
    )

    @classmethod
    def _validate_provider_auth(
        cls,
        *,
        label: str,
        provider: Optional[str],
        api_key: Optional[str],
        api_base: Optional[str],
        ak: Optional[str],
        sk: Optional[str],
        region: Optional[str],
    ) -> None:
        """Validate provider name and provider-specific auth requirements.

        Shared by both the top-level config validator (single-credential mode)
        and the per-credential validator (multi-credential mode).

        Args:
            label: Prefix used in error messages, e.g. "Embedding" or
                "credentials[ark-primary]".
            provider: Provider name (already lowercased / normalized).
            api_key, api_base, ak, sk, region: Resolved auth fields, with
                credential values taking precedence over parent fallbacks
                in multi-credential mode.
        """
        if not provider:
            raise ValueError(f"{label}: provider is required")
        if provider not in cls._VALID_PROVIDERS:
            raise ValueError(
                f"{label}: invalid provider '{provider}'. Must be one of: "
                + ", ".join(f"'{p}'" for p in cls._VALID_PROVIDERS)
            )

        if provider == "openai":
            # Allow missing api_key when api_base is set (e.g. local OpenAI-compatible servers)
            if not api_key and not api_base:
                raise ValueError(f"{label}: OpenAI provider requires 'api_key' to be set")
        elif provider == "azure":
            if not api_key:
                raise ValueError(f"{label}: Azure provider requires 'api_key' to be set")
            if not api_base:
                raise ValueError(
                    f"{label}: Azure provider requires 'api_base' (Azure endpoint) to be set"
                )
        elif provider in {
            "volcengine",
            "jina",
            "gemini",
            "voyage",
            "minimax",
            "cohere",
            "dashscope",
        }:
            if not api_key:
                provider_label = {
                    "volcengine": "Volcengine",
                    "jina": "Jina",
                    "gemini": "Gemini",
                    "voyage": "Voyage",
                    "minimax": "MiniMax",
                    "cohere": "Cohere",
                    "dashscope": "DashScope",
                }[provider]
                raise ValueError(f"{label}: {provider_label} provider requires 'api_key' to be set")
        elif provider == "vikingdb":
            missing = [n for n, v in (("ak", ak), ("sk", sk), ("region", region)) if not v]
            if missing:
                raise ValueError(
                    f"{label}: VikingDB provider requires the following fields: "
                    f"{', '.join(missing)}"
                )
        # ollama / litellm / local: no auth requirement enforced here

    @model_validator(mode="after")
    def validate_config(self):
        """Validate configuration completeness and consistency"""
        if self.backend and not self.provider:
            self.provider = self.backend

        if not self.model and not any(c.model for c in self.credentials):
            raise ValueError("Embedding model name is required")

        # When credentials are configured, defer provider/api_key validation to
        # per-credential checks; the parent-level provider/api_key may be left
        # blank because each credential carries its own settings.
        if self.credentials:
            self._validate_credentials()
            self._validate_credential_dimensions()
            return self

        self._validate_provider_auth(
            label="Embedding",
            provider=self.provider,
            api_key=self.api_key,
            api_base=self.api_base,
            ak=self.ak,
            sk=self.sk,
            region=self.region,
        )

        self._validate_provider_specific_options(
            label="Embedding",
            provider=self.provider,
            model=self.model,
        )

        return self

    def _validate_provider_specific_options(
        self, *, label: str, provider: Optional[str], model: Optional[str]
    ) -> None:
        """Validate provider-specific options that go beyond auth.

        These rules depend on the provider/model pair and on parent-level
        fields (``query_param``, ``document_param``, ``input``, ``dimension``,
        ``enable_fusion``, etc.) that are shared across all credentials. They
        must run for both the single-credential path (using ``self.provider``)
        and the multi-credential path (using each credential's resolved
        provider/model), otherwise invalid configurations slip past startup
        validation and surface only at runtime — after collection schema and
        embedding metadata may already have been written.
        """
        if not provider:
            return

        if provider == "gemini":
            _GEMINI_TASK_TYPES = {
                "RETRIEVAL_QUERY",
                "RETRIEVAL_DOCUMENT",
                "SEMANTIC_SIMILARITY",
                "CLASSIFICATION",
                "CLUSTERING",
                "QUESTION_ANSWERING",
                "FACT_VERIFICATION",
                "CODE_RETRIEVAL_QUERY",
            }
            for field_name, value in [
                ("query_param", self.query_param),
                ("document_param", self.document_param),
            ]:
                if value and value.upper() not in _GEMINI_TASK_TYPES:
                    raise ValueError(
                        f"{label}: invalid {field_name} '{value}' for Gemini. "
                        f"Valid task_types: {', '.join(sorted(_GEMINI_TASK_TYPES))}"
                    )

        elif provider == "dashscope":
            if self.input == "text" and (
                self.enable_fusion is not None
                or self.res_level is not None
                or self.max_video_frames is not None
            ):
                raise ValueError(
                    f"{label}: parameters enable_fusion, res_level, and max_video_frames "
                    "only apply to multimodal input mode"
                )

        elif provider == "litellm":
            # litellm handles auth via env vars or explicit api_key; no strict requirement
            if not self.dimension:
                raise ValueError(
                    f"{label}: LiteLLM provider requires 'dimension' to be set explicitly. "
                    "Check your embedding model's documentation for the correct dimension."
                )

        elif provider == "local":
            from openviking.models.embedder.local_embedders import get_local_model_spec

            get_local_model_spec(model)

    def _validate_credentials(self) -> None:
        """Validate each credential when credentials list is non-empty.

        Each credential must resolve a provider (from itself or the parent) and
        meet that provider's required fields. The parent-level provider/api_key
        are used as fallbacks where appropriate. Provider-specific options that
        depend on parent-level fields (e.g. LiteLLM dimension, Gemini task
        types, DashScope multimodal-only params) are also re-checked per
        resolved credential so the credentials path enforces the same invariants
        as the single-credential path.
        """
        for idx, cred in enumerate(self.credentials):
            cred_id = cred.id or f"credential-{idx}"
            label = f"credentials[{cred_id}]"
            resolved_provider = (cred.provider or self.provider or "").lower() or None
            resolved_model = cred.model or self.model
            self._validate_provider_auth(
                label=label,
                provider=resolved_provider,
                api_key=cred.api_key or self.api_key,
                api_base=cred.api_base or self.api_base,
                ak=cred.ak or self.ak,
                sk=cred.sk or self.sk,
                region=cred.region or self.region,
            )
            self._validate_provider_specific_options(
                label=label,
                provider=resolved_provider,
                model=resolved_model,
            )

    def _validate_credential_dimensions(self) -> None:
        """Ensure all credentials produce vectors of the same dimension.

        Mixing credentials whose embedders return different vector lengths
        causes ``dense vector dimension mismatch`` errors at write time and
        silently breaks retrieval. We therefore reject such configurations at
        startup. Dimensions are resolved using the same heuristics as
        ``get_effective_dimension`` (provider + model), with the explicit
        parent ``self.dimension`` always winning when set.
        """
        if len(self.credentials) <= 1:
            return

        resolved: list[tuple[str, int]] = []
        for idx, cred in enumerate(self.credentials):
            cred_id = cred.id or f"credential-{idx}"
            provider = (cred.provider or self.provider or "").lower()
            model = cred.model or self.model
            try:
                dim = self._resolve_dimension_for(provider, model)
            except ValueError:
                # Unknown dimension (e.g. ollama with no explicit dim and
                # unknown model): skip - the per-credential validation above
                # would have already required `dimension` if needed via
                # parent.dimension, and resolution failures here are non-fatal
                # because the credential may still work at runtime.
                continue
            if dim is None:
                continue
            resolved.append((cred_id, dim))

        distinct = {dim for _, dim in resolved}
        if len(distinct) > 1:
            details = ", ".join(f"{cid}={dim}" for cid, dim in resolved)
            raise ValueError(
                "Embedding credentials have conflicting vector dimensions: "
                f"{details}. All credentials must produce vectors of the same "
                "dimension; mixing different dimensions corrupts the vector "
                "store. Either align provider/model across credentials, or "
                "set 'dimension' explicitly on the parent embedding config "
                "to force a fixed schema dimension."
            )

    def _resolve_dimension_for(self, provider: Optional[str], model: Optional[str]) -> Optional[int]:
        return resolve_embedding_dimension_for(self, provider, model)

    def _effective_provider(self) -> Optional[str]:
        """Resolve the provider that actually drives this config.

        When credentials are configured, the first credential's provider takes
        precedence over the parent's (which may still hold its default value of
        ``volcengine``). Without this fallback, credential-only configurations
        targeting a non-default provider would silently use the parent's
        default for dimension/metadata resolution and produce a vector-space
        mismatch (e.g. parent volcengine -> 2048 dim while the actual OpenAI
        embedder returns 1536).
        """
        if self.credentials and self.credentials[0].provider:
            return self.credentials[0].provider
        return self.provider

    def _effective_model(self) -> Optional[str]:
        """Resolve the model that actually drives this config.

        Same rationale as ``_effective_provider``: credential-level model wins
        when present so dimension/metadata reflect the model the embedder will
        actually call.
        """
        if self.credentials and self.credentials[0].model:
            return self.credentials[0].model
        return self.model

    def get_effective_dimension(self) -> int:
        return compute_effective_dimension(self)

