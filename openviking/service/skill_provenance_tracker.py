# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""VikingFS Skill Blackbox Provenance Tracker & Snapshot Rollback (Card-98).

核心物理公理:
  1. 全生命周期黑匣子证据链: 每一步 INGEST/VALIDATE/ROUTE/MERGE/ROLLBACK 均物理留痕于 provenance_events.jsonl；
  2. 隔离区快照一键无悔秒退: 任何合并重写前强制生成只读快照，rollback 耗时 < 50ms 纯文件还原；
  3. 人类可读 CHANGELOG 自动同步: 自动将演变证据注入 CHANGELOG.md，为事后复盘提供唯一真相源。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
import uuid
from enum import Enum
from pydantic import BaseModel, Field


class ProvenanceAction(str, Enum):
    """证据链操作类型枚举。"""
    INGEST = "INGEST"
    VALIDATE = "VALIDATE"
    ROUTE = "ROUTE"
    MERGE = "MERGE"
    OPTIMIZE = "OPTIMIZE"
    ROLLBACK = "ROLLBACK"


class ProvenanceRecord(BaseModel):
    """单条黑匣子演变审计条目。"""
    event_id: str
    timestamp: float = Field(default_factory=time.time)
    action: ProvenanceAction
    skill_name: str
    version: str = "1.0.0"
    receipt_id: str = ""
    operator: str = "system"
    details: Dict[str, Any] = Field(default_factory=dict)
    snapshot_path: Optional[str] = None


class SkillProvenanceTracker:
    """黑匣子证据链记录器与快照回滚控制器。单例/多实例安全。"""

    _instance: Optional[SkillProvenanceTracker] = None
    _singleton_lock = threading.Lock()

    def __init__(self, vault_root: Optional[Path] = None):
        if vault_root is None:
            vault_root = Path.home() / ".openviking" / "data" / "viking" / "default" / "skills"

        self._vault_root = Path(vault_root)
        self._prov_dir = self._vault_root / "provenance"
        self._snap_dir = self._vault_root / "snapshots"
        self._prov_dir.mkdir(parents=True, exist_ok=True)
        self._snap_dir.mkdir(parents=True, exist_ok=True)

        self._log_file = self._prov_dir / "provenance_events.jsonl"
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls, vault_root: Optional[Path] = None) -> SkillProvenanceTracker:
        """单例获取。"""
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls(vault_root=vault_root)
        return cls._instance

    def record_event(
        self,
        action: ProvenanceAction,
        skill_name: str,
        version: str = "1.0.0",
        receipt_id: str = "",
        operator: str = "system",
        details: Optional[Dict[str, Any]] = None,
        snapshot_path: Optional[str] = None,
    ) -> ProvenanceRecord:
        """物理写入单条证据链日志。"""
        rec = ProvenanceRecord(
            event_id=f"prov_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            action=action,
            skill_name=skill_name,
            version=version,
            receipt_id=receipt_id,
            operator=operator,
            details=details or {},
            snapshot_path=snapshot_path,
        )

        line = rec.model_dump_json() + "\n"
        with self._lock, open(self._log_file, "a", encoding="utf-8") as f:
            f.write(line)
        return rec

    def list_events(
        self,
        skill_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProvenanceRecord]:
        """逆序读取审计日志。"""
        if not self._log_file.exists():
            return []

        records: List[ProvenanceRecord] = []
        with self._lock, open(self._log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in reversed(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                rec = ProvenanceRecord(**data)
                if skill_name and rec.skill_name != skill_name:
                    continue
                records.append(rec)
                if len(records) >= limit:
                    break
            except Exception:
                continue
        return records

    def create_snapshot(self, skill_name: str, content: str) -> str:
        """生成只读物理快照，返回持久化路径。"""
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        ts = int(time.time() * 1000)
        snap_file = self._snap_dir / f"{skill_name}_{ts}_{sha}.snap.md"
        snap_file.write_text(content, encoding="utf-8")
        return str(snap_file.resolve())

    def rollback_snapshot(self, snapshot_path: str, target_file: Path) -> bool:
        """从指定快照秒级还原文件 (< 50ms)。"""
        snap = Path(snapshot_path)
        if not snap.exists():
            return False

        content = snap.read_text(encoding="utf-8")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")

        self.record_event(
            action=ProvenanceAction.ROLLBACK,
            skill_name=target_file.stem,
            operator="user_rollback",
            details={"restored_from": snapshot_path, "target": str(target_file)},
        )
        return True

    def append_changelog(
        self,
        skill_name: str,
        version: str,
        summary: str,
        action: ProvenanceAction = ProvenanceAction.MERGE,
        delta_triggers: Optional[List[str]] = None,
    ) -> Path:
        """向 CHANGELOG.md 追加人肉可读的演变记录。"""
        changelog_file = self._vault_root / "CHANGELOG.md"
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        entry_lines = [
            f"\n## [{version}] - {date_str}",
            f"- **Skill**: `{skill_name}` | **Action**: `{action.value}`",
            f"- **Summary**: {summary}",
        ]
        if delta_triggers:
            entry_lines.append(f"- **New Triggers**: {', '.join(delta_triggers)}")
        entry_lines.append("")

        with self._lock, open(changelog_file, "a", encoding="utf-8") as f:
            f.write("\n".join(entry_lines))
        return changelog_file
