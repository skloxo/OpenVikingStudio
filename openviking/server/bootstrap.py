# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Bootstrap script for OpenViking HTTP Server."""

import argparse
import asyncio
import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Optional

import uvicorn

from openviking.server.app import (
    WORKER_BOT_API_URL_ENV,
    WORKER_WITH_BOT_ENV,
    create_app,
)
from openviking.server.bot_gateway_manager import (
    VIKINGBOT_DEFAULT_HOST,
    VIKINGBOT_DEFAULT_PORT,
    BotProcess,
    resolve_cli_config_for_bot,
    resolve_default_bot_log_dir,
    start_vikingbot_gateway,
    stop_vikingbot_gateway,
    wait_for_bot_ready,
)
from openviking.server.config import get_server_url_from_server_data, load_server_config
from openviking.server.db_integrity_check import run_database_integrity_self_check
from openviking_cli.utils.config import OPENVIKING_CONFIG_ENV
from openviking_cli.utils.config.config_loader import resolve_config_path
from openviking_cli.utils.config.consts import DEFAULT_OV_CONF
from openviking_cli.utils.logger import configure_uvicorn_logging

# Backward compatibility aliases
_start_vikingbot_gateway = start_vikingbot_gateway
_stop_vikingbot_gateway = stop_vikingbot_gateway
_wait_for_bot_ready = wait_for_bot_ready
_resolve_default_bot_log_dir = resolve_default_bot_log_dir
_resolve_cli_config_for_bot = resolve_cli_config_for_bot


def _get_version() -> str:
    try:
        from openviking._version import version as __version__

        return __version__
    except Exception:
        try:
            import openviking

            return getattr(openviking, "__version__", "1.4.0")
        except Exception:
            return "1.4.0"


