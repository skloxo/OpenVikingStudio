# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
import pytest
from unittest.mock import AsyncMock, MagicMock
from openviking.server.routers.skills import _entry_looks_like_skill


@pytest.mark.asyncio
async def test_entry_looks_like_skill_filters_anomalies():
    service = MagicMock()
    ctx = MagicMock()

    # 1. Dot-prefixed directories like .clawhub
    dot_entry = {"uri": "viking://user/default/skills/.clawhub", "name": ".clawhub", "isDir": True}
    assert await _entry_looks_like_skill(service, ctx, dot_entry) is False

    # 2. Timestamped backup archives like 2026-05-06T09-55-26Z
    ts_entry = {"uri": "viking://user/default/skills/2026-05-06T09-55-26Z", "name": "2026-05-06T09-55-26Z", "isDir": True}
    assert await _entry_looks_like_skill(service, ctx, ts_entry) is False

    # 3. Backup and curator named directories
    curator_entry = {"uri": "viking://user/default/skills/curator-temp", "name": "curator-temp", "isDir": True}
    assert await _entry_looks_like_skill(service, ctx, curator_entry) is False

    # 4. Valid normal skill with abstract
    valid_entry = {
        "uri": "viking://user/default/skills/my-agent-skill",
        "name": "my-agent-skill",
        "isDir": True,
        "abstract": "name: my-agent-skill\ndescription: A valid skill for agent orchestration\n",
    }
    assert await _entry_looks_like_skill(service, ctx, valid_entry) is True
