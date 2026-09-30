# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for SkillSanitizer and SkillRetinaAuditor."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from openviking.service.skill_retina_cron import SkillRetinaAuditor
from openviking.service.skill_sanitizer import SkillSanitizer
from openviking.utils.skill_processor import validate_skill_name


def test_sanitize_skill_name_basic():
    """Verify normal conversion to lowercase kebab-case."""
    assert SkillSanitizer.sanitize_skill_name("My Super Skill") == "my-super-skill"
    assert SkillSanitizer.sanitize_skill_name("CamelCaseName") == "camelcasename"
    assert SkillSanitizer.sanitize_skill_name("snake_case_skill") == "snake-case-skill"
    assert SkillSanitizer.sanitize_skill_name("mix__with--dashes") == "mix-with-dashes"
    assert SkillSanitizer.sanitize_skill_name("skill.v1.0") == "skill-v1-0"


def test_sanitize_skill_name_unicode_and_empty():
    """Verify non-ascii strings or special characters are safely handled."""
    # Transliteration or fallback
    res = SkillSanitizer.sanitize_skill_name("Café De Paris")
    assert "cafe" in res
    assert validate_skill_name(res) == res

    # Pure Chinese or emoji fallback to default prefix
    chinese_res = SkillSanitizer.sanitize_skill_name("技能测试")
    assert chinese_res.startswith("skill-")
    assert validate_skill_name(chinese_res) == chinese_res

    # Empty string
    empty_res = SkillSanitizer.sanitize_skill_name("")
    assert empty_res.startswith("skill-")
    assert validate_skill_name(empty_res) == empty_res


def test_sanitize_skill_name_truncation():
    """Verify names longer than 64 characters are cleanly truncated."""
    long_name = "a" * 80 + "-extra-long-name"
    sanitized = SkillSanitizer.sanitize_skill_name(long_name)
    assert len(sanitized) <= 64
    assert not sanitized.endswith("-")
    assert validate_skill_name(sanitized) == sanitized


def test_is_anomalous_dir_name():
    """Verify anomalous backup/temporary directory detection."""
    # Anomalous
    assert SkillSanitizer.is_anomalous_dir_name(".git") is True
    assert SkillSanitizer.is_anomalous_dir_name(".clawhub") is True
    assert SkillSanitizer.is_anomalous_dir_name("__pycache__") is True
    assert SkillSanitizer.is_anomalous_dir_name("temp_skill.bak") is True
    assert SkillSanitizer.is_anomalous_dir_name("temp_skill.tmp") is True
    assert SkillSanitizer.is_anomalous_dir_name("backup-2026-03") is True
    assert SkillSanitizer.is_anomalous_dir_name("curator-temp-dir") is True
    assert SkillSanitizer.is_anomalous_dir_name("2026-09-30-backup") is True

    # Legitimate business skills
    assert SkillSanitizer.is_anomalous_dir_name("curator-agent") is False
    assert SkillSanitizer.is_anomalous_dir_name("market-scanner") is False
    assert SkillSanitizer.is_anomalous_dir_name("tdd-assistant") is False


def test_verify_and_repair_skill_file():
    """Verify checking and auto-scaffolding SKILL.md contents."""
    # 1. Empty or missing content -> scaffolds new SKILL.md
    res_empty = SkillSanitizer.verify_and_repair_skill_file("my-test-skill", "")
    assert res_empty.repaired is True
    assert "name: my-test-skill" in res_empty.skill_md_content
    assert "description:" in res_empty.skill_md_content

    # 2. Existing valid SKILL.md -> no repair needed
    valid_content = "---\nname: my-test-skill\ndescription: Test description\n---\n# My Test Skill\n"
    res_valid = SkillSanitizer.verify_and_repair_skill_file("my-test-skill", valid_content)
    assert res_valid.is_valid is True
    assert res_valid.repaired is False

    # 3. Malformed YAML frontmatter -> repaired while preserving markdown body
    broken_content = "---\nname: [unclosed list\n---\n# Header\nBody content"
    res_broken = SkillSanitizer.verify_and_repair_skill_file("my-test-skill", broken_content)
    assert res_broken.repaired is True
    assert "name: my-test-skill" in res_broken.skill_md_content
    assert "Body content" in res_broken.skill_md_content


@pytest.mark.asyncio
async def test_skill_retina_auditor_audit_and_heal():
    """Verify retina auditor detects anomalies and heals them to guarantee identity."""
    service = MagicMock()
    ctx = MagicMock()

    # Setup mock file system: 1 healthy skill, 1 skill with missing SKILL.md, 1 backup anomaly
    mock_entries = [
        {"uri": "viking://agent/skills/healthy-skill", "name": "healthy-skill", "isDir": True},
        {"uri": "viking://agent/skills/broken-skill", "name": "broken-skill", "isDir": True},
        {"uri": "viking://agent/skills/curator-temp", "name": "curator-temp", "isDir": True},
    ]

    service.fs.ls = AsyncMock(return_value=mock_entries)

    # In-memory file storage mock
    fs_files = {
        "viking://agent/skills/healthy-skill/SKILL.md": (
            b"---\nname: healthy-skill\ndescription: Healthy skill\n---\n# Healthy"
        )
    }

    async def mock_stat(uri, ctx=None):
        if uri in fs_files:
            return {"uri": uri, "isDir": False}
        return None

    async def mock_read_file(uri, ctx=None):
        if uri in fs_files:
            return fs_files[uri]
        raise FileNotFoundError(f"{uri} not found")

    async def mock_write_file(uri, content, ctx=None):
        fs_files[uri] = content
        return {"status": "ok"}

    service.fs.stat = AsyncMock(side_effect=mock_stat)
    service.fs.read_file = AsyncMock(side_effect=mock_read_file)
    service.fs.write_file = AsyncMock(side_effect=mock_write_file)

    # Step 1: Audit detects discrepancy
    report = await SkillRetinaAuditor.audit_skills(service, ctx, "viking://agent/skills")
    assert report.fs_count == 2  # healthy-skill and broken-skill (curator-temp is skipped)
    assert report.api_count == 1  # only healthy-skill
    assert report.is_identical is False
    assert len(report.anomalies) == 2  # curator-temp (anomaly) + broken-skill (missing_skill_md)

    # Step 2: Heal self-repairs missing SKILL.md
    healed_report = await SkillRetinaAuditor.heal_skills(service, ctx, "viking://agent/skills")
    assert healed_report.healed_count == 1
    assert "viking://agent/skills/broken-skill/SKILL.md" in fs_files

    # Step 3: Now both business skills are healthy and identical
    assert healed_report.fs_count == 2
    assert healed_report.api_count == 2
    assert healed_report.healthy_count == 2
