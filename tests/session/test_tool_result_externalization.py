# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import json

import pytest

import openviking.session.session as session_module
import openviking.session.tool_result_store as tool_result_store
from openviking.message import ToolPart
from openviking.server.config import ToolOutputExternalizationConfig
from openviking.session import Session
from openviking.session.tool_result_store import ToolResultStore
from openviking_cli.exceptions import NotFoundError


class MemoryVikingFS:
    def __init__(self):
        self.files = {}

    async def write_file(self, uri, content, *, ctx=None, lease_ref=None):  # noqa: ANN001
        self.files[uri] = content

    async def append_file(self, uri, content, *, ctx=None, lease_ref=None):  # noqa: ANN001
        self.files[uri] = self.files.get(uri, "") + content

    async def exists(self, uri, ctx=None):  # noqa: ANN001
        return uri in self.files

    async def read_file(self, uri, *, ctx=None):  # noqa: ANN001
        if uri not in self.files:
            raise NotFoundError(uri, "file")
        return self.files[uri]

    async def ls(self, uri, *, output="original", node_limit=1000, ctx=None):  # noqa: ANN001
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


@pytest.fixture(autouse=True)
def _drain_background_tasks():
    yield


@pytest.fixture
def session():
    return Session(MemoryVikingFS(), session_id="test_session_tool_results")


@pytest.fixture
def session_with_tool_call(session):
    tool_id = "test_tool_001"
    tool_part = ToolPart(
        tool_id=tool_id,
        tool_name="test_tool",
        tool_input={"param": "value"},
        tool_status="running",
    )
    msg = session.add_message("assistant", [tool_part])
    return session, msg.id, tool_id


def _small_config(**overrides):
    values = {
        "threshold_chars": 20,
        "preview_chars": 12,
        "assistant_turn_inline_budget_chars": 30,
        "assistant_turn_preview_budget_chars": 20,
        "min_preview_chars": 4,
    }
    values.update(overrides)
    return ToolOutputExternalizationConfig(**values)


def _json_items_payload(count: int) -> str:
    items = ",".join(f'{{"id":{idx},"name":"item{idx}"}}' for idx in range(count))
    return f'{{"items":[{items}]}}'


