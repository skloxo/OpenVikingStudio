"""Core reverse proxy and streaming forwarding engine for OpenViking Gateway 2.0.

Handles transparent upstream streaming, header cleansing, and dual-track translation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from openviking_gateway.config import GatewayConfig
from openviking_gateway.kernel import GatewayKernel
from openviking_gateway.protocols import (
    anthropic_to_openai_request,
    openai_to_anthropic_response,
    OpenAIToAnthropicStreamAdapter,
)
from openviking_gateway.tool_loop import (
    HiddenToolLoopExecutor,
    VIKING_HIDDEN_TOOLS_OPENAI,
)
from openviking_gateway.capture import SessionCaptureEngine

logger = logging.getLogger("openviking_gateway.proxy")

HOP_BY_HOP_HEADERS = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _format_exc_message(exc: Exception) -> str:
    """Safely format exception message ensuring non-empty explanation."""
    msg = str(exc).strip()
    if msg:
        return msg
    if hasattr(exc, "args") and exc.args and str(exc.args[0]).strip():
        return str(exc.args[0]).strip()
    cls_name = exc.__class__.__name__
    return f"{cls_name}: Upstream connection or request error"


class GatewayProxy:
    """Core reverse proxy for OpenAI and Anthropic dual-track protocols."""

    def __init__(self, config: GatewayConfig, client: Optional[httpx.AsyncClient] = None):
        self.config = config
        self._client = client
        self._owns_client = client is None
        self.kernel = GatewayKernel(config)
        self.tool_loop = HiddenToolLoopExecutor(config)
        self.capture = SessionCaptureEngine(config)

    async def get_client(self) -> httpx.AsyncClient:
        """Retrieve or lazily initialize the shared AsyncClient."""
        is_closed = getattr(self._client, "is_closed", False) is True
        if self._client is None or is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
            )
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        """Close the internal HTTP client and companion engines."""
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()
        await self.kernel.aclose()
        await self.tool_loop.aclose()
        await self.capture.aclose()

    def _prepare_headers(
        self, request: Request, target_protocol: str
    ) -> Dict[str, str]:
        """Clean and normalize headers for upstream forwarding."""
        headers: Dict[str, str] = {}
        for key, value in request.headers.items():
            k_lower = key.lower()
            if k_lower not in HOP_BY_HOP_HEADERS:
                headers[k_lower] = value

        headers["accept-encoding"] = "identity"
        headers["content-type"] = "application/json"

        # Apply upstream authorization credentials
        auth_header = request.headers.get("authorization")
        api_key = (
            auth_header.split("Bearer ")[-1].strip()
            if auth_header and "Bearer " in auth_header
            else request.headers.get("x-api-key")
        ) or self.config.upstream_api_key

        if target_protocol == "anthropic":
            if api_key:
                headers["x-api-key"] = api_key
            headers.setdefault("anthropic-version", "2023-06-01")
            headers.pop("authorization", None)
        else:
            if api_key:
                headers["authorization"] = f"Bearer {api_key}"
            headers.pop("x-api-key", None)

        return headers

    async def forward_chat_completions(
        self, request: Request, payload: Dict[str, Any]
    ) -> Response:
        """Forward OpenAI /v1/chat/completions to upstream with memory injection & tool loop."""
        client = await self.get_client()
        stream = bool(payload.get("stream", False))
        headers = self._prepare_headers(request, target_protocol=self.config.upstream_protocol)
        target_url = f"{self.config.upstream_base_url}/chat/completions"

        req_payload = dict(payload)
        # 1. Pre-flight memory context injection
        messages = req_payload.get("messages", [])
        injected_messages = await self.kernel.pre_flight_inject(messages)
        req_payload["messages"] = injected_messages

        # 2. Attach hidden tools if enabled and non-streaming
        if not stream and self.config.enable_hidden_tool_loop:
            existing_tools = list(req_payload.get("tools") or [])
            tool_names = {t.get("function", {}).get("name") for t in existing_tools if isinstance(t, dict)}
            for ht in VIKING_HIDDEN_TOOLS_OPENAI:
                if ht["function"]["name"] not in tool_names:
                    existing_tools.append(ht)
            req_payload["tools"] = existing_tools

        try:
            if stream:
                async def sse_stream_gen() -> AsyncGenerator[bytes, None]:
                    async with client.stream(
                        "POST", target_url, json=req_payload, headers=headers
                    ) as upstream_resp:
                        if upstream_resp.status_code >= 400:
                            err_body = await upstream_resp.aread()
                            yield f"data: {err_body.decode('utf-8', errors='replace')}\n\n".encode("utf-8")
                            return
                        async for line in upstream_resp.aiter_lines():
                            if line:
                                yield f"{line}\n\n".encode("utf-8")

                return StreamingResponse(
                    sse_stream_gen(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

            # Non-streaming request with hidden tool loop
            resp = await client.post(target_url, json=req_payload, headers=headers)
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            if resp.status_code == 200 and isinstance(data, dict):
                # Run hidden tool loop if model invoked viking tools
                data = await self.tool_loop.run_loop_if_needed(
                    client, target_url, headers, req_payload, data
                )
                # 3. Asynchronous session capture
                choices = data.get("choices", [])
                if choices:
                    reply = choices[0].get("message", {}).get("content", "")
                    if reply:
                        asyncio.create_task(
                            self.capture.capture_turn(
                                injected_messages, reply, model=req_payload.get("model", "")
                            )
                        )

            return JSONResponse(content=data, status_code=resp.status_code)

        except Exception as exc:
            err_msg = _format_exc_message(exc)
            logger.error("Error forwarding chat completion: %s", err_msg)
            return JSONResponse(
                content={"error": {"message": err_msg, "type": "gateway_proxy_error"}},
                status_code=502,
            )

    async def forward_messages(
        self, request: Request, payload: Dict[str, Any]
    ) -> Response:
        """Forward Anthropic /v1/messages, with dual-track translation if needed."""
        client = await self.get_client()
        stream = bool(payload.get("stream", False))

        # Check if upstream is native Anthropic or OpenAI dual-track translation
        if self.config.upstream_protocol == "anthropic":
            headers = self._prepare_headers(request, target_protocol="anthropic")
            target_url = f"{self.config.upstream_base_url}/messages"
            try:
                if stream:
                    async def anthropic_sse_gen() -> AsyncGenerator[bytes, None]:
                        async with client.stream(
                            "POST", target_url, json=payload, headers=headers
                        ) as upstream_resp:
                            async for chunk in upstream_resp.aiter_bytes():
                                yield chunk

                    return StreamingResponse(
                        anthropic_sse_gen(),
                        media_type="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                    )
                resp = await client.post(target_url, json=payload, headers=headers)
                return JSONResponse(content=resp.json(), status_code=resp.status_code)
            except Exception as exc:
                err_msg = _format_exc_message(exc)
                logger.error("Error forwarding native Anthropic messages: %s", err_msg)
                return JSONResponse(
                    content={"type": "error", "error": {"type": "api_error", "message": err_msg}},
                    status_code=502,
                )

        # Dual-track: Anthropic request -> OpenAI upstream -> Anthropic response
        openai_req = anthropic_to_openai_request(payload)
        headers = self._prepare_headers(request, target_protocol="openai")
        target_url = f"{self.config.upstream_base_url}/chat/completions"

        # Pre-flight memory injection for Anthropic protocol
        injected_messages = await self.kernel.pre_flight_inject(openai_req.get("messages", []))
        openai_req["messages"] = injected_messages

        if not stream and self.config.enable_hidden_tool_loop:
            existing_tools = list(openai_req.get("tools") or [])
            tool_names = {t.get("function", {}).get("name") for t in existing_tools if isinstance(t, dict)}
            for ht in VIKING_HIDDEN_TOOLS_OPENAI:
                if ht["function"]["name"] not in tool_names:
                    existing_tools.append(ht)
            openai_req["tools"] = existing_tools

        try:
            if stream:
                adapter = OpenAIToAnthropicStreamAdapter(model=payload.get("model", "gpt-4o"))

                async def translated_sse_gen() -> AsyncGenerator[bytes, None]:
                    async with client.stream(
                        "POST", target_url, json=openai_req, headers=headers
                    ) as upstream_resp:
                        if upstream_resp.status_code >= 400:
                            err_text = (await upstream_resp.aread()).decode("utf-8", errors="replace")
                            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'upstream_error', 'message': err_text}})}\n\n".encode("utf-8")
                            return

                        buffer = ""
                        async for chunk_bytes in upstream_resp.aiter_bytes():
                            buffer += chunk_bytes.decode("utf-8", errors="replace")
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if not line or not line.startswith("data:"):
                                    continue
                                data_str = line[5:].strip()
                                if data_str == "[DONE]":
                                    continue
                                try:
                                    chunk_dict = json.loads(data_str)
                                    events = adapter.process_chunk(chunk_dict)
                                    for ev_type, ev_data in events:
                                        yield f"event: {ev_type}\ndata: {json.dumps(ev_data)}\n\n".encode("utf-8")
                                except Exception:
                                    pass

                return StreamingResponse(
                    translated_sse_gen(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

            # Non-streaming dual-track translation with tool loop
            resp = await client.post(target_url, json=openai_req, headers=headers)
            if resp.status_code >= 400:
                return JSONResponse(
                    content={"type": "error", "error": {"type": "upstream_error", "message": resp.text}},
                    status_code=resp.status_code,
                )
            openai_resp = resp.json()

            # Execute tool loop if needed
            if isinstance(openai_resp, dict):
                openai_resp = await self.tool_loop.run_loop_if_needed(
                    client, target_url, headers, openai_req, openai_resp
                )

            anthropic_resp = openai_to_anthropic_response(openai_resp)

            # Capture turn asynchronously
            content_blocks = anthropic_resp.get("content", [])
            if content_blocks:
                reply_text = content_blocks[0].get("text", "")
                if reply_text:
                    asyncio.create_task(
                        self.capture.capture_turn(
                            injected_messages, reply_text, model=payload.get("model", "")
                        )
                    )

            return JSONResponse(content=anthropic_resp, status_code=200)

        except Exception as exc:
            err_msg = _format_exc_message(exc)
            logger.error("Error in dual-track messages translation: %s", err_msg)
            return JSONResponse(
                content={"type": "error", "error": {"type": "api_error", "message": err_msg}},
                status_code=502,
            )
