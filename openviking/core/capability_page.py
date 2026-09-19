"""
Capability Page Engine (Tencent Capability Pages Architecture).

Implements the three-segment skill profile:
- T+ (Positive Triggers): Explicit intent anchors and positive exemplars
- T- (Negative Boundaries): Hard negative boundaries and confusing counter-examples
- B (Discriminative Body): Functional contracts, input/output schemas, prerequisites

Deployment Isolation Rule:
- Vector/BM25 index MUST only contain T+ and B.
- T- MUST NEVER be indexed in the retrieval vector space to prevent semantic drift.
- T- is strictly reserved for Stage-2 Cross-Encoder / Router adjudication.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiscriminativeBody(BaseModel):
    """B: Functional description, prerequisites, and input/output contracts."""
    summary: str
    prerequisites: List[str] = Field(default_factory=list)
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: Dict[str, str] = Field(default_factory=dict)


class CapabilityPage(BaseModel):
    """Tencent Capability Page: Three-segment skill profile."""
    skill_id: str
    skill_name: str
    cluster_id: str = "general"
    positive_triggers: List[str] = Field(default_factory=list)   # T+
    negative_boundaries: List[str] = Field(default_factory=list) # T-
    discriminative_body: DiscriminativeBody
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class DeploymentIsolationIndexer:
    """Enforces deployment isolation: T+ and B are indexed; T- is strictly excluded."""

    @staticmethod
    def get_indexable_content(page: CapabilityPage) -> str:
        """
        Builds the string to be vectorized/BM25 indexed.
        CRITICAL RULE: Only includes T+ (positive triggers) and B (discriminative body).
        T- (negative boundaries) is physically excluded to prevent vector space contamination.
        """
        body = page.discriminative_body
        parts = [
            f"Skill: {page.skill_name}",
            f"Cluster: {page.cluster_id}",
            f"Summary: {body.summary}",
        ]
        if body.prerequisites:
            parts.append(f"Prerequisites: {', '.join(body.prerequisites)}")
        if page.positive_triggers:
            parts.append("Positive Triggers (T+): " + " | ".join(page.positive_triggers))
        return "\n".join(parts)

    @staticmethod
    def verify_isolation(page: CapabilityPage, indexed_text: str) -> bool:
        """
        Retina verification: Verifies that none of the T- boundaries leaked into indexed_text.
        Returns True if perfectly isolated, False if a leakage was detected.
        """
        for neg in page.negative_boundaries:
            cleaned_neg = neg.strip().lower()
            if cleaned_neg and len(cleaned_neg) > 6 and cleaned_neg in indexed_text.lower():
                return False
        return True


class CapabilityPageStore:
    """Store and registry for Capability Pages."""

    def __init__(self) -> None:
        self._pages: Dict[str, CapabilityPage] = {}

    def upsert_page(self, page: CapabilityPage) -> CapabilityPage:
        page.updated_at = time.time()
        self._pages[page.skill_id] = page
        return page

    def get_page(self, skill_id: str) -> Optional[CapabilityPage]:
        return self._pages.get(skill_id)

    def list_pages(self, cluster_id: Optional[str] = None) -> List[CapabilityPage]:
        if cluster_id:
            return [p for p in self._pages.values() if p.cluster_id == cluster_id]
        return list(self._pages.values())

    def delete_page(self, skill_id: str) -> bool:
        return bool(self._pages.pop(skill_id, None))

    def get_clusters(self) -> List[str]:
        clusters = set(p.cluster_id for p in self._pages.values())
        return sorted(list(clusters))

    def count(self) -> int:
        return len(self._pages)


# Global singleton instance
capability_store = CapabilityPageStore()
