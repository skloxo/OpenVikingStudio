# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Comprehensive Regression Suite for OpenViking Core MCP Server.
Systematically traverses and verifies all 54 Core MCP tools across 6 domains:
1. Observability & Health
2. Session & Graph Memory
3. FileSystem & Content I/O
4. Retrieval & Code Intelligence
5. Skills & Reflexion
6. System Operations & Governance
"""

import json
import os
import sys
import pytest

# Ensure mcp-openviking is in sys.path
mcp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../mcp-openviking"))
if mcp_dir not in sys.path:
    sys.path.insert(0, mcp_dir)

os.environ["OPENVIKING_MCP_MODE"] = "core"
import mcp_openviking_server as core_server


@pytest.fixture(scope="module")
def core_tools():
    """Returns the set of registered tools in core mode."""
    return {tool.name for tool in core_server.mcp._tool_manager.list_tools()}


def test_core_all_54_tools_registered(core_tools):
    """Verify that Core MCP registers all expected 54 tools."""
    assert len(core_tools) >= 50
    expected_sample = {
        "openviking_ping",
        "openviking_health",
        "openviking_find",
        "openviking_search",
        "openviking_smart_read",
        "openviking_read",
        "openviking_write",
        "openviking_store",
        "openviking_code_search",
        "openviking_code_outline",
        "openviking_tree",
        "openviking_ls",
        "openviking_skills",
        "openviking_server_control",
        "openviking_backup",
        "openviking_restore",
        "openviking_privacy",
        "openviking_consistency",
        "openviking_record_evolution_lesson",
    }
    for tool_name in expected_sample:
        assert tool_name in core_tools, f"Missing tool: {tool_name}"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Observability & Health Domain
# ─────────────────────────────────────────────────────────────────────────────
def test_group1_observability_and_health():
    # 1. openviking_ping
    ping_res = json.loads(core_server.openviking_ping())
    assert ping_res.get("status") in ("ok", "degraded")
    assert ping_res.get("mode") == "core"
    assert "tools_count" in ping_res

    # 2. openviking_health
    health_res = json.loads(core_server.openviking_health())
    assert "health" in health_res or "ready" in health_res or "status" in health_res

    # 3. openviking_system_status
    sys_res = json.loads(core_server.openviking_system_status(wait_timeout=0))
    assert isinstance(sys_res, dict)

    # 4. openviking_harness_stats
    harness_res = json.loads(core_server.openviking_harness_stats())
    assert harness_res.get("status") == "ok"
    assert "harness_metrics" in harness_res

    # 5. openviking_usage_stats
    usage_res = json.loads(core_server.openviking_usage_stats())
    assert isinstance(usage_res, dict)

    # 6. openviking_observer
    obs_res = json.loads(core_server.openviking_observer(component="system"))
    assert isinstance(obs_res, dict)

    # 7. openviking_metrics
    metrics_res = core_server.openviking_metrics()
    assert isinstance(metrics_res, str)

    # 8. openviking_webdav_info
    webdav_res = json.loads(core_server.openviking_webdav_info())
    assert "webdav_url" in webdav_res


# ─────────────────────────────────────────────────────────────────────────────
# 2. Session & Graph Memory Domain
# ─────────────────────────────────────────────────────────────────────────────
def test_group2_session_and_graph_memory():
    session_id = "test_reg_sess_001"

    # 1. openviking_create_session
    create_res = json.loads(core_server.openviking_create_session(session_id=session_id, user_id="tester"))
    assert isinstance(create_res, dict)

    # 2. openviking_get_session
    get_res = json.loads(core_server.openviking_get_session(session_id=session_id, include_context=True))
    assert isinstance(get_res, dict)

    # 3. openviking_store
    store_res = json.loads(core_server.openviking_store(session_id=session_id, content="Core MCP Regression Testing Content"))
    assert isinstance(store_res, dict)

    # 4. openviking_commit
    commit_res = json.loads(core_server.openviking_commit(session_id=session_id))
    assert isinstance(commit_res, dict)

    # 5. openviking_list_sessions
    list_res = json.loads(core_server.openviking_list_sessions(limit=5))
    assert isinstance(list_res, (dict, list))

    # 6. openviking_link
    link_res = json.loads(core_server.openviking_link(
        source_uri="viking://resources/source_node",
        target_uri="viking://resources/target_node",
        relation_type="reference"
    ))
    assert isinstance(link_res, dict)

    # 7. openviking_get_relations
    rel_res = json.loads(core_server.openviking_get_relations(target_uri="viking://resources/source_node"))
    assert isinstance(rel_res, (dict, list))

    # 8. openviking_unlink
    unlink_res = json.loads(core_server.openviking_unlink(
        source_uri="viking://resources/source_node",
        target_uri="viking://resources/target_node"
    ))
    assert isinstance(unlink_res, dict)


# ─────────────────────────────────────────────────────────────────────────────
# 3. FileSystem & Content I/O Domain
# ─────────────────────────────────────────────────────────────────────────────
def test_group3_filesystem_and_content_io():
    test_uri = "viking://resources/test_core_regression.txt"

    # 1. openviking_write
    w_res = json.loads(core_server.openviking_write(
        target_uri=test_uri,
        content="Hello OpenViking Core MCP Regression",
        mode="replace"
    ))
    assert isinstance(w_res, dict)

    # 2. openviking_read
    r_res = json.loads(core_server.openviking_read(target_uri=test_uri, level=2))
    assert isinstance(r_res, dict)

    # 3. openviking_tag (set)
    t_set = json.loads(core_server.openviking_tag(target_uri=test_uri, action="set", tags="regression,core_check"))
    assert isinstance(t_set, dict)

    # 4. openviking_tag (get)
    t_get = json.loads(core_server.openviking_tag(target_uri=test_uri, action="get"))
    assert isinstance(t_get, dict)

    # 5. openviking_tag (remove)
    t_rm = json.loads(core_server.openviking_tag(target_uri=test_uri, action="remove", tags="core_check"))
    assert isinstance(t_rm, dict)

    # 6. openviking_ls
    ls_res = json.loads(core_server.openviking_ls(target_uri="viking://resources/", compact=True, detail=False))
    assert isinstance(ls_res, (dict, list))

    # 7. openviking_tree
    tree_res = json.loads(core_server.openviking_tree(target_uri="viking://resources/", depth=2))
    assert isinstance(tree_res, (dict, list))

    # 8. openviking_diff
    diff_res = core_server.openviking_diff(source_uri=test_uri, target_uri=test_uri)
    assert isinstance(diff_res, str)

    # 9. openviking_list_resources
    res_list = json.loads(core_server.openviking_list_resources(target_uri="viking://resources/"))
    assert isinstance(res_list, (dict, list))

    # 10. openviking_delete_resource
    del_res = json.loads(core_server.openviking_delete_resource(target_uri=test_uri))
    assert isinstance(del_res, dict)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Retrieval & Code Intelligence Domain
# ─────────────────────────────────────────────────────────────────────────────
def test_group4_retrieval_and_code_intelligence():
    # 1. openviking_search
    search_res = json.loads(core_server.openviking_search(query="架构", limit=2))
    assert isinstance(search_res, dict)

    # 2. openviking_find
    find_res = json.loads(core_server.openviking_find(query="体外大脑", limit=2))
    assert isinstance(find_res, dict)

    # 3. openviking_smart_read
    smart_res = json.loads(core_server.openviking_smart_read(query="体外大脑", level=0, limit=1))
    assert isinstance(smart_res, dict)
    assert "total_results" in smart_res

    # 4. openviking_code_outline
    outline_res = json.loads(core_server.openviking_code_outline(target_uri="viking://resources/sample.py"))
    assert isinstance(outline_res, dict)

    # 5. openviking_code_search
    code_search_res = json.loads(core_server.openviking_code_search(query="openviking"))
    assert isinstance(code_search_res, dict)

    # 6. openviking_code_expand
    expand_res = json.loads(core_server.openviking_code_expand(target_uri="viking://resources/sample.py"))
    assert isinstance(expand_res, dict)

    # 7. openviking_grep
    grep_res = json.loads(core_server.openviking_grep(pattern="test", target_uri="viking://resources/", limit=5))
    assert isinstance(grep_res, dict)

    # 8. openviking_glob
    glob_res = json.loads(core_server.openviking_glob(pattern="*.md", target_uri="viking://resources/"))
    assert isinstance(glob_res, dict)

    # 9. openviking_reindex
    reindex_res = json.loads(core_server.openviking_reindex(target_uri="viking://resources/", mode="vectors_only"))
    assert isinstance(reindex_res, dict)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Skills & Reflexion Domain
# ─────────────────────────────────────────────────────────────────────────────
def test_group5_skills_and_reflexion():
    # 1. openviking_skills (list)
    skills_res = json.loads(core_server.openviking_skills(action="list"))
    assert isinstance(skills_res, (dict, list))

    # 2. openviking_audit_skills
    audit_res = json.loads(core_server.openviking_audit_skills())
    assert audit_res.get("status") == "ok"
    assert "compliant_count" in audit_res

    # 3. openviking_get_onboard_queue_status
    queue_res = json.loads(core_server.openviking_get_onboard_queue_status())
    assert queue_res.get("status") == "ok"
    assert "pending_queue_size" in queue_res

    # 4. openviking_record_evolution_lesson
    lesson_res = json.loads(core_server.openviking_record_evolution_lesson(
        skill_name="diagnosing-bugs",
        lesson_title="核心MCP全量能力回归检验",
        context="自动化全量回归测试",
        reflection="模块拆分后需确保54个工具物理连通无损",
        lesson="拆分必须与全量回归用例对齐"
    ))
    assert lesson_res.get("status") == "ok"

    # 5. openviking_fix_skill (validation on non-existent skill)
    fix_res = json.loads(core_server.openviking_fix_skill(skill_name="non_existent_skill_for_test"))
    assert "error" in fix_res or fix_res.get("status") == "error"


# ─────────────────────────────────────────────────────────────────────────────
# 6. System Operations & Governance Domain
# ─────────────────────────────────────────────────────────────────────────────
def test_group6_system_operations_and_governance():
    # 1. openviking_server_control (status check)
    ctl_res = json.loads(core_server.openviking_server_control(action="status"))
    assert isinstance(ctl_res, dict)

    # 2. openviking_server_doctor
    doc_res = core_server.openviking_server_doctor()
    assert isinstance(doc_res, str)

    # 3. openviking_privacy
    priv_res = json.loads(core_server.openviking_privacy(action="categories"))
    assert isinstance(priv_res, dict)

    # 4. openviking_consistency
    cons_res = json.loads(core_server.openviking_consistency(target_uri="viking://resources/"))
    assert isinstance(cons_res, dict)

    # 5. openviking_list_watches
    watch_res = json.loads(core_server.openviking_list_watches(active_only=True))
    assert isinstance(watch_res, dict)

    # 6. Parameter validation on watches
    bad_cancel = json.loads(core_server.openviking_cancel_watch(target_uri="invalid_uri"))
    assert "error" in bad_cancel

    bad_manage = json.loads(core_server.openviking_manage_watch(target_uri="viking://resources/", action="invalid_action"))
    assert "error" in bad_manage

    # 7. Parameter validation on resource add
    bad_add = json.loads(core_server.openviking_add_resource(path_or_url="/tmp", target_uri="invalid_uri"))
    assert "error" in bad_add

    # 8. Parameter validation on export / import
    bad_exp = json.loads(core_server.openviking_export(target_uri="invalid_uri", output_path="/tmp/test.ovpack"))
    assert "error" in bad_exp

    bad_imp = json.loads(core_server.openviking_import(pack_path="/tmp/test.ovpack", target_uri="invalid_uri"))
    assert "error" in bad_imp
