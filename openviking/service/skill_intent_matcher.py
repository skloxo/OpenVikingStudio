"""Skill Trigger Intent Matching & Simulation Sandbox Engine (SSOT).

Provides zero-dependency, high-precision intent matching and collision detection
for SKILL.md trigger phrases against natural language queries:
1. Multi-level tokenization & character n-gram Jaccard similarity
2. Substring containment boosting for domain keywords
3. Intent routing collision detection between multiple skills
4. Strongly-typed SkillIntentMatchResult & SkillCollisionReport
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


def _normalize_text(text: str) -> str:
    """Normalize text by lowercasing and stripping non-alphanumeric punctuation."""
    cleaned = re.sub(r"[\s\-_,.:;!?~`'\"/\\|()\[\]{}<>]+", " ", text.lower())
    return cleaned.strip()


def _get_ngrams(text: str, n: int = 2) -> set[str]:
    """Extract character n-grams for robust cross-language fuzzy matching."""
    norm = _normalize_text(text).replace(" ", "")
    if len(norm) < n:
        return {norm} if norm else set()
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def _calculate_similarity(query: str, trigger: str) -> float:
    """Calculate blended intent similarity score [0.0, 1.0] between query and trigger."""
    q_norm = _normalize_text(query)
    t_norm = _normalize_text(trigger)

    if not q_norm or not t_norm:
        return 0.0

    # 1. Exact match
    if q_norm == t_norm:
        return 1.0

    # 2. Substring containment boost
    if t_norm in q_norm:
        # Trigger is fully contained in query
        coverage = len(t_norm) / len(q_norm)
        return min(1.0, 0.85 + 0.15 * coverage)
    if q_norm in t_norm:
        coverage = len(q_norm) / len(t_norm)
        return min(0.95, 0.75 + 0.20 * coverage)

    # 3. Bigram & Trigram Jaccard similarity
    bi_q = _get_ngrams(q_norm, 2)
    bi_t = _get_ngrams(t_norm, 2)
    tri_q = _get_ngrams(q_norm, 3)
    tri_t = _get_ngrams(t_norm, 3)

    jaccard_bi = len(bi_q & bi_t) / len(bi_q | bi_t) if (bi_q | bi_t) else 0.0
    jaccard_tri = len(tri_q & tri_t) / len(tri_q | tri_t) if (tri_q | tri_t) else 0.0

    blended_jaccard = 0.6 * jaccard_bi + 0.4 * jaccard_tri
    return round(blended_jaccard, 4)


@dataclass
class SkillIntentMatchResult:
    """Diagnostic report for trigger matching simulation."""

    matched: bool
    query: str
    best_trigger: str
    score: float
    threshold: float
    matched_triggers: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "query": self.query,
            "best_trigger": self.best_trigger,
            "score": round(self.score, 4),
            "threshold": self.threshold,
            "matched_triggers": self.matched_triggers,
            "reason": self.reason,
        }


@dataclass
class SkillCollisionReport:
    """Report for trigger collision analysis across registered skills."""

    has_collision: bool
    collisions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_collision": self.has_collision,
            "collisions": self.collisions,
        }


class SkillIntentMatcher:
    """Zero-side-effect intent simulation and conflict resolver."""

    @classmethod
    def match_intent(
        cls,
        query: str,
        triggers: list[str],
        threshold: float = 0.60,
    ) -> SkillIntentMatchResult:
        """Simulate trigger matching against a candidate natural language query."""
        if not query or not query.strip() or not triggers:
            return SkillIntentMatchResult(
                matched=False,
                query=query or "",
                best_trigger="",
                score=0.0,
                threshold=threshold,
                reason="Query or triggers list is empty.",
            )

        scored_triggers: list[dict[str, Any]] = []
        for trig in triggers:
            trig_str = trig.strip()
            if not trig_str:
                continue
            sim = _calculate_similarity(query, trig_str)
            scored_triggers.append({"trigger": trig_str, "score": sim})

        if not scored_triggers:
            return SkillIntentMatchResult(
                matched=False,
                query=query,
                best_trigger="",
                score=0.0,
                threshold=threshold,
                reason="No valid trigger candidates to evaluate.",
            )

        scored_triggers.sort(key=lambda item: item["score"], reverse=True)
        best = scored_triggers[0]
        matched = best["score"] >= threshold

        reason = (
            f"Score {best['score']} >= threshold {threshold} on trigger '{best['trigger']}'"
            if matched
            else f"Best score {best['score']} < threshold {threshold} on trigger '{best['trigger']}'"
        )

        return SkillIntentMatchResult(
            matched=matched,
            query=query,
            best_trigger=best["trigger"],
            score=best["score"],
            threshold=threshold,
            matched_triggers=scored_triggers,
            reason=reason,
        )

    @classmethod
    def detect_collisions(
        cls,
        candidate_triggers: list[str],
        existing_skills: dict[str, list[str]],
        threshold: float = 0.80,
    ) -> SkillCollisionReport:
        """Detect intent routing conflicts between candidate triggers and registered skills."""
        collisions: list[dict[str, Any]] = []

        for skill_name, skill_triggers in existing_skills.items():
            overlapping: list[dict[str, Any]] = []
            max_sim = 0.0

            for c_trig in candidate_triggers:
                c_str = c_trig.strip()
                if not c_str:
                    continue
                for e_trig in skill_triggers:
                    e_str = e_trig.strip()
                    if not e_str:
                        continue
                    sim = _calculate_similarity(c_str, e_str)
                    if sim >= threshold:
                        overlapping.append({
                            "candidate_trigger": c_str,
                            "existing_trigger": e_str,
                            "similarity": sim,
                        })
                        if sim > max_sim:
                            max_sim = sim

            if overlapping:
                collisions.append({
                    "conflicting_skill": skill_name,
                    "max_similarity": round(max_sim, 4),
                    "overlapping_triggers": overlapping,
                })

        return SkillCollisionReport(
            has_collision=len(collisions) > 0,
            collisions=collisions,
        )
