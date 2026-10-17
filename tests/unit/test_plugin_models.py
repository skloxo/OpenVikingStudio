# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Plugin Quad-Model Strongly-Typed DTOs.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-01
"""

import pytest
from pydantic import ValidationError

from openviking.models.plugin import (
    GuiSchemaDefinition,
    HookDefinition,
    PluginHealthProbe,
    QuadPluginDefinition,
    SkillDefinition,
    ToolDefinition,
)


def test_tool_definition_contract():
    """验证 ToolDefinition 字段与默认值契约。"""
    tool = ToolDefinition(
        name="openviking_find",
        description="记忆语义检索工具",
        category="core",
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        is_dangerous=False,
    )
    assert tool.name == "openviking_find"
    assert tool.category == "core"
    assert tool.is_dangerous is False
    assert tool.parameters_schema["type"] == "object"


def test_hook_definition_contract():
    """验证 HookDefinition 字段与默认值契约。"""
    hook = HookDefinition(
        hook_id="ov_pre_invocation",
        name="记忆前置自动召回预取",
        trigger_event="before_prompt_submit",
        description="提问前静默召回上下文并注入 Prompt 顶部",
    )
    assert hook.hook_id == "ov_pre_invocation"
    assert hook.enabled is True
    assert hook.trigger_event == "before_prompt_submit"


def test_skill_definition_contract():
    """验证 SkillDefinition 字段契约。"""
    skill = SkillDefinition(
        skill_id="openviking-memory-ops",
        name="体外大脑记忆操作认知导轨",
        description="约束 Agent 记忆操作序列，杜绝重复盲搜",
        sop_summary="outline -> grep -> read -> commit",
        rules=["严禁开局盲搜", "写前必须先快照"],
    )
    assert skill.skill_id == "openviking-memory-ops"
    assert len(skill.rules) == 2


def test_quad_plugin_definition_full_roundtrip():
    """验证 QuadPluginDefinition 完整装配与 JSON 序列化反序列化。"""
    plugin = QuadPluginDefinition(
        plugin_id="openviking-memory",
        name="OpenViking 记忆体外大脑",
        version="1.0.0",
        category="platform",
        description="长程记忆与先验知识中枢",
        skill=SkillDefinition(
            skill_id="openviking-memory-ops",
            name="记忆操作认知导轨",
            description="操作指南",
            sop_summary="查库第一",
        ),
        hooks=[
            HookDefinition(
                hook_id="ov_pre_invocation",
                name="预取Hook",
                trigger_event="pre_invoke",
                description="自动预热",
            )
        ],
        tools=[
            ToolDefinition(name="openviking_find", description="检索记忆"),
            ToolDefinition(name="openviking_read", description="深读正文"),
        ],
        gui=GuiSchemaDefinition(
            settings_fields={"apiUrl": {"type": "string", "default": "http://127.0.0.1:1933"}},
            dashboard_route="/plugins",
        ),
        health=PluginHealthProbe(status="healthy", latency_ms=1.2, message="OK"),
    )

    # 序列化为 JSON 字符串
    json_data = plugin.model_dump_json()
    assert "openviking-memory" in json_data
    assert "openviking_find" in json_data

    # 反序列化还原
    restored = QuadPluginDefinition.model_validate_json(json_data)
    assert restored.plugin_id == plugin.plugin_id
    assert len(restored.tools) == 2
    assert restored.health.status == "healthy"
    assert restored.health.latency_ms == 1.2


def test_quad_plugin_validation_fail_fast():
    """验证必填字段缺失时 Fail-Fast 报错。"""
    with pytest.raises(ValidationError):
        # 缺少 skill 必须字段
        QuadPluginDefinition(
            plugin_id="broken-plugin",
            name="残缺插件",
            description="缺少 Skill 应该报错",
        )
