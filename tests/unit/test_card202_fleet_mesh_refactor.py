# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-202: fleet-mesh self-contained adapter, multi-node adaptive routing, and ghost-alias cleanup tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FLEET_DIR = REPO_ROOT / "integrations" / "antigravity" / "fleet-mesh"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fleet_mesh_server_exposes_exact_two_tools():
    server_mod = _load_module("fleet_mesh_server_test", FLEET_DIR / "server.py")
    tool_names = set(server_mod.mcp._tool_manager._tools.keys())
    assert tool_names == {"openviking_fleet_check", "openviking_fleet_sync"}


def test_fleet_mesh_adaptive_endpoint_and_three_part_key_headers(monkeypatch):
    server_mod = _load_module("fleet_mesh_adaptive_test", FLEET_DIR / "server.py")
    monkeypatch.delenv("OPENVIKING_API", raising=False)
    monkeypatch.delenv("OPENVIKING_ACTOR_PEER", raising=False)

    with patch.object(server_mod, "_probe_health", return_value={"status": "ok"}):
        assert server_mod.resolve_adaptive_endpoint({}) == "http://127.0.0.1:1933"

    with patch.object(server_mod, "_probe_health", return_value=None):
        assert server_mod.resolve_adaptive_endpoint({"api_url": "https://hub.example.red/"}) == "https://hub.example.red"
        assert server_mod.resolve_adaptive_endpoint({}) == "https://vk.tide.red"

    monkeypatch.setenv("OPENVIKING_USER", "spoofed")
    monkeypatch.setenv("OPENVIKING_ACCOUNT", "spoofed_acc")
    headers_bound = server_mod.build_auth_headers("ov.uid123.sig456", "antigravity@node-a", "1.0.6")
    assert headers_bound["Authorization"] == "Bearer ov.uid123.sig456"
    assert headers_bound["X-OpenViking-Actor-Peer"] == "antigravity@node-a"
    assert "X-OpenViking-User" not in headers_bound
    assert "X-OpenViking-Account" not in headers_bound


def test_setup_install_inspect_uninstall_lifecycle(tmp_path: Path, monkeypatch):
    setup_mod = _load_module("fleet_mesh_setup_test", FLEET_DIR / "setup.py")
    fake_gemini = tmp_path / ".gemini" / "config"
    fake_gemini.mkdir(parents=True)
    target_dir = fake_gemini / "plugins" / "fleet-mesh"

    # Seed legacy registry + ghost MCP aliases
    (fake_gemini / "config.json").write_text(json.dumps({"plugins": {}}), encoding="utf-8")
    (fake_gemini / "mcp_config.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "fleet": {"command": "python", "args": ["C:/Users/Skl/Desktop/coding/OpenVikingStudio/mcp.py"]},
                    "openviking-fleet": {"command": "python", "args": ["old.py"]},
                    "fleet_mesh": {"command": "python", "args": ["old2.py"]},
                    "keepass-vault": {"command": "python", "args": ["kp.py"]},
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(setup_mod, "GEMINI_CONFIG_DIR", fake_gemini)
    monkeypatch.setattr(setup_mod, "DEFAULT_TARGET_DIR", target_dir)
    monkeypatch.delenv("OPENVIKING_ACTOR_PEER", raising=False)

    setup_mod.install_plugin(target_dir, "https://vk.tide.red", "ov.key.sig")

    # 1. Self-contained server.py & zero external desktop hardcodes
    assert (target_dir / "server.py").is_file()
    priv_mcp = json.loads((target_dir / "mcp_config.json").read_text(encoding="utf-8"))
    priv_args = priv_mcp["mcpServers"]["core"]["args"]
    assert priv_args == [(target_dir / "server.py").resolve().as_posix()]
    assert "Desktop/coding/OpenVikingStudio" not in json.dumps(priv_mcp)
    assert "fleet_master" not in (target_dir / "config.json").read_text(encoding="utf-8")

    # 2. Dynamic peer & ghost-alias purging
    cfg = json.loads((target_dir / "config.json").read_text(encoding="utf-8"))
    assert cfg["actor_peer"].startswith("antigravity@")
    global_mcp = json.loads((fake_gemini / "mcp_config.json").read_text(encoding="utf-8"))["mcpServers"]
    assert "fleet" not in global_mcp
    assert "openviking-fleet" not in global_mcp
    assert "fleet_mesh" not in global_mcp
    assert "fleet-mesh" in global_mcp and "keepass-vault" in global_mcp

    # 3. Registry metadata aligned with openviking-studio
    ide_cfg = json.loads((fake_gemini / "config.json").read_text(encoding="utf-8"))
    reg_entry = ide_cfg["plugins"]["fleet-mesh"]
    assert reg_entry["enabled"] is True
    assert reg_entry["installedFrom"]["marketplace"] == "openviking-studio"

    # 4. Inspect & uninstall symmetric lifecycle
    with patch.object(setup_mod, "_probe_local_health", return_value=True):
        assert setup_mod.inspect_plugin(target_dir) is True

    setup_mod.uninstall_plugin(target_dir)
    assert not target_dir.exists()
    assert "fleet-mesh" not in json.loads((fake_gemini / "config.json").read_text(encoding="utf-8"))["plugins"]
    assert "fleet-mesh" not in json.loads((fake_gemini / "mcp_config.json").read_text(encoding="utf-8"))["mcpServers"]


def test_server_inspect_cli_exits_cleanly():
    cp = subprocess.run(
        [sys.executable, str(FLEET_DIR / "server.py"), "--inspect"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    assert cp.returncode == 0
    assert "Fleet Mesh MCP Server" in cp.stdout
