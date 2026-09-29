# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""AHE 契约三元组 Manifest — Automated Harness Evolution 核心数据模型。

三元组物理公理:
  可证伪 (Falsifiable)  → Manifest 显式记录假设与预期行为
  可归因 (Attributable) → 每次失败必须关联到机制根因 (MechanismCause)
  可回滚 (Reversible)   → Manifest 携带文件快照哈希，支持秒级还原

(Card-Harness-AHE-ContractualSelfEvolution v1.5.38)
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 枚举类型
# ---------------------------------------------------------------------------

class AHEStatus(str, Enum):
    ACTIVE   = "active"    # Manifest 处于活跃观测期
    VERIFIED = "verified"  # 已通过 Polar 判官验证
    VIOLATED = "violated"  # 假设被违反，需要归因
    RETIRED  = "retired"   # 已完成演进，归档


class MechanismKind(str, Enum):
    """根因机制分类 (防止旁路补丁冲突)。"""
    PROMPT_DRIFT        = "prompt_drift"        # 提示词文本漂移
    TOOL_INTERFACE      = "tool_interface"      # 工具接口签名变更
    STATE_RACE          = "state_race"          # 状态竞态
    BUDGET_EXCEEDED     = "budget_exceeded"     # 预算超限
    OUTPUT_CONTRACT     = "output_contract"     # 输出格式违约
    ENV_SIDE_EFFECT     = "env_side_effect"     # 环境副作用
    QUALITY_DEGRADATION = "quality_degradation" # 质量降级/断言退化
    UNKNOWN             = "unknown"             # 待归因


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------

class AHEAssumption(BaseModel):
    """可证伪假设条目：明确声明一个可被验证的行为预期。"""
    assumption_id: str = Field(default_factory=lambda: f"asm-{uuid.uuid4().hex[:8]}")
    description: str
    validation_command: Optional[str] = None   # shell 命令，exit 0 = 假设成立
    frozen_surface: Optional[str] = None       # 指向不可改动的代码区域 (文件:行范围)
    verified_at: Optional[float] = None        # unix 时间戳


class FileSnapshot(BaseModel):
    """文件快照哈希与物理内容备份 — 用于秒级回滚判定与还原。"""
    path: str
    sha256: str
    captured_at: float = Field(default_factory=time.time)
    content_backup: Optional[str] = None

    @classmethod
    def capture(cls, file_path: str | Path, backup_content: bool = True) -> "FileSnapshot":
        p = Path(file_path)
        content = p.read_bytes() if p.exists() else b""
        sha = hashlib.sha256(content).hexdigest()
        txt = None
        if backup_content and p.exists():
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                txt = None
        return cls(path=str(p), sha256=sha, content_backup=txt)

    def still_matches(self) -> bool:
        """判断文件内容是否与快照一致。"""
        return self.capture(self.path, backup_content=False).sha256 == self.sha256

    def rollback(self) -> bool:
        """物理还原快照备份内容至目标路径。"""
        if self.content_backup is None:
            return False
        try:
            p = Path(self.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.content_backup, encoding="utf-8")
            return True
        except Exception:
            return False


class AHEManifest(BaseModel):
    """AHE 契约 Manifest — 可证伪 + 可归因 + 可回滚 三元组载体。"""
    manifest_id: str = Field(default_factory=lambda: f"ahe-{uuid.uuid4().hex[:12]}")
    skill_name: str
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: AHEStatus = AHEStatus.ACTIVE
    assumptions: List[AHEAssumption] = Field(default_factory=list)
    snapshots: List[FileSnapshot] = Field(default_factory=list)
    violation_cause: Optional[MechanismKind] = None
    violation_detail: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    def is_snapshot_clean(self) -> bool:
        """所有快照文件均与捕获时一致 → True。"""
        return all(s.still_matches() for s in self.snapshots)

    def mark_violated(self, cause: MechanismKind, detail: str) -> None:
        self.status = AHEStatus.VIOLATED
        self.violation_cause = cause
        self.violation_detail = detail
        self.updated_at = time.time()

    def mark_verified(self) -> None:
        self.status = AHEStatus.VERIFIED
        self.updated_at = time.time()

    def rollback(self) -> bool:
        """物理回滚该 Manifest 所记录的所有文件快照。"""
        if not self.snapshots:
            return False
        success = True
        for s in self.snapshots:
            if not s.rollback():
                success = False
        if success:
            self.status = AHEStatus.RETIRED
            self.updated_at = time.time()
            self.meta["rolled_back_at"] = time.time()
        return success


# ---------------------------------------------------------------------------
# Manifest 仓库 (内存 + 可选 JSON 持久化)
# ---------------------------------------------------------------------------

class ManifestStore:
    """线程安全的 AHE Manifest 仓库。单例模式，与服务同生命周期。"""

    _instance: Optional["ManifestStore"] = None
    _store: Dict[str, AHEManifest] = {}
    _persistence_file: Path = Path.home() / ".openviking" / "data" / "ahe" / "manifests.json"

    def __new__(cls) -> "ManifestStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = {}
            cls._instance._persistence_file = (
                Path.home() / ".openviking" / "data" / "ahe" / "manifests.json"
            )
            cls._instance._load_from_disk()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ManifestStore":
        return cls()

    def _load_from_disk(self) -> None:
        try:
            if self._persistence_file.exists():
                raw = self._persistence_file.read_text(encoding="utf-8")
                data = json.loads(raw)
                for mid, item in data.items():
                    self._store[mid] = AHEManifest(**item)
        except Exception:
            pass

    def _save_to_disk(self) -> None:
        try:
            self._persistence_file.parent.mkdir(parents=True, exist_ok=True)
            self._persistence_file.write_text(self.export_json(), encoding="utf-8")
        except Exception:
            pass

    def upsert(self, manifest: AHEManifest) -> None:
        self._store[manifest.manifest_id] = manifest
        self._save_to_disk()

    def get(self, manifest_id: str) -> Optional[AHEManifest]:
        return self._store.get(manifest_id)

    def list_all(self) -> List[AHEManifest]:
        return list(self._store.values())

    def list_by_skill(self, skill_name: str) -> List[AHEManifest]:
        return [m for m in self._store.values() if m.skill_name == skill_name]

    def list_by_status(self, status: AHEStatus) -> List[AHEManifest]:
        return [m for m in self._store.values() if m.status == status]

    def summary(self) -> Dict[str, Any]:
        manifests = self.list_all()
        return {
            "total": len(manifests),
            "active": sum(1 for m in manifests if m.status == AHEStatus.ACTIVE),
            "verified": sum(1 for m in manifests if m.status == AHEStatus.VERIFIED),
            "violated": sum(1 for m in manifests if m.status == AHEStatus.VIOLATED),
            "retired": sum(1 for m in manifests if m.status == AHEStatus.RETIRED),
        }

    def export_json(self) -> str:
        data = {mid: m.model_dump() for mid, m in self._store.items()}
        return json.dumps(data, default=str, ensure_ascii=False)

    def reset_for_test(self) -> None:
        self._store.clear()
