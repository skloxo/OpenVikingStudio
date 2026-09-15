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
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
        """Initialize the FTS5 virtual table and metadata index."""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
                        uri UNINDEXED,
                        title,
                        content,
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
                conn.commit()
            finally:
                conn.close()

    def _sanitize_query(self, query: str) -> str:
        """Sanitize query string to safe FTS5 query syntax."""
        cleaned = re.sub(r'["\*\^:\(\)\.\/\-,;\{\}\[\]@#\$%\&!=+\?<>]', " ", query).strip()
        tokens = [t.strip() for t in re.split(r"\s+", cleaned) if t.strip()]
        if not tokens:
            return ""
        safe_terms = []
        for token in tokens:
            safe_token = re.sub(r"[^\w_]", "", token)
            if not safe_token:
                continue
            safe_terms.append(f"{safe_token}*")
            if "_" in safe_token:
                subparts = [p for p in safe_token.split("_") if p]
                if len(subparts) > 1:
                    joined_parts = " ".join(f"{p}*" for p in subparts)
                    safe_terms.append(f"({joined_parts})")
        if not safe_terms:
            return ""
        return " OR ".join(safe_terms)

    def index_document(
        self,
        uri: str,
        title: str,
        content: str,
        level: int = 2,
        context_type: str = "resource",
    ) -> bool:
        """Upsert a single document into FTS5 index."""
        if not uri or not content:
            return False

        with self._db_lock:
            conn = self._get_connection()
            try:
                # Delete existing by uri
                conn.execute("DELETE FROM fts_documents WHERE uri = ?", (uri,))
                conn.execute(
                    """
                    INSERT INTO fts_documents(uri, title, content, level, context_type)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (uri, title or "", content, level, context_type),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO fts_meta(uri) VALUES (?)",
                    (uri,),
                )
                conn.commit()
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

        indexed = 0
        with self._db_lock:
            conn = self._get_connection()
            try:
                for item in items:
                    uri = item.get("uri")
                    content = item.get("content")
                    if not uri or not content:
                        continue
                    title = item.get("title", "")
                    level = item.get("level", 2)
                    context_type = item.get("context_type", "resource")

                    conn.execute("DELETE FROM fts_documents WHERE uri = ?", (uri,))
                    conn.execute(
                        """
                        INSERT INTO fts_documents(uri, title, content, level, context_type)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (uri, title, content, level, context_type),
                    )
                    conn.execute("INSERT OR REPLACE INTO fts_meta(uri) VALUES (?)", (uri,))
                    indexed += 1
                conn.commit()
            except Exception:
                conn.rollback()
            finally:
                conn.close()
        return indexed

    def delete_document(self, uri: str) -> bool:
        """Remove a document from FTS5 index."""
        with self._db_lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM fts_documents WHERE uri = ?", (uri,))
                conn.execute("DELETE FROM fts_meta WHERE uri = ?", (uri,))
                conn.commit()
                return True
            finally:
                conn.close()

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
                   bm25(fts_documents) as raw_score,
                   snippet(fts_documents, 2, '<b>', '</b>', '...', 16) as snippet
            FROM fts_documents
            WHERE fts_documents MATCH ?
        """
        params: List[Any] = [fts_query]

        if context_type:
            sql += " AND context_type = ?"
            params.append(context_type)

        sql += " ORDER BY raw_score ASC LIMIT ?"
        params.append(max(1, limit))

        results: List[BM25Match] = []
        with self._db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                for rank, row in enumerate(rows, start=1):
                    uri, title, level, c_type, raw_score, snippet = row

                    # Filter by target_directories if provided
                    if target_directories:
                        if not any(uri.startswith(d.rstrip("/")) for d in target_directories):
                            continue

                    # SQLite FTS5 bm25 produces negative numbers; more negative == better match
                    # Normalize to [0.0, 1.0] where 1.0 is the best score
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
                            rank=rank,
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
