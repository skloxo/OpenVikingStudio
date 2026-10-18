# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Local backend collection adapter."""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from openviking.storage.vectordb.collection.collection import Collection
from openviking.storage.vectordb.collection.local_collection import get_or_create_local_collection
from openviking_cli.utils.logger import get_logger

from .base import CollectionAdapter

logger = get_logger(__name__)


class LocalCollectionAdapter(CollectionAdapter):
    """Adapter for local embedded vectordb backend."""

    DEFAULT_LOCAL_PROJECT_NAME = "vectordb"

    def __init__(
        self,
        collection_name: str,
        project_path: str,
        index_name: str,
        collection_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(collection_name=collection_name, index_name=index_name)
        self.mode = "local"
        self._project_path = project_path
        self._collection_config = dict(collection_config or {})
        self._load_lock = threading.RLock()

    @classmethod
    def from_config(cls, config: Any):
        project_path = (
            str(Path(config.path) / cls.DEFAULT_LOCAL_PROJECT_NAME) if config.path else ""
        )
        collection_config: Dict[str, Any] = {}
        cuvs_config = getattr(config, "cuvs", None)
        if cuvs_config is not None and getattr(cuvs_config, "auto_enable", False):
            collection_config = {
                "dense_search": {
                    "backend": "auto_cuvs",
                    **cuvs_config.model_dump(),
                }
            }
        return cls(
            collection_name=config.name or "context",
            project_path=project_path,
            index_name=config.index_name or "default",
            collection_config=collection_config,
        )

    def _collection_path(self) -> str:
        if not self._project_path:
            return ""
        return str(Path(self._project_path) / self._collection_name)

    def _load_existing_collection_if_needed(self) -> None:
        with self._load_lock:
            if self._collection is not None:
                return
            collection_path = self._collection_path()
            if not collection_path:
                return
            meta_path = os.path.join(collection_path, "collection_meta.json")
            if os.path.exists(meta_path):
                self._collection = get_or_create_local_collection(
                    path=collection_path, config=self._collection_config
                )
                if self._index_name and not self._collection.has_index(self._index_name):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        scalar_index_fields = meta.get("ScalarIndex", [])
                        index_meta = self._build_default_index_meta(
                            index_name=self._index_name,
                            distance="cosine",
                            use_sparse=False,
                            sparse_weight=0.0,
                            scalar_index_fields=scalar_index_fields,
                        )
                        self._collection.create_index(self._index_name, index_meta)
                        logger.info("Automatically restored missing index '%s'", self._index_name)
                    except Exception as exc:
                        logger.warning("Failed to auto-restore missing index %s: %s", self._index_name, exc)

    def _create_backend_collection(self, meta: Dict[str, Any]) -> Collection:
        collection_path = self._collection_path()
        if collection_path:
            os.makedirs(collection_path, exist_ok=True)
        return get_or_create_local_collection(
            meta_data=meta,
            path=collection_path,
            config=self._collection_config,
        )

    def update_data(self, data_list: List[Dict[str, Any]]):
        collection = self.get_collection()
        result = collection.update_data(data_list)
        return list(result.ids or [])

    def begin_bulk_ingest(self) -> None:
        self.get_collection().begin_bulk_ingest()

    def end_bulk_ingest(self) -> None:
        self.get_collection().end_bulk_ingest()


class CuVSCollectionAdapter(LocalCollectionAdapter):
    """Embedded OpenViking storage with dense search executed by NVIDIA cuVS."""

    def __init__(
        self,
        collection_name: str,
        project_path: str,
        index_name: str,
        cuvs_config: Dict[str, Any],
    ):
        super().__init__(
            collection_name=collection_name,
            project_path=project_path,
            index_name=index_name,
            collection_config={
                "dense_search": {
                    "backend": "cuvs",
                    **cuvs_config,
                }
            },
        )
        self.mode = "cuvs"

    @classmethod
    def from_config(cls, config: Any):
        project_path = (
            str(Path(config.path) / cls.DEFAULT_LOCAL_PROJECT_NAME) if config.path else ""
        )
        cuvs_config = config.cuvs.model_dump() if config.cuvs is not None else {}
        return cls(
            collection_name=config.name or "context",
            project_path=project_path,
            index_name=config.index_name or "default",
            cuvs_config=cuvs_config,
        )
