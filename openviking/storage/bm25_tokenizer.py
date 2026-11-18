# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Zero-dependency CJK + code-symbol tokenizer and FTS5 query builder for BM25."""

from __future__ import annotations

import re
import unicodedata
from typing import List

STOPWORDS = frozenset(
    "的 了 是 在 和 与 或 哪 什么 哪个 哪些 如何 怎么 为什么 是否 这 那 一个 一种 请 我 你 他 它 吗 呢 吧 地 得 "
    "the a an of in on at to for and or is are was were be by with from which what who how when "
    "where does do did that this it as".split()
)

_CJK_SPAN_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_CLEAN_RE = re.compile(r'["\*\^:\(\)\.\/\-,;\{\}\[\]@#\$%\&!=+\?<>]')
_QUOTE_WRAP_RE = re.compile(r"[^\w_]")
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_FTS_RESERVED = frozenset({"and", "or", "not", "near"})


def extract_cjk_tokens(text: str) -> List[str]:
    """Extract normalized CJK bigrams, trigrams, and short terms for FTS5 indexing/querying."""
    if not text:
        return []
    norm = unicodedata.normalize("NFKC", text)
    tokens: List[str] = []
    for span in _CJK_SPAN_RE.findall(norm):
        n = len(span)
        if n <= 4 and span not in STOPWORDS:
            tokens.append(span)
        if n >= 2:
            for i in range(n - 1):
                bg = span[i : i + 2]
                if bg not in STOPWORDS:
                    tokens.append(bg)
        if n >= 3:
            for i in range(n - 2):
                tg = span[i : i + 3]
                if tg not in STOPWORDS:
                    tokens.append(tg)
    return tokens


def build_cjk_token_field(title: str, content: str, max_tokens: int = 8192) -> str:
    """Build space-delimited CJK index field while keeping code symbols untouched."""
    tokens = extract_cjk_tokens(f"{title or ''} {content or ''}")
    if not tokens:
        return ""
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return " ".join(tokens)


def sanitize_fts_query(query: str, max_terms: int = 48) -> str:
    """Build an FTS5 MATCH expression combining code symbol terms and CJK n-grams."""
    if not query or not query.strip():
        return ""
    norm = unicodedata.normalize("NFKC", query)
    cleaned = _ASCII_CLEAN_RE.sub(" ", norm).strip()
    raw_tokens = [t.strip() for t in re.split(r"\s+", cleaned) if t.strip()]

    terms: List[str] = []
    seen: set[str] = set()

    def _add(expr: str) -> None:
        if expr and expr not in seen and len(terms) < max_terms:
            seen.add(expr)
            terms.append(expr)

    for token in raw_tokens:
        ascii_only = "".join(ch for ch in token if ord(ch) < 128)
        safe_ascii = _QUOTE_WRAP_RE.sub("", ascii_only)
        if safe_ascii:
            low = safe_ascii.lower()
            if low not in STOPWORDS and low not in _FTS_RESERVED:
                _add(f"{safe_ascii}*")
                if "_" in safe_ascii:
                    subparts = [p for p in safe_ascii.split("_") if p and p.lower() not in STOPWORDS and p.lower() not in _FTS_RESERVED]
                    if len(subparts) > 1:
                        _add(f"({' '.join(f'{p}*' for p in subparts)})")
                else:
                    camel_parts = [p for p in _CAMEL_SPLIT_RE.split(safe_ascii) if len(p) >= 2 and p.lower() not in STOPWORDS and p.lower() not in _FTS_RESERVED]
                    if len(camel_parts) > 1:
                        _add(f"({' '.join(f'{p}*' for p in camel_parts)})")
                if safe_ascii.isdigit():
                    _add(f'"{safe_ascii}"')

        for cjk in extract_cjk_tokens(token):
            _add('"' + cjk.replace('"', '""') + '"')

    for cjk in extract_cjk_tokens(norm):
        _add('"' + cjk.replace('"', '""') + '"')

    return " OR ".join(terms)
