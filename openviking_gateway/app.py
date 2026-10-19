"""FastAPI application factory for OpenViking Gateway 2.0.

Provides fully compatible OpenAI and Anthropic reverse proxy routes on port 1934.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from openviking_gateway.config import GatewayConfig, get_gateway_config
from openviking_gateway.proxy import GatewayProxy

GATEWAY_VERSION = "1.7.138"


def create_gateway_app(config: Optional[GatewayConfig] = None) -> FastAPI:
    """Instantiate and configure the standalone Gateway FastAPI application."""
    cfg = config or get_gateway_config()

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        yield
        if hasattr(app_instance.state, "proxy") and app_instance.state.proxy:
            await app_instance.state.proxy.aclose()

    app = FastAPI(
        title="OpenViking Gateway 2.0",
        description="High-performance transparent proxy and dual-track translation gateway",
        version=GATEWAY_VERSION,
        docs_url="/docs" if cfg.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Attach config & proxy to app state
    app.state.config = cfg
    app.state.proxy = GatewayProxy(cfg)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check probe reporting gateway metadata."""
        return {
            "status": "ok",
            "gateway": "openviking_gateway",
            "version": GATEWAY_VERSION,
            "port": cfg.port,
            "upstream_protocol": cfg.upstream_protocol,
            "dual_track": cfg.enable_dual_track_translation,
            "timestamp": int(time.time()),
        }

    @app.get("/v1/models")
    async def list_models() -> Dict[str, Any]:
        """Compatible OpenAI /v1/models listing."""
        now = int(time.time())
        models = [
            {
                "id": cfg.default_model,
                "object": "model",
                "created": now,
                "owned_by": "openviking_gateway",
            }
        ]
        # Common models for external client auto-discovery
        common = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20241022"]
        for m in common:
            if m != cfg.default_model:
                models.append(
                    {
                        "id": m,
                        "object": "model",
                        "created": now,
                        "owned_by": "openviking_gateway",
                    }
                )
        return {"object": "list", "data": models}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Any:
        """OpenAI-compatible chat completion proxy endpoint."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                content={"error": {"message": "Invalid JSON body", "type": "invalid_request_error"}},
                status_code=400,
            )
        return await app.state.proxy.forward_chat_completions(request, payload)

    @app.post("/v1/messages")
    async def messages(request: Request) -> Any:
        """Anthropic-compatible messages proxy endpoint."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                content={"type": "error", "error": {"type": "invalid_request_error", "message": "Invalid JSON body"}},
                status_code=400,
            )
        return await app.state.proxy.forward_messages(request, payload)

    return app
