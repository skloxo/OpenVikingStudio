"""Protocol dual-track translation engine for OpenViking Gateway 2.0.

Provides bidirectional translation between OpenAI and Anthropic formats:
- Anthropic Request -> OpenAI Request
- OpenAI Response -> Anthropic Response
- OpenAI Streaming SSE chunks -> Anthropic SSE Events
"""

from __future__ import annotations

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

    usage = resp.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text_content}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
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

            usage = chunk.get("usage", {})
            output_tokens = usage.get("completion_tokens", 0)

            events.append(
                (
                    "content_block_stop",
                    {
                        "type": "content_block_stop",
                        "index": self.block_index,
                    },
                )
            )
            events.append(
                (
                    "message_delta",
                    {
                        "type": "message_delta",
                        "delta": {
                            "stop_reason": stop_reason,
                            "stop_sequence": None,
                        },
                        "usage": {"output_tokens": output_tokens},
                    },
                )
            )
            events.append(("message_stop", {"type": "message_stop"}))

        return events
