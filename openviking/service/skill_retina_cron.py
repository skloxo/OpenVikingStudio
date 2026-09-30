# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Skill retina audit and self-healing cron engine.

Ensures the Physical Identity Equation:
    Count_FS == Count_API
By auditing skill directory roots, detecting anomalies, and auto-scaffolding
missing or damaged SKILL.md files.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from openviking.service.skill_sanitizer import SkillSanitizer
from openviking_cli.exceptions import NotFoundError

logger = logging.getLogger(__name__)


@dataclass
class SkillAnomaly:
    """Description of an anomaly in the skills storage directory."""

    uri: str
    name: str
    anomaly_type: str
    detail: str


@dataclass
class SkillRetinaReport:
    """Audit and healing report for a skill root."""

    timestamp: float
    root_uri: str
    fs_count: int
    api_count: int
    is_identical: bool
    healthy_count: int
    anomalies_count: int
    healed_count: int
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    healed: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillRetinaAuditor:
    """Audits and heals skill roots to guarantee physical identity."""

    @classmethod
    async def audit_skills(
        cls,
        service: Any,
        ctx: Any,
        root_uri: str,
    ) -> SkillRetinaReport:
        """Audit physical filesystem vs API entries for a skill root."""
        start_time = time.time()
        try:
            fs_entries = await service.fs.ls(
                root_uri,
                ctx=ctx,
                output="agent",
                abs_limit=1024,
                node_limit=1000,
            )
        except NotFoundError:
            fs_entries = []

        # Filter out non-directories and internal hidden folders
        fs_dirs = [
            e for e in fs_entries
            if isinstance(e, dict) and e.get("isDir", False)
        ]

        anomalies: List[SkillAnomaly] = []
        healthy_skills: List[str] = []

        for dir_entry in fs_dirs:
            uri = dir_entry.get("uri", "")
            name = dir_entry.get("name", "")

            # Check if internal anomaly or backup
            if SkillSanitizer.is_anomalous_dir_name(name):
                anomalies.append(
                    SkillAnomaly(
                        uri=uri,
                        name=name,
                        anomaly_type="internal_or_backup_anomaly",
                        detail="Directory starts with dot/archive or has .bak/.tmp suffix",
                    )
                )
                continue

            # Check for SKILL.md existence
            skill_md_uri = f"{uri.rstrip('/')}/SKILL.md"
            has_skill_md = False
            skill_md_content = ""
            try:
                stat = await service.fs.stat(skill_md_uri, ctx=ctx)
                if stat and not stat.get("isDir", False):
                    has_skill_md = True
                    # Read content to check metadata
                    try:
                        read_res = await service.fs.read_file(skill_md_uri, ctx=ctx)
                        if isinstance(read_res, bytes):
                            skill_md_content = read_res.decode("utf-8", errors="replace")
                        elif isinstance(read_res, str):
                            skill_md_content = read_res
                    except Exception:
                        pass
            except Exception:
                has_skill_md = False

            if not has_skill_md:
                anomalies.append(
                    SkillAnomaly(
                        uri=uri,
                        name=name,
                        anomaly_type="missing_skill_md",
                        detail="Skill directory is missing SKILL.md file",
                    )
                )
                continue

            # Check YAML frontmatter validity
            check_res = SkillSanitizer.verify_and_repair_skill_file(name, skill_md_content)
            if check_res.repaired:
                anomalies.append(
                    SkillAnomaly(
                        uri=uri,
                        name=name,
                        anomaly_type="invalid_skill_md_meta",
                        detail=check_res.reason,
                    )
                )
            else:
                healthy_skills.append(name)

        # Count of legitimate business skill directories
        legitimate_dirs = [
            d for d in fs_dirs
            if not SkillSanitizer.is_anomalous_dir_name(d.get("name", ""))
        ]
        fs_count = len(legitimate_dirs)
        api_count = len(healthy_skills)
        is_identical = (fs_count == api_count and len(anomalies) == 0)

        return SkillRetinaReport(
            timestamp=start_time,
            root_uri=root_uri,
            fs_count=fs_count,
            api_count=api_count,
            is_identical=is_identical,
            healthy_count=len(healthy_skills),
            anomalies_count=len(anomalies),
            healed_count=0,
            anomalies=[asdict(a) for a in anomalies],
            healed=[],
        )

    @classmethod
    async def heal_skills(
        cls,
        service: Any,
        ctx: Any,
        root_uri: str,
    ) -> SkillRetinaReport:
        """Self-heal anomalies by scaffolding missing SKILL.md or repairing YAML."""
        audit_res = await cls.audit_skills(service, ctx, root_uri)
        healed: List[Dict[str, Any]] = []

        for anomaly in audit_res.anomalies:
            anomaly_type = anomaly.get("anomaly_type")
            uri = anomaly.get("uri", "")
            name = anomaly.get("name", "")

            # Only heal fixable skill directory anomalies (not backup archives)
            if anomaly_type in ("missing_skill_md", "invalid_skill_md_meta"):
                skill_md_uri = f"{uri.rstrip('/')}/SKILL.md"
                existing_content = ""
                try:
                    read_res = await service.fs.read_file(skill_md_uri, ctx=ctx)
                    if isinstance(read_res, bytes):
                        existing_content = read_res.decode("utf-8", errors="replace")
                    elif isinstance(read_res, str):
                        existing_content = read_res
                except Exception:
                    pass

                repair_result = SkillSanitizer.verify_and_repair_skill_file(
                    skill_dir_name=name,
                    skill_md_content=existing_content,
                )

                if repair_result.repaired and repair_result.skill_md_content:
                    try:
                        content_bytes = repair_result.skill_md_content.encode("utf-8")
                        await service.fs.write_file(skill_md_uri, content_bytes, ctx=ctx)
                        healed.append({
                            "uri": uri,
                            "name": name,
                            "action": "repaired_and_scaffolded_skill_md",
                            "reason": repair_result.reason,
                        })
                    except Exception as err:
                        logger.warning("Failed to heal skill %s: %s", uri, err)

        # Re-audit after healing
        final_audit = await cls.audit_skills(service, ctx, root_uri)
        final_audit.healed_count = len(healed)
        final_audit.healed = healed

        return final_audit
