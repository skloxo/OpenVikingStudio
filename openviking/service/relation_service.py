# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Relation Service for OpenViking.

Provides relation management operations: relations, link, unlink, topology listing.
Backed by SQLite RelationStore (Card-20F).
"""

from typing import Any, Dict, List, Optional, Union

from openviking.core.uri_validation import validate_viking_uri
from openviking.server.identity import RequestContext
from openviking.storage.relations_store import RelationItem, RelationStore
from openviking.storage.viking_fs import VikingFS
from openviking_cli.exceptions import NotInitializedError
from openviking_cli.utils import get_logger

logger = get_logger(__name__)


class RelationService:
    """Relation management service backed by persistent SQLite storage."""

    def __init__(self, viking_fs: Optional[VikingFS] = None, store: Optional[RelationStore] = None):
        self._viking_fs = viking_fs
        self._store = store or RelationStore.get_instance()

    def set_viking_fs(self, viking_fs: VikingFS) -> None:
        """Set VikingFS instance (for deferred initialization)."""
        self._viking_fs = viking_fs

    def _ensure_initialized(self) -> VikingFS:
        """Ensure VikingFS is initialized."""
        if not self._viking_fs:
            raise NotInitializedError("VikingFS")
        return self._viking_fs

    async def relations(self, uri: str, ctx: RequestContext) -> List[Dict[str, Any]]:
        """Get outbound relations (returns [{"uri": "...", "reason": "..."}, ...])."""
        uri = validate_viking_uri(uri)
        # 1. 优先查 SQLite 物理持久化关系库 (Card-20F SSOT)
        links = self._store.get_outbound(uri)
        if links:
            return links
        # 2. 回退兼容 VikingFS 内部实现 (若有)
        if self._viking_fs and hasattr(self._viking_fs, "relations"):
            try:
                return await self._viking_fs.relations(uri, ctx=ctx)
            except Exception:
                pass
        return []

    async def link(
        self,
        from_uri: str,
        uris: Union[str, List[str]],
        ctx: RequestContext,
        reason: str = "",
        link_type: str = "related_to",
        weight: float = 1.0,
    ) -> None:
        """Create link (single or multiple) and persist to SQLite relations.db."""
        from_uri = validate_viking_uri(from_uri, field_name="from_uri")
        if isinstance(uris, list):
            target_uris = [validate_viking_uri(u, field_name="to_uris") for u in uris]
            self._store.add_links_batch(from_uri, target_uris, reason=reason, link_type=link_type, weight=weight)
        else:
            target_uri = validate_viking_uri(uris, field_name="to_uris")
            self._store.add_link(from_uri, target_uri, reason=reason, link_type=link_type, weight=weight)

        # 兼容通知 VikingFS 底层
        if self._viking_fs and hasattr(self._viking_fs, "link"):
            try:
                await self._viking_fs.link(from_uri, uris, reason, ctx=ctx)
            except Exception:
                pass

    async def unlink(self, from_uri: str, uri: str, ctx: RequestContext) -> None:
        """Remove link (remove specified URI from relations.db)."""
        from_uri = validate_viking_uri(from_uri, field_name="from_uri")
        target_uri = validate_viking_uri(uri, field_name="to_uri")
        self._store.remove_link(from_uri, target_uri)

        # 兼容通知 VikingFS 底层
        if self._viking_fs and hasattr(self._viking_fs, "unlink"):
            try:
                await self._viking_fs.unlink(from_uri, uri, ctx=ctx)
            except Exception:
                pass

    def list_all_relations(self, limit: int = 500) -> List[RelationItem]:
        """全量查询系统内的显式关联关系。"""
        return self._store.list_all_links(limit=limit)

    def count_relations(self) -> int:
        """查询显式关联总数。"""
        return self._store.count_links()
