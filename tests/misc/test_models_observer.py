# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Focused tests for model status observability."""

from openviking.storage.observers.models_observer import ModelsObserver


class _ConfiguredVLM:
    model = "astron-code-latest"
    provider = "litellm"

    def get_token_usage(self):
        return {"usage_by_model": {}}


class _ConfiguredVLMWithUnavailableUsage(_ConfiguredVLM):
    def get_token_usage(self):
        raise RuntimeError("usage backend unavailable")


def test_configured_vlm_is_visible_before_usage_is_recorded():
    status = ModelsObserver(vlm_instance=_ConfiguredVLM()).get_status_table()

    assert "VLM Models:" in status
    assert "astron-code-latest" in status
    assert "litellm" in status


def test_configured_vlm_is_visible_when_usage_lookup_fails():
    status = ModelsObserver(vlm_instance=_ConfiguredVLMWithUnavailableUsage()).get_status_table()

    assert "VLM Models:" in status
    assert "astron-code-latest" in status


class _ConfiguredCompressor:
    model_name = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"
    provider = "local"


class _CompressorWithUsage:
    def get_token_usage(self):
        return {
            "usage_by_model": {
                "microsoft/llmlingua-2-xlm-roberta-large-meetingbank": {
                    "usage_by_provider": {
                        "local": {
                            "call_count": 42,
                            "prompt_tokens": 12800,
                            "completion_tokens": 6200,
                            "total_tokens": 19000,
                            "last_updated": "2026-08-24 18:00:00",
                        }
                    }
                }
            }
        }


def test_configured_compressor_is_visible_in_status_table():
    observer = ModelsObserver(compressor_instance=_ConfiguredCompressor())
    status = observer.get_status_table()

    assert "Compressor Models:" in status
    assert "microsoft/llmlingua-2-xlm-roberta-large-meetingbank" in status
    assert "local" in status
    assert observer.is_healthy() is True


def test_compressor_token_usage_is_visible():
    observer = ModelsObserver(compressor_instance=_CompressorWithUsage())
    status = observer.get_status_table()

    assert "Compressor Models:" in status
    assert "42" in status
    assert "12800" in status
    assert "19000" in status


def test_historical_models_are_consolidated_per_domain():
    class _VLM:
        model = "mux-flash"
        provider = "openai"

    class _Emb:
        model_name = "qwen3-vl-emb"
        provider = "openai"

    class _Rer:
        model_name = "qwen3-vl-rer"
        provider = "openai"

    observer = ModelsObserver(
        vlm_instance=_VLM(),
        embedding_instance=_Emb(),
        rerank_instance=_Rer(),
        compressor_instance=_ConfiguredCompressor(),
    )
    status = observer.get_status_table()

    # Verify each category exists
    assert "VLM Models:" in status
    assert "Embedding Models:" in status
    assert "Rerank Models:" in status
    assert "Compressor Models:" in status

    # Verify active models exist
    assert "mux-flash" in status
    assert "qwen3-vl-emb" in status
    assert "qwen3-vl-rer" in status

    # Verify historical consolidation rows exist inside tables
    assert "历史已下线模型汇总" in status
    # Verify no separate standalone archived table
    assert "Archived Models:" not in status
