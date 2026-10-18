# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-Extraction-ZeroThinking-BisectionHeal (v1.5.11).
Tests truncation failure detection, dual-threshold gates, recursive bisection,
safe chunking, and telemetry tracking.
"""

import pytest
from unittest.mock import MagicMock

from openviking.session.memory.bisection_heal import (
    estimate_message_tokens,
    check_dual_threshold_gate,
    pre_slice_messages,
    is_truncation_failure,
    bisect_messages,
    safe_chunk_memory_content,
    merge_resolved_operations,
    record_heal_event,
    get_bisection_heal_metrics,
    reset_heal_metrics,
    TRUNCATION_CHAR_THRESHOLD,
    TRUNCATION_TOKEN_THRESHOLD,
)
from openviking.session.memory.dataclass import (
    ResolvedOperations,
    ResolvedOperation,
    MemoryFile,
    WikiLink,
)


class TestBisectionHealCore:
    """Test fundamental algorithmic units of bisection healing."""

    def setup_method(self):
        reset_heal_metrics()

    def test_estimate_message_tokens(self):
        # Empty messages
        assert estimate_message_tokens([]) == 0

        # String messages
        msgs = ["Short message", "Another slightly longer message for testing."]
        tokens = estimate_message_tokens(msgs)
        assert tokens > 0

        # Dict messages
        dict_msgs = [
            {"role": "user", "content": "A" * 400},
            {"role": "assistant", "content": "B" * 200},
        ]
        # (400 + 200) / 3.5 ≈ 171 + 8 = 179
        assert estimate_message_tokens(dict_msgs) >= 170

    def test_dual_threshold_gate_logic(self):
        # Well below thresholds -> False
        short_msgs = [{"role": "user", "content": "Hello"}]
        assert check_dual_threshold_gate(short_msgs) is False

        # Exceeds char threshold -> True
        long_char_msg = [{"role": "user", "content": "x" * (TRUNCATION_CHAR_THRESHOLD + 100)}]
        assert check_dual_threshold_gate(long_char_msg) is True

        # Exceeds token threshold -> True
        many_msgs = [{"role": "user", "content": "token " * 300} for _ in range(50)]
        assert check_dual_threshold_gate(many_msgs) is True

    def test_pre_slice_messages(self):
        # Small message list -> single slice
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        slices = pre_slice_messages(msgs, max_tokens_per_slice=1000)
        assert len(slices) == 1
        assert len(slices[0]) == 5

        # Larger message list exceeding slice token limit -> multiple slices with overlap
        big_msgs = [{"role": "user", "content": "word " * 1000} for _ in range(10)]
        slices = pre_slice_messages(big_msgs, max_tokens_per_slice=1500, overlap_messages=2)
        assert len(slices) >= 2
        # Verify overlap exists between adjacent slices
        slice_0_last = slices[0][-1]
        slice_1_first = slices[1][0]
        assert slice_0_last in slices[1] or slice_1_first in slices[0]

    def test_is_truncation_failure_detection(self):
        # 1. Detected via finish_reason == 'length'
        mock_resp = MagicMock()
        mock_resp.finish_reason = "length"
        assert is_truncation_failure(mock_resp, '{"ops": [', None) is True

        # 2. Detected via finish_reason == 'max_tokens'
        mock_resp.finish_reason = "max_tokens"
        assert is_truncation_failure(mock_resp, "incomplete content", None) is True

        # 3. Detected via JSON truncation syntax error
        normal_resp = MagicMock()
        normal_resp.finish_reason = "stop"
        assert is_truncation_failure(normal_resp, '{"key": "val', "Unterminated string starting at line 1") is True
        assert is_truncation_failure(normal_resp, '{"data": [1, 2,', "Expecting value: line 1 column 15") is True

        # 4. Normal complete JSON failure should not be treated as truncation
        assert is_truncation_failure(normal_resp, '{"unknown_tool": true}', "Field required: upsert_operations") is False

    def test_bisect_messages(self):
        # 4 messages bisected with overlap=1 -> mid=2, left=[:3], right=[2:]
        msgs = [f"m_{i}" for i in range(4)]
        left, right = bisect_messages(msgs, overlap=1)
        assert len(left) == 3
        assert len(right) == 2
        assert right[0] in left  # Overlap exists

        # Empty or single message
        assert bisect_messages([]) == ([], [])
        assert bisect_messages(["single"]) == (["single"], [])

    def test_safe_chunk_memory_content(self):
        # Small content untouched
        small_op = ResolvedOperation(
            uris=["viking://memories/test.md"],
            memory_fields={"content": "Normal sized memory content"},
            memory_type="context",
        )
        small_ops = ResolvedOperations(
            upsert_operations=[small_op],
            delete_file_contents=[],
            errors=[],
        )
        res = safe_chunk_memory_content(small_ops, max_chars=1000)
        assert len(res.upsert_operations) == 1
        assert res.upsert_operations[0].memory_fields["content"] == "Normal sized memory content"

        # Giant content split into safe chunks
        giant_content = "Paragraph header.\n" + ("Long text block. " * 500)
        giant_op = ResolvedOperation(
            uris=["viking://memories/giant.md"],
            memory_fields={"content": giant_content},
            memory_type="context",
        )
        giant_ops = ResolvedOperations(
            upsert_operations=[giant_op],
            delete_file_contents=[],
            errors=[],
        )
        res_split = safe_chunk_memory_content(giant_ops, max_chars=1000)
        assert len(res_split.upsert_operations) > 1
        assert all(len(op.memory_fields["content"]) <= 1200 for op in res_split.upsert_operations)
        # Verify URI numbering for chunks
        assert "_chunk_1" in res_split.upsert_operations[1].uris[0]

    def test_merge_resolved_operations(self):
        from openviking.session.memory.dataclass import StoredLink

        op1 = ResolvedOperation(
            uris=["viking://memories/a.md"],
            memory_fields={"content": "Content A"},
            memory_type="context",
        )
        op2 = ResolvedOperation(
            uris=["viking://memories/b.md"],
            memory_fields={"content": "Content B"},
            memory_type="context",
        )
        link1 = StoredLink(
            from_uri="viking://memories/a.md",
            to_uri="viking://memories/b.md",
            link_type="related_to",
        )
        del_file = MemoryFile(uri="viking://memories/old.md", content="Old")

        res1 = ResolvedOperations(
            upsert_operations=[op1],
            delete_file_contents=[],
            errors=[],
            resolved_links=[link1],
        )
        res2 = ResolvedOperations(
            upsert_operations=[op2],
            delete_file_contents=[del_file],
            errors=[],
        )

        merged = merge_resolved_operations([res1, res2])
        assert len(merged.upsert_operations) == 2
        assert len(merged.delete_file_contents) == 1
        assert len(merged.resolved_links) == 1
        assert merged.delete_file_contents[0].uri == "viking://memories/old.md"

    def test_telemetry_recording(self):
        record_heal_event("total_extractions", 5)
        record_heal_event("truncations_detected", 2)
        record_heal_event("bisection_heals_triggered", 2)
        record_heal_event("bisection_heals_success", 2)
        record_heal_event("zero_thinking_enforced_count", 5)

        metrics = get_bisection_heal_metrics()
        assert metrics["total_extractions"] == 5
        assert metrics["truncations_detected"] == 2
        assert metrics["bisection_heals_triggered"] == 2
        assert metrics["bisection_heals_success"] == 2
        assert metrics["zero_thinking_enforced_count"] == 5
        assert metrics["heal_success_rate"] == 100.0


class TestExtractLoopBisectionIntegration:
    """Integration test suite for ExtractLoop and bisection self-healing."""

    def setup_method(self):
        reset_heal_metrics()

    @pytest.mark.asyncio
    async def test_run_triggers_bisection_heal_on_truncation(self):
        """Verify that when truncation occurs in ExtractLoop.run(), bisection heal is invoked and succeeds."""
        from unittest.mock import AsyncMock
        from openviking.session.memory.extract_loop import ExtractLoop

        mock_provider = MagicMock()
        mock_provider.messages = [
            {"role": "user", "content": "User prompt 1 " * 50},
            {"role": "assistant", "content": "Assistant turn 1 " * 50},
            {"role": "user", "content": "User prompt 2 " * 50},
            {"role": "assistant", "content": "Assistant turn 2 " * 50},
        ]
        mock_provider.get_memory_schemas = MagicMock(return_value=[])
        mock_provider.get_output_language = MagicMock(return_value="en")
        mock_provider.get_tools = MagicMock(return_value=[])
        mock_provider.read_file_contents = {}
        mock_provider.prefetch = AsyncMock(return_value=[])

        loop = ExtractLoop(
            vlm=MagicMock(),
            viking_fs=MagicMock(),
            context_provider=mock_provider,
            isolation_handler=MagicMock(),
        )
        loop._extract_context = MagicMock()
        loop._extract_context.page_id_map = MagicMock()

        # Simulate truncation failure on _call_llm
        async def fake_call_llm(messages):
            resp = MagicMock()
            resp.finish_reason = "length"
            resp.content = '{"memory": ['
            loop._last_vlm_response = resp
            loop._last_llm_failure_content = resp.content
            loop._last_llm_error = "Expecting value: line 1 column 12"
            return (None, None)

        loop._call_llm = AsyncMock(side_effect=fake_call_llm)

        # Expected healed operations from bisection
        healed_op = ResolvedOperation(
            uris=["viking://memories/healed.md"],
            memory_fields={"content": "Successfully healed through bisection."},
            memory_type="context",
        )
        expected_healed_ops = ResolvedOperations(
            upsert_operations=[healed_op],
            delete_file_contents=[],
            errors=[],
        )
        loop._run_bisection_heal = AsyncMock(return_value=expected_healed_ops)

        # Run ExtractLoop
        final_ops, raw_links = await loop.run()

        # Assertions
        assert len(final_ops.upsert_operations) == 1
        assert final_ops.upsert_operations[0].uris == ["viking://memories/healed.md"]
        loop._run_bisection_heal.assert_awaited_once()

        # Verify telemetry counters were updated
        metrics = get_bisection_heal_metrics()
        assert metrics["truncations_detected"] >= 1
        assert metrics["bisection_heals_triggered"] >= 1
        assert metrics["bisection_heals_success"] >= 1

    @pytest.mark.asyncio
    async def test_run_bisection_heal_spawns_and_merges(self):
        """Verify _run_bisection_heal bisects messages, runs sub-loops and merges results."""
        from unittest.mock import AsyncMock, patch
        from openviking.session.memory.extract_loop import ExtractLoop

        mock_provider = MagicMock()
        mock_provider.messages = [
            {"role": "user", "content": f"msg {i}"} for i in range(6)
        ]
        mock_provider.latest_archive_overview = "Overview"

        loop = ExtractLoop(
            vlm=MagicMock(),
            viking_fs=MagicMock(),
            context_provider=mock_provider,
            isolation_handler=MagicMock(),
        )

        op_left = ResolvedOperation(
            uris=["viking://memories/left.md"],
            memory_fields={"content": "Left branch memory"},
            memory_type="context",
        )
        op_right = ResolvedOperation(
            uris=["viking://memories/right.md"],
            memory_fields={"content": "Right branch memory"},
            memory_type="context",
        )
        left_res = ResolvedOperations(upsert_operations=[op_left], delete_file_contents=[], errors=[])
        right_res = ResolvedOperations(upsert_operations=[op_right], delete_file_contents=[], errors=[])

        with patch.object(ExtractLoop, "run", AsyncMock(side_effect=[(left_res, []), (right_res, [])])):
            with patch("openviking.session.memory.session_extract_context_provider.SessionExtractContextProvider.prepare_extraction_messages", AsyncMock()):
                healed = await loop._run_bisection_heal(mock_provider.messages)

        assert healed is not None
        assert len(healed.upsert_operations) == 2
        healed_uris = [op.uris[0] for op in healed.upsert_operations]
        assert "viking://memories/left.md" in healed_uris
        assert "viking://memories/right.md" in healed_uris

    def test_simulate_bisection_heal_run(self):
        """Verify simulation function returns full diagnosis for tests & UI."""
        from openviking.session.memory.bisection_heal import simulate_bisection_heal_run

        result = simulate_bisection_heal_run()
        assert result["status"] == "success"
        assert result["zero_thinking_enforced"] is True
        assert result["dual_threshold_triggered"] is True
        assert result["pre_slices_generated"] >= 1
        assert "tokens_saved_ratio" in result

    @pytest.mark.asyncio
    async def test_system_router_bisection_endpoints(self):
        """Verify FastAPI system endpoints for bisection telemetry and probe drill."""
        import json
        from openviking.server.routers.system import (
            get_bisection_heal_telemetry,
            bisection_heal_simulation_probe,
            BisectionHealProbeRequest,
        )

        resp = await get_bisection_heal_telemetry(_ctx=MagicMock())
        assert resp.status_code == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["status"] == "healthy"
        assert "thresholds" in body
        assert body["thresholds"]["char_threshold"] == 4000
        assert body["thresholds"]["msg_threshold"] == 25

        probe_req = BisectionHealProbeRequest(scenario="drill_test")
        probe_resp = await bisection_heal_simulation_probe(probe_req, _ctx=MagicMock())
        assert probe_resp.status_code == 200
        probe_body = json.loads(probe_resp.body.decode("utf-8"))
        assert probe_body["status"] == "success"
        assert probe_body["zero_thinking_enforced"] is True
        assert "metrics" in probe_body


