import hashlib

import pytest

from openviking.message import Message, ToolPart
from openviking.server.identity import RequestContext, Role
from openviking.session.memory.dataclass import ResolvedOperation, ResolvedOperations
from openviking.session.memory.experience_lineage import (
    collect_read_experience_uris,
    experience_source_tag,
    experience_uri_to_tag_key,
    normalize_trajectory_outcome,
    trajectory_outcome_tag,
)
from openviking.session.train.components.trajectory_analyzer import (
    _trajectory_search_tags_by_uri,
)
from openviking_cli.session.user_id import UserIdentifier


def _ctx() -> RequestContext:
    return RequestContext(user=UserIdentifier("account", "alice"), role=Role.USER)


def test_collect_read_experience_uris_supports_generic_openviking_reads():
    uri = "viking://user/alice/memories/experiences/order-exchange.md"
    opencode_uri = "viking://user/alice/memories/experiences/opencode.md"
    messages = [
        Message(
            id="call",
            role="assistant",
            parts=[
                ToolPart(
                    tool_id="read-1",
                    tool_name="mcp__openviking__read",
                    tool_input={"uri": uri},
                    tool_status="pending",
                ),
                ToolPart(
                    tool_id="search-1",
                    tool_name="mcp__openviking__find",
                    tool_input={"query": "exchange"},
                    tool_status="completed",
                    tool_output='{"results":[{"uri":"%s"}]}' % uri,
                ),
            ],
        ),
        Message(
            id="result",
            role="user",
            parts=[
                ToolPart(
                    tool_id="read-1",
                    tool_name="mcp__openviking__read",
                    tool_status="completed",
                    tool_output='{"uri":"%s"}' % uri,
                ),
                ToolPart(
                    tool_id="read-2",
                    tool_name="openviking_read",
                    tool_input={"uri": "viking://user/bob/memories/experiences/other.md"},
                    tool_status="completed",
                ),
                ToolPart(
                    tool_id="read-2-current-user",
                    tool_name="openviking_read",
                    tool_input={"uri": opencode_uri},
                    tool_status="completed",
                ),
                ToolPart(
                    tool_id="read-3",
                    tool_name="read",
                    tool_input={"uri": uri},
                    tool_status="error",
                ),
            ],
        ),
    ]

    assert collect_read_experience_uris(messages, ctx=_ctx()) == [uri, opencode_uri]


@pytest.mark.parametrize("tool_name", ["multi_read", "openviking_multi_read"])
def test_collect_read_experience_uris_filters_failed_multi_read_results(tool_name):
    first_uri = "viking://user/alice/memories/experiences/first.md"
    failed_uri = "viking://user/alice/memories/experiences/failed.md"
    messages = [
        Message(
            id="multi-read",
            role="user",
            parts=[
                ToolPart(
                    tool_id="multi-read-1",
                    tool_name=tool_name,
                    tool_input={"uris": [first_uri, failed_uri]},
                    tool_status="completed",
                    tool_output=(
                        '{"results":['
                        f'{{"uri":"{first_uri}","success":true}},'
                        f'{{"uri":"{failed_uri}","success":false}}]}}'
                    ),
                )
            ],
        )
    ]

    assert collect_read_experience_uris(messages, ctx=_ctx()) == [first_uri]


def test_collect_read_experience_uris_ignores_removed_dedicated_tool():
    messages = [
        Message(
            id="legacy-read",
            role="user",
            parts=[
                ToolPart(
                    tool_id="legacy-read-1",
                    tool_name="read_experience",
                    tool_input={"uri": "viking://user/alice/memories/experiences/legacy.md"},
                    tool_status="completed",
                )
            ],
        )
    ]

    assert collect_read_experience_uris(messages, ctx=_ctx()) == []


def test_experience_source_tag_uses_experience_uri_as_key():
    """experience_source_tag 必须产生合规的 xp.<sha256_16hex>=1 格式。"""
    uri = "viking://user/alice/memories/experiences/无订单号换货处理.md"

    tag = experience_source_tag(uri)
    key = experience_uri_to_tag_key(uri)

    # 格式: xp.<16hex>=1
    assert tag == f"{key}=1"
    assert tag.startswith("xp.")
    assert tag.count("=") == 1
    # key 长度必须 <= 64 (实际约 20 字符)
    actual_key = tag.split("=", 1)[0]
    assert len(actual_key) <= 64
    # 字符集合规：只含 [a-z0-9_.\-]
    import re
    assert re.match(r"^[a-z0-9][a-z0-9_.-]*$", actual_key)


def test_experience_source_tag_preserves_case_and_escapes_equals_without_collisions():
    """不同 URI（大小写/特殊字符不同）必须生成不同的 tag，且同 URI 必须稳定生成相同 tag。"""
    uppercase_uri = "viking://user/Alice/memories/experiences/Exchange=Flow.md"
    lowercase_uri = "viking://user/alice/memories/experiences/exchange=flow.md"

    uppercase_tag = experience_source_tag(uppercase_uri)
    lowercase_tag = experience_source_tag(lowercase_uri)

    # 两个不同 URI 生成的 tag 必须不同（哈希无碰撞）
    assert uppercase_tag != lowercase_tag
    # 每个 tag 都只含一个 = 号
    assert uppercase_tag.count("=") == 1
    assert lowercase_tag.count("=") == 1
    # 格式必须是 xp.<16hex>=1
    assert uppercase_tag.startswith("xp.")
    assert lowercase_tag.startswith("xp.")
    # 稳定性：多次调用同 URI 产生相同结果
    assert experience_source_tag(uppercase_uri) == uppercase_tag
    assert experience_source_tag(lowercase_uri) == lowercase_tag
    # 哈希值正确性验证（对齐实现的 SHA-256[:16]）
    expected_upper_hash = hashlib.sha256(uppercase_uri.encode("utf-8")).hexdigest()[:16]
    assert uppercase_tag == f"xp.{expected_upper_hash}=1"


def test_source_experiences_create_transient_tags_for_every_generated_trajectory():
    first_uri = "viking://user/alice/memories/experiences/exchange.md"
    second_uri = "viking://user/alice/memories/experiences/refund.md"
    operations = ResolvedOperations(
        upsert_operations=[
            ResolvedOperation(
                memory_fields={"trajectory_name": "exchange", "outcome": "success"},
                memory_type="trajectories",
                uris=["viking://user/alice/memories/trajectories/exchange.md"],
            ),
            ResolvedOperation(
                memory_fields={"trajectory_name": "refund", "outcome": "failure"},
                memory_type="trajectories",
                uris=["viking://user/alice/memories/trajectories/refund.md"],
            ),
        ],
        delete_file_contents=[],
        errors=[],
    )

    tags_by_uri = _trajectory_search_tags_by_uri(
        operations,
        [first_uri, second_uri, first_uri],
    )

    assert tags_by_uri == {
        "viking://user/alice/memories/trajectories/exchange.md": [
            experience_source_tag(first_uri),
            experience_source_tag(second_uri),
            "trajectory_outcome=success",
        ],
        "viking://user/alice/memories/trajectories/refund.md": [
            experience_source_tag(first_uri),
            experience_source_tag(second_uri),
            "trajectory_outcome=failure",
        ],
    }
    for operation in operations.upsert_operations:
        assert "source_experience_uris" not in operation.memory_fields


def test_trajectory_outcome_tag_normalizes_unknown_values():
    assert trajectory_outcome_tag(" SUCCESS ") == "trajectory_outcome=success"
    assert trajectory_outcome_tag("unexpected") == "trajectory_outcome=unknown"
    assert normalize_trajectory_outcome(None) == "unknown"
