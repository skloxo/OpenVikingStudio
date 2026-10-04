"""Card-65 Unit Tests: Skill Vectorization & Vault Ingestion Cockpit.

Verifies:
1. Pre-flight validation gatekeeper blocking invalid skills
2. URI normalization and SHA256 content fingerprinting
3. Local mirror physical persistence and overwrite handling
4. FastMCP openviking_skill_publish tool invocation
5. Version alignment gate (v1.7.19+)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from openviking.service.skill_publisher import SkillPublisher
from openviking.server.mcp_endpoint import openviking_skill_publish
from openviking._version import __version__


VALID_SKILL_DRAFT = """---
name: vault-indexing
description: Automated vectorization and vault indexing pipeline for multi-agent skills.
allowed-tools:
  - find
  - openviking_history_search
triggers:
  - 索引入库
  - 技能上架
---
# Vault Indexing SOP
1. Calculate sha256 checksum.
2. Ingest into Viking master memory.
"""

INVALID_SKILL_DRAFT = """---
name: Invalid Slug!
description: ""
---
Broken skill content
"""


def test_skill_publisher_valid_publish():
    result = SkillPublisher.publish_skill(VALID_SKILL_DRAFT)
    assert result.success is True
    assert result.slug == "vault-indexing"
    assert result.target_uri == "viking://resources/master_memory/skills/vault-indexing/SKILL.md"
    assert len(result.version_hash) == 12
    assert result.metadata.get("name") == "vault-indexing"
    assert result.metadata.get("version_hash") == result.version_hash
    assert any("Content length:" in d for d in result.diagnostics)


def test_skill_publisher_preflight_gatekeeper_rejection():
    result = SkillPublisher.publish_skill(INVALID_SKILL_DRAFT)
    assert result.success is False
    assert "Pre-flight validation failed" in result.error
    assert result.target_uri == ""


def test_skill_publisher_physical_mirror(tmp_path: Path):
    mirror_dir = tmp_path / "skills_mirror"
    result = SkillPublisher.publish_skill(
        VALID_SKILL_DRAFT,
        force_overwrite=True,
        local_mirror_dir=mirror_dir,
    )
    assert result.success is True
    persisted_file = mirror_dir / "vault-indexing" / "SKILL.md"
    assert persisted_file.exists()
    assert persisted_file.read_text(encoding="utf-8") == VALID_SKILL_DRAFT


@pytest.mark.asyncio
async def test_openviking_skill_publish_mcp_tool():
    raw_json = await openviking_skill_publish(VALID_SKILL_DRAFT)
    data = json.loads(raw_json)
    assert data["success"] is True
    assert data["slug"] == "vault-indexing"
    assert data["target_uri"].startswith("viking://")


def test_card65_version_alignment():
    pkg_path = Path(__file__).resolve().parents[2] / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    pkg_version = pkg_data["version"]
    assert pkg_version == __version__, f"Version mismatch: {pkg_version} vs {__version__}"

    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7), f"Expected 1.7.x, got {__version__}"
    assert parts[2] >= 19, f"Expected patch >= 19, got {parts[2]}"
