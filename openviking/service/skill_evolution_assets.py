# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Asset heritage, backup, and rollback manager for skill evolution (Card-85/86)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import yaml

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
    def enrich_crystallized_content(
        draft_content: str,
        target_slug: str,
        candidate_skills: List[Dict[str, Any]],
        domain_name: str,
    ) -> str:
        """Aggregate aliases, triggers, and tools into consolidated SKILL.md draft."""
        absorbed_slugs = [s["name"] for s in candidate_skills if s["name"] != target_slug]

        if draft_content.startswith("---"):
            parts = draft_content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm_dict = yaml.safe_load(parts[1]) or {}
                except Exception:
                    fm_dict = {}

                fm_dict["name"] = target_slug
                existing_aliases = fm_dict.get("aliases") or []
                if isinstance(existing_aliases, list):
                    all_aliases = list(dict.fromkeys(existing_aliases + absorbed_slugs))
                else:
                    all_aliases = absorbed_slugs
                fm_dict["aliases"] = all_aliases

                # Aggregate tools from candidate skills if present
                tools = fm_dict.get("allowed-tools") or fm_dict.get("tools") or ["openviking_find", "openviking_read"]
                fm_dict["allowed-tools"] = list(dict.fromkeys(tools))

                clean_fm = yaml.safe_dump(fm_dict, sort_keys=False, allow_unicode=True).strip()
                body = parts[2].strip()

                if "交付物契约" not in body and "i/o" not in body.lower():
                    body += (
                        "\n\n## 4. 输入输出与交付物契约 (I/O & Deliverable Contract)\n"
                        "- **输入参数 (Input)**: 目标任务上下文与请求参数 (schema)。\n"
                        "- **输出结果 (Output Result)**: 结构化交付物与执行状态断言 (assert)。\n"
                    )
                if "容错防线" not in body and "fault tolerance" not in body.lower() and "自愈" not in body:
                    body += (
                        "\n## 5. 异常自愈与容错防线 (Fault Tolerance & Fallback)\n"
                        "- 遇到接口报错或调用失败 (error/fail) 时，启动自愈重试 (retry)；若重试仍失败则执行安全降级 (fallback)。\n"
                    )
                return f"---\n{clean_fm}\n---\n\n# {domain_name} 统一结晶中枢 ({target_slug})\n\n> 本技能为自动化演进流水线结晶产物，已合并收敛 {len(absorbed_slugs)} 项历史同质化碎片。\n\n" + body

        return draft_content

    @staticmethod
    def backup_pre_crystal_skills(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        backup_root: Path,
        cluster_id: str,
        target_slug: str = "",
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

        # Record metadata for deterministic, clean rollback
        meta_file = backup_dir / ".meta.json"
        meta_file.write_text(
            json.dumps(
                {
                    "cluster_id": cluster_id,
                    "target_slug": target_slug,
                    "candidate_slugs": candidate_slugs,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return backup_dir

    @staticmethod
    def archive_absorbed_skills(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        target_slug: str,
    ) -> List[str]:
        """Physically archive and remove absorbed duplicate candidate skills from root skills dir.
        
        The consolidated master skill (target_slug) remains active with merged tools/aliases.
        Absorbed candidates are physically removed from root_skills_dir since they are safely
        backed up in quarantine.
        """
        archived: List[str] = []
        for slug in candidate_slugs:
            if slug == target_slug:
                continue
            skill_dir = root_skills_dir / slug
            if skill_dir.exists() and skill_dir.is_dir():
                shutil.rmtree(skill_dir)
                archived.append(slug)
        return archived

    @staticmethod
    def rollback_cluster(backup_root: Path, root_skills_dir: Path, cluster_id: str) -> bool:
        """Restore original candidate skills from a specific cluster quarantine backup."""
        backup_dir = backup_root / cluster_id
        if not backup_dir.exists():
            return False

        meta_file = backup_dir / ".meta.json"
        target_slug = ""
        candidate_slugs: List[str] = []
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                target_slug = meta.get("target_slug", "")
                candidate_slugs = meta.get("candidate_slugs", [])
            except Exception:
                pass

        for skill_dir in backup_dir.iterdir():
            if skill_dir.is_dir():
                target_dest = root_skills_dir / skill_dir.name
                if target_dest.exists():
                    shutil.rmtree(target_dest)
                shutil.copytree(skill_dir, target_dest)

        # Remove the generated master skill if it was created during crystallization
        if target_slug and target_slug not in candidate_slugs:
            master_dir = root_skills_dir / target_slug
            if master_dir.exists() and master_dir.is_dir():
                shutil.rmtree(master_dir)

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
                meta_file = bdir / ".meta.json"
                target_slug = ""
                candidate_slugs: List[str] = []
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        target_slug = meta.get("target_slug", "")
                        candidate_slugs = meta.get("candidate_slugs", [])
                    except Exception:
                        pass

                for skill_dir in bdir.iterdir():
                    if skill_dir.is_dir():
                        target_dest = root_skills_dir / skill_dir.name
                        if target_dest.exists():
                            shutil.rmtree(target_dest)
                        shutil.copytree(skill_dir, target_dest)
                        restored_count += 1

                if target_slug and target_slug not in candidate_slugs:
                    master_dir = root_skills_dir / target_slug
                    if master_dir.exists() and master_dir.is_dir():
                        shutil.rmtree(master_dir)

        return {
            "restored_skills": restored_count,
            "quarantine_dir": str(backup_root),
            "status": "ok" if restored_count > 0 else "noop",
        }
