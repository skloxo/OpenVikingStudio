"""Card-63 Unit Tests: Skill Live Generator & YAML Static Validation Test Suite.

Verifies:
1. Valid YAML Frontmatter parsing with slug compliance and metadata extraction
2. Mandatory field enforcement (name, description)
3. Ghost tool detection warnings in allowed-tools
4. Error handling for malformed delimiters and broken YAML syntax
5. FastMCP openviking_skill_validate tool invocation
6. Version alignment gate (v1.7.17+)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from openviking.service.skill_validator import SkillValidator, validate_skill_content
from openviking.server.mcp_endpoint import openviking_skill_validate
from openviking._version import __version__


VALID_SKILL_SAMPLE = """---
name: memory-compaction
description: Automated compaction of fragmented session transcripts and context cache.
allowed-tools:
  - openviking_tokenshift_compress
  - find
triggers:
  - 压缩记忆
  - 记忆整理
---
# Memory Compaction SOP
Step 1: Inspect session footprint.
Step 2: Trigger tokenshift compression.
"""

INVALID_NAME_SKILL_SAMPLE = """---
name: Invalid_Skill_Name With Space
description: Valid description for an invalid skill name test.
---
# Content body
"""

MISSING_DESCRIPTION_SAMPLE = """---
name: valid-slug-name
description: ""
---
# Content body
"""

GHOST_TOOL_SAMPLE = """---
name: ghost-tool-explorer
description: Skill attempting to invoke unregistered shadow tools.
allowed-tools:
  - nonexistent_phantom_tool_xyz
  - find
---
# Content body
"""


def test_skill_validator_valid_spec():
    result = validate_skill_content(VALID_SKILL_SAMPLE)
    assert result.is_valid is True
    assert result.name == "memory-compaction"
    assert len(result.errors) == 0
    assert result.body_length > 0
    assert "openviking_tokenshift_compress" in result.parsed_metadata.get("allowed-tools", [])


def test_skill_validator_empty_and_delimiter_errors():
    empty_res = validate_skill_content("")
    assert empty_res.is_valid is False
    assert any("empty" in err.lower() for err in empty_res.errors)

    no_delim_res = validate_skill_content("# Raw markdown without YAML delimiters")
    assert no_delim_res.is_valid is False
    assert any("frontmatter" in err.lower() for err in no_delim_res.errors)


def test_skill_validator_broken_yaml():
    broken_yaml = """---
name: [broken-yaml
description: missing bracket
---
# Body
"""
    result = validate_skill_content(broken_yaml)
    assert result.is_valid is False
    assert any("YAML parsing error" in err for err in result.errors)


def test_skill_validator_slug_and_mandatory_fields():
    # Invalid slug name
    inv_name_res = validate_skill_content(INVALID_NAME_SKILL_SAMPLE)
    assert inv_name_res.is_valid is False
    assert any("kebab-case" in err for err in inv_name_res.errors)

    # Missing description
    missing_desc_res = validate_skill_content(MISSING_DESCRIPTION_SAMPLE)
    assert missing_desc_res.is_valid is False
    assert any("description" in err.lower() for err in missing_desc_res.errors)


def test_skill_validator_ghost_tool_warnings():
    result = validate_skill_content(GHOST_TOOL_SAMPLE)
    # Warnings do not invalidate the skill, but flag diagnostics
    assert result.is_valid is True
    assert any("nonexistent_phantom_tool_xyz" in warn for warn in result.warnings)


@pytest.mark.asyncio
async def test_openviking_skill_validate_mcp_tool():
    raw_json = await openviking_skill_validate(VALID_SKILL_SAMPLE)
    data = json.loads(raw_json)
    assert data["is_valid"] is True
    assert data["name"] == "memory-compaction"
    assert data["errors"] == []


def test_card63_version_alignment():
    pkg_path = Path(__file__).resolve().parents[2] / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    pkg_version = pkg_data["version"]
    assert pkg_version == __version__, f"Version mismatch: {pkg_version} vs {__version__}"

    # SemVer verification: Major=1, Minor=7, Patch >= 17
    parts = [int(p) for p in __version__.split(".")]
    assert (parts[0], parts[1]) == (1, 7), f"Expected 1.7.x, got {__version__}"
    assert parts[2] >= 17, f"Expected patch >= 17, got {parts[2]}"
