# -*- coding: utf-8 -*-
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Map-Shuffle-Reduce Compiler module for OpenViking.

Provides scalable offline knowledge compilation and domain clustering.
"""

from openviking.parse.compiler.pipeline import (
    CompilationResult,
    DocumentChunk,
    DomainBucket,
    KnowledgeCompiler,
    L0Overview,
    SourceDocument,
)

__all__: list[str] = [
    "CompilationResult",
    "DocumentChunk",
    "DomainBucket",
    "KnowledgeCompiler",
    "L0Overview",
    "SourceDocument",
]
