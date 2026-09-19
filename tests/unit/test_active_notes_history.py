# -*- coding: utf-8 -*-
"""Unit tests for Card-Context-ActiveNotesAndHistory (Active Notes & History Dual-Repository).

Validates:
1. ActiveNotes creation, partial patching, and monotonic version increments.
2. HistoryMessage append, turn ordering, and lossless fidelity.
3. list_history_windows paging and ordering.
4. search_history keyword/exact symbol retrieval without hallucination.
5. Context budget savings (>80%) vs raw history piling.
6. FastAPI REST endpoints.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_db_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_active_notes_history.db")
        yield db_path


def test_notes_create_and_update(temp_db_path):
    from openviking.service.active_notes_history import (
        ActiveNotesHistoryManager,
        ActiveNotes,
    )

    manager = ActiveNotesHistoryManager(db_path=temp_db_path)
    session_id = "session_test_001"

    notes = manager.get_or_create_notes(session_id)
    assert notes.session_id == session_id
    assert notes.version == 1
    assert notes.active_goal == ""
    assert len(notes.working_constraints) == 0

    updated = manager.update_notes(
        session_id=session_id,
        active_goal="重构检索层双路混检",
        working_constraints=["NO GREEN EVER 🚫", "端口物理收口为 1933", "单文件 100~300 行"],
        current_state="Step 2/4: 编写红灯测试",
        discovered_facts=["SQLite WAL 模式具备原子无锁读特性"],
    )

    assert updated.version == 2
    assert updated.active_goal == "重构检索层双路混检"
    assert len(updated.working_constraints) == 3
    assert updated.current_state == "Step 2/4: 编写红灯测试"
    assert "SQLite WAL 模式具备原子无锁读特性" in updated.discovered_facts

    fetched = manager.get_or_create_notes(session_id)
    assert fetched.version == 2
    assert fetched.active_goal == updated.active_goal


def test_history_append_and_list_windows(temp_db_path):
    from openviking.service.active_notes_history import ActiveNotesHistoryManager

    manager = ActiveNotesHistoryManager(db_path=temp_db_path)
    session_id = "session_test_002"

    m1 = manager.append_history(
        session_id=session_id,
        role="user",
        content="请排查端口 1936 是否还在监听？",
    )
    assert m1.turn_index == 1
    assert m1.role == "user"

    m2 = manager.append_history(
        session_id=session_id,
        role="assistant",
        content="已执行 netstat 检查，端口 1936 已完全物理下线，当前唯一监听端口为 1933。",
    )
    assert m2.turn_index == 2

    m3 = manager.append_history(
        session_id=session_id,
        role="user",
        content="很好，请继续推进下一个任务。",
    )
    assert m3.turn_index == 3

    # Window pagination
    window = manager.list_history_windows(session_id=session_id, offset=0, limit=2)
    assert len(window) == 2
    assert window[0].turn_index == 1
    assert window[1].turn_index == 2

    window_next = manager.list_history_windows(session_id=session_id, offset=2, limit=2)
    assert len(window_next) == 1
    assert window_next[0].turn_index == 3


def test_history_search_exact_path_and_error(temp_db_path):
    from openviking.service.active_notes_history import ActiveNotesHistoryManager

    manager = ActiveNotesHistoryManager(db_path=temp_db_path)
    session_id = "session_test_003"

    manager.append_history(session_id, "user", "开始执行测试")
    manager.append_history(session_id, "assistant", "报错: ERR_CONNECTION_REFUSED_1933 at /opt/openviking/run.py")
    manager.append_history(session_id, "user", "请修复上述连接问题")
    manager.append_history(session_id, "assistant", "已修改配置文件 config.yaml，连接正常")

    # Search for exact error code
    results = manager.search_history(session_id, query="ERR_CONNECTION_REFUSED_1933", top_k=5)
    assert len(results) >= 1
    assert "ERR_CONNECTION_REFUSED_1933" in results[0].content
    assert results[0].turn_index == 2

    # Search for specific file path
    path_results = manager.search_history(session_id, query="run.py", top_k=5)
    assert len(path_results) >= 1
    assert "/opt/openviking/run.py" in path_results[0].content


def test_context_budget_and_savings(temp_db_path):
    from openviking.service.active_notes_history import ActiveNotesHistoryManager

    manager = ActiveNotesHistoryManager(db_path=temp_db_path)
    session_id = "session_test_004"

    # Add active notes
    manager.update_notes(
        session_id=session_id,
        active_goal="高密度上下文与历史分仓测试",
        working_constraints=["切除有损全局压缩", "双轨分仓存储"],
        current_state="执行中",
        discovered_facts=["History 独立分仓零失真"],
    )

    # Simulate 20 turns of long conversation
    for i in range(20):
        manager.append_history(
            session_id=session_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"这是第 {i+1} 轮的长对话内容，包含长段代码和详细的调试日志。" * 10,
        )

    stats = manager.get_stats(session_id)
    assert stats["history_count"] == 20
    assert stats["history_total_tokens"] > 1000
    assert stats["notes_tokens"] < stats["history_total_tokens"]
    assert stats["token_saving_ratio"] > 0.80  # Over 80% saved in active context
    assert stats["fidelity_rate"] == 1.0  # 100% fidelity


def test_fastapi_endpoints():
    from openviking.server.app import create_app
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    import uuid
    session_id = f"api_test_session_{uuid.uuid4().hex[:8]}"

    # 1. Update notes
    put_resp = client.put(
        "/api/v1/context/notes",
        json={
            "session_id": session_id,
            "active_goal": "API 自动化测试",
            "working_constraints": ["Rule 1", "Rule 2"],
            "current_state": "Running",
            "discovered_facts": ["Fact 1"],
        },
    )
    assert put_resp.status_code == 200
    notes_data = put_resp.json()
    assert notes_data["active_goal"] == "API 自动化测试"
    assert notes_data["version"] >= 1

    # 2. Get notes
    get_resp = client.get(f"/api/v1/context/notes?session_id={session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["active_goal"] == "API 自动化测试"

    # 3. Append history
    app_resp = client.post(
        "/api/v1/context/history/append",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "测试消息 API 调阅: SYMBOL_XYZ_8899",
        },
    )
    assert app_resp.status_code == 200
    msg = app_resp.json()
    assert msg["role"] == "user"
    assert msg["turn_index"] == 1

    # 4. List windows
    win_resp = client.get(f"/api/v1/context/history/windows?session_id={session_id}&offset=0&limit=10")
    assert win_resp.status_code == 200
    messages = win_resp.json()
    assert len(messages) == 1

    # 5. Search history
    search_resp = client.post(
        "/api/v1/context/history/search",
        json={"session_id": session_id, "query": "SYMBOL_XYZ_8899", "top_k": 5},
    )
    assert search_resp.status_code == 200
    search_hits = search_resp.json()
    assert len(search_hits) >= 1
    assert "SYMBOL_XYZ_8899" in search_hits[0]["content"]

    # 6. Context stats
    stats_resp = client.get(f"/api/v1/context/stats?session_id={session_id}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["history_count"] == 1
    assert stats["fidelity_rate"] == 1.0
