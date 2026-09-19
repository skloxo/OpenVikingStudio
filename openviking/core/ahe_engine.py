# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""AHE 调度引擎 — 整合 Manifest / ClusterCatalog / PolarJudge 三大子系统。

AHEEngine 提供统一入口:
  - create_manifest()     → 创建并注册新契约 Manifest
  - verify_manifest()     → 调用 Polar 判官逐一验证假设
  - ingest_violation()    → 失败后归因聚类 + Patch 冲突检测
  - report_snapshot_drift → 检测文件快照漂移（可回滚判定）

(Card-Harness-AHE-ContractualSelfEvolution v1.5.38)
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from openviking.core.ahe_cluster_catalog import ClusterCatalog, ClusterEntry
from openviking.core.ahe_manifest import (
    AHEAssumption,
    AHEManifest,
    AHEStatus,
    FileSnapshot,
    ManifestStore,
    MechanismKind,
)
from openviking.core.polar_judge import PolarJudge, PolarProbeResult, PolarVerdict


# ---------------------------------------------------------------------------
# 引擎入口
# ---------------------------------------------------------------------------

class AHEEngine:
    """AHE 契约三元组调度引擎。全服务单例。"""

    _instance: Optional["AHEEngine"] = None

    def __new__(cls) -> "AHEEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = ManifestStore.get_instance()
            cls._instance._catalog = ClusterCatalog.get_instance()
            cls._instance._polar = PolarJudge(default_timeout_sec=30.0)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AHEEngine":
        return cls()

    # -----------------------------------------------------------------------
    # Manifest 管理
    # -----------------------------------------------------------------------

    def create_manifest(
        self,
        skill_name: str,
        assumptions: Optional[List[Dict[str, Any]]] = None,
        snapshot_paths: Optional[List[str]] = None,
    ) -> AHEManifest:
        """创建并注册 AHE 契约 Manifest。"""
        asm_list: List[AHEAssumption] = []
        for a in (assumptions or []):
            asm_list.append(AHEAssumption(**a))

        snaps: List[FileSnapshot] = []
        for p in (snapshot_paths or []):
            snaps.append(FileSnapshot.capture(p))

        manifest = AHEManifest(
            skill_name=skill_name,
            assumptions=asm_list,
            snapshots=snaps,
        )
        self._store.upsert(manifest)
        return manifest

    def get_manifest(self, manifest_id: str) -> Optional[AHEManifest]:
        return self._store.get(manifest_id)

    def list_manifests(
        self,
        skill_name: Optional[str] = None,
        status: Optional[AHEStatus] = None,
    ) -> List[AHEManifest]:
        if skill_name:
            return self._store.list_by_skill(skill_name)
        if status:
            return self._store.list_by_status(status)
        return self._store.list_all()

    # -----------------------------------------------------------------------
    # Polar 验证
    # -----------------------------------------------------------------------

    def verify_manifest(
        self,
        manifest_id: str,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """对 Manifest 中所有假设调用 Polar 判官验证。

        Returns
        -------
        dict 包含:
          manifest_id, skill_name, status, results (每条假设探测结果)
        """
        manifest = self._store.get(manifest_id)
        if manifest is None:
            return {"error": f"Manifest {manifest_id!r} not found"}

        results: List[Dict[str, Any]] = []
        all_passed = True

        for asm in manifest.assumptions:
            if not asm.validation_command:
                results.append({
                    "assumption_id": asm.assumption_id,
                    "description": asm.description,
                    "verdict": "skip",
                    "reason": "No validation_command defined",
                })
                continue

            probe: PolarProbeResult = self._polar.probe_assumption(
                asm.validation_command, cwd=cwd
            )
            passed = probe.verdict == PolarVerdict.PASS
            if passed:
                asm.verified_at = time.time()
            else:
                all_passed = False

            results.append({
                "assumption_id": asm.assumption_id,
                "description": asm.description,
                "command": asm.validation_command,
                "verdict": probe.verdict.value,
                "exit_code": probe.exit_code,
                "duration_ms": probe.duration_ms,
                "stderr_tail": probe.stderr_tail[-500:] if probe.stderr_tail else "",
            })

        if all_passed:
            manifest.mark_verified()
        else:
            manifest.mark_violated(
                MechanismKind.UNKNOWN,
                "Polar verification failed on one or more assumptions",
            )

        self._store.upsert(manifest)

        return {
            "manifest_id": manifest_id,
            "skill_name": manifest.skill_name,
            "status": manifest.status.value,
            "results": results,
        }

    # -----------------------------------------------------------------------
    # 根因归因与冲突检测
    # -----------------------------------------------------------------------

    def ingest_violation(
        self,
        manifest_id: str,
        mechanism: MechanismKind,
        description: str = "",
    ) -> Dict[str, Any]:
        """将失败归因聚类，检测冻结面补丁冲突。"""
        entry: ClusterEntry = self._catalog.ingest(mechanism, manifest_id, description)
        conflict = self._catalog.find_patch_conflict(mechanism)

        manifest = self._store.get(manifest_id)
        if manifest:
            manifest.mark_violated(mechanism, description)
            self._store.upsert(manifest)

        return {
            "cluster_id": entry.cluster_id,
            "mechanism": mechanism.value,
            "occurrence_count": entry.occurrence_count,
            "patch_conflict_detected": conflict is not None,
            "patch_commit": conflict.patch_commit if conflict else None,
        }

    # -----------------------------------------------------------------------
    # 快照漂移检测
    # -----------------------------------------------------------------------

    def check_snapshot_drift(self, manifest_id: str) -> Dict[str, Any]:
        """检查 Manifest 文件快照是否漂移（可回滚判定依据）。"""
        manifest = self._store.get(manifest_id)
        if manifest is None:
            return {"error": f"Manifest {manifest_id!r} not found"}

        drifted = [
            {"path": s.path, "sha256": s.sha256}
            for s in manifest.snapshots
            if not s.still_matches()
        ]
        clean = len(drifted) == 0

        return {
            "manifest_id": manifest_id,
            "snapshot_clean": clean,
            "drifted_files": drifted,
            "total_snapshots": len(manifest.snapshots),
        }

    # -----------------------------------------------------------------------
    # 汇总
    # -----------------------------------------------------------------------

    def global_summary(self) -> Dict[str, Any]:
        return {
            "manifests": self._store.summary(),
            "clusters": self._catalog.summary(),
        }
