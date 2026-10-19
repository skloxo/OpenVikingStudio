"""Unit tests for GatewayProxy class in openviking_gateway."""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request

from openviking_gateway.config import GatewayConfig
from openviking_gateway.proxy import GatewayProxy, HOP_BY_HOP_HEADERS


def make_dummy_request(headers: dict = None) -> Request:
    """Helper to construct dummy starlette Request with custom headers."""
    raw_headers = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode("latin1"), v.encode("latin1")))

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/chat/completions",
        "headers": raw_headers,
    }
    return Request(scope)


def test_prepare_headers_filtering():
    config = GatewayConfig(upstream_api_key="default-key-123")
    proxy = GatewayProxy(config)

    headers = {
        "Host": "localhost:1934",
        "Connection": "keep-alive",
        "Authorization": "Bearer client-custom-key",
        "User-Agent": "Cursor-Client/1.0",
        "Content-Length": "128",
    }
    req = make_dummy_request(headers)
    cleaned = proxy._prepare_headers(req, target_protocol="openai")

    # Hop by hop headers filtered
    for h in HOP_BY_HOP_HEADERS:
        assert h not in cleaned

    assert cleaned["authorization"] == "Bearer client-custom-key"
    assert cleaned["user-agent"] == "Cursor-Client/1.0"
    assert cleaned["content-type"] == "application/json"


def test_prepare_headers_anthropic_protocol():
    config = GatewayConfig(upstream_api_key="anthropic-secret-key")
    proxy = GatewayProxy(config)

    headers = {
        "x-api-key": "client-anthropic-key",
    }
    req = make_dummy_request(headers)
    cleaned = proxy._prepare_headers(req, target_protocol="anthropic")

    assert cleaned["x-api-key"] == "client-anthropic-key"
    assert cleaned["anthropic-version"] == "2023-06-01"
    assert "authorization" not in cleaned


@pytest.mark.asyncio
async def test_proxy_forward_chat_completions_error_handling():
    config = GatewayConfig(upstream_base_url="https://invalid.upstream.test/v1")
    proxy = GatewayProxy(config)

    # Mock client to raise network error
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    proxy._client = mock_client
    proxy._owns_client = False

    req = make_dummy_request()
    resp = await proxy.forward_chat_completions(req, {"model": "gpt-4o"})

    assert resp.status_code == 502
    data = json.loads(resp.body.decode("utf-8"))
    assert data["error"]["type"] == "gateway_proxy_error"
    assert "Connection refused" in data["error"]["message"]
