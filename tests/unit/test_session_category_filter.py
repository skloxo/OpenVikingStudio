# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test for session category filtering and anti-entropy heartbeat detection."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from openviking.service.session_service import SessionService
from openviking.server.identity import RequestContext, Role, UserIdentifier


@pytest.fixture
def mock_ctx():
    user = UserIdentifier(user_id="default", account_id="default")
    return RequestContext(user=user, role=Role(Role.USER))


@pytest.fixture
def session_service():
    srv = SessionService()
    # Mock dependencies
    mock_fs = MagicMock()
    mock_vikingdb = MagicMock()
    mock_compressor = MagicMock()

    entries = [
        {"name": "user_session_alpha", "isDir": True, "modTime": "2026-09-15T10:00:00Z"},
        {"name": "cron_hourly_probe_01", "isDir": True, "modTime": "2026-09-15T11:00:00Z"},
        {"name": "heartbeat_node_3070", "isDir": True, "modTime": "2026-09-15T11:30:00Z"},
        {"name": "user_session_beta", "isDir": True, "modTime": "2026-09-15T12:00:00Z"},
        {"name": "ping_check_99", "isDir": True, "modTime": "2026-09-15T12:15:00Z"},
    ]
    mock_fs.ls = AsyncMock(return_value=entries)
    srv.set_dependencies(mock_vikingdb, mock_fs, mock_compressor)
    return srv


@pytest.mark.asyncio
async def test_session_category_filter_all(session_service, mock_ctx):
    results = await session_service.sessions(mock_ctx, category="all")
    assert len(results) == 5
    ids = [r["session_id"] for r in results]
    assert "user_session_alpha" in ids
    assert "cron_hourly_probe_01" in ids


@pytest.mark.asyncio
async def test_session_category_filter_interactive_only(session_service, mock_ctx):
    results = await session_service.sessions(mock_ctx, category="interactive")
    assert len(results) == 2
    ids = [r["session_id"] for r in results]
    assert "user_session_alpha" in ids
    assert "user_session_beta" in ids
    assert "cron_hourly_probe_01" not in ids
    assert "heartbeat_node_3070" not in ids
    assert "ping_check_99" not in ids


@pytest.mark.asyncio
async def test_session_category_filter_heartbeat_only(session_service, mock_ctx):
    results = await session_service.sessions(mock_ctx, category="heartbeat")
    assert len(results) == 3
    ids = [r["session_id"] for r in results]
    assert "cron_hourly_probe_01" in ids
    assert "heartbeat_node_3070" in ids
    assert "ping_check_99" in ids
    assert "user_session_alpha" not in ids


def test_dynamic_heartbeat_session_registration(session_service):
    custom_id = "random-uuid-9999-internal-task"
    assert session_service._is_heartbeat_session(custom_id) is False
    session_service.register_heartbeat_session(custom_id)
    assert session_service._is_heartbeat_session(custom_id) is True
