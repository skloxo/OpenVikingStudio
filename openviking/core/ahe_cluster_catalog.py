# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""AHE 根因机制聚类目录 (Root-Cause Cluster Catalog)。

核心价值：
  防范旁路补丁冲突 (No Nested Layering):
    - 每次 Harness 失败必须关联到一个「机制根因」
    - 聚类相同根因的失败，识别系统性漏洞
    - 「冻结面排除」: 已有补丁覆盖的根因绝不重复打补丁

(Card-Harness-AHE-ContractualSelfEvolution v1.5.38)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openviking.core.ahe_manifest import MechanismKind


# ---------------------------------------------------------------------------
# 聚类条目
# ---------------------------------------------------------------------------

@dataclass
class ClusterEntry:
    """单条根因聚类记录。"""
    cluster_id: str = field(default_factory=lambda: f"cls-{uuid.uuid4().hex[:8]}")
    mechanism: MechanismKind = MechanismKind.UNKNOWN
    description: str = ""
    # 相关的 manifest_id 列表
    manifest_ids: List[str] = field(default_factory=list)
    # 是否已有补丁覆盖 — 冻结面：不再接受相同机制的新补丁
    patched: bool = False
    patch_commit: Optional[str] = None
    first_seen_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    occurrence_count: int = 1

    def add_occurrence(self, manifest_id: str) -> None:
        if manifest_id not in self.manifest_ids:
            self.manifest_ids.append(manifest_id)
        self.occurrence_count += 1
        self.last_seen_at = time.time()

    def mark_patched(self, commit: str) -> None:
        self.patched = True
        self.patch_commit = commit


# ---------------------------------------------------------------------------
# 聚类目录（单例）
# ---------------------------------------------------------------------------

class ClusterCatalog:
    """根因机制聚类目录，全服务单例，内存持久。

    主要功能:
      - ingest(mechanism, manifest_id)  → 归入对应聚类（或新建）
      - find_patch_conflict(mechanism)  → 若已有补丁覆盖，返回告警
      - get_top_clusters(n)             → 返回发生频率最高的 n 个聚类
    """

    _instance: Optional["ClusterCatalog"] = None

    def __new__(cls) -> "ClusterCatalog":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._clusters: Dict[str, ClusterEntry] = {}
            # MechanismKind → cluster_id 映射（简单按机制类型聚合）
            cls._instance._mech_index: Dict[MechanismKind, str] = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ClusterCatalog":
        return cls()

    def ingest(
        self,
        mechanism: MechanismKind,
        manifest_id: str,
        description: str = "",
    ) -> ClusterEntry:
        """将失败归入对应聚类，返回聚类条目。"""
        if mechanism in self._mech_index:
            cls_id = self._mech_index[mechanism]
            entry = self._clusters[cls_id]
            entry.add_occurrence(manifest_id)
        else:
            entry = ClusterEntry(
                mechanism=mechanism,
                description=description or mechanism.value,
                manifest_ids=[manifest_id],
            )
            self._clusters[entry.cluster_id] = entry
            self._mech_index[mechanism] = entry.cluster_id

        return entry

    def find_patch_conflict(self, mechanism: MechanismKind) -> Optional[ClusterEntry]:
        """若该机制已有补丁覆盖（冻结面），返回条目作为冲突告警。"""
        cls_id = self._mech_index.get(mechanism)
        if cls_id is None:
            return None
        entry = self._clusters[cls_id]
        return entry if entry.patched else None

    def mark_patched(self, mechanism: MechanismKind, commit: str) -> bool:
        cls_id = self._mech_index.get(mechanism)
        if cls_id is None:
            return False
        self._clusters[cls_id].mark_patched(commit)
        return True

    def get_all(self) -> List[ClusterEntry]:
        return sorted(
            self._clusters.values(),
            key=lambda c: c.occurrence_count,
            reverse=True,
        )

    def get_top(self, n: int = 5) -> List[ClusterEntry]:
        return self.get_all()[:n]

    def summary(self) -> Dict:
        clusters = self.get_all()
        return {
            "total_clusters": len(clusters),
            "patched_clusters": sum(1 for c in clusters if c.patched),
            "unpatched_clusters": sum(1 for c in clusters if not c.patched),
            "top_mechanism": clusters[0].mechanism.value if clusters else None,
            "total_occurrences": sum(c.occurrence_count for c in clusters),
        }

    def reset_for_test(self) -> None:
        """测试专用：重置状态。"""
        self._clusters.clear()
        self._mech_index.clear()
