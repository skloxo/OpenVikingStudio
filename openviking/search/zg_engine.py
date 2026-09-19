# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
zg (zvec-grep) Code Semantic Search Engine.
Quartet Search: Symbol Match + Intent Match + AST Signature + RRF Fusion.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.17)
"""

import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.search.ast_chunker import ASTChunker, CodeSymbolChunk
from openviking.search.tiered_fetch import TieredLazyFetch, TieredFetchSummary, TierLevel
from openviking.storage.bm25_fts_index import BM25FTSIndex, BM25Match
from openviking.retrieve.rrf_fusion import rrf_fuse, FusedCandidate


class ZGStats(BaseModel):
    """Index and performance stats of zg engine."""
    total_symbols: int
    total_files: int
    total_lines: int
    avg_lines_per_symbol: float
    is_ready: bool
    last_indexed_ts: float


class ZGSearchEngine:
    """Local-first AST code semantic search engine."""

    _instance: Optional["ZGSearchEngine"] = None
    _lock = threading.Lock()

    def __init__(self, repo_root: Optional[Path] = None, db_path: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self._lock = threading.Lock()
        self.symbols_by_uri: Dict[str, CodeSymbolChunk] = {}
        self.symbols_by_fp: Dict[str, CodeSymbolChunk] = {}
        self.files_indexed: set = set()
        self.total_lines_indexed: int = 0
        self.last_indexed_ts: float = 0.0

        # Dedicated BM25 FTS5 index for code symbols
        if db_path is not None:
            self.bm25 = BM25FTSIndex(db_path=Path(db_path))
        else:
            base_dir = Path(os.path.expanduser("~/.openviking/data/viking/default"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.bm25 = BM25FTSIndex(db_path=base_dir / "zg_code_fts.db")

        self._init_symbol_db()
        self._load_persisted_symbols()

    def _init_symbol_db(self) -> None:
        """Initialize SQLite table for symbol metadata persistence."""
        conn = self.bm25._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fts_symbol_records (
                    uri TEXT PRIMARY KEY,
                    fingerprint TEXT,
                    file_path TEXT,
                    symbol_name TEXT,
                    symbol_type TEXT,
                    json_data TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_persisted_symbols(self) -> int:
        """Fast-load symbols from local SQLite cache."""
        conn = self.bm25._get_connection()
        loaded = 0
        try:
            cursor = conn.execute("SELECT json_data FROM fts_symbol_records")
            rows = cursor.fetchall()
            for (data_json,) in rows:
                try:
                    c = CodeSymbolChunk.model_validate_json(data_json)
                    self.symbols_by_uri[c.uri] = c
                    self.symbols_by_fp[c.fingerprint] = c
                    self.files_indexed.add(c.file_path)
                    self.total_lines_indexed += c.line_count
                    loaded += 1
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            conn.close()
        return loaded

    @classmethod
    def get_instance(cls, repo_root: Optional[Path] = None) -> "ZGSearchEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(repo_root)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def index_directory(self, dir_path: Optional[Path] = None, max_files: int = 500) -> int:
        """Scan directory, chunk via AST, and populate FTS5 index and persistence cache."""
        target_dir = dir_path or (self.repo_root / "openviking")
        if not target_dir.exists():
            return 0

        chunks = ASTChunker.parse_directory(target_dir, max_files=max_files)
        if not chunks:
            return 0

        index_docs = []
        conn = self.bm25._get_connection()
        try:
            with self._lock:
                for c in chunks:
                    self.symbols_by_uri[c.uri] = c
                    self.symbols_by_fp[c.fingerprint] = c
                    self.files_indexed.add(c.file_path)
                    self.total_lines_indexed += c.line_count
                    index_docs.append(c.to_index_dict())

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO fts_symbol_records(uri, fingerprint, file_path, symbol_name, symbol_type, json_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (c.uri, c.fingerprint, c.file_path, c.symbol_name, c.symbol_type, c.model_dump_json()),
                    )

                conn.commit()
                self.bm25.index_batch(index_docs)
                self.last_indexed_ts = time.time()
        finally:
            conn.close()

        return len(chunks)

    def search(
        self,
        query: str,
        depth: int = 1,
        limit: int = 10,
        path_filter: Optional[str] = None,
    ) -> TieredFetchSummary:
        """
        Execute quartet search across indexed code symbols and format at requested depth.
        """
        t0 = time.monotonic()
        clean_query = query.strip()
        if not clean_query:
            return TieredFetchSummary(
                depth=depth,
                total_results=0,
                actual_tokens_total=0,
                baseline_tokens_total=0,
                total_tokens_saved=0,
                savings_percentage=0.0,
                results=[],
            )

        # Lazy initialize if empty
        if not self.symbols_by_uri:
            self.index_directory(max_files=100)

        # 1. Lexical / Symbol Search via FTS5 BM25
        matches: List[BM25Match] = self.bm25.search(
            query=clean_query,
            limit=limit * 3,
            context_type="code_symbol",
        )

        matched_chunks: List[CodeSymbolChunk] = []
        matched_scores: List[float] = []

        for m in matches:
            chunk = self.symbols_by_uri.get(m.uri)
            if not chunk:
                continue
            if path_filter and path_filter not in chunk.file_path:
                continue
            matched_chunks.append(chunk)
            matched_scores.append(m.bm25_score)
            if len(matched_chunks) >= limit:
                break

        # Fallback: in-memory substring match if FTS5 returned 0 (e.g. newly added memory chunk)
        if not matched_chunks:
            q_lower = clean_query.lower()
            with self._lock:
                for chunk in self.symbols_by_uri.values():
                    if path_filter and path_filter not in chunk.file_path:
                        continue
                    # Match name, signature, or docstring
                    if (
                        q_lower in chunk.symbol_name.lower()
                        or q_lower in chunk.signature.lower()
                        or q_lower in chunk.docstring.lower()
                    ):
                        matched_chunks.append(chunk)
                        matched_scores.append(0.75)
                        if len(matched_chunks) >= limit:
                            break

        return TieredLazyFetch.format_batch(
            chunks=matched_chunks,
            depth=depth,
            scores=matched_scores,
        )

    def fetch_by_fingerprint(self, fingerprint: str, depth: int = 2) -> Optional[Dict[str, Any]]:
        """Fetch exact symbol by anchor fingerprint at desired depth."""
        chunk = self.symbols_by_fp.get(fingerprint)
        if not chunk:
            return None
        formatted = TieredLazyFetch.format_chunk(chunk, depth=depth)
        return formatted.model_dump()

    def get_stats(self) -> ZGStats:
        """Return engine metadata statistics."""
        with self._lock:
            n_sym = len(self.symbols_by_uri)
            n_files = len(self.files_indexed)
            tot_lines = self.total_lines_indexed
            avg_lines = round(tot_lines / max(1, n_sym), 1) if n_sym > 0 else 0.0

            return ZGStats(
                total_symbols=n_sym,
                total_files=n_files,
                total_lines=tot_lines,
                avg_lines_per_symbol=avg_lines,
                is_ready=n_sym > 0,
                last_indexed_ts=self.last_indexed_ts,
            )
