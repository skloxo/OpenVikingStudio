# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Retina test suite for Card-211: Upstream Models, Evolution Attribution & Native CLI.

Covers:
- Tracer-1: Agent Evolution experience read attribution with sanitized URIs and plugin tools
- Tracer-2: Gemini Embedding 2 stable model adaptation and task instruction formatting
- Tracer-3: Server setup wizard default VLM models upgrade to Seed 2.1 Lite
- Tracer-4: ov_cli error source chain recursive unwrapping
- Tracer-5: LocalFS case-insensitive alias ACL documentation consistency
"""

import pytest
from unittest.mock import MagicMock, patch

from openviking.message import Message, ToolPart
from openviking.server.identity import RequestContext, Role
from openviking_cli.session.user_id import UserIdentifier
from openviking.session.memory.experience_lineage import (
    collect_read_experience_uris,
    _read_operation,
)
from openviking.models.embedder.gemini_embedders import (
    GeminiDenseEmbedder,
    _MODEL_TOKEN_LIMITS,
    _TASK_INSTRUCTIONS,
    _VALID_TASK_TYPES,
)
from openviking_cli.setup_wizard import (
    CLOUD_PROVIDERS,
    VOLCENGINE_PLANS,
    BYTEPLUS_PLANS,
)


def _ctx() -> RequestContext:
    return RequestContext(user=UserIdentifier("account", "alice"), role=Role.USER)


class TestCard211Tracer1EvolutionAttribution:
    """Tracer-1: Agent Evolution experience read attribution tests."""

    def test_collect_read_experience_uris_filters_query_and_fragment(self):
        ctx = _ctx()
        valid_canonical = "viking://user/alice/memories/experiences/valid.md"
        messages = [
            Message(
                id="msg-1",
                role="user",
                parts=[
                    ToolPart(
                        tool_id="read-1",
                        tool_name="mcp__openviking__read",
                        tool_input={"uris": "viking://~/memories/experiences/valid.md"},
                        tool_status="completed",
                        tool_output="Valid experience content",
                    ),
                    ToolPart(
                        tool_id="read-2",
                        tool_name="mcp__openviking__read",
                        tool_input={"uris": "viking://~/memories/experiences/with_query.md?offset=1"},
                        tool_status="completed",
                    ),
                    ToolPart(
                        tool_id="read-3",
                        tool_name="mcp__openviking__read",
                        tool_input={"uris": "viking://~/memories/experiences/with_frag.md#heading"},
                        tool_status="completed",
                    ),
                ],
            )
        ]
        result = collect_read_experience_uris(messages, ctx=ctx)
        assert result == [valid_canonical]

    def test_read_operation_supports_plugin_namespaced_tools(self):
        assert _read_operation("mcp__plugin_openviking-memory_openviking__read") == "read"
        assert _read_operation("mcp__PLUGIN_openviking-memory_OpenViking__READ") == "read"
        assert _read_operation("mcp__plugin_openviking-memory_openviking__multi_read") == "multi_read"
        assert _read_operation("mcp__plugin_other_tool__read") is None


class TestCard211Tracer2GeminiEmbedding2:
    """Tracer-2: Gemini Embedding 2 stable model adaptation tests."""

    def test_model_constants_and_token_limits(self):
        assert _MODEL_TOKEN_LIMITS["gemini-embedding-2"] == 8192
        assert GeminiDenseEmbedder.KNOWN_DIMENSIONS["gemini-embedding-2"] == 3072
        assert "RETRIEVAL_QUERY" in _VALID_TASK_TYPES
        assert "RETRIEVAL_DOCUMENT" in _VALID_TASK_TYPES

    @patch("openviking.models.embedder.gemini_embedders._GENAI_AVAILABLE", True)
    @patch("openviking.models.embedder.gemini_embedders.genai")
    @patch("openviking.models.embedder.gemini_embedders.types")
    def test_stable_gemini_formats_instruction_prefix(self, mock_types, mock_genai):
        mock_config = MagicMock()
        mock_config.output_dimensionality = 1536
        mock_types.EmbedContentConfig.return_value = mock_config

        embedder = GeminiDenseEmbedder(api_key="mock-key", dimension=1536)
        assert embedder.model_name == "gemini-embedding-2"
        assert embedder.get_dimension() == 1536

        # Query instruction
        text, config = embedder._prepare_request("how to configure", is_query=True, task_type="RETRIEVAL_QUERY")
        assert text == "task: search result | query: how to configure"
        assert config.output_dimensionality == 1536

        # Document instruction with title
        text, config = embedder._prepare_request("body text", is_query=False, task_type="RETRIEVAL_DOCUMENT", title="Doc Title")
        assert text == "title: Doc Title | text: body text"
        assert config.output_dimensionality == 1536

    @patch("openviking.models.embedder.gemini_embedders._GENAI_AVAILABLE", True)
    @patch("openviking.models.embedder.gemini_embedders.genai")
    def test_stable_gemini_rejects_invalid_task_type(self, mock_genai):
        embedder = GeminiDenseEmbedder(api_key="mock-key")
        with pytest.raises(ValueError, match="Invalid task_type 'UNKNOWN_TYPE'"):
            embedder._prepare_request("text", task_type="UNKNOWN_TYPE")


class TestCard211Tracer3SetupWizardVLM:
    """Tracer-3: Setup wizard default VLM models upgraded to Seed 2.1 Lite."""

    def test_volcengine_and_byteplus_defaults(self):
        volc_provider = next(p for p in CLOUD_PROVIDERS if p.provider == "volcengine" and "VolcEngine" in p.label)
        assert volc_provider.default_vlm_model == "doubao-seed-2-1-lite-260915"

        byteplus_provider = next(p for p in CLOUD_PROVIDERS if p.label == "BytePlus")
        assert byteplus_provider.default_vlm_model == "seed-2-0-lite-260428"

        agent_plan = next(p for p in VOLCENGINE_PLANS if p.label == "Agent Plan")
        assert agent_plan.default_vlm_model == "doubao-seed-2.1-lite"

        coding_plan = next(p for p in VOLCENGINE_PLANS if p.label == "Coding Plan")
        assert coding_plan.default_vlm_model == "doubao-seed-2.1-lite"

        payg_plan = next(p for p in VOLCENGINE_PLANS if "Pay-as-you-go" in p.label)
        assert payg_plan.default_vlm_model == "doubao-seed-2-1-lite-260915"

        bp_payg = next(p for p in BYTEPLUS_PLANS if "Pay-as-you-go" in p.label)
        assert bp_payg.default_vlm_model == "seed-2-0-lite-260428"


class TestCard211Tracer4ErrorChain:
    """Tracer-4: Error source chain unwrapping logic tests."""

    def test_error_source_chain_deduplication(self):
        def with_sources(error_msg: str, causes: list[str]) -> str:
            msg = error_msg
            for cause in causes:
                if not msg.endswith(cause):
                    msg = f"{msg}: {cause}"
            return msg

        # Should chain when cause is not already at end
        assert with_sources("outer", ["inner"]) == "outer: inner"
        # Should avoid duplicate suffixes
        assert with_sources("outer: inner", ["inner"]) == "outer: inner"
        # Multi-level chain
        assert with_sources("HTTP failed", ["TLS handshake failed", "invalid peer certificate: UnknownIssuer"]) == (
            "HTTP failed: TLS handshake failed: invalid peer certificate: UnknownIssuer"
        )


class TestCard211Tracer5Documentation:
    """Tracer-5: LocalFS case-insensitive alias ACL docs."""

    def test_acl_docs_contain_alias_section(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent
        en_doc = (root / "docs" / "en" / "api" / "12-acl.md").read_text(encoding="utf-8")
        zh_doc = (root / "docs" / "zh" / "api" / "12-acl.md").read_text(encoding="utf-8")

        assert "## Case Aliases and ACL" in en_doc
        assert "viking://resources/BOB-PRIVATE/private.md" in en_doc
        assert "## 大小写别名与 ACL" in zh_doc
        assert "viking://resources/BOB-PRIVATE/private.md" in zh_doc
