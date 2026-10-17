# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Data consistency checks between VikingFS content and vector index records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openviking.core.context import ResourceContentType
from openviking.core.namespace import is_session_uri
from openviking.server.identity import RequestContext
from openviking.storage.expr import Eq
from openviking.utils.embedding_utils import get_resource_content_type
from openviking_cli.utils.logger import get_logger
from openviking_cli.utils.uri import VikingURI

logger = get_logger(__name__)

NON_INDEX_SCOPES = frozenset({"session"})
PUBLIC_MISSING_RECORD_LIMIT = 20
ERROR_DETAILS_MISSING_RECORD_LIMIT = 1


@dataclass(frozen=True)
class IndexExpectation:
    """One vector index record expected from filesystem content."""

    uri: str
    rel_path: str
    level: int

    @property
    def key(self) -> str:
        path = self.rel_path or "."
        return f"{path}#level={self.level}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "path": self.rel_path,
            "level": self.level,
            "key": self.key,
        }


@dataclass(frozen=True)
class IndexConsistencyReport:
    """Result of checking filesystem/index consistency and orphan hygiene for a subtree."""

    expected: tuple[IndexExpectation, ...]
    missing_records: tuple[IndexExpectation, ...]
    orphan_records: tuple[str, ...] = ()
    bm25_orphan_uris: tuple[str, ...] = ()
    pruned_vector_count: int = 0
    pruned_bm25_count: int = 0
    consistency_score: float = 100.0

    @property
    def ok(self) -> bool:
        return not self.missing_records and not self.orphan_records and not self.bm25_orphan_uris

    def details(self, limit: int = ERROR_DETAILS_MISSING_RECORD_LIMIT) -> dict[str, Any]:
        limited = self.missing_records[:limit]
        return {
            "ok": self.ok,
            "consistency_score": self.consistency_score,
            "expected_count": len(self.expected),
            "missing_record_count": len(self.missing_records),
            "orphan_record_count": len(self.orphan_records),
            "bm25_orphan_count": len(self.bm25_orphan_uris),
            "pruned_vector_count": self.pruned_vector_count,
            "pruned_bm25_count": self.pruned_bm25_count,
            "missing_records": [item.key for item in limited],
            "missing_records_truncated": len(self.missing_records) > len(limited),
        }

    def to_dict(self, limit: int = PUBLIC_MISSING_RECORD_LIMIT) -> dict[str, Any]:
        limited_missing = self.missing_records[:limit]
        limited_orphans = self.orphan_records[:limit]
        limited_bm25 = self.bm25_orphan_uris[:limit]
        return {
            "ok": self.ok,
            "consistency_score": self.consistency_score,
            "expected_count": len(self.expected),
            "missing_record_count": len(self.missing_records),
            "orphan_record_count": len(self.orphan_records),
            "bm25_orphan_count": len(self.bm25_orphan_uris),
            "pruned_vector_count": self.pruned_vector_count,
            "pruned_bm25_count": self.pruned_bm25_count,
            "missing_records": [item.to_dict() for item in limited_missing],
            "orphan_records": list(limited_orphans),
            "bm25_orphan_records": list(limited_bm25),
            "missing_records_truncated": len(self.missing_records) > len(limited_missing),
        }


def _join_uri(base_uri: str, rel_path: str) -> str:
    return VikingURI(base_uri).join(rel_path).uri


def _entry_uri(root_uri: str, entry: dict[str, Any]) -> str:
    uri = entry.get("uri")
    if isinstance(uri, str) and uri:
        return uri
    rel_path = str(entry.get("rel_path") or "")
    return _join_uri(root_uri, rel_path)


def _is_index_scope(uri: str) -> bool:
    try:
        return VikingURI(uri).scope not in NON_INDEX_SCOPES and not is_session_uri(uri)
    except Exception:
        return False


def _leaf_name(uri_or_path: str) -> str:
    return uri_or_path.rstrip("/").split("/")[-1]


