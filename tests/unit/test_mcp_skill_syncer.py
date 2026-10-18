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
    from tools.skill_syncer import (
        _corrupted_skill_cache,
        _rejected_skills_cache,
        _synced_skills_cache,
        _ingest_lock,
    )
    if _ingest_lock.locked():
        try:
            _ingest_lock.release()
        except RuntimeError:
            pass
    _corrupted_skill_cache.clear()
    _rejected_skills_cache.clear()
    _synced_skills_cache.clear()

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


def test_auto_ingest_skips_corrupted_skill_via_preflight():
    """验证格式损坏的技能被本地 Pre-flight 静态语法门禁拦截，且绝不发起远程 POST 请求"""
    from tools.skill_syncer import _corrupted_skill_cache

    _corrupted_skill_cache.clear()

    found_skills = {
        "corrupted-skill": {
            "name": "corrupted-skill",
            "description": "损坏的技能",
            "content": "This is totally invalid yaml without frontmatter delimiters",
        },
        "valid-skill": {
            "name": "valid-skill",
            "description": "合规的技能",
            "content": "---\nname: valid-skill\ndescription: \"合规有效\"\n---\n# OK",
        },
    }

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "status": "ok",
        "result": {"skills": []},
    }
    mock_client.post.return_value = {"status": "ok", "result": {"root_uri": "viking://agent/skills/valid-skill"}}

    with patch("tools.skill_syncer.http_client", mock_client):
        _auto_ingest_missing_to_vikingfs(found_skills)

    # 验证损坏的技能被加入缓存，且只对 valid-skill 发起 post
    assert "corrupted-skill" in _corrupted_skill_cache
    assert mock_client.post.call_count == 1
    assert "valid-skill" in mock_client.post.call_args[0][1]["data"]


def test_skill_loader_resilient_frontmatter_parsing():
    """验证 SkillLoader 能够自愈 BOM、换行缺失的闭合 delimiter 及冒号语法"""
    from openviking.core.skill_loader import SkillLoader

    # 1. 带 BOM 和换行粘连的闭合分隔符
    raw_sticky = '\ufeff---\nname: resilient-sticky\ndescription: "粘连测试"\"---\n# Body content'
    parsed = SkillLoader.parse(raw_sticky)
    assert parsed["name"] == "resilient-sticky"
    assert parsed["description"] == "粘连测试"

    # 2. 开头有多余空白行
    raw_blanks = '\n\n---\nname: blank-prefix\ndescription: "前导空行"\n---\n# Content'
    parsed2 = SkillLoader.parse(raw_blanks)
    assert parsed2["name"] == "blank-prefix"

    # 3. 字段内包含三短横线及正文内包含水平分割线（逆向审讯：绝不提前误切断）
    raw_with_dashes = '---\nname: inner-dashes\ndescription: "包含---但不是闭合"\n---\n# Body\n---\nMore body'
    parsed3 = SkillLoader.parse(raw_with_dashes)
    assert parsed3["name"] == "inner-dashes"
    assert parsed3["description"] == "包含---但不是闭合"
    assert "# Body\n---\nMore body" in parsed3["content"]


def test_auto_ingest_skips_scenarios_and_caches_rejections():
    """验证已作为 Scenario/Alias 归入大包的技能被直接跳过，且失败技能被哈希缓存抑制重发"""
    from tools.skill_syncer import _rejected_skills_cache, _synced_skills_cache

    _rejected_skills_cache.clear()
    _synced_skills_cache.clear()

    found_skills = {
        "openviking-master": {
            "name": "openviking-master",
            "description": "已被大包合并的场景技能",
            "content": "---\nname: openviking-master\ndescription: \"已合并场景\"\n---\n# Master",
        },
        "rejected-skill": {
            "name": "rejected-skill",
            "description": "将被拒收的技能",
            "content": "---\nname: rejected-skill\ndescription: \"拒收测试\"\n---\n# Rejected",
        },
    }

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "status": "ok",
        "result": {
            "skills": [
                {
                    "name": "openviking",
                    "scenarios": ["openviking-master", "openviking-ops"],
                    "aliases": ["ov-master"],
                }
            ]
        },
    }
    # 第一次 rejected-skill 返回门禁拦截
    mock_client.post.return_value = {"status": "error", "message": "SkillOpt rejected"}

    with patch("tools.skill_syncer.http_client", mock_client):
        # 第一次执行：openviking-master 作为 scenario 被直接跳过，只尝试提交 rejected-skill
        _auto_ingest_missing_to_vikingfs(found_skills)
        assert mock_client.post.call_count == 1
        assert "openviking-master" in _synced_skills_cache
        assert "rejected-skill" in _rejected_skills_cache

        # 第二次执行：rejected-skill 内容哈希未变，直接被缓存阻断，call_count 依然保持 1
        _auto_ingest_missing_to_vikingfs(found_skills)
        assert mock_client.post.call_count == 1


def test_auto_ingest_scenario_md_and_hyphen_normalization_dedup():
    """验证包含 .md 后缀的场景名以及下划线/连字符归一化技能被 100% 识别并跳过"""
    from tools.skill_syncer import _synced_skills_cache

    _synced_skills_cache.clear()

    found_skills = {
        "mac_production_deploy": {
            "name": "mac_production_deploy",
            "description": "下划线命名的本地技能",
            "content": "---\nname: mac_production_deploy\ndescription: \"下划线技能\"\n---\n# Content",
        },
        "auto-pr": {
            "name": "auto-pr",
            "description": "已被大包收录的工序",
            "content": "---\nname: auto-pr\ndescription: \"已收录工序\"\n---\n# Content",
        },
        "path-skill": {
            "name": "path-skill",
            "description": "服务端返回带路径的场景",
            "content": "---\nname: path-skill\ndescription: \"带路径场景\"\n---\n# Content",
        },
    }

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "status": "ok",
        "result": {
            "skills": [
                {
                    "name": "park-grid-governance",
                    "scenarios": ["mac-production-deploy.md"],
                },
                {
                    "name": "codebase-engineering",
                    "scenarios": [{"name": "auto-pr.md"}],
                },
                {
                    "name": "developer-productivity",
                    "scenarios": ["scenarios/deep/path-skill.md"],
                },
            ]
        },
    }

    with patch("tools.skill_syncer.http_client", mock_client):
        _auto_ingest_missing_to_vikingfs(found_skills)
        # 三项均命中场景去重，绝不发起远程 POST 请求
        assert mock_client.post.call_count == 0
        assert "mac_production_deploy" in _synced_skills_cache
        assert "auto-pr" in _synced_skills_cache
        assert "path-skill" in _synced_skills_cache


