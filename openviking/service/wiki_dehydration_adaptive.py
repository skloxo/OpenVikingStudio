# -*- coding: utf-8 -*-
"""Adaptive Auto-Dehydration Classifier (Munger Inversion & Zero-Intervention SSOT).

First Principles:
1. Zero Human Friction: Memory retrieval should be silent, automatic, and frictionless.
   Users and agents should NOT be required to explicitly remember `dehydrate=True`.
2. Munger Inversion Guardrails (Fail-Safe Preservation):
   - Inversion A (Code Safety): NEVER apply natural language token pruning to source code
     (.py, .ts, .json, .yaml, etc.) to prevent AST/syntax breakage.
   - Inversion B (Short Text Overhead): Skip short snippets (< 800 chars / ~200 tokens)
     where compression ROI is negligible and model latency is a net negative.
   - Inversion C (Anti-Recompression): Prevent degradation caused by recursive multi-pass compression.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional, Set, Tuple

# Source code and strictly structured data file extensions that MUST NOT be pruned by LLMLingua-2
PRESERVED_SOURCE_EXTENSIONS: Set[str] = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".conf", ".sql", ".sh", ".bash", ".zsh",
    ".go", ".rs", ".c", ".cpp", ".h", ".hpp", ".java", ".kt",
    ".css", ".scss", ".less", ".xml", ".html",
}

# Document extensions eligible for natural language and markdown prose dehydration
DEHYDRATABLE_DOC_EXTENSIONS: Set[str] = {
    ".md", ".markdown", ".txt", ".wiki", ".rst",
}

DEFAULT_MIN_CHARS_THRESHOLD: int = 800


def should_auto_dehydrate(
    content: str,
    uri_or_path: Optional[str] = None,
    min_chars_threshold: int = DEFAULT_MIN_CHARS_THRESHOLD,
) -> Tuple[bool, str]:
    """
    Decide whether a given document should be silently auto-dehydrated.

    Returns:
        (should_dehydrate: bool, reason: str)
    """
    if not isinstance(content, str) or not content.strip():
        return False, "empty content"

    stripped = content.strip()
    if len(stripped) < min_chars_threshold:
        return False, f"content too short for compression ({len(stripped)} < {min_chars_threshold} chars)"

    # Rule 1: Extension-based physical safety check
    if uri_or_path:
        clean_path = uri_or_path.split("?")[0].split("#")[0]
        _, ext = os.path.splitext(clean_path.lower())
        if ext in PRESERVED_SOURCE_EXTENSIONS:
            return False, f"source code or structured config preserved as-is: {ext}"

    # Rule 2: Pure JSON check
    if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
        try:
            json.loads(stripped)
            return False, "structured JSON payload preserved as-is"
        except Exception:
            pass

    # Rule 3: Anti-recompression check
    if "<!-- llmlingua-2:dehydrated -->" in stripped or "dehydrated_by: llmlingua" in stripped:
        return False, "document already dehydrated"

    # Rule 4: High-density source code heuristic (if no filename provided)
    if not uri_or_path:
        lines = stripped.splitlines()
        code_like_lines = sum(
            1 for line in lines[:30]
            if re.match(r"^\s*(def |class |import |from |export |const |let |var |func |package |//|/\*)", line)
        )
        if len(lines) > 0 and (code_like_lines / min(len(lines), 30)) > 0.4:
            return False, "source code pattern detected without markdown container"

    return True, "adaptive long markdown/prose document"
