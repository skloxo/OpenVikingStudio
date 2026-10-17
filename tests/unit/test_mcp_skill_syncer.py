# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for MCP Skill Syncer & Auto Ingestion Guard (tools.skill_syncer).
验证技能自动同步、脱敏、元数据提取及向 VikingFS 自动补齐收录逻辑。
"""

from unittest.mock import MagicMock, patch
import pytest

import sys
from pathlib import Path

# 将 mcp-openviking 根目录注入模块搜索路径
mcp_root = str(Path(__file__).resolve().parents[2] / "mcp-openviking")
if mcp_root not in sys.path:
    sys.path.insert(0, mcp_root)

from tools.skill_syncer import (
    _desensitize_text,
    _extract_frontmatter_metadata,
    _auto_ingest_missing_to_vikingfs,
)


def test_desensitize_text_masks_sensitive_patterns(monkeypatch):
    dummy_secret = "SecretMockToken9988"
    dummy_key = "s" + "k-" + "testdummykeyforunit1234567890"
    monkeypatch.setenv("OV_TEST_SECRET_PATTERN", dummy_secret)
    raw = f"Bearer {dummy_key} and {dummy_secret}"
    masked = _desensitize_text(raw)
    assert dummy_secret not in masked
    assert dummy_key not in masked
    assert "[REDACTED_API_KEY]" in masked
    assert "[REDACTED_PASSWORD]" in masked


def test_extract_frontmatter_metadata():
    fm_content = """---
name: test-skill
description: "测试技能"
tags:
  - testing
  - engineering
allowed-tools:
  - openviking_find
  - openviking_search
---

# Test Skill Body
"""
    tags, tools = _extract_frontmatter_metadata(fm_content)
    assert tags == ["testing", "engineering"]
    assert tools == ["openviking_find", "openviking_search"]


def test_extract_frontmatter_empty_or_non_yaml():
    tags, tools = _extract_frontmatter_metadata("# Just markdown without frontmatter")
    assert tags == []
    assert tools == []


def test_auto_ingest_missing_to_vikingfs():
    found_skills = {
        "existing-skill": {
            "name": "existing-skill",
            "description": "已存在技能",
            "content": "---\nname: existing-skill\n---",
        },
        "new-skill": {
            "name": "new-skill",
            "description": "待入库新技能",
            "content": "---\nname: new-skill\ndescription: \"待入库新技能\"\n---\n# New Skill",
        },
        ".hidden-skill": {
            "name": ".hidden-skill",
            "description": "隐藏技能应跳过",
            "content": "---\nname: .hidden-skill\n---",
        },
        "no-desc-skill": {
            "name": "no-desc-skill",
            "description": "暂无简介",
            "content": "# No desc",
        },
    }

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "status": "ok",
        "result": {
            "skills": [
                {"name": "existing-skill", "uri": "viking://agent/skills/existing-skill"}
            ]
        },
    }
    mock_client.post.return_value = {"status": "ok", "result": {"root_uri": "viking://agent/skills/new-skill"}}

    with patch("tools.skill_syncer.http_client", mock_client):
        _auto_ingest_missing_to_vikingfs(found_skills)

    # 验证只对 new-skill 发起了 post 调用
    assert mock_client.post.call_count == 1
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/api/v1/skills"
    payload = call_args[0][1]
    assert payload["target_uri"] == "viking://agent/skills"
    assert "new-skill" in payload["data"]
