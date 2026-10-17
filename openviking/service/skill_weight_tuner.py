# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill Weight Dynamic Tuner & Ingestion Engine (SSOT).

Implements the dynamic weight tuning and persistence mechanism from Microsoft SkillOpt:
1. Adaptive weight modulation driven by Attempt execution outcomes (PASS / DEGRADED / FAIL)
2. Clamped utility boundaries [0.1, 2.0] with default neutral baseline (1.0)
3. Persistent JSON ledger ingestion with fast in-memory snapshot caching
4. Weighted intent score computation for candidate skill ranking
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

from openviking.service.skill_weight_types import (
    AttemptVerdict,
    SkillWeightProfile,
    WeightTuneResult,
)


MIN_WEIGHT = 0.10
MAX_WEIGHT = 2.00
ALPHA_BOOST = 0.05
BETA_PENALTY = 0.15


class SkillWeightTuner:
    """Thread-safe persistent dynamic skill weight tuning engine."""

    _instance: Optional[SkillWeightTuner] = None
    _lock = threading.RLock()

    def __init__(self, storage_path: Optional[Path | str] = None) -> None:
        self._profiles: Dict[str, SkillWeightProfile] = {}
        if storage_path:
            self._storage_path = Path(storage_path)
        else:
            base_dir = Path(os.environ.get("OPENVIKING_DATA_DIR", Path.home() / ".openviking" / "data"))
            self._storage_path = base_dir / "skill_weights.json"

        self._load_from_disk()

    @classmethod
    def get_instance(cls, storage_path: Optional[Path | str] = None) -> SkillWeightTuner:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(storage_path=storage_path)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _load_from_disk(self) -> None:
        try:
            if self._storage_path and self._storage_path.exists():
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                for slug, pdata in data.items():
                    self._profiles[slug] = SkillWeightProfile(
                        skill_slug=slug,
                        weight=float(pdata.get("weight", 1.0)),
                        total_attempts=int(pdata.get("total_attempts", 0)),
                        passed_attempts=int(pdata.get("passed_attempts", 0)),
                        failed_attempts=int(pdata.get("failed_attempts", 0)),
                        degraded_attempts=int(pdata.get("degraded_attempts", 0)),
                        last_updated=float(pdata.get("last_updated", time.time())),
                        recent_history=list(pdata.get("recent_history", [])),
                        notes=str(pdata.get("notes", "")),
                    )
        except Exception:
            # Fallback to pristine in-memory state on corrupted file
            pass

    def _save_to_disk(self) -> None:
        try:
            if self._storage_path:
                self._storage_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {slug: p.to_dict() for slug, p in self._profiles.items()}
                self._storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def get_profile(self, skill_slug: str) -> SkillWeightProfile:
        with self._lock:
            slug = skill_slug.strip().lower()
            if slug not in self._profiles:
                self._profiles[slug] = SkillWeightProfile(skill_slug=slug)
            return self._profiles[slug]

    def list_profiles(self) -> List[SkillWeightProfile]:
        with self._lock:
            return list(self._profiles.values())

    def tune_weight(
        self,
        skill_slug: str,
        verdict: AttemptVerdict | str,
        confidence: float = 1.0,
        notes: str = "",
    ) -> WeightTuneResult:
        """Modulate skill weight dynamically based on Attempt feedback."""
        with self._lock:
            slug = skill_slug.strip().lower()
            profile = self.get_profile(slug)
            prev_weight = profile.weight

            if isinstance(verdict, str):
                try:
                    verdict_enum = AttemptVerdict(verdict.upper())
                except ValueError:
                    verdict_enum = AttemptVerdict.DEGRADED
            else:
                verdict_enum = verdict

            conf = max(0.0, min(1.0, float(confidence)))
            delta = 0.0

            if verdict_enum == AttemptVerdict.PASS:
                delta = ALPHA_BOOST * conf
                profile.passed_attempts += 1
                msg = f"Attempt PASS: weight boosted by +{delta:.4f}"
            elif verdict_enum == AttemptVerdict.DEGRADED:
                delta = -(BETA_PENALTY * 0.5) * (1.0 - conf * 0.5)
                profile.degraded_attempts += 1
                msg = f"Attempt DEGRADED: weight penalized by {delta:.4f}"
            else:  # FAIL
                delta = -BETA_PENALTY * max(0.5, conf)
                profile.failed_attempts += 1
                msg = f"Attempt FAIL: weight heavily penalized by {delta:.4f}"

            new_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, prev_weight + delta))
            profile.weight = round(new_weight, 4)
            profile.total_attempts += 1
            profile.last_updated = time.time()
            profile.recent_history.append(verdict_enum.value)
            if notes:
                profile.notes = notes

            self._save_to_disk()

            return WeightTuneResult(
                skill_slug=slug,
                previous_weight=prev_weight,
                new_weight=new_weight,
                weight_delta=delta,
                verdict=verdict_enum,
                profile=profile,
                message=msg,
            )

    def calculate_weighted_score(self, raw_score: float, skill_slug: str) -> float:
        """Modulate raw trigger similarity score by dynamic skill weight."""
        with self._lock:
            profile = self.get_profile(skill_slug)
            weighted = raw_score * profile.weight
            return round(min(1.0, max(0.0, weighted)), 4)

    def reset_profile(self, skill_slug: str) -> SkillWeightProfile:
        with self._lock:
            slug = skill_slug.strip().lower()
            self._profiles[slug] = SkillWeightProfile(skill_slug=slug)
            self._save_to_disk()
            return self._profiles[slug]
