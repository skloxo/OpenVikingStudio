# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
from __future__ import annotations

from typing import Any, Dict

from pydantic import ValidationError

from .config_utils import format_validation_error, warn_unknown_config_fields, warn_unknown_fields
from .log_config import LogConfig
from .memory_config import MemoryConfig
from .open_viking_config_models import ParserRuntimeConfig
from .open_viking_config_singleton import _get_config_logger


class _OpenVikingConfigSerdeMixin:
    """Dictionary serialization and deserialization helpers for OpenVikingConfig."""

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "OpenVikingConfig":
        """Create configuration from dictionary."""
        try:
            # Make a copy to avoid modifying the original
            config_copy = config.copy()

            parser_types = [
                "pdf",
                "code",
                "image",
                "audio",
                "video",
                "markdown",
                "anydoc",
                "html",
                "text",
                "directory",
                "feishu",
                "webfeed",
            ]

            warn_unknown_config_fields(
                data=config_copy,
                model=cls,
                extra_valid_fields={"server", "bot", "parsers", "skills"},
                logger=_get_config_logger(),
            )

            # Remove sections managed by other loaders (e.g. server config)
            config_copy.pop("server", None)
            config_copy.pop("bot", None)
            config_copy.pop("skills", None)

            # Handle parser configurations from nested "parsers" section
            parser_configs = {}
            missing_parser_download_temp_dir = object()
            parser_download_temp_dir = missing_parser_download_temp_dir
            if "parsers" in config_copy:
                parser_configs = config_copy.pop("parsers")
                if parser_configs is None:
                    parser_configs = {}
                if not isinstance(parser_configs, dict):
                    raise ValueError("Invalid parsers config: 'parsers' section must be an object")
                parser_configs = parser_configs.copy()
                if "excel" in parser_configs:
                    parser_configs.pop("excel")
                    _get_config_logger().error(
                        "Config field 'parsers.excel' was removed and is ignored; "
                        "spreadsheet parsing now uses 'parsers.anydoc'."
                    )
                parser_download_temp_dir = parser_configs.pop(
                    "download_temp_dir", missing_parser_download_temp_dir
                )
                warn_unknown_fields(
                    data=parser_configs,
                    valid_fields=set(parser_types) | {"download_temp_dir"},
                    path_prefix="parsers",
                    logger=_get_config_logger(),
                )
            for parser_type in parser_types:
                if parser_type in config_copy:
                    parser_configs[parser_type] = config_copy.pop(parser_type)

            # Handle log configuration from nested "log" section
            log_config_data = None
            if "log" in config_copy:
                log_config_data = config_copy.pop("log")

            # Handle memory configuration from nested "memory" section
            memory_config_data = None
            if "memory" in config_copy:
                memory_config_data = config_copy.pop("memory")

            instance = cls(**config_copy)

            # Apply log configuration
            if log_config_data is not None:
                instance.log = LogConfig.from_dict(log_config_data)

            # Apply memory configuration
            if memory_config_data is not None:
                try:
                    instance.memory = MemoryConfig.from_dict(memory_config_data)
                except ValidationError as e:
                    raise ValueError(
                        format_validation_error(
                            root_model=MemoryConfig,
                            error=e,
                            path_prefix="memory",
                        )
                    ) from None
            instance._check_expiry_backend()

            # Apply parser configurations
            if parser_download_temp_dir is not missing_parser_download_temp_dir:
                instance.parser = ParserRuntimeConfig(download_temp_dir=parser_download_temp_dir)

            for parser_type in parser_types:
                if parser_type in parser_configs:
                    parser_data = parser_configs[parser_type]
                    config_class = getattr(instance, parser_type).__class__
                    if isinstance(parser_data, dict):
                        warn_unknown_fields(
                            data=parser_data,
                            valid_fields=set(config_class.__dataclass_fields__),
                            path_prefix=f"parsers.{parser_type}",
                            logger=_get_config_logger(),
                        )
                    setattr(instance, parser_type, config_class.from_dict(parser_data))

            # Check dimension consistency
            if (
                getattr(instance, "storage", None)
                and getattr(instance.storage, "vectordb", None)
                and getattr(instance, "embedding", None)
            ):
                instance.storage.vectordb.apply_resolved_dimension(instance.embedding.dimension)
                db_dim = instance.storage.vectordb.dimension
                emb_dim = instance.embedding.dimension
                if db_dim > 0 and emb_dim > 0 and db_dim != emb_dim:
                    logging.warning(
                        f"Dimension mismatch: VectorDB dimension is {db_dim}, "
                        f"but Embedding dimension is {emb_dim}. "
                        "This may cause errors during vector search."
                    )
            return instance
        except ValidationError as e:
            # The formatted error omits input values; do not reattach a raw
            # validation traceback which could expose nested credentials.
            raise ValueError(format_validation_error(root_model=cls, error=e)) from None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()

    def get_query_planner(self) -> VLMConfig:
        """Return the model config used for retrieval intent analysis and query planning."""
        if self.query_planner is not None and self.query_planner._has_any_config():
            return self.query_planner
        return self.vlm


