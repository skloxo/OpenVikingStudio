# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Asset heritage, backup, and rollback manager for skill evolution (Card-85/86)."""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Canonical clustering definitions for known high-density domains
CANONICAL_DOMAINS: List[Dict[str, Any]] = [
    {
        "id": "feishu-suite",
        "domain": "Feishu / Lark 飞书生态",
        "target": "feishu-hub",
        "keywords": ["feishu", "lark", "bitable"],
    },
    {
        "id": "tide-quant",
        "domain": "Financial & Trading 股票/量化/交易",
        "target": "tide-quant-hub",
        "keywords": ["stock", "trading", "akshare", "alpha", "crypto", "kline", "market"],
    },
    {
        "id": "git-forge",
        "domain": "Git & GitHub 版本管理与协作",
        "target": "git-forge",
        "keywords": ["github", "gitlab", "git-workflow", "git-pr"],
    },
    {
        "id": "devops-ops",
        "domain": "DevOps & Infrastructure 运维/容器/部署",
        "target": "devops-ops",
        "keywords": ["docker", "k8s", "kubernetes", "container", "deploy", "server-monitor"],
    },
    {
        "id": "web-automation",
        "domain": "Web & Browser 自动化与爬虫",
        "target": "web-automation",
        "keywords": ["browser", "playwright", "puppeteer", "scrapling", "selenium", "crawl"],
    },
]


class SkillAssetHeritageManager:
    """Manages file inheritance, quarantine snapshots, and rollbacks for skills."""

    @staticmethod
    def inherit_subfiles(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        target_dir: Path,
        dry_run: bool = False,
    ) -> List[str]:
        """Migrate auxiliary scripts and assets from absorbed skills into crystallized directory."""
        inherited: List[str] = []
        for slug in candidate_slugs:
            src_dir = root_skills_dir / slug
            if not src_dir.exists():
                continue
            for item in src_dir.rglob("*"):
                if item.is_file() and item.name != "SKILL.md" and not item.name.startswith("."):
                    rel = item.relative_to(src_dir)
                    inherited.append(f"{slug}/{rel}")
                    if not dry_run:
                        dest_file = target_dir / rel
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
        return inherited

    @staticmethod
    def backup_pre_crystal_skills(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        backup_root: Path,
        cluster_id: str,
    ) -> Path:
        """Create an atomic snapshot of candidate skills in quarantine before consolidation."""
        backup_dir = backup_root / cluster_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        for slug in candidate_slugs:
            src = root_skills_dir / slug
            if src.exists():
                dest = backup_dir / slug
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
        return backup_dir

    @staticmethod
    def rollback_cluster(backup_root: Path, root_skills_dir: Path, cluster_id: str) -> bool:
        """Restore original candidate skills from a specific cluster quarantine backup."""
        backup_dir = backup_root / cluster_id
        if not backup_dir.exists():
            return False

        for skill_dir in backup_dir.iterdir():
            if skill_dir.is_dir():
                target_dest = root_skills_dir / skill_dir.name
                if target_dest.exists():
                    shutil.rmtree(target_dest)
                shutil.copytree(skill_dir, target_dest)
        return True

    @staticmethod
    def rollback_crystallization(
        backup_root: Path,
        root_skills_dir: Path,
        quarantine_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore original candidate skills from all or specific quarantine backup snapshots."""
        if not backup_root.exists():
            return {"restored_skills": 0, "quarantine_dir": str(backup_root), "status": "noop"}

        restored_count = 0
        target_dirs = (
            [backup_root / quarantine_timestamp]
            if quarantine_timestamp and (backup_root / quarantine_timestamp).exists()
            else [d for d in backup_root.iterdir() if d.is_dir()]
        )

        for bdir in target_dirs:
            if bdir.is_dir():
                for skill_dir in bdir.iterdir():
                    if skill_dir.is_dir():
                        target_dest = root_skills_dir / skill_dir.name
                        if target_dest.exists():
                            shutil.rmtree(target_dest)
                        shutil.copytree(skill_dir, target_dest)
                        restored_count += 1

        return {
            "restored_skills": restored_count,
            "quarantine_dir": str(backup_root),
            "status": "ok" if restored_count > 0 else "noop",
        }