async def _read_text_if_exists(viking_fs, uri: str, ctx: RequestContext) -> str:
    try:
        if not await viking_fs.exists(uri, ctx=ctx):
            return ""
        content = await viking_fs.read_file(uri, ctx=ctx)
        return content.decode("utf-8") if isinstance(content, bytes) else str(content)
    except Exception:
        return ""


def _directory_candidates(
    root_uri: str,
    entries: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if root_uri != "viking://" and _is_index_scope(root_uri):
        candidates.append((root_uri, ""))

    for entry in entries:
        if not entry.get("isDir"):
            continue
        uri = _entry_uri(root_uri, entry)
        if not _is_index_scope(uri):
            continue
        rel_path = str(entry.get("rel_path") or "")
        candidates.append((uri, rel_path))
    return candidates


def _file_candidates(
    root_uri: str,
    entries: list[dict[str, Any]],
) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    for entry in entries:
        if entry.get("isDir"):
            continue
        size = entry.get("size")
        if isinstance(size, int) and not isinstance(size, bool) and size == 0:
            continue
        uri = _entry_uri(root_uri, entry)
        if not _is_index_scope(uri):
            continue
        rel_path = str(entry.get("rel_path") or "")
        name = str(entry.get("name") or _leaf_name(rel_path))
        if name.startswith("."):
            continue
        candidates.append((uri, rel_path, name))
    return candidates


async def build_index_expectations(
    viking_fs,
    root_uri: str,
    entries: list[dict[str, Any]],
    ctx: RequestContext,
) -> tuple[IndexExpectation, ...]:
    """Build the index records expected from current filesystem content."""
    expectations: list[IndexExpectation] = []

    for uri, rel_path in _directory_candidates(root_uri, entries):
        abstract = await _read_text_if_exists(viking_fs, f"{uri}/.abstract.md", ctx)
        overview = await _read_text_if_exists(viking_fs, f"{uri}/.overview.md", ctx)
        if abstract:
            expectations.append(IndexExpectation(uri=uri, rel_path=rel_path, level=0))
        if overview:
            expectations.append(IndexExpectation(uri=uri, rel_path=rel_path, level=1))

    for uri, rel_path, name in _file_candidates(root_uri, entries):
        if get_resource_content_type(name) == ResourceContentType.TEXT:
            expectations.append(IndexExpectation(uri=uri, rel_path=rel_path, level=2))

    return tuple(sorted(expectations, key=lambda item: (item.rel_path, item.level)))


def _record_level(record: dict[str, Any]) -> int | None:
    level = record.get("level")
    if isinstance(level, bool) or not isinstance(level, int):
        return None
    return level


async def _fetch_index_records(vector_store, uri: str, ctx: RequestContext) -> list[dict[str, Any]]:
    if not vector_store or not hasattr(vector_store, "filter"):
        return []

    kwargs = {
        "filter": Eq("uri", uri),
        "limit": 10,
        "output_fields": ["uri", "level"],
    }
    try:
        return await vector_store.filter(**kwargs, ctx=ctx)
    except TypeError:
        try:
            return await vector_store.filter(**kwargs)
        except Exception as exc:
            logger.warning(f"Failed to check vector index records for {uri}: {exc}")
    except Exception as exc:
        logger.warning(f"Failed to check vector index records for {uri}: {exc}")
    return []


async def _fetch_all_indexed_uris(vector_store, root_uri: str, ctx: RequestContext) -> set[str]:
    """Scan or filter indexed URIs from the vector store under root_uri."""
    indexed_uris: set[str] = set()
    if not vector_store:
        return indexed_uris

    try:
        if hasattr(vector_store, "scroll"):
            records = await vector_store.scroll(limit=2000, output_fields=["uri"], ctx=ctx)
            for r in records or []:
                u = r.get("uri") if isinstance(r, dict) else getattr(r, "uri", None)
                if u and _is_subpath_or_equal(u, root_uri):
                    indexed_uris.add(u)
        elif hasattr(vector_store, "filter"):
            records = await vector_store.filter(limit=2000, output_fields=["uri"], ctx=ctx)
            for r in records or []:
                u = r.get("uri") if isinstance(r, dict) else getattr(r, "uri", None)
                if u and _is_subpath_or_equal(u, root_uri):
                    indexed_uris.add(u)
    except Exception as exc:
        logger.debug(f"Scan indexed URIs skipped: {exc}")

    return indexed_uris


def _is_subpath_or_equal(uri: str, root_uri: str) -> bool:
    if root_uri in ("viking://", "viking:"):
        return True
    norm_root = root_uri.rstrip("/")
    return uri == norm_root or uri.startswith(norm_root + "/")


async def check_index_consistency(
    viking_fs,
    vector_store,
    root_uri: str,
    entries: list[dict[str, Any]],
    ctx: RequestContext,
    prune: bool = False,
    bm25_index: Any = None,
) -> IndexConsistencyReport:
    """Check that filesystem content has the expected vector and BM25 index records,
    and optionally prune orphan records that no longer exist in the filesystem."""
    expectations = await build_index_expectations(viking_fs, root_uri, entries, ctx)
    missing_records: list[IndexExpectation] = []

    records_by_uri: dict[str, dict[int, dict[str, Any]]] = {}
    for expectation in expectations:
        if expectation.uri not in records_by_uri:
            records = await _fetch_index_records(vector_store, expectation.uri, ctx)
            records_by_uri[expectation.uri] = {
                level: record for record in records if (level := _record_level(record)) is not None
            }
        record = records_by_uri[expectation.uri].get(expectation.level)
        if record is None:
            missing_records.append(expectation)

    valid_expected_uris = {exp.uri for exp in expectations}

    # 1. Reverse Check: Detect orphan vector records
    indexed_vector_uris = await _fetch_all_indexed_uris(vector_store, root_uri, ctx)
    orphan_vector_records: list[str] = sorted(
        [u for u in indexed_vector_uris if u not in valid_expected_uris]
    )

    pruned_vector_count = 0
    if prune and orphan_vector_records:
        for u in orphan_vector_records:
            if hasattr(vector_store, "remove_by_uri"):
                try:
                    await vector_store.remove_by_uri(u)
                    pruned_vector_count += 1
                except Exception as exc:
                    logger.warning(f"Failed to prune orphan vector {u}: {exc}")

    # 2. Reverse Check: Detect orphan BM25 FTS5 records
    if bm25_index is None:
        try:
            from openviking.storage.bm25_fts_index import BM25FTSIndex
            bm25_index = BM25FTSIndex.get_instance()
        except Exception:
            bm25_index = None

    bm25_orphan_uris: list[str] = []
    pruned_bm25_count = 0
    if bm25_index and hasattr(bm25_index, "list_all_uris"):
        try:
            filter_prefix = None if root_uri in ("viking://", "viking:") else root_uri
            indexed_bm25 = bm25_index.list_all_uris(prefix=filter_prefix)
            bm25_orphan_uris = sorted([u for u in indexed_bm25 if u not in valid_expected_uris])
            if prune and hasattr(bm25_index, "prune_orphans"):
                pruned_bm25_count = bm25_index.prune_orphans(valid_expected_uris, prefix=filter_prefix)
        except Exception as exc:
            logger.warning(f"Failed to check/prune BM25 orphans: {exc}")

    # 3. Calculate Consistency Health Score
    total_expected = len(expectations)
    active_missing = len(missing_records)
    active_orphans = (len(orphan_vector_records) - pruned_vector_count) + (len(bm25_orphan_uris) - pruned_bm25_count)
    total_anomalies = active_missing + max(0, active_orphans)

    if total_expected == 0:
        score = 100.0 if total_anomalies == 0 else 0.0
    else:
        penalty = (total_anomalies / total_expected) * 100.0
        score = max(0.0, round(100.0 - penalty, 1))

    return IndexConsistencyReport(
        expected=expectations,
        missing_records=tuple(missing_records),
        orphan_records=tuple(orphan_vector_records),
        bm25_orphan_uris=tuple(bm25_orphan_uris),
        pruned_vector_count=pruned_vector_count,
        pruned_bm25_count=pruned_bm25_count,
        consistency_score=score,
    )
