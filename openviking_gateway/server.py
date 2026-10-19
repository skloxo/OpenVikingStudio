"""Server runner and entrypoint for OpenViking Gateway 2.0.

Runs the isolated microservice on port 1934 (or custom port).
"""

from __future__ import annotations

import argparse
import sys
import uvicorn

from openviking_gateway.config import GatewayConfig, get_gateway_config
from openviking_gateway.app import create_gateway_app


def run_gateway(
    host: str | None = None,
    port: int | None = None,
    upstream_url: str | None = None,
    upstream_key: str | None = None,
    upstream_protocol: str | None = None,
    debug: bool = False,
) -> None:
    """Launch the Gateway 2.0 microservice with uvicorn."""
    cfg = get_gateway_config()
    if host:
        cfg.host = host
    if port:
        cfg.port = port
    if upstream_url:
        cfg.upstream_base_url = upstream_url.rstrip("/")
    if upstream_key:
        cfg.upstream_api_key = upstream_key
    if upstream_protocol:
        cfg.upstream_protocol = upstream_protocol
    if debug:
        cfg.debug = debug

    app = create_gateway_app(cfg)
    print(f"[OpenViking Gateway 2.0] Listening on http://{cfg.host}:{cfg.port}")
    print(f"[OpenViking Gateway 2.0] Upstream: {cfg.upstream_base_url} ({cfg.upstream_protocol})")
    print(f"[OpenViking Gateway 2.0] Dual-track translation: {cfg.enable_dual_track_translation}")

    uvicorn.run(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level="debug" if cfg.debug else "info",
        access_log=cfg.debug,
    )


def main() -> None:
    """CLI entrypoint for running openviking_gateway."""
    parser = argparse.ArgumentParser(description="OpenViking Gateway 2.0 Reverse Proxy")
    parser.add_argument("--host", type=str, default=None, help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen (default: 1934)")
    parser.add_argument("--upstream-url", type=str, default=None, help="Upstream LLM base URL")
    parser.add_argument("--upstream-key", type=str, default=None, help="Upstream API key")
    parser.add_argument(
        "--upstream-protocol",
        type=str,
        default=None,
        choices=["openai", "anthropic"],
        help="Upstream protocol",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    run_gateway(
        host=args.host,
        port=args.port,
        upstream_url=args.upstream_url,
        upstream_key=args.upstream_key,
        upstream_protocol=args.upstream_protocol,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
