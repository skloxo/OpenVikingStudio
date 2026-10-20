"""Protocol dual-track translation engine for OpenViking Gateway 2.0.

Provides bidirectional translation between OpenAI and Anthropic formats:
- Anthropic Request -> OpenAI Request
- OpenAI Response -> Anthropic Response
- OpenAI Streaming SSE chunks -> Anthropic SSE Events
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field



class AnthropicMessage(BaseModel):
    """Anthropic user/assistant message item."""

    role: str
    content: Union[str, List[Dict[str, Any]]]


class AnthropicMessagesRequest(BaseModel):
    """Standard Anthropic /v1/messages request structure."""

    model: str
    messages: List[AnthropicMessage]
    max_tokens: Optional[int] = Field(default=4096)
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stream: Optional[bool] = False
    stop_sequences: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None


def _extract_text_content(content: Union[str, List[Dict[str, Any]]]) -> str:
    """Extract plain text from string or structured content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(parts)
    return str(content)


def anthropic_to_openai_request(
    req: Union[AnthropicMessagesRequest, Dict[str, Any]]
) -> Dict[str, Any]:
    """Convert Anthropic /v1/messages request payload to OpenAI /v1/chat/completions."""
    if isinstance(req, dict):
        req = AnthropicMessagesRequest(**req)

    openai_messages: List[Dict[str, Any]] = []

    # Handle system message
    if req.system:
        system_text = _extract_text_content(req.system)
        if system_text.strip():
            openai_messages.append({"role": "system", "content": system_text})

    # Convert conversation turns
    for m in req.messages:
        role = "user" if m.role == "user" else "assistant"
        text = _extract_text_content(m.content)
        openai_messages.append({"role": role, "content": text})

    result: Dict[str, Any] = {
        "model": req.model,
        "messages": openai_messages,
        "stream": bool(req.stream),
    }

    if req.max_tokens is not None:
        result["max_tokens"] = req.max_tokens
    if req.temperature is not None:
        result["temperature"] = req.temperature
    if req.top_p is not None:
        result["top_p"] = req.top_p
    if req.stop_sequences:
        result["stop"] = req.stop_sequences

    return result


def openai_to_anthropic_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI /v1/chat/completions response into Anthropic format."""
    msg_id = resp.get("id") or f"msg_{uuid.uuid4().hex[:20]}"
    model = resp.get("model", "unknown")
    choices = resp.get("choices", [])

    text_content = ""
    stop_reason = "end_turn"
    if choices:
        choice = choices[0]
        msg = choice.get("message", {})
        text_content = msg.get("content") or ""
        openai_finish = choice.get("finish_reason")
        if openai_finish == "length":
            stop_reason = "max_tokens"
        elif openai_finish == "tool_calls":
            stop_reason = "tool_use"
        elif openai_finish == "stop":
            stop_reason = "end_turn"

    usage_info = usage_of(resp, excludes_cache=False)

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text_content}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage_info["input_tokens"],
            "output_tokens": usage_info["output_tokens"],
            "cache_read_input_tokens": usage_info["cached_tokens"],
            "cache_creation_input_tokens": usage_info["cache_write_tokens"],
        },
    }



class OpenAIToAnthropicStreamAdapter:
    """Stateful adapter translating OpenAI SSE chunks into Anthropic SSE events."""

    def __init__(self, model: str = "gpt-4o", message_id: Optional[str] = None):
        self.model = model
        self.message_id = message_id or f"msg_{uuid.uuid4().hex[:20]}"
        self.started = False
        self.finished = False
        self.block_index = 0

    def process_chunk(self, chunk: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Convert a single OpenAI chunk into zero or more Anthropic events."""
        events: List[Tuple[str, Dict[str, Any]]] = []

        chunk_id = chunk.get("id")
        if chunk_id:
            self.message_id = chunk_id

        choices = chunk.get("choices", [])
        delta_text = ""
        finish_reason = None

        if choices:
            c = choices[0]
            finish_reason = c.get("finish_reason")
            delta = c.get("delta", {})
            delta_text = delta.get("content") or ""

        # Emit message_start and content_block_start on first chunk
        if not self.started:
            self.started = True
            events.append(
                (
                    "message_start",
                    {
                        "type": "message_start",
                        "message": {
                            "id": self.message_id,
                            "type": "message",
                            "role": "assistant",
                            "model": self.model,
                            "content": [],
                            "stop_reason": None,
                            "stop_sequence": None,
                            "usage": {"input_tokens": 0, "output_tokens": 0},
                        },
                    },
                )
            )
            events.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": self.block_index,
                        "content_block": {"type": "text", "text": ""},
                    },
                )
            )

        # Emit content delta if present
        if delta_text:
            events.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": self.block_index,
                        "delta": {"type": "text_delta", "text": delta_text},
                    },
                )
            )

        # Emit completion events when finish_reason is provided
        if finish_reason and not self.finished:
            self.finished = True
            stop_reason = "end_turn"
            if finish_reason == "length":
                stop_reason = "max_tokens"
            elif finish_reason == "tool_calls":
                stop_reason = "tool_use"

            usage_info = usage_of(chunk, excludes_cache=False)
            output_tokens = usage_info["output_tokens"]

            events.append(
                (
                    "content_block_stop",
                    {
                        "type": "content_block_stop",
                        "index": self.block_index,
                    },
                )
            )
            message_delta_usage: Dict[str, Any] = {"output_tokens": output_tokens}
            if usage_info["cached_tokens"]:
                message_delta_usage["cache_read_input_tokens"] = usage_info["cached_tokens"]
            if usage_info["cache_write_tokens"]:
                message_delta_usage["cache_creation_input_tokens"] = usage_info["cache_write_tokens"]

            events.append(
                (
                    "message_delta",
                    {
                        "type": "message_delta",
                        "delta": {
                            "stop_reason": stop_reason,
                            "stop_sequence": None,
                        },
                        "usage": message_delta_usage,
                    },
                )
            )
            events.append(("message_stop", {"type": "message_stop"}))

        return events


