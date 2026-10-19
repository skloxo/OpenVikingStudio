"""OpenViking Gateway 2.0 package.

Provides high-performance OpenAI and Anthropic dual-track reverse proxy.
"""

from openviking_gateway.config import GatewayConfig, get_gateway_config
from openviking_gateway.protocols import (
    AnthropicMessage,
    AnthropicMessagesRequest,
    anthropic_to_openai_request,
    openai_to_anthropic_response,
    OpenAIToAnthropicStreamAdapter,
)
from openviking_gateway.proxy import GatewayProxy
from openviking_gateway.app import create_gateway_app, GATEWAY_VERSION
from openviking_gateway.server import run_gateway

__version__ = GATEWAY_VERSION
__all__ = [
    "GatewayConfig",
    "get_gateway_config",
    "GatewayProxy",
    "create_gateway_app",
    "run_gateway",
    "AnthropicMessage",
    "AnthropicMessagesRequest",
    "anthropic_to_openai_request",
    "openai_to_anthropic_response",
    "OpenAIToAnthropicStreamAdapter",
]
