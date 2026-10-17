# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Data Models and DTOs for Tri-Gate Entropy Crystallization & SSOT Distillation.
(Card-Memory-EntropyCrystallizer-IdleDaemon-Closure / v1.5.80)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryFragment(BaseModel):
    """Raw candidate memory fragment in the crystallization pool."""

    uri: str
    content: str
    created_at: float = Field(default_factory=time.time)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TriGateRule(BaseModel):
    """Configuration thresholds for the tri-gate barrier."""

    min_cluster_size: int = 5
    min_avg_cosine_similarity: float = 0.75
    cooling_period_hours: float = 24.0


class TriGateEvaluation(BaseModel):
    """Verification results for the three parallel hard gates."""

    passed: bool
    cluster_size: int
    cluster_size_passed: bool
    avg_similarity: float
    similarity_passed: bool
    cooling_hours: float
    cooling_passed: bool
    rejection_reasons: List[str] = Field(default_factory=list)


class CrystalContextBounds(BaseModel):
    """L1: Target version range, provenance source URIs, and evidence hashes."""

    version_range: str
    source_uris: List[str]
    evidence_hashes: List[str]
    distilled_at: float = Field(default_factory=time.time)
    distiller_id: str = "openviking-crystallizer"


class CrystalNegativeBoundary(BaseModel):
    """L2: Repulsion sentinels, deprecated anti-patterns, and forbidden keywords."""

    deprecated_patterns: List[str] = Field(default_factory=list)
    forbidden_keywords: List[str] = Field(default_factory=list)


class FactCrystal(BaseModel):
    """Three-Tier Immutable Fact Crystal Schema (L0 / L1 / L2)."""

    uri: str
    axiom: str  # L0: Core Immutable Axiom
    context_bounds: CrystalContextBounds  # L1: Version range & Evidence chain
    negative_boundary: CrystalNegativeBoundary  # L2: Negative Repulsion Boundary
    status: str = "active"
    created_at: float = Field(default_factory=time.time)


class CrystallizationResult(BaseModel):
    """Result of distilling a cluster of fragments into an immutable Fact Crystal."""

    crystal: FactCrystal
    superseded_uris: List[str]
    net_entropy_reduced: int
    evaluation: TriGateEvaluation


class TriGateRejectionError(ValueError):
    """Raised when crystallization is attempted on candidates failing the tri-gate barrier."""

    pass