async def test_externalized_tool_output_generates_synopsis_once(session: Session, monkeypatch):
    session._tool_output_externalization_config = _small_config(
        threshold_chars=20,
        preview_chars=200,
    )
    raw = '{"users":[{"id":1,"name":"Ada"},{"id":2,"name":"Lin"}],"meta":{"count":2}}' * 3

    calls = 0
    original = tool_result_store.generate_tool_result_synopsis

    def wrapped(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(tool_result_store, "generate_tool_result_synopsis", wrapped)
    monkeypatch.setattr(session_module, "generate_tool_result_synopsis", wrapped)

    session.add_message(
        "user",
        [
            ToolPart(
                tool_id="call_json_synopsis_once",
                tool_name="fetch_json",
                tool_output=raw,
                tool_status="completed",
            )
        ],
    )

    assert calls == 1


async def test_list_tool_results_filters_tool_name_before_limit():
    class FakeVikingFS:
        def __init__(self):
            self.entries = [
                {"name": "tr_other", "isDir": True},
                {"name": "tr_target", "isDir": True},
            ]
            self.metadata = {
                "tr_other": {"tool_result_id": "tr_other", "tool_name": "other"},
                "tr_target": {"tool_result_id": "tr_target", "tool_name": "target"},
            }

        async def ls(self, uri, *, output, node_limit, ctx):  # noqa: ANN001
            return self.entries[:node_limit]

        async def read_file(self, uri, *, ctx):  # noqa: ANN001
            tool_result_id = uri.rstrip("/").split("/")[-2]
            return json.dumps(self.metadata[tool_result_id])

    store = ToolResultStore(
        FakeVikingFS(),
        "viking://user/alice/sessions/filter-before-limit",
        "filter-before-limit",
        ctx=None,
    )

    result = await store.list(tool_name="target", limit=1)

    assert result["tool_results"] == [{"tool_result_id": "tr_target", "tool_name": "target"}]


async def test_tool_output_below_threshold_stays_inline(session: Session):
    session._tool_output_externalization_config = _small_config(
        threshold_chars=50,
        preview_chars=20,
    )
    small_output = "Short tool output within threshold"
    session.add_message(
        "user",
        [
            ToolPart(
                tool_id="call_small_001",
                tool_name="small_fetch",
                tool_output=small_output,
                tool_status="completed",
            )
        ],
    )
    msg = session.messages[-1]
    part = msg.parts[0]
    assert isinstance(part, ToolPart)
    assert part.tool_output == small_output
    assert not part.tool_output_truncated
    assert part.tool_output_ref is None or part.tool_output_ref == ""


async def test_tool_output_above_threshold_externalized_and_persisted(session: Session):
    session._tool_output_externalization_config = _small_config(
        threshold_chars=30,
        preview_chars=15,
    )
    long_output = "Line 1: system initialized successfully\nLine 2: diagnostics ok\nLine 3: finished."
    session.add_message(
        "user",
        [
            ToolPart(
                tool_id="call_large_001",
                tool_name="run_diagnostics",
                tool_output=long_output,
                tool_status="completed",
            )
        ],
    )
    msg = session.messages[-1]
    part = msg.parts[0]
    assert isinstance(part, ToolPart)
    assert part.tool_output_truncated is True
    assert part.tool_output_original_chars == len(long_output)
    assert part.tool_output_ref.startswith(f"{session._session_uri}/tool-results/tr_")
    assert "[OpenViking tool result externalized]" in part.tool_output

    # 验证影子文件落盘
    tool_result_id = part.tool_output_ref.rstrip("/").split("/")[-1]
    output_file = f"{part.tool_output_ref}/output.txt"
    meta_file = f"{part.tool_output_ref}/metadata.json"
    assert output_file in session._viking_fs.files
    assert meta_file in session._viking_fs.files
    assert session._viking_fs.files[output_file] == long_output

    # 验证 read_tool_result 接口
    read_full = await session.read_tool_result(tool_result_id, limit=-1)
    assert read_full["content"] == long_output
    assert read_full["total_chars"] == len(long_output)
    assert read_full["has_more"] is False
    assert read_full["metadata"]["tool_name"] == "run_diagnostics"

    # 验证分页读取
    read_chunk = await session.read_tool_result(tool_result_id, offset=0, limit=20)
    assert read_chunk["content"] == long_output[:20]
    assert read_chunk["has_more"] is True


async def test_search_tool_result(session: Session):
    session._tool_output_externalization_config = _small_config(
        threshold_chars=20,
        preview_chars=10,
    )
    content = "Alpha beta gamma delta epsilon zeta eta theta iota kappa"
    session.add_message(
        "user",
        [
            ToolPart(
                tool_id="call_search_001",
                tool_name="search_probe",
                tool_output=content,
                tool_status="completed",
            )
        ],
    )
    part = session.messages[-1].parts[0]
    tool_result_id = part.tool_output_ref.rstrip("/").split("/")[-1]

    search_res = await session.search_tool_result(tool_result_id, query="gamma", limit=5)
    assert len(search_res["matches"]) >= 1
    assert "gamma" in search_res["matches"][0]["snippet"]


async def test_hydrate_tool_outputs_for_extraction(session: Session):
    session._tool_output_externalization_config = _small_config(
        threshold_chars=25,
        preview_chars=10,
    )
    original_text = "Important memory payload that exceeds threshold for extraction test"
    session.add_message(
        "user",
        [
            ToolPart(
                tool_id="call_extract_001",
                tool_name="extract_source",
                tool_output=original_text,
                tool_status="completed",
            )
        ],
    )
    assert session.messages[-1].parts[0].tool_output_truncated is True

    hydrated = await session._hydrate_tool_outputs_for_extraction(session.messages)
    hydrated_part = hydrated[-1].parts[0]
    assert isinstance(hydrated_part, ToolPart)
    assert hydrated_part.tool_output == original_text
    # 消息实例本身依然保持轻量存根，不被水合污染
    assert session.messages[-1].parts[0].tool_output != original_text
