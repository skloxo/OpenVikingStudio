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
