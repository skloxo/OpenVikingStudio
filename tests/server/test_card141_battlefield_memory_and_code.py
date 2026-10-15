# -*- coding: utf-8 -*-
"""Card-141 TDD 自动化测试视网膜: 核心记忆与代码战地完全体整并重构

契约目标:
1. openviking-memory 战地工具池精准收敛为 34 项战地工具 (零代码短板, 零特权污染);
2. 完整覆盖 6 大战地维度:
   - 长程记忆与检索 (8 项)
   - 工作区与深度代码 AST (11 项)
   - 技能中心感知与发布 (6 项, 锚定 1214 全域技能)
   - 工单自主建卡与哨兵 (4 项, 异常自主建卡吹哨)
   - 超大文档代客泊车 (2 项, 50MB+ 异步批处理防 504)
   - 安全脱敏与传感器 (3 项)
3. 3 项核心 Hook 物理守卫闭环 (ov_pre_invocation, ov_lesson_crystallizer, ov_sandbox_guard);
4. 与已解耦的 cpa-squad (2 项) 和 fleet-mesh (2 项) 保持严格正交, 零冗余交叉;
5. 别名反查与 REST API 响应完全体契约对齐。
"""

import pytest
from fastapi.testclient import TestClient

from openviking.service.plugin_registry import PluginRegistry, BATTLEFIELD_34_TOOL_NAMES
from openviking.server.app import create_app


@pytest.fixture(autouse=True)
def reset_plugin_registry():
    """每次测试前重置单例状态。"""
    PluginRegistry.reset_instance()
    yield
    PluginRegistry.reset_instance()


def test_card141_battlefield_34_tools_completeness():
    """测试 1: 验证 BATTLEFIELD_34_TOOL_NAMES 契约常量的完整性与领域正交性。"""
    assert len(BATTLEFIELD_34_TOOL_NAMES) == 34, f"期望 34 项战地工具，实际包含 {len(BATTLEFIELD_34_TOOL_NAMES)} 项"

    # 1. 记忆中枢 (8 项)
    expected_memory = {
        "find", "search", "read", "write", "store", "link", "get_relations", "unlink"
    }
    # 2. 代码与工作区 AST (11 项)
    expected_code = {
        "ls", "tree", "grep", "glob", "code_outline", "code_search",
        "code_expand", "diff", "smart_read", "tokenshift_compress", "tag"
    }
    # 3. 技能中心感知与发布 (6 项)
    expected_skills = {
        "skills", "audit_skills", "auto_onboard_skills",
        "get_onboard_queue_status", "fix_skill", "record_evolution_lesson"
    }
    # 4. 工单自主建卡与哨兵 (4 项)
    expected_cards = {
        "file_task_card", "list_pending_cards", "resolve_task_card", "task_cards_summary"
    }
    # 5. 大文档泊车 (2 项)
    expected_valet = {
        "valet_handover", "valet_ticket_status"
    }
    # 6. 安全脱敏与传感器 (3 项)
    expected_sensors = {
        "privacy", "ping", "harness_stats"
    }

    all_expected = expected_memory | expected_code | expected_skills | expected_cards | expected_valet | expected_sensors
    assert len(all_expected) == 34, f"期望 34 种工具，实际合并为 {len(all_expected)}"

    # 校验每个基础工具名在 BATTLEFIELD_34_TOOL_NAMES 中都有对应的条目
    for tool_name in all_expected:
        has_match = any(
            t == tool_name or t == f"openviking_{tool_name}"
            for t in BATTLEFIELD_34_TOOL_NAMES
        )
        assert has_match, f"缺失预期的战地工具: {tool_name}"


def test_card141_memory_plugin_structure_and_hooks():
    """测试 2: 验证 openviking-memory 插件实体的战地工具数量、3 项 Hook 与专属技能。"""
    registry = PluginRegistry.get_instance()
    plugin = registry.get_plugin("openviking-memory")
    assert plugin is not None
    assert plugin.plugin_id == "openviking-memory"

    # 工具数必须收敛为 34 项战地工具
    assert len(plugin.tools) == 34, f"期望 openviking-memory 具备 34 项工具，实际拥有 {len(plugin.tools)} 项"

    # 3 项 Hook 物理守卫
    hook_ids = {h.hook_id for h in plugin.hooks}
    assert "ov_pre_invocation" in hook_ids
    assert "ov_lesson_crystallizer" in hook_ids
    assert "ov_sandbox_guard" in hook_ids

    # 专属技能契约
    assert plugin.skill is not None
    assert plugin.skill.skill_id == "openviking-memory"

    # 探针描述
    assert "34 tools" in plugin.health.message.lower() or "34" in plugin.health.message


def test_card141_rest_api_endpoint_battlefield_parity():
    """测试 3: 验证 REST API 端点 /api/v1/plugins/openviking-memory 真实返回 34 项战地工具。"""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/v1/plugins/openviking-memory")
    assert resp.status_code == 200
    data = resp.json()

    assert data["plugin_id"] == "openviking-memory"
    assert len(data["tools"]) == 34
    assert len(data["hooks"]) == 3
    assert data["skill"]["skill_id"] == "openviking-memory"
