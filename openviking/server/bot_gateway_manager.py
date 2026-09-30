# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Vikingbot gateway subprocess manager for OpenViking HTTP Server."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional

from openviking_cli.utils.config import OPENVIKING_CONFIG_ENV
from openviking_cli.utils.config.config_loader import resolve_config_path
from openviking_cli.utils.config.consts import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_OV_CONF,
    DEFAULT_OVCLI_CONF,
    OPENVIKING_CLI_CONFIG_ENV,
)

VIKINGBOT_DEFAULT_HOST = "127.0.0.1"
VIKINGBOT_DEFAULT_PORT = 18790


@dataclass
class BotProcess:
    process: subprocess.Popen
    log_file: Optional[Any] = None


def resolve_default_bot_log_dir(config_path: Optional[str]) -> str:
    """Resolve default bot log directory from current ov.conf storage.workspace."""
    default_storage = DEFAULT_CONFIG_DIR / "data"
    default_log_dir = default_storage / "bot" / "logs"

    resolved_path = resolve_config_path(config_path, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF)
    if resolved_path is None:
        return str(default_log_dir)

    try:
        with open(resolved_path, "r", encoding="utf-8-sig") as f:
            raw = os.path.expandvars(f.read())
        data = json.loads(raw)
        storage = data.get("storage", {})
        workspace = storage.get("workspace") if isinstance(storage, dict) else None
        if not workspace:
            return str(default_log_dir)
        return str(Path(workspace).expanduser().resolve() / "bot" / "logs")
    except Exception:
        return str(default_log_dir)


def resolve_cli_config_for_bot(config_path: Optional[str]) -> Optional[str]:
    """Resolve which ovcli.conf the vikingbot child process should use."""
    explicit_cli_config = os.environ.get(OPENVIKING_CLI_CONFIG_ENV)
    if explicit_cli_config:
        return explicit_cli_config

    resolved_ov_conf = resolve_config_path(config_path, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF)
    if resolved_ov_conf is not None:
        colocated_cli_config = Path(resolved_ov_conf).resolve().parent / DEFAULT_OVCLI_CONF
        if colocated_cli_config.exists():
            return str(colocated_cli_config)

    default_cli_config = DEFAULT_CONFIG_DIR / DEFAULT_OVCLI_CONF
    if default_cli_config.exists():
        return str(default_cli_config)

    return None


def wait_for_bot_ready(process: subprocess.Popen, status_path: Path) -> None:
    """A running child is not ready until its sandbox and HTTP server are ready."""
    started = time.monotonic()
    timeout = 900
    while time.monotonic() - started < timeout:
        if process.poll() is not None:
            raise RuntimeError(
                f"VikingBot exited before becoming ready (code {process.returncode})."
            )
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            status = {}
        if status.get("pid") == process.pid:
            timeout = max(timeout, int(status.get("timeout", timeout)))
            if status.get("status") == "failed":
                raise RuntimeError(status.get("error") or "VikingBot initialization failed")
            if status.get("status") == "ready":
                return
        time.sleep(0.1)
    raise TimeoutError("VikingBot readiness timed out; check Docker/image pulls and the Bot log.")


def start_vikingbot_gateway(
    enable_logging: bool,
    log_dir: str,
    port: int = VIKINGBOT_DEFAULT_PORT,
    config_path: Optional[str] = None,
    managed_server_url: Optional[str] = None,
) -> Optional[BotProcess]:
    """Start vikingbot gateway as a subprocess."""
    print("Starting vikingbot gateway...")

    vikingbot_cmd = None
    if shutil.which("vikingbot"):
        vikingbot_cmd = ["vikingbot", "gateway"]
    else:
        python_cmd = sys.executable
        try:
            result = subprocess.run(
                [python_cmd, "-m", "vikingbot", "--help"], capture_output=True, timeout=15
            )
            if result.returncode == 0:
                vikingbot_cmd = [python_cmd, "-m", "vikingbot", "gateway"]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    if vikingbot_cmd is None:
        print("Warning: vikingbot not found. Please install vikingbot first.")
        print("  uv pip install -e '.[bot,dev]'")
        return None

    vikingbot_cmd.extend(["--host", VIKINGBOT_DEFAULT_HOST, "--port", str(port)])
    resolved_config = resolve_config_path(config_path, OPENVIKING_CONFIG_ENV, DEFAULT_OV_CONF)
    if resolved_config is not None:
        vikingbot_cmd.extend(["--config", str(resolved_config)])

    log_file = None
    stdout_handler = None
    stderr_handler = None
    log_file_path = None

    if enable_logging:
        try:
            os.makedirs(log_dir, exist_ok=True)
            log_filename = "vikingbot.log"
            log_file_path = os.path.join(log_dir, log_filename)
            log_file = open(log_file_path, "a")
            stdout_handler = log_file
            stderr_handler = log_file
            print(f"Vikingbot logs will be written to: {log_file_path}")
        except Exception as e:
            print(f"Warning: Failed to setup bot logging: {e}")
            if log_file:
                log_file.close()
                log_file = None
            stdout_handler = None
            stderr_handler = None

    startup_directory = tempfile.TemporaryDirectory(prefix="vikingbot-startup-")
    status_path = Path(startup_directory.name) / "status.json"
    process = None
    try:
        env = os.environ.copy()
        env["VIKINGBOT_STARTUP_STATUS"] = str(status_path)
        cli_config_path = resolve_cli_config_for_bot(config_path)
        if cli_config_path is not None:
            env[OPENVIKING_CLI_CONFIG_ENV] = cli_config_path
        env["VIKINGBOT_WITH_OPENVIKING_SERVER"] = "1"
        repo_root = str(Path(__file__).resolve().parent.parent.parent)
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{repo_root}:{existing_pp}" if existing_pp else repo_root
        env["PYTHONSAFEPATH"] = "1"
        if managed_server_url:
            env["VIKINGBOT_MANAGED_OV_SERVER_URL"] = managed_server_url

        process = subprocess.Popen(
            vikingbot_cmd,
            stdout=stdout_handler,
            stderr=stderr_handler,
            text=True,
            env=env,
            cwd=repo_root,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

        waiter = wait_for_bot_ready
        try:
            import openviking.server.bootstrap as bs
            if hasattr(bs, "_wait_for_bot_ready"):
                waiter = getattr(bs, "_wait_for_bot_ready")
        except Exception:
            pass
        waiter(process, status_path)

        print(f"Vikingbot gateway started (PID: {process.pid})")
        return BotProcess(process=process, log_file=log_file)

    except BaseException as e:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if log_file:
            log_file.close()
        print(f"Failed to start vikingbot gateway: {e}")
        if log_file_path:
            print(f"VikingBot startup details: {log_file_path}")
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        return None
    finally:
        startup_directory.cleanup()


def stop_vikingbot_gateway(bot_process: BotProcess) -> None:
    """Stop the vikingbot gateway subprocess."""
    if bot_process is None:
        return

    print(f"\nStopping vikingbot gateway (PID: {bot_process.process.pid})...")
    try:
        bot_process.process.terminate()
        try:
            bot_process.process.wait(timeout=30)
            print("Vikingbot gateway stopped gracefully.")
        except subprocess.TimeoutExpired:
            bot_process.process.kill()
            bot_process.process.wait()
            print("Vikingbot gateway force killed.")
    except Exception as e:
        print(f"Error stopping vikingbot gateway: {e}")
    finally:
        if bot_process.log_file is not None:
            try:
                bot_process.log_file.close()
            except Exception as e:
                print(f"Error closing bot log file: {e}")
