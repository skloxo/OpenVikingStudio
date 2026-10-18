# -*- coding: utf-8 -*-
"""Unit tests for Card-20A: ov_session_archiver transcript telemetry extraction and reporting."""

import json
import pytest
from pathlib import Path

# Add hooks directory to path for import
import sys
sys.path.insert(0, "/home/skloxo/aho/openclaw/project/.agents/hooks")

import ov_session_archiver


def test_extract_telemetry_from_transcript(tmp_path):
    """Verify that extract_telemetry_from_transcript accurately parses JSONL transcripts."""
    transcript_file = tmp_path / "sample_transcript.jsonl"
    lines = [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "content": "请帮我实现一个LRU缓存算法，并结合OpenViking存储",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "content": "好的，以下是LRU缓存的实现：\n```python\nclass LRUCache:\n    def __init__(self, capacity: int):\n        self.capacity = capacity\n```\n并且我们调用 openviking_find 检索记忆。",
            "tool_calls": [{"name": "openviking_find", "arguments": {"query": "LRU"}}],
        },
        {
            "step_index": 2,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "content": "不对，缺少 get 和 put 方法，报错了，请重新修改",
        },
        {
            "step_index": 3,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "content": "已修正：\n```python\nclass LRUCache:\n    def get(self, key):\n        pass\n```",
        },
    ]

    with open(transcript_file, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    telemetry = ov_session_archiver.extract_telemetry_from_transcript(str(transcript_file))
    assert telemetry is not None
    assert telemetry["total_tokens"] > 0
    assert telemetry["effective_tokens"] > 0
    assert telemetry["effective_tokens"] <= telemetry["total_tokens"]
    # openviking tool called
    assert telemetry["top5_hits"] >= 1
    # step 2 had "不对" and "报错"
    assert telemetry["interventions_count"] >= 1


def test_extract_hermes_messages_from_transcript(tmp_path):
    """Verify that extract_hermes_messages_from_transcript parses conversation turns for Hermes (Card-20E)."""
    transcript_file = tmp_path / "sample_hermes_transcript.jsonl"
    lines = [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "content": "请分析系统的内存泄漏",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "content": "好的，正在检查常驻线程。",
            "tool_calls": [{"name": "exec", "arguments": {"command": "ps aux"}}],
        },
    ]

    with open(transcript_file, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    msgs = ov_session_archiver.extract_hermes_messages_from_transcript(
        str(transcript_file), session_id="test_sess_hermes"
    )
    assert len(msgs) == 2
    assert msgs[0]["session_id"] == "test_sess_hermes"
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "请分析系统的内存泄漏"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["tool_calls"] is not None
    assert msgs[1]["tool_calls"][0]["name"] == "exec"