# Fields relays put cache counts in, at the top of usage or in its token details.
CACHE_READ = ("cache_read_input_tokens", "cached_tokens", "prompt_cache_hit_tokens")
CACHE_WRITE = ("cache_creation_input_tokens", "cache_write_tokens", "cached_creation_tokens")


def usage_of(value: dict, excludes_cache: bool = False) -> dict:
    """Token counts from any protocol's usage, including compatible endpoints that mix forms.

    ``input_tokens`` always includes cached and written tokens: Anthropic counts them apart
    (``excludes_cache``), Chat and Responses totals already hold them.
    """
    usage = value.get("usage") or {}
    scopes = [
        usage,
        usage.get("prompt_tokens_details") or {},
        usage.get("input_tokens_details") or {},
    ]
    # Relays copy one count into several fields and zero-fill the rest.
    cached, written = (
        max((s[k] for s in scopes for k in keys if s.get(k) is not None), default=0)
        for keys in (CACHE_READ, CACHE_WRITE)
    )
    # Each protocol's own total first; compatible endpoints often fill both, one with zero.
    own, other = (
        ("input_tokens", "prompt_tokens") if excludes_cache else ("prompt_tokens", "input_tokens")
    )
    input_tokens = usage.get(own) or usage.get(other) or 0
    # A total below its own cache counted the cache apart, as older relays do too.
    if excludes_cache or input_tokens < cached + written:
        input_tokens += cached + written
    return {
        "input_tokens": input_tokens,
        "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens") or 0,
        "cached_tokens": cached,
        "cache_write_tokens": written,
    }


def add_usage(total: dict, usage: dict) -> None:
    """Accumulate usage numbers in-place, skipping nulls and preserving boolean/string flags."""
    for key, value in (usage or {}).items():
        if value is None:
            continue
        if isinstance(value, dict):
            sub = total.setdefault(key, {})
            if isinstance(sub, dict):
                add_usage(sub, value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            total[key] = total.get(key, 0) + value
        else:
            total[key] = value


class SSEDecoder:
    """Incremental byte framing with precompiled newline-first pattern."""

    # A frame ends at a blank line. Finding the newline first is much faster than an optional CR.
    frame_end = re.compile(rb"\n\r?\n")

    def __init__(self, max_buffer: int = 8 * 1024 * 1024):
        self.buffer = b""
        self.max_buffer = max_buffer

    def feed(self, chunk: bytes) -> list[bytes]:
        buffer, frames, start = self.buffer + chunk, [], 0
        for match in self.frame_end.finditer(buffer):
            frames.append(buffer[start : match.end()])
            start = match.end()
        self.buffer = buffer[start:]
        if len(self.buffer) > self.max_buffer:
            raise ValueError("SSE event exceeds capture limit")
        return frames

    @staticmethod
    def data(frame: bytes) -> dict | None:
        lines = [line[5:].lstrip(b" ") for line in frame.splitlines() if line.startswith(b"data:")]
        if not lines:
            return None
        payload = b"\n".join(lines).strip()
        if not payload or payload == b"[DONE]":
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None


REI_CASE_EXCEPTIONS = ("\u0130", "\u0131", "\u00df")  # i-dot, dotless-i, sharp-s

AUXILIARY_PATTERNS = [
    r"summariz",
    r"compact",
    r"title",
    r"classify",
    r"heartbeat",
    r"suggest",
]
LOWERED_AUXILIARY = [re.compile(p) for p in AUXILIARY_PATTERNS]


def auxiliary(text: str) -> bool:
    """Whether ``text`` matches an auxiliary pattern, ignoring case with O(1) literal scan."""
    if LOWERED_AUXILIARY and not any(c in text for c in REI_CASE_EXCEPTIONS):
        text_lower = text.lower()
        return any(pattern.search(text_lower) for pattern in LOWERED_AUXILIARY)
    return any(re.search(pattern, text, re.I) for pattern in AUXILIARY_PATTERNS)


