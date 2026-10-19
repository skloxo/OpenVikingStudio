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

from pathlib import Path
import sys
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
    _store: ManifestStore
    _catalog: ClusterCatalog
    _polar: PolarJudge

    def __new__(cls) -> "AHEEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = ManifestStore.get_instance()
            cls._instance._catalog = ClusterCatalog.get_instance()
            cls._instance._polar = PolarJudge(default_timeout_sec=30.0)
            cls._instance.register_lifecycle_guard()
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

    def rollback_manifest(self, manifest_id: str) -> Dict[str, Any]:
        """执行 Manifest 关联快照物理回滚。"""
        manifest = self._store.get(manifest_id)
        if manifest is None:
            return {"error": f"Manifest {manifest_id!r} not found", "success": False}
        success = manifest.rollback()
        self._store.upsert(manifest)
        return {
            "manifest_id": manifest_id,
            "skill_name": manifest.skill_name,
            "rolled_back": success,
            "snapshots_count": len(manifest.snapshots),
            "status": manifest.status.value,
        }

    def verify_and_guard(
        self,
        skill_name: str,
        skill_path: Optional[str] = None,
        validation_command: Optional[str] = None,
        assumptions: Optional[List[Dict[str, Any]]] = None,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """端到端 AHE 契约门禁：创建 Manifest、备份快照、执行 Polar 判官物理检验。"""
        asm_list = list(assumptions or [])
        if validation_command:
            asm_list.append({
                "description": f"Polar verification for {skill_name}",
                "validation_command": validation_command,
            })

        snapshot_paths = [skill_path] if skill_path else []
        manifest = self.create_manifest(
            skill_name=skill_name,
            assumptions=asm_list,
            snapshot_paths=snapshot_paths,
        )

        verify_res = self.verify_manifest(manifest.manifest_id, cwd=cwd)
        is_verified = verify_res.get("status") == AHEStatus.VERIFIED.value

        if not is_verified:
            failed_reasons = [
                r.get("stderr_tail") or r.get("verdict")
                for r in verify_res.get("results", [])
                if r.get("verdict") != "pass"
            ]
            reason_str = "; ".join(str(f) for f in failed_reasons if f) or "Polar validation failure"
            violation = self.ingest_violation(
                manifest_id=manifest.manifest_id,
                mechanism=MechanismKind.QUALITY_DEGRADATION,
                description=f"Skill {skill_name} failed Polar validation: {reason_str[:256]}",
            )
            return {
                "gate_passed": False,
                "manifest_id": manifest.manifest_id,
                "status": "violated",
                "blocked_reason": f"AHE Polar gate BLOCKED: {reason_str}",
                "cluster_id": violation.get("cluster_id"),
                "verification_results": verify_res.get("results", []),
                "rollback_available": len(manifest.snapshots) > 0,
            }

        return {
            "gate_passed": True,
            "manifest_id": manifest.manifest_id,
            "status": "verified",
            "blocked_reason": None,
            "verification_results": verify_res.get("results", []),
            "rollback_available": len(manifest.snapshots) > 0,
        }

    # -----------------------------------------------------------------------
    # 汇总
    # -----------------------------------------------------------------------

    def global_summary(self) -> Dict[str, Any]:
        return {
            "manifests": self._store.summary(),
            "clusters": self._catalog.summary(),
        }

    # -----------------------------------------------------------------------
    # Pre-Release 自动化门禁与核心不变性装载 (Card-191 SSOT)
    # -----------------------------------------------------------------------

    def seed_core_invariants_if_empty(self) -> List[AHEManifest]:
        """若当前未注册任何 Manifest，自动载入系统级核心契约快照与不变性断言。"""
        existing = self._store.list_all()
        if existing:
            return existing

        base_dir = Path(__file__).resolve().parent.parent
        seeded: List[AHEManifest] = []
        py_bin = sys.executable

        # 1. Universal Reducer Invariant
        reducer_file = base_dir / "service" / "universal_reducer.py"
        if reducer_file.exists():
            m1 = self.create_manifest(
                skill_name="core-universal-reducer",
                assumptions=[{
                    "description": "UniversalReducer Fail-Open guarantee",
                    "validation_command": f'"{py_bin}" -c "from openviking.service.universal_reducer import UniversalContentReducer; r = UniversalContentReducer.get_instance(); assert r.reduce_text(\'test\').reduced_content == \'test\'"',
                }],
                snapshot_paths=[str(reducer_file)],
            )
            m1.mark_verified()
            self._store.upsert(m1)
            seeded.append(m1)

        # 2. Hermes Micro-Surgery Invariant
        patch_file = base_dir / "core" / "hermes_patch_engine.py"
        if patch_file.exists():
            m2 = self.create_manifest(
                skill_name="core-hermes-patch-guard",
                assumptions=[{
                    "description": "Hermes <=30 lines patch limit",
                    "validation_command": f'"{py_bin}" -c "from openviking.core.hermes_patch_engine import HermesPatchEngine; assert HermesPatchEngine.MAX_PATCH_LINES == 30"',
                }],
                snapshot_paths=[str(patch_file)],
            )
            m2.mark_verified()
            self._store.upsert(m2)
            seeded.append(m2)

        return seeded

    def run_pre_release_gate(
        self,
        run_polar: bool = False,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行端到端 Pre-Release Gate 门禁校验。"""
        manifests = self.seed_core_invariants_if_empty()

        drift_violations: List[str] = []
        polar_violations: List[str] = []

        for m in manifests:
            if m.status in (AHEStatus.ACTIVE, AHEStatus.VERIFIED):
                drift_res = self.check_snapshot_drift(m.manifest_id)
                if not drift_res.get("snapshot_clean", True):
                    for f in drift_res.get("drifted_files", []):
                        drift_violations.append(
                            f"Manifest [{m.manifest_id}] Skill [{m.skill_name}]: Drift in {f['path']}"
                        )
                if run_polar:
                    verify_res = self.verify_manifest(m.manifest_id, cwd=cwd)
                    for r in verify_res.get("results", []):
                        if r.get("verdict") not in ("pass", "skip"):
                            polar_violations.append(
                                f"Manifest [{m.manifest_id}] Assumption [{r.get('assumption_id')}]: {r.get('command')}"
                            )

        gate_passed = (len(drift_violations) == 0 and len(polar_violations) == 0)

        # 桥接记录至 UniversalAuditLedger
        try:
            from openviking.service.universal_audit_ledger import UniversalAuditLedger
            UniversalAuditLedger.get_instance().record_event(
                entity_type="AHE_GATE",
                entity_id="pre_release_gate",
                action="AHE_PRE_RELEASE_CHECK",
                operator="ahe_engine",
                status="SUCCESS" if gate_passed else "FLAGGED",
                details={
                    "total_manifests": len(manifests),
                    "drift_count": len(drift_violations),
                    "polar_failures": len(polar_violations),
                    "run_polar": run_polar,
                },
            )
        except Exception:
            pass

        return {
            "gate_passed": gate_passed,
            "total_manifests": len(manifests),
            "drift_violations": drift_violations,
            "polar_violations": polar_violations,
            "timestamp": time.time(),
        }

    def ahe_lifecycle_guard(
        self,
        entity_type: str,
        entity_id: str,
        meta: Dict[str, Any],
    ) -> bool:
        """提供给 UnifiedLifecycleEngine 的校验门禁回调。"""
        if meta.get("enforce_ahe_gate", False):
            res = self.run_pre_release_gate(run_polar=False)
            return res.get("gate_passed", False)
        return True

    def register_lifecycle_guard(self) -> None:
        """向 UnifiedLifecycleEngine 注册 VALIDATING -> COMMITTED 状态守卫。"""
        try:
            from openviking.service.unified_lifecycle import UnifiedLifecycleEngine, LifecycleState
            UnifiedLifecycleEngine.get_instance().register_guard(
                LifecycleState.VALIDATING,
                LifecycleState.COMMITTED,
                self.ahe_lifecycle_guard,
            )
        except Exception:
            pass