def _abort_if_port_in_use(port: int, label: str) -> None:
    """Exit with a clear message if anything is already listening on ``port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            in_use = True
        except (ConnectionRefusedError, socket.timeout, OSError):
            in_use = False
    if in_use:
        print(
            f"Error: {label} port {port} is already in use.\n"
            f"  A previous process is still bound — refusing to start a duplicate.\n"
            f"  Identify it:  lsof -nP -iTCP:{port} -sTCP:LISTEN\n"
            f"  Kill it, then retry.",
            file=sys.stderr,
        )
        sys.exit(1)


def _normalize_host_arg(host: Optional[str]) -> Optional[str]:
    """Normalize special CLI host values."""
    if host is None:
        return None
    if host.strip().lower() == "all":
        return None
    return host


def main():
    """Main entry point for openviking-server command."""
    parser = argparse.ArgumentParser(
        description="OpenViking HTTP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"openviking-server {_get_version()}",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to ov.conf config file",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of uvicorn worker processes (default: 1, or server.workers in ov.conf)",
    )
    parser.add_argument(
        "--bot",
        "--with-bot",
        action="store_true",
        dest="with_bot",
        help="Enable Bot API proxy to Vikingbot (requires Vikingbot running)",
    )
    parser.add_argument(
        "--bot-port",
        type=int,
        default=VIKINGBOT_DEFAULT_PORT,
        dest="bot_port",
        help=f"Vikingbot gateway port (default: {VIKINGBOT_DEFAULT_PORT})",
    )
    parser.add_argument(
        "--enable-bot-logging",
        action="store_true",
        dest="enable_bot_logging",
        default=None,
        help="Enable logging vikingbot output to files (default: True when --with-bot is used)",
    )
    parser.add_argument(
        "--disable-bot-logging",
        action="store_false",
        dest="enable_bot_logging",
        help="Disable logging vikingbot output to files",
    )
    parser.add_argument(
        "--bot-log-dir",
        type=str,
        default=None,
        help="Directory to store vikingbot log files (default: {storage.workspace or ~/.openviking/data}/bot/logs)",
    )

    args = parser.parse_args()

    if args.config is not None:
        os.environ[OPENVIKING_CONFIG_ENV] = args.config

    from openviking_cli.utils.config.open_viking_config import OpenVikingConfigSingleton

    try:
        resolved_config_path = resolve_config_path(
            args.config,
            OPENVIKING_CONFIG_ENV,
            DEFAULT_OV_CONF,
        )
        config = load_server_config(args.config)
        OpenVikingConfigSingleton.initialize(config_path=args.config)
    except (FileNotFoundError, ValueError) as e:
        if isinstance(e, ValueError):
            print(
                f"Failed to load OpenViking server configuration from {resolved_config_path}:\n{e}",
                file=sys.stderr,
            )
            print(
                "\nValidate the configuration with:\n"
                "  openviking-server doctor\n\n"
                "See examples/ov.conf.example for supported fields.",
                file=sys.stderr,
            )
        else:
            print(e, file=sys.stderr)
        sys.exit(1)

    configure_uvicorn_logging()

    # 🏥 Database and WAL quick_check integrity self-check (Card-35)
    try:
        db_report = run_database_integrity_self_check()
        print(
            f"Database integrity check: {db_report['passed_databases']}/{db_report['total_databases']} passed "
            f"({db_report['duration_ms']}ms, {db_report['fts5_rebuilt_count']} FTS5 rebuilt)"
        )
    except Exception as e:
        print(f"Warning: Database startup self-check failed to run: {e}", file=sys.stderr)

    # 🔍 Authentication health check - CRITICAL: will exit if check fails
    try:
        from openviking.server.auth.health_check import run_startup_health_check_or_exit

        asyncio.run(run_startup_health_check_or_exit(config))
    except Exception as e:
        print(f"Warning: Authentication health check failed to run: {e}", file=sys.stderr)
        print("Continuing startup anyway...", file=sys.stderr)

    # Ensure Ollama is running if configured
    try:
        from openviking_cli.utils.ollama import detect_ollama_in_config, ensure_ollama_for_server

        ov_config = OpenVikingConfigSingleton.get_instance()
        uses_ollama, ollama_host, ollama_port = detect_ollama_in_config(ov_config)
        if uses_ollama:
            result = ensure_ollama_for_server(ollama_host, ollama_port)
            if result.success:
                print(f"Ollama is running at {ollama_host}:{ollama_port}")
            else:
                print(
                    f"Warning: Ollama not available at {ollama_host}:{ollama_port}. "
                    f"Embedding/VLM may fail. ({result.message})",
                    file=sys.stderr,
                )
                if result.stderr_output:
                    print(f"  Ollama stderr: {result.stderr_output}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Ollama pre-flight check failed: {e}", file=sys.stderr)

    if args.host is not None:
        config.host = _normalize_host_arg(args.host)
    if args.port is not None:
        config.port = args.port
    if args.workers is not None:
        config.workers = args.workers
    if args.with_bot:
        config.with_bot = True

    bot_process: Optional[BotProcess] = None
    if config.with_bot:
        bot_port = args.bot_port
        config.bot_api_url = f"http://{VIKINGBOT_DEFAULT_HOST}:{bot_port}"
        _abort_if_port_in_use(bot_port, "vikingbot gateway")
        print(f"Bot API proxy enabled, forwarding to {config.bot_api_url}")
        enable_bot_logging = args.enable_bot_logging
        if enable_bot_logging is None:
            enable_bot_logging = True
        bot_log_dir = args.bot_log_dir or resolve_default_bot_log_dir(args.config)
        bot_process = _start_vikingbot_gateway(
            enable_bot_logging,
            bot_log_dir,
            bot_port,
            config_path=args.config,
            managed_server_url=get_server_url_from_server_data(config),
        )
        if bot_process is None:
            print(
                "Error: --with-bot was requested, but VikingBot could not be started.",
                file=sys.stderr,
            )
            sys.exit(1)

    app = create_app(
        config,
        config_path=(
            str(resolved_config_path) if resolved_config_path is not None else args.config
        ),
    )
    workers_info = f" (workers: {config.workers})" if config.workers > 1 else ""
    print(f"OpenViking HTTP Server is running on {config.host}:{config.port}{workers_info}")

    try:
        workers = config.workers
        if workers > 1:
            os.environ[WORKER_WITH_BOT_ENV] = "1" if config.with_bot else "0"
            os.environ[WORKER_BOT_API_URL_ENV] = config.bot_api_url
            uvicorn.run(
                "openviking.server.app:create_worker_app",
                factory=True,
                host=config.host,
                port=config.port,
                workers=workers,
                timeout_keep_alive=config.timeout_keep_alive,
                log_config=None,
            )
        else:
            uvicorn.run(
                app,
                host=config.host,
                port=config.port,
                timeout_keep_alive=config.timeout_keep_alive,
                log_config=None,
            )
    finally:
        if bot_process is not None:
            _stop_vikingbot_gateway(bot_process)


if __name__ == "__main__":
    main()
