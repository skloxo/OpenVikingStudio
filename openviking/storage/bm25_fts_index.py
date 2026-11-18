# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
SQLite3 FTS5 Inverted Index & BM25 Sparse Lexical Search Engine.

Key Principles:
1. Zero External Dependencies: Built on Python's native sqlite3 with FTS5.
2. Code & Symbol Precision: Native unicode61 tokenizer matching exact symbols, ports, paths, and function names.
3. Thread-Safe & Local-First: Connection per thread or thread-safe lock with WAL mode.
4. Normalized BM25: Converts negative FTS5 scores to [0, 1] for unified rank fusion.
"""

import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

from openviking.storage.bm25_tokenizer import build_cjk_token_field, sanitize_fts_query


class BM25Match(BaseModel):
    """BM25 search match item."""
    uri: str
    title: str = ""
    level: int = 2
    context_type: str = "resource"
    bm25_raw_score: float = 0.0
    bm25_score: float = 0.0  # Normalized [0, 1]
    snippet: str = ""
    rank: int = 0


class BM25IndexStats(BaseModel):
    """BM25 index statistics."""
    total_documents: int
    db_size_bytes: int
    db_path: str
    is_ready: bool


class BM25FTSIndex:
    """Thread-safe SQLite FTS5 inverted index for fast lexical retrieval."""

    SCHEMA_VERSION = "2"
    _instance: Optional["BM25FTSIndex"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            base_dir = Path(os.path.expanduser("~/.openviking/data/viking/default"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "bm25_index.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db_lock = threading.Lock()
        self._df_cache: Dict[str, int] = {}
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "BM25FTSIndex":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize schema v2 FTS5 virtual table (with CJK token column) and metadata."""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fts_schema_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    """
                )
                row = conn.execute(
                    "SELECT value FROM fts_schema_meta WHERE key = 'schema_version'"
                ).fetchone()
                cols = {
                    r[1]
                    for r in conn.execute("PRAGMA table_info('fts_documents')").fetchall()
                }
                needs_rebuild = (row is None or row[0] != self.SCHEMA_VERSION) or (
                    bool(cols) and "cjk_tokens" not in cols
                )
                migrated_rows: List[tuple[Any, ...]] = []
                if needs_rebuild and {"uri", "title", "content"}.issubset(cols):
                    try:
                        level_expr = "level" if "level" in cols else "2"
                        ctype_expr = "context_type" if "context_type" in cols else "'resource'"
                        migrated_rows = conn.execute(
                            f"SELECT uri, title, content, {level_expr}, {ctype_expr} FROM fts_documents"
                        ).fetchall()
                    except Exception:
                        migrated_rows = []
                if needs_rebuild:
                    conn.execute("DROP TABLE IF EXISTS fts_documents;")
                    conn.execute("DROP TABLE IF EXISTS fts_meta;")
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
                        uri UNINDEXED,
                        title,
                        content,
                        cjk_tokens,
                        level UNINDEXED,
                        context_type UNINDEXED,
                        tokenize="unicode61 tokenchars '_' remove_diacritics 2"
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS fts_meta (
                        uri TEXT PRIMARY KEY,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                if migrated_rows:
                    prepared = [
                        r
                        for u, t, c, lvl, ctype in migrated_rows
                        if (r := self._prepare_row(u, t, c, int(lvl or 2), str(ctype or "resource"))) is not None
                    ]
                    if prepared:
                        self._upsert_prepared_rows(conn, prepared)
                conn.execute(
                    "INSERT OR REPLACE INTO fts_schema_meta(key, value) VALUES ('schema_version', ?)",
                    (self.SCHEMA_VERSION,),
                )
                conn.commit()
            finally:
                conn.close()

    def _sanitize_query(self, query: str) -> str:
        """Sanitize query string to safe FTS5 syntax covering code symbols and CJK."""
        return sanitize_fts_query(query)

    @staticmethod
    def _prepare_row(
        uri: Optional[str],
        title: Optional[str],
        content: Optional[str],
        level: int,
        context_type: str,
    ) -> Optional[tuple[str, str, str, str, int, str]]:
        if not uri or not content:
            return None
        if content.startswith("data:image/") or ";base64," in content[:100]:
            return None
        resolved_title = (title or Path(uri).name or uri)[:512]
        clean_content = content[:65536]
        cjk_tokens = build_cjk_token_field(resolved_title, clean_content)
        return (uri, resolved_title, clean_content, cjk_tokens, int(level), context_type or "resource")

    def _upsert_prepared_rows(
        self,
        conn: sqlite3.Connection,
        rows: List[tuple[str, str, str, str, int, str]],
    ) -> None:
        uris = [(r[0],) for r in rows]
        conn.executemany("DELETE FROM fts_documents WHERE uri = ?", uris)
        conn.executemany(
            """
            INSERT INTO fts_documents(uri, title, content, cjk_tokens, level, context_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.executemany("INSERT OR REPLACE INTO fts_meta(uri) VALUES (?)", uris)

    def index_document(
        self,
        uri: str,
        title: Optional[str] = None,
        content: str = "",
        level: int = 2,
        context_type: str = "resource",
    ) -> bool:
        """Upsert a single document into FTS5 index with payload guard."""
        row = self._prepare_row(uri, title, content, level, context_type)
        if row is None:
            return False

        with self._db_lock:
            conn = self._get_connection()
            try:
                self._upsert_prepared_rows(conn, [row])
                conn.commit()
                self._df_cache.clear()
                return True
            except Exception:
                conn.rollback()
                return False
            finally:
                conn.close()

    def index_batch(self, items: List[Dict[str, Any]]) -> int:
        """Batch insert documents into FTS5 index in a single transaction."""
        if not items:
            return 0

        deduped: Dict[str, tuple[str, str, str, str, int, str]] = {}
        for item in items:
            row = self._prepare_row(
                item.get("uri"),
                item.get("title", ""),
                item.get("content", ""),
                item.get("level", 2),
                item.get("context_type", "resource"),
            )
            if row is not None:
                deduped[row[0]] = row

        rows = list(deduped.values())
        if not rows:
            return 0

        with self._db_lock:
            conn = self._get_connection()
            try:
                self._upsert_prepared_rows(conn, rows)
                if len(rows) >= 32:
                    conn.execute("INSERT INTO fts_documents(fts_documents) VALUES('optimize')")
                conn.commit()
                self._df_cache.clear()
                return len(rows)
            except Exception:
                conn.rollback()
                return 0
            finally:
                conn.close()

    def delete_document(self, uri: str) -> bool:
        """Remove a document from FTS5 index."""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM fts_documents WHERE uri = ?", (uri,))
                conn.execute("DELETE FROM fts_meta WHERE uri = ?", (uri,))
                conn.commit()
                self._df_cache.clear()
                return True
            finally:
                conn.close()

    def list_all_uris(self, prefix: Optional[str] = None) -> List[str]:
        """List all indexed document URIs from metadata index, optionally filtered by prefix."""
        with self._db_lock:
            conn = self._get_connection()
            try:
                if prefix:
                    cur = conn.execute("SELECT uri FROM fts_meta WHERE uri LIKE ?;", (f"{prefix}%",))
                else:
                    cur = conn.execute("SELECT uri FROM fts_meta;")
                return [row[0] for row in cur.fetchall()]
            finally:
                conn.close()

    def prune_orphans(self, valid_uris: set, prefix: Optional[str] = None) -> int:
        """Prune documents from FTS5 whose URIs are not in valid_uris."""
        all_uris = self.list_all_uris(prefix=prefix)
        orphan_uris = [u for u in all_uris if u not in valid_uris]
        if not orphan_uris:
            return 0
        pruned = 0
        with self._db_lock:
            conn = self._get_connection()
            try:
                for u in orphan_uris:
                    conn.execute("DELETE FROM fts_documents WHERE uri = ?", (u,))
                    conn.execute("DELETE FROM fts_meta WHERE uri = ?", (u,))
                    pruned += 1
                conn.commit()
                self._df_cache.clear()
            except Exception:
                conn.rollback()
            finally:
                conn.close()
        return pruned

    def get_terms_df(self, terms: Sequence[str]) -> Dict[str, int]:
        """Return cached document frequencies for candidate terms."""
        cleaned = [t.strip() for t in terms if t and t.strip()]
        if not cleaned:
            return {}
        with self._db_lock:
            missing = [t for t in dict.fromkeys(cleaned) if t not in self._df_cache]
            if missing:
                conn = self._get_connection()
                try:
                    for term in missing:
                        q = '"' + term.replace('"', '""') + '"'
                        row = conn.execute(
                            "SELECT COUNT(*) FROM fts_documents WHERE fts_documents MATCH ?",
                            (q,),
                        ).fetchone()
                        self._df_cache[term] = int(row[0]) if row else 0
                finally:
                    conn.close()
            return {t: self._df_cache[t] for t in cleaned}

    def get_term_df(self, term: str) -> int:
        """Return document frequency for a single term using the in-memory cache."""
        if not term or not term.strip():
            return 0
        return self.get_terms_df([term])[term]

    @staticmethod
    def _build_target_dir_clause(target_directories: List[str]) -> tuple[str, List[str]]:
        def _esc(val: str) -> str:
            return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        clauses: List[str] = []
        params: List[str] = []
        is_resource_search = False
        for raw_dir in target_directories:
            stripped = raw_dir.strip()
            if not stripped:
                continue
            if stripped.rstrip("/") in ("viking://", "viking:", "viking://resources", "viking://agent"):
                is_resource_search = True
            if stripped.endswith("://"):
                clauses.append("(uri = ? OR uri LIKE ? ESCAPE '\\')")
                params.extend([stripped, f"{_esc(stripped)}%"])
            else:
                d_norm = stripped.rstrip("/")
                clauses.append("(uri = ? OR uri LIKE ? ESCAPE '\\')")
                params.extend([d_norm, f"{_esc(d_norm)}/%"])
        if is_resource_search:
            clauses.append("(uri LIKE 'code://%' OR uri LIKE 'skill://%' OR uri LIKE '%code/%')")
        if not clauses:
            return "", []
        return f" AND ({' OR '.join(clauses)})", params

    def search(
        self,
        query: str,
        limit: int = 20,
        context_type: Optional[str] = None,
        target_directories: Optional[List[str]] = None,
    ) -> List[BM25Match]:
        """
        Execute BM25 lexical ranking search.
        Returns ranked BM25Match instances with normalized [0, 1] score.
        """
        fts_query = self._sanitize_query(query)
        if not fts_query:
            return []

        sql = """
            SELECT uri, title, level, context_type,
                   bm25(fts_documents, 0.0, 2.0, 1.0, 1.2, 0.0, 0.0) as raw_score,
                   snippet(fts_documents, 2, '<b>', '</b>', '...', 16) as snippet
            FROM fts_documents
            WHERE fts_documents MATCH ?
        """
        params: List[Any] = [fts_query]

        if context_type:
            sql += " AND context_type = ?"
            params.append(context_type)

        if target_directories:
            dir_clause, dir_params = self._build_target_dir_clause(target_directories)
            sql += dir_clause
            params.extend(dir_params)

        sql += " ORDER BY raw_score ASC LIMIT ?"
        params.append(max(1, limit))

        results: List[BM25Match] = []
        with self._db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                for row in rows:
                    uri, title, level, c_type, raw_score, snippet = row

                    norm_score = 1.0 / (1.0 + max(0.0, -float(raw_score)))
                    results.append(
                        BM25Match(
                            uri=uri,
                            title=title or "",
                            level=int(level or 2),
                            context_type=c_type or "resource",
                            bm25_raw_score=float(raw_score),
                            bm25_score=round(norm_score, 4),
                            snippet=snippet or "",
                            rank=len(results) + 1,
                        )
                    )
            finally:
                conn.close()

        return results

    def get_stats(self) -> BM25IndexStats:
        """Return index statistics."""
        total = 0
        size_bytes = 0
        if self.db_path.exists():
            size_bytes = self.db_path.stat().st_size
            with self._db_lock:
                conn = self._get_connection()
                try:
                    cur = conn.execute("SELECT COUNT(*) FROM fts_meta;")
                    row = cur.fetchone()
                    total = row[0] if row else 0
                except Exception:
                    pass
                finally:
                    conn.close()

        return BM25IndexStats(
            total_documents=total,
            db_size_bytes=size_bytes,
            db_path=str(self.db_path),
            is_ready=self.db_path.exists(),
        )
