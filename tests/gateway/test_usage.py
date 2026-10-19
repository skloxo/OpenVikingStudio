# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Gateway Prompt Cache usage extraction and SSEDecoder framing."""

from __future__ import annotations

import pytest

from openviking_gateway.protocols import (
    CACHE_READ,
    CACHE_WRITE,
    SSEDecoder,
    add_usage,
    usage_of,
)


@pytest.mark.parametrize(
    ("usage", "anthropic", "expected"),
    [
        # Anthropic own form: cache excluded from input_tokens -> added to total input
        (
            {
                "input_tokens": 100,
                "cache_read_input_tokens": 800,
                "cache_creation_input_tokens": 50,
            },
            True,
            (950, 800, 50),
        ),
        # OpenAI own form: prompt_tokens_details.cached_tokens
        (
            {"prompt_tokens": 950, "prompt_tokens_details": {"cached_tokens": 800}},
            False,
            (950, 800, 0),
        ),
        (
            {"input_tokens": 950, "input_tokens_details": {"cached_tokens": 800}},
            False,
            (950, 800, 0),
        ),
        # Zero-filled Anthropic fields do not hide cached_tokens in details
        (
            {
                "prompt_tokens": 950,
                "prompt_tokens_details": {"cached_tokens": 800},
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
            False,
            (950, 800, 0),
        ),
        # LiteLLM: Chat totals already hold both cache fields it adds at the top
        (
            {
                "prompt_tokens": 1000,
                "prompt_tokens_details": {"cached_tokens": 800},
                "cache_read_input_tokens": 800,
                "cache_creation_input_tokens": 50,
            },
            False,
            (1000, 800, 50),
        ),
        ({"input_tokens": 950, "cache_read_input_tokens": 800}, False, (950, 800, 0)),
        # Anthropic-compatible endpoints that also send a Chat total
        (
            {"prompt_tokens": 0, "input_tokens": 100, "cache_read_input_tokens": 800},
            True,
            (900, 800, 0),
        ),
        (
            {"input_tokens": 100, "cache_read_input_tokens": None, "cached_tokens": 800},
            True,
            (900, 800, 0),
        ),
        # DeepSeek, Kimi, DashScope and OpenRouter field names
        (
            {
                "prompt_tokens": 950,
                "prompt_cache_hit_tokens": 800,
                "prompt_cache_miss_tokens": 150,
            },
            False,
            (950, 800, 0),
        ),
        (
            {
                "prompt_tokens": 19,
                "cached_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 10},
            },
            False,
            (19, 10, 0),
        ),
        (
            {
                "prompt_tokens": 1000,
                "prompt_tokens_details": {
                    "cached_tokens": 600,
                    "cache_creation_input_tokens": 300,
                },
            },
            False,
            (1000, 600, 300),
        ),
        (
            {
                "prompt_tokens": 1000,
                "prompt_tokens_details": {"cached_tokens": 600, "cache_write_tokens": 300},
            },
            False,
            (1000, 600, 300),
        ),
        # new-api fills both totals, one with zero
        (
            {
                "prompt_tokens": 0,
                "input_tokens": 950,
                "input_tokens_details": {"cached_tokens": 800},
            },
            False,
            (950, 800, 0),
        ),
        (
            {
                "prompt_tokens": 950,
                "input_tokens": 0,
                "prompt_tokens_details": {"cached_tokens": 800},
                "input_tokens_details": None,
            },
            False,
            (950, 800, 0),
        ),
        # Total below cache added back
        (
            {"prompt_tokens": 10, "prompt_tokens_details": {"cached_tokens": 800}},
            False,
            (810, 800, 0),
        ),
        # No cache fields
        ({"input_tokens": 100, "cache_read_input_tokens": None}, True, (100, 0, 0)),
        ({"prompt_tokens": 950, "prompt_tokens_details": {}}, False, (950, 0, 0)),
    ],
)
def test_usage_of_reads_every_upstream_form(usage, anthropic, expected):
    result = usage_of({"usage": usage}, excludes_cache=anthropic)
    assert (
        result["input_tokens"],
        result["cached_tokens"],
        result["cache_write_tokens"],
    ) == expected


def test_add_usage_skips_nulls_and_accumulates():
    total = {}
    for usage in (
        {"cache_read_input_tokens": None, "prompt_tokens_details": None, "is_byok": False},
        {"cache_read_input_tokens": 5, "prompt_tokens_details": {"cached_tokens": 80}},
        {"cache_read_input_tokens": None, "prompt_tokens_details": None, "is_byok": False},
    ):
        add_usage(total, usage)
    assert total == {
        "cache_read_input_tokens": 5,
        "prompt_tokens_details": {"cached_tokens": 80},
        "is_byok": False,
    }


def test_sse_decoder_framing_and_chunk_split():
    decoder = SSEDecoder()
    # Feed partial chunk
    frames1 = decoder.feed(b"data: {\"test\": 1}\n")
    assert frames1 == []

    # Finish frame
    frames2 = decoder.feed(b"\n")
    assert len(frames2) == 1
    assert b"\"test\": 1" in frames2[0]

    # Multiple frames in one chunk
    frames3 = decoder.feed(b"data: a\n\ndata: b\n\n")
    assert len(frames3) == 2


def test_auxiliary_pattern_matching():
    from openviking_gateway.protocols import auxiliary

    assert auxiliary("Please summarize this context") is True
    assert auxiliary("COMPACT the previous conversation") is True
    assert auxiliary("generate title") is True
    assert auxiliary("classify the following document") is True
    assert auxiliary("write a python script to parse json") is False
    # Case exception fallback
    assert auxiliary("SUMMAR\u0130ZE") is True

