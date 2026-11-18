# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-208 regression suite: Workspace layered config, .openviking.toml & dynamic peer resolution."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from openviking_cli.utils.config.workspace_config import (
    persist_workspace_peer,
    read_registry_entry,
    resolve_workspace_settings,
)
from openviking_cli.utils.config.workspace_identity import (
    find_workspace_root,
    legacy_sanitize,
    normalize_git_remote,
    resolve_workspace_identity,
    sanitize_peer_id,
)
from openviking_cli.utils.config.workspace_peer import resolve_workspace_peer


REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_git_repo(repo_dir: Path, remote_url: str = "git@github.com:volcengine/OpenViking.git") -> None:
    git_dir = repo_dir / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    if remote_url:
        (git_dir / "config").write_text(f'[remote "origin"]\n\turl = {remote_url}\n', encoding="utf-8")


def test_git_remote_normalization_and_sanitization():
    ssh = normalize_git_remote("git@github.com:Volcengine/OpenViking.git")
    https = normalize_git_remote("https://oauth2:ghp_secret@github.com:8443/volcengine/OpenViking/")
    assert ssh == "github.com/volcengine/openviking"
    assert https == ssh
    assert normalize_git_remote("file:///tmp/repo") == ""
    assert normalize_git_remote(r"C:\src\repo") == ""

    assert sanitize_peer_id(ssh) == "github.com-volcengine-openviking"
    assert sanitize_peer_id("ext-secret") == "x-ext-secret"
    assert sanitize_peer_id("__self") == "self"
    long_peer = sanitize_peer_id("a" * 130)
    assert len(long_peer) <= 100


def test_workspace_discovery_worktree_submodule_and_non_git(tmp_path: Path):
    env = {"HOME": str(tmp_path), "OPENVIKING_HOME": str(tmp_path / "ovhome"), "OPENVIKING_STATE_DIR": str(tmp_path / "state")}

    # 1. Plain non-git directory gets no workspace root & no peer (user-level fallback)
    scratch = tmp_path / "Downloads" / "oneoff"
    scratch.mkdir(parents=True)
    assert find_workspace_root(scratch, env)["root"] == ""
    assert resolve_workspace_peer(str(scratch), env=env)["peer_id"] == ""

    # 2. Main repo + nested subdirectory converge to same git remote peer
    repo = tmp_path / "projects" / "app"
    _make_git_repo(repo)
    sub = repo / "src" / "pkg"
    sub.mkdir(parents=True)
    p_main = resolve_workspace_peer(str(repo), env=env)
    p_sub = resolve_workspace_peer(str(sub), env=env)
    assert p_main["peer_id"] == "github.com-volcengine-openviking"
    assert p_sub["peer_id"] == p_main["peer_id"]
    assert p_sub["legacy_peer_id"] == legacy_sanitize(str(sub))

    # 3. Linked worktree shares commondir -> converges to main repo peer
    wt = tmp_path / "projects" / "app-wt"
    wt_gitdir = repo / ".git" / "worktrees" / "app-wt"
    wt_gitdir.mkdir(parents=True)
    (wt_gitdir / "commondir").write_text("../..", encoding="utf-8")
    wt.mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {wt_gitdir}\n", encoding="utf-8")
    assert resolve_workspace_peer(str(wt), env=env)["peer_id"] == p_main["peer_id"]

    # 4. Submodule under .git/modules keeps its own identity
    submod = repo / "vendor" / "submod"
    mod_gitdir = repo / ".git" / "modules" / "submod"
    mod_gitdir.mkdir(parents=True)
    (mod_gitdir / "config").write_text('[remote "origin"]\n\turl = git@github.com:org/submod.git\n', encoding="utf-8")
    submod.mkdir(parents=True)
    (submod / ".git").write_text("gitdir: ../../.git/modules/submod\n", encoding="utf-8")
    assert resolve_workspace_peer(str(submod), env=env)["peer_id"] == "github.com-org-submod"


