# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""FSService extension helpers for MCP mounts, directory rules, and compile finalization."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Sequence

from openviking.server.identity import RequestContext
from openviking.storage.acl import AclAction
from openviking.storage.expr import And, Eq, In
from openviking.utils.embedding_utils import vectorize_directory_meta
from openviking.utils.path_safety import validate_safe_viking_uri_path
from openviking_cli.exceptions import NotInitializedError, OpenVikingError
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

_COMPILE_DIRECTORY_TAG_TIMEOUT_SECONDS = 60.0
_COMPILE_DIRECTORY_TAG_POLL_SECONDS = 3.0


class _FSCompileOpsMixin:
    """Mixin adding batch ACL/tag checks and compile directory finalization to FSService."""

    async def ensure_write_access(self, uri: str, ctx: RequestContext) -> None:
        """Validate write access without mutating the target."""
        viking_fs = self._ensure_initialized()
        await viking_fs._ensure_access(uri, ctx, action=AclAction.WRITE)

    async def ensure_remove_access(self, uri: str, ctx: RequestContext) -> None:
        """Validate namespace and ACL checks used when removing a file."""
        viking_fs = self._ensure_initialized()
        await viking_fs._ensure_access(uri, ctx, action=AclAction.MANAGE)

    async def can_read_many(
        self,
        uris: Sequence[str],
        ctx: RequestContext,
    ) -> Dict[str, bool]:
        """Return caller-specific read visibility for each URI."""
        viking_fs = self._ensure_initialized()
        return await viking_fs._can_access_many(list(uris), ctx, action=AclAction.READ)

    async def get_tags_many(
        self,
        uris: Sequence[str],
        ctx: RequestContext,
        *,
        check_access: bool = True,
    ) -> Dict[str, List[str]]:
        """Return vector-backed retrieval tags for each URI."""
        unique_uris = list(dict.fromkeys(uris))
        if not unique_uris:
            return {}
        if check_access:
            access = await self.can_read_many(unique_uris, ctx)
            unique_uris = [uri for uri in unique_uris if access.get(uri, False)]
        entries = [{"uri": uri, "isDir": False} for uri in unique_uris]
        tagged_entries = await self._attach_and_filter_tags(
            entries,
            ctx,
            tags=None,
            include_tags=True,
        )
        return {str(entry["uri"]): list(entry.get("tags") or []) for entry in tagged_entries}

    async def _directory_index_records(self, uri: str, ctx: RequestContext) -> List[Dict[str, Any]]:
        """Read L0/L1 vector records and tags for a directory URI."""
        viking_fs = self._ensure_initialized()
        store = viking_fs._get_vector_store()
        if store is None:
            raise NotInitializedError("Vector store")
        records, cursor = await store.scroll(
            filter=And([Eq("uri", uri), In("level", [0, 1])]),
            limit=3,
            output_fields=["id", "uri", "level", "search_tags"],
            ctx=ctx,
        )
        if cursor is not None or len({record["level"] for record in records}) != len(records):
            raise OpenVikingError(
                f"Duplicate directory index records: {uri}", code="FAILED_PRECONDITION"
            )
        return records

    async def finalize_compile_directories(self, uri: str, ctx: RequestContext) -> Dict[str, Any]:
        """Ensure L0/L1 directory index and tag the target directory as ``compile_target=true``."""
        viking_fs = self._ensure_initialized()
        uri = validate_safe_viking_uri_path(uri)
        await viking_fs._ensure_access(uri, ctx, action=AclAction.WRITE)

        records = await self._directory_index_records(uri, ctx)
        if not records:
            abstract = ""
            try:
                abstract = (await viking_fs.abstract(uri, ctx=ctx)).strip()
            except Exception:
                abstract = ""
            if not abstract:
                abstract = "This is the compile generated folder"
                await viking_fs.write_file(f"{uri}/.abstract.md", abstract, ctx=ctx)
            await vectorize_directory_meta(uri=uri, abstract=abstract, ctx=ctx)
            records = await self._directory_index_records(uri, ctx)

        expected_levels = {record["level"] for record in records}
        applied_levels: set[int] = set()
        set_tags_result = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _COMPILE_DIRECTORY_TAG_TIMEOUT_SECONDS
        while True:
            records = await self._directory_index_records(uri, ctx)
            actual_levels = {record["level"] for record in records}
            expected_levels.update(actual_levels)
            untagged_levels = {
                record["level"]
                for record in records
                if "compile_target=true" not in (record.get("search_tags") or [])
            }
            if untagged_levels - applied_levels:
                set_tags_result = await self.set_tags(
                    uri, ["compile_target=true"], mode="append", recursive=False, ctx=ctx
                )
                if set_tags_result.get("success_count", 0) >= 2:
                    applied_levels.update({0, 1})
                records = await self._directory_index_records(uri, ctx)
                actual_levels = {record["level"] for record in records}
                expected_levels.update(actual_levels)
            tagged_levels = {
                record["level"]
                for record in records
                if "compile_target=true" in (record.get("search_tags") or [])
            }
            if not expected_levels or not (expected_levels - tagged_levels):
                break
            remaining = deadline - loop.time()
            if remaining <= 0:
                details = {
                    "directory": uri,
                    "expected_levels": sorted(expected_levels),
                    "actual_levels": sorted(actual_levels),
                    "tagged_levels": sorted(tagged_levels),
                    "records": records,
                    "set_tags_result": set_tags_result,
                }
                logger.error("Compile directory tag validation timed out: %s", details)
                raise OpenVikingError(
                    f"Compile directory tags are incomplete: {uri}",
                    code="PROCESSING_ERROR",
                    details=details,
                )
            await asyncio.sleep(min(_COMPILE_DIRECTORY_TAG_POLL_SECONDS, remaining))
        return {"directory_count": 1}
