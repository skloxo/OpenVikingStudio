# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import pytest
import time
from datetime import datetime, timezone

from openviking.message import ToolPart
from openviking.server.config import ToolOutputExternalizationConfig
from openviking.session import Session
from openviking_cli.exceptions import NotFoundError


class FakeVikingFS:
    def __init__(self):
        self.files = {}

    async def write_file(self, uri, content, *, ctx=None, lease_ref=None):
        self.files[uri] = content

    async def append_file(self, uri, content, *, ctx=None, lease_ref=None):
        self.files[uri] = self.files.get(uri, "") + content

    async def read_file(self, uri, *, ctx=None):
        if uri not in self.files:
            raise NotFoundError(uri, "file")
        return self.files[uri]

    async def exists(self, uri, ctx=None):
        return uri in self.files

    async def ls(self, uri, *, output="original", node_limit=1000, ctx=None):
        prefix = uri.rstrip("/") + "/"
        names = set()
        for file_uri in self.files:
            if not file_uri.startswith(prefix):
                continue
            rest = file_uri[len(prefix) :]
            first = rest.split("/", 1)[0]
            if first:
                names.add(first)
        return [{"name": name, "isDir": True} for name in sorted(names)][:node_limit]

    async def rm(self, uri, *, recursive=False, ctx=None):
        to_del = [f for f in self.files if f == uri or f.startswith(uri.rstrip("/") + "/")]
        for f in to_del:
            self.files.pop(f, None)


@pytest.fixture
def session():
    sess = Session(FakeVikingFS(), session_id="test_card171_session")
    sess._tool_output_externalization_config = ToolOutputExternalizationConfig(
        threshold_chars=20,
        preview_chars=10,
    )
    return sess


@pytest.mark.asyncio
async def test_tool_result_prune_quota(session: Session):
    for i in range(5):
        session.add_message(
            "user",
            [
                ToolPart(
                    tool_id=f"tool_quota_{i}",
                    tool_name="test_runner",
                    tool_output=f"Output exceeding threshold for run {i} padding data 1234567890",
                    tool_status="completed",
                )
            ],
        )

    listed = await session.list_tool_results(limit=100)
    assert len(listed["tool_results"]) == 5

    # 裁剪保留最多 2 条
    res = await session.prune_tool_results(max_entries=2)
    assert res["pruned_count"] == 3

    after_prune = await session.list_tool_results(limit=100)
    assert len(after_prune["tool_results"]) == 2


@pytest.mark.asyncio
async def test_tool_result_prune_expired(session: Session):
    session.add_message(
        "user",
        [
            ToolPart(
                tool_id="tool_old",
                tool_name="old_tool",
                tool_output="Old output exceeding threshold 12345678901234567890",
                tool_status="completed",
            )
        ],
    )
    listed = await session.list_tool_results()
    assert len(listed["tool_results"]) == 1

    # max_age_seconds=0 会立即将已生成的记录视为过期
    res = await session.prune_tool_results(max_age_seconds=-1)
    assert res["pruned_count"] == 1

    remaining = await session.list_tool_results()
    assert len(remaining["tool_results"]) == 0
