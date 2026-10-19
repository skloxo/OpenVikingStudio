# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Backward-compatible facade for HierarchicalRetriever, delegating to GlobalHybridRetriever."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openviking.models.rerank import RerankClient
from openviking.retrieve.global_hybrid_retriever import (
    GlobalHybridRetriever,
    RetrieverMode,
    _has_context_type_filter,
)
from openviking.storage.vikingdb_manager import VikingDBManager, VikingDBManagerProxy
from openviking_cli.utils.config import RerankConfig
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "HierarchicalRetriever",
    "RetrieverMode",
    "RerankClient",
    "VikingDBManagerProxy",
    "_has_context_type_filter",
]


class HierarchicalRetriever(GlobalHybridRetriever):
    """
    Backward-compatible facade for global retrieval.

    Inherits from and delegates to GlobalHybridRetriever. Zero-breaking drop-in replacement.
    """

    def _init_rerank_client(self, rerank_config: RerankConfig) -> Any:
        return RerankClient.from_config(rerank_config)

    def _create_vector_proxy(self, ctx: Any) -> Any:
        return VikingDBManagerProxy(self.vector_store, ctx)
