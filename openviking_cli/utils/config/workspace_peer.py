# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Dynamic workspace peer inheritance, template expansion, and override resolution."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Mapping, Optional

from .ovcli_config import load_ovcli_config
from .workspace_config import resolve_workspace_settings
from .workspace_identity import legacy_sanitize, resolve_workspace_identity, sanitize_peer_id

PEER_SOURCE_PRESETS: Dict[str, List[str]] = {
    "git": ["{git_remote}", "{git_root}"],
    "cwd": ["{cwd}"],
    "none": [],
}
DEFAULT_PEER_SOURCE = "git"
_VAR_RE = re.compile(r"\{([a-z_]+)\}")


def _env_bool(raw: Optional[str], fallback: bool = True) -> bool:
    if raw is None or raw == "":
        return fallback
    val = raw.strip().lower()
    if val in ("0", "false", "no", "off"):
        return False
    if val in ("1", "true", "yes", "on"):
        return True
    return fallback


def peer_source_templates(source: Any, warnings: Optional[List[str]] = None) -> List[str]:
    """Expand a `peer.source` preset, template, or fallback list into templates."""
    if isinstance(source, list):
        return [str(item) for item in source if str(item).strip()]
    raw = str(source or "").strip()
    if not raw:
        return PEER_SOURCE_PRESETS[DEFAULT_PEER_SOURCE]
    if raw in PEER_SOURCE_PRESETS:
        return PEER_SOURCE_PRESETS[raw]
    if "{" in raw:
        return [raw]
    if warnings is not None:
        warnings.append(
            f"ignored peer.source {raw!r}: expected preset ({', '.join(PEER_SOURCE_PRESETS)}) or template; "
            f"falling back to {DEFAULT_PEER_SOURCE}"
        )
    return PEER_SOURCE_PRESETS[DEFAULT_PEER_SOURCE]


def render_peer_template(template: str, variables: Mapping[str, str]) -> str:
    """All-or-nothing template expansion: any empty variable discards the candidate template."""
    text = str(template or "")
    if not text:
        return ""
    missing = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal missing
        name = match.group(1)
        val = str(variables.get(name, "") or "")
        if not val:
            missing = True
        return val

    rendered = _VAR_RE.sub(_replace, text)
    return "" if missing else rendered


def _ovcli_plugin_settings(harness: str, env: Mapping[str, str]) -> Dict[str, Any]:
    cfg = load_ovcli_config(env.get("OPENVIKING_CLI_CONFIG_FILE"))
    if not cfg or not isinstance(cfg.plugin, dict):
        return {"actor_peer_id": cfg.actor_peer_id if cfg else ""}
    shared = {k: v for k, v in cfg.plugin.items() if not isinstance(v, dict)}
    scoped = cfg.plugin.get(harness) if harness and isinstance(cfg.plugin.get(harness), dict) else {}
    out = {**shared, **scoped}
    if cfg.actor_peer_id and not out.get("peerId"):
        out["actor_peer_id"] = cfg.actor_peer_id
    return out


def resolve_workspace_peer(
    cwd: str = "",
    *,
    harness: str = "",
    env: Optional[Mapping[str, str]] = None,
    explicit_peer_id: str = "",
    workspace_peer: Optional[bool] = None,
    peer_source: Any = None,
) -> Dict[str, Any]:
    """Resolve effective project peer identity with full env > workspace > ovcli > git precedence."""
    environ = env if env is not None else os.environ
    effective_cwd = cwd or os.getcwd()
    ovcli = _ovcli_plugin_settings(harness, environ)
    ws = resolve_workspace_settings(effective_cwd, env=environ)
    ws_settings = ws["settings"]
    warnings = list(ws["warnings"])

    env_peer = str(environ.get("OPENVIKING_PEER_ID") or environ.get("OPENVIKING_ACTOR_PEER") or "").strip()
    ws_peer = str(ws_settings.get("peerId") or "").strip()
    cli_peer = str(explicit_peer_id or ovcli.get("peerId") or ovcli.get("actor_peer_id") or "").strip()
    final_explicit = env_peer or ws_peer or cli_peer

    ws_enabled = _env_bool(
        environ.get("OPENVIKING_WORKSPACE_PEER"),
        True if workspace_peer is None else bool(workspace_peer),
    )

    recall_enabled = ws_settings.get("autoRecall")
    capture_enabled = ws_settings.get("autoCapture")
    peer_scope = str(
        environ.get("OPENVIKING_RECALL_PEER_SCOPE")
        or ws_settings.get("recallPeerScope")
        or ovcli.get("recallPeerScope")
        or "all"
    ).strip()
    if peer_scope not in ("all", "actor"):
        peer_scope = "all"

    base_meta = {
        "workspace_root": ws["root"],
        "recall_enabled": True if recall_enabled is None else bool(recall_enabled),
        "capture_enabled": True if capture_enabled is None else bool(capture_enabled),
        "peer_scope": peer_scope,
        "score_threshold": ws_settings.get("scoreThreshold"),
        "commit_token_threshold": ws_settings.get("commitTokenThreshold"),
        "provenance": ws["provenance"],
        "warnings": warnings,
        "announced": ws["announced"],
    }

    if final_explicit:
        return {**base_meta, "peer_id": final_explicit, "source": "explicit", "origin": "explicit", "legacy_peer_id": ""}
    if not ws_enabled:
        return {**base_meta, "peer_id": "", "source": "none", "origin": "disabled", "legacy_peer_id": ""}

    chosen_source = environ.get("OPENVIKING_PEER_SOURCE") or peer_source or ws_settings.get("peerSource") or ovcli.get("peerSource")
    templates = peer_source_templates(chosen_source, warnings)
    if not templates:
        return {**base_meta, "peer_id": "", "source": "none", "origin": "none", "legacy_peer_id": ""}

    identity = resolve_workspace_identity(cwd=effective_cwd, env=environ)
    variables = {**identity["vars"], "harness": sanitize_peer_id(harness)}
    legacy_id = legacy_sanitize(effective_cwd)
    for tmpl in templates:
        rendered = render_peer_template(tmpl, variables)
        if rendered:
            return {
                **base_meta,
                "peer_id": rendered,
                "source": "workspace",
                "origin": tmpl,
                "legacy_peer_id": "" if rendered == legacy_id else legacy_id,
            }
    return {**base_meta, "peer_id": "", "source": "none", "origin": "unresolved", "legacy_peer_id": legacy_id}