def test_toml_security_precedence_persistence_and_registry_negative_evidence(tmp_path: Path):
    ov_home = tmp_path / "ovhome"
    env = {
        "HOME": str(tmp_path),
        "OPENVIKING_HOME": str(ov_home),
        "OPENVIKING_STATE_DIR": str(tmp_path / "state"),
    }
    proj = tmp_path / "code" / "demo"
    sub = proj / "nested" / "dir"
    sub.mkdir(parents=True)

    # Persist project peer into .openviking.toml from nested folder after creating marker
    toml_path = persist_workspace_peer(str(proj), peer_id="proj-alpha", peer_source="git", target="toml", env=env)
    assert toml_path.name == ".openviking.toml"
    assert resolve_workspace_peer(str(sub), env=env)["peer_id"] == "proj-alpha"

    # Inject banned credential keys + ${HOME} literal + numeric overflow into .openviking.toml
    toml_path.write_text(
        'version = 1\n'
        'notes = "literal ${HOME}"\n'
        'api_key = "sk-evil"\n'
        'url = "https://evil.example"\n'
        'cli_config_profile = "prod"\n\n'
        '[peer]\n'
        'id = "proj-alpha"\n\n'
        '[recall]\n'
        'enabled = false\n'
        'peer_scope = "actor"\n'
        'max_items = 999\n',
        encoding="utf-8",
    )
    ws = resolve_workspace_settings(str(sub), env=env)
    assert ws["value"]["notes"] == "literal ${HOME}"
    assert "api_key" not in ws["value"]
    assert "url" not in ws["value"]
    assert "cli_config_profile" not in ws["value"]
    assert ws["settings"]["recallLimit"] == 100
    assert ws["settings"]["recallPeerScope"] == "actor"
    assert ws["settings"]["autoRecall"] is False
    assert len(ws["warnings"]) >= 4

    # Layer precedence: config.local.json > .openviking/config.json > .openviking.toml
    persist_workspace_peer(str(proj), peer_id="team-json-peer", target="json", env=env)
    assert resolve_workspace_peer(str(sub), env=env)["peer_id"] == "team-json-peer"

    persist_workspace_peer(str(proj), peer_id="local-json-peer", target="local", env=env)
    resolved_local = resolve_workspace_peer(str(sub), env=env)
    assert resolved_local["peer_id"] == "local-json-peer"
    assert resolved_local["provenance"]["peer.id"]["shadowed"][0]["value"] == "team-json-peer"

    # Registry outranks repo layers; OPENVIKING_PEER_ID outranks registry
    _make_git_repo(proj, "git@github.com:org/repo-one.git")
    persist_workspace_peer(str(proj), peer_id="registry-peer", target="registry", env=env)
    assert resolve_workspace_peer(str(sub), env=env)["peer_id"] == "registry-peer"
    assert resolve_workspace_peer(str(sub), env={**env, "OPENVIKING_PEER_ID": "env-override"})["peer_id"] == "env-override"

    # Negative evidence: replacing remote under same directory must ignore stale registry entry
    _make_git_repo(proj, "git@github.com:org/repo-two.git")
    id_two = resolve_workspace_identity(str(proj), env=env, cache=False)
    reg_two = read_registry_entry(str(proj), identity=id_two, env=env)
    assert reg_two["entry"] is None


def test_peer_templates_and_opt_out_modes(tmp_path: Path):
    env = {"HOME": str(tmp_path), "OPENVIKING_HOME": str(tmp_path / "ovhome"), "OPENVIKING_STATE_DIR": str(tmp_path / "state")}
    repo = tmp_path / "repo"
    _make_git_repo(repo, "git@github.com:volc/studio.git")

    by_harness = resolve_workspace_peer(str(repo), harness="antigravity", env=env, peer_source="{git_remote}-{harness}")
    assert by_harness["peer_id"] == "github.com-volc-studio-antigravity"

    disabled = resolve_workspace_peer(str(repo), env={**env, "OPENVIKING_WORKSPACE_PEER": "0"})
    assert disabled["peer_id"] == ""
    assert disabled["source"] == "none"

    cwd_mode = resolve_workspace_peer(str(repo), env=env, peer_source="cwd")
    assert cwd_mode["peer_id"] == legacy_sanitize(str(repo))


def test_antigravity_plugin_workspace_resolver_and_hooks(tmp_path: Path):
    plugin_dir = REPO_ROOT / "packages" / "plugins" / "openviking-memory"
    resolver_path = plugin_dir / "shared" / "workspace_resolver.py"
    spec = importlib.util.spec_from_file_location("ov_mem_workspace_resolver", resolver_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ov_mem_workspace_resolver"] = mod
    spec.loader.exec_module(mod)

    repo = tmp_path / "work" / "agent-proj"
    _make_git_repo(repo, "https://github.com/skloxo/OpenVikingStudio.git")
    (repo / ".openviking.toml").write_text(
        'version = 1\n[peer]\nid = "studio-custom-peer"\n[recall]\nenabled = true\npeer_scope = "actor"\n',
        encoding="utf-8",
    )
    env = {
        "HOME": str(tmp_path),
        "OPENVIKING_HOME": str(tmp_path / "ovhome"),
        "OPENVIKING_ACTOR_PEER": "antigravity@MACHINE-FALLBACK",
    }
    state = mod.resolve_workspace_runtime(
        cwd=str(repo),
        plugin_config={"actor_peer": "antigravity@MACHINE-FALLBACK"},
        env=env,
    )
    # Explicit workspace config beats machine fallback antigravity@...
    assert state["peer_id"] == "studio-custom-peer"
    assert state["peer_source"] == "explicit"
    assert state["peer_scope"] == "actor"
    assert state["recall_enabled"] is True

    # Git repo without custom peer.id still beats auto-generated antigravity@... fallback
    (repo / ".openviking.toml").unlink()
    git_state = mod.resolve_workspace_runtime(
        cwd=str(repo),
        plugin_config={"actor_peer": "antigravity@MACHINE-FALLBACK"},
        env=env,
    )
    assert git_state["peer_id"] == "github.com-skloxo-openvikingstudio"
    assert git_state["peer_source"] == "workspace"
