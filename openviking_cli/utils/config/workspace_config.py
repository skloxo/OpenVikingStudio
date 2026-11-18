# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Layered workspace config reader, TOML/JSON parser, security filter, and peer persistence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .workspace_identity import (
    CONFIG_DIR_NAME,
    LOCAL_FILE,
    TEAM_FILE,
    TOML_FILE,
    find_workspace_root,
    identity_key,
    resolve_workspace_identity,
)
from .workspace_toml import parse_toml_safely, persist_workspace_peer_with

CONFIG_VERSION = 1
MAX_CONFIG_BYTES = 64 * 1024
MAX_DEPTH = 32

_UNSAFE_KEYS = frozenset({"__proto__", "constructor", "prototype", "__class__", "__dict__"})
_FREE_FORM_SECTIONS = frozenset({"labels"})

FORBIDDEN_KEYS = frozenset(
    {
        "url",
        "base_url",
        "mcp_url",
        "api_key",
        "bearer_token",
        "root_api_key",
        "gateway_token",
        "oidc_token",
        "ldap_username",
        "ldap_password",
        "account",
        "account_id",
        "user",
        "user_id",
        "auth_mode",
        "extra_headers",
        "credential_source",
        "cli_config_file",
        "config_file",
        "baseUrl",
        "mcpUrl",
        "apiKey",
        "bearerToken",
        "rootApiKey",
        "gatewayToken",
        "accountId",
        "userId",
        "authMode",
        "extraHeaders",
        "credentialSource",
        "credentialPath",
        "configPath",
    }
)

_RANGES: Dict[str, Tuple[float, float, bool]] = {
    "recall.dedup_turns": (0, 20, True),
    "recall.max_items": (1, 100, True),
    "recall.score_threshold": (0.0, 1.0, False),
    "capture.commit_token_threshold": (1000, 1_000_000, True),
}
_ENUMS: Dict[str, Tuple[str, ...]] = {"recall.peer_scope": ("all", "actor")}

KNOB_MAP: Dict[str, str] = {
    "peer.id": "peerId",
    "peer.source": "peerSource",
    "recall.enabled": "autoRecall",
    "recall.peer_scope": "recallPeerScope",
    "recall.events_decay_protection": "recallEventsDecayProtection",
    "recall.dedup_turns": "recallDedupTurns",
    "recall.max_items": "recallLimit",
    "recall.score_threshold": "scoreThreshold",
    "capture.enabled": "autoCapture",
    "capture.commit_token_threshold": "commitTokenThreshold",
    "bypass.session_patterns": "bypassSessionPatterns",
}


def _strip_forbidden(
    value: Any,
    banned: frozenset[str],
    warnings: List[str],
    path: str = "",
    depth: int = 0,
) -> Any:
    if depth > MAX_DEPTH:
        raise ValueError(f"nested more than {MAX_DEPTH} levels at '{path}'")
    if isinstance(value, list):
        return [
            _strip_forbidden(item, banned, warnings, f"{path}[{i}]", depth + 1)
            for i, item in enumerate(value)
        ]
    if not isinstance(value, dict):
        return value

    out: Dict[str, Any] = {}
    for key, child in value.items():
        here = f"{path}.{key}" if path else key
        if key in _UNSAFE_KEYS:
            warnings.append(f"ignored '{here}': a config file may not reach runtime internals")
            continue
        if key in banned:
            warnings.append(
                f"ignored '{here}': connection and credential settings belong in ovcli.conf or the environment"
            )
            continue
        child_banned = frozenset() if key in _FREE_FORM_SECTIONS else banned
        out[key] = _strip_forbidden(child, child_banned, warnings, here, depth + 1)
    return out


def read_workspace_file(
    path: str | Path,
    root: str | Path = "",
    layer: str = "",
    fmt: Optional[str] = None,
) -> Dict[str, Any]:
    """Read a workspace JSON or `.openviking.toml` file safely with zero `${VAR}` expansion."""
    file_path = Path(path)
    warnings: List[str] = []
    empty = {"path": str(file_path), "layer": layer, "exists": False, "data": None, "warnings": warnings}

    try:
        st = file_path.lstat()
    except OSError:
        return empty
    empty["exists"] = True
    if not file_path.is_file():
        warnings.append(f"{file_path} is not a regular file")
        return empty
    if st.st_size > MAX_CONFIG_BYTES:
        warnings.append(f"{file_path} is larger than {MAX_CONFIG_BYTES} bytes")
        return empty
    if root:
        try:
            rel = file_path.resolve().relative_to(Path(root).resolve())
            if str(rel) == ".":
                warnings.append(f"{file_path} resolves outside the workspace")
                return empty
        except (OSError, ValueError):
            warnings.append(f"{file_path} resolves outside the workspace")
            return empty

    detected_fmt = fmt or ("toml" if file_path.suffix.lower() == ".toml" else "json")
    try:
        raw_text = file_path.read_text(encoding="utf-8-sig" if detected_fmt == "json" else "utf-8")
        parsed = parse_toml_safely(raw_text) if detected_fmt == "toml" else json.loads(raw_text)
    except Exception as exc:
        warnings.append(f"{file_path} is not valid {detected_fmt.upper()} ({exc})")
        return empty

    if not isinstance(parsed, dict):
        warnings.append(f"{file_path} must contain an object")
        return empty

    declared_ver = parsed.get("version")
    if declared_ver is None and detected_fmt == "toml":
        declared_ver = CONFIG_VERSION
    if declared_ver != CONFIG_VERSION or isinstance(declared_ver, bool):
        warnings.append(f"{file_path} declares version {declared_ver!r}; supported version is {CONFIG_VERSION}")
        return empty

    filtered = {k: v for k, v in parsed.items() if k not in ("version", "$schema", "min_client_version")}
    banned = FORBIDDEN_KEYS if layer == "registry" else FORBIDDEN_KEYS | {"cli_config_profile"}
    try:
        data = _strip_forbidden(filtered, banned, warnings)
    except ValueError as exc:
        warnings.append(f"{file_path} is nested too deeply ({exc})")
        return empty
    if parsed.get("min_client_version"):
        data["min_client_version"] = str(parsed["min_client_version"])
    return {"path": str(file_path), "layer": layer, "exists": True, "data": data, "warnings": warnings}


def registry_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    environ = env if env is not None else os.environ
    ov_home = str(environ.get("OPENVIKING_HOME") or "").strip()
    base = Path(os.path.expanduser(ov_home)) if ov_home else (Path.home() / ".openviking")
    return base / "workspaces"


def slot_name(root: str, identity: Optional[Mapping[str, Any]] = None) -> str:
    key = identity_key(identity) if identity else "path"
    source = root if key == "path" else key
    label = key.rsplit("/", 1)[-1] if key.startswith("remote:") else Path(root).name
    readable = re.sub(r"[^a-zA-Z0-9._-]+", "-", label or "").strip("-")[:40]
    digest = hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"{readable}-{digest}.json" if readable else f"{digest}.json"


def read_registry_entry(
    root: str,
    identity: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    path = registry_dir(env) / slot_name(root, identity)
    file_res = read_workspace_file(path, layer="registry")
    warnings = list(file_res["warnings"])
    entry = file_res["data"]
    if not entry:
        return {"path": str(path), "entry": None, "warnings": warnings, "conflict": False}
    if identity:
        expected = identity_key(identity)
        stored = str(entry.get("identity") or "")
        if stored and stored != expected:
            warnings.append(f"{path} was recorded for repository ({stored}); ignoring entry for {expected}")
            return {"path": str(path), "entry": None, "warnings": warnings, "conflict": True}
    return {"path": str(path), "entry": entry, "warnings": warnings, "conflict": False}


def _shadow(prov: Dict[str, Any], here: str, value: Any, source: str) -> None:
    prev = prov.get(here)
    shadowed = [{"value": prev["value"], "source": prev["source"], **({} if True else {})}, *prev["shadowed"]] if prev else []
    prov[here] = {"value": value, "source": source, "shadowed": shadowed}


def _merge_into(target: Dict[str, Any], source: Dict[str, Any], layer: str, prov: Dict[str, Any], path: str = "", depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError(f"nested more than {MAX_DEPTH} levels at '{path}'")
    for key, val in source.items():
        if key in _UNSAFE_KEYS:
            continue
        here = f"{path}.{key}" if path else key
        if isinstance(val, dict):
            if not isinstance(target.get(key), dict):
                if key in target:
                    _shadow(prov, here, "(section)", layer)
                target[key] = {}
            _merge_into(target[key], val, layer, prov, here, depth + 1)
        elif isinstance(val, list):
            reset = bool(val and val[0] == "!reset")
            incoming = val[1:] if reset else val
            inheritable = (not reset) and isinstance(target.get(key), list)
            merged = list(target[key]) if inheritable else []
            for item in incoming:
                if item not in merged:
                    merged.append(item)
            prev = prov.get(here)
            if inheritable and prev:
                prov[here] = {"value": merged, "source": " + ".join(filter(None, [prev["source"], layer])), "shadowed": prev["shadowed"]}
            else:
                _shadow(prov, here, merged, f"{layer} (reset)" if reset else layer)
            target[key] = merged
        else:
            _shadow(prov, here, val, layer)
            target[key] = val


def merge_config_layers(layers: List[Dict[str, Any]], warnings: Optional[List[str]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Merge lowest-to-highest layers and return `(merged_dict, provenance)`."""
    merged: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}
    warn_list = warnings if warnings is not None else []
    for item in layers:
        data = item.get("data")
        layer = str(item.get("layer") or "unknown")
        if not isinstance(data, dict):
            continue
        try:
            _merge_into(merged, data, layer, provenance)
        except ValueError as exc:
            warn_list.append(f"skipped {layer}: {exc}")
    return merged, provenance


def _nested_get(obj: Dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _nested_set(obj: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    if value is None:
        cur.pop(parts[-1], None)
    else:
        cur[parts[-1]] = value


def normalize_workspace_config(value: Dict[str, Any], warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    warn_list = warnings if warnings is not None else []
    for path, (lo, hi, is_int) in _RANGES.items():
        raw = _nested_get(value, path)
        if raw is None:
            continue
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            warn_list.append(f"ignored '{path}': {raw!r} is not a number")
            _nested_set(value, path, None)
            continue
        try:
            num = float(raw)
        except ValueError:
            warn_list.append(f"ignored '{path}': {raw!r} is not a number")
            _nested_set(value, path, None)
            continue
        if not math.isfinite(num):
            _nested_set(value, path, None)
            continue
        clamped: Any = int(min(hi, max(lo, int(num) if is_int else num))) if is_int else min(hi, max(lo, num))
        if clamped != num:
            warn_list.append(f"clamped '{path}' from {num} to {clamped} (allowed {lo}..{hi})")
        _nested_set(value, path, clamped)

    for path, allowed in _ENUMS.items():
        raw = _nested_get(value, path)
        if raw is not None and raw not in allowed:
            warn_list.append(f"ignored '{path}': {raw!r} is not one of {', '.join(allowed)}")
            _nested_set(value, path, None)
    return value


def resolve_workspace_settings(cwd: str = "", env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """Resolve full merged workspace configuration, projected settings, and provenance."""
    empty = {"settings": {}, "root": "", "provenance": {}, "warnings": [], "announced": [], "value": {}}
    root_info = find_workspace_root(cwd, env)
    root = str(root_info.get("root") or "")
    if not root:
        return empty

    root_path = Path(root)
    candidates = [
        (f"{TOML_FILE} (workspace)", root_path / TOML_FILE, root, "toml"),
        (f"{TEAM_FILE} (workspace)", root_path / CONFIG_DIR_NAME / TEAM_FILE, root, "json"),
        (f"{LOCAL_FILE} (workspace)", root_path / CONFIG_DIR_NAME / LOCAL_FILE, root, "json"),
    ]
    layers: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for layer_name, file_path, ws_root, fmt in candidates:
        res = read_workspace_file(file_path, root=ws_root, layer=layer_name, fmt=fmt)
        warnings.extend(res["warnings"])
        if res["data"]:
            layers.append({"layer": layer_name, "data": res["data"]})

    identity = resolve_workspace_identity(cwd=cwd, env=env)
    reg = read_registry_entry(root, identity=identity, env=env)
    warnings.extend(reg["warnings"])
    if reg["entry"]:
        if isinstance(reg["entry"].get("settings"), dict):
            layers.append({"layer": "registry", "data": reg["entry"]["settings"]})
        if isinstance(reg["entry"].get("peer"), dict):
            layers.append({"layer": "registry", "data": {"peer": reg["entry"]["peer"]}})

    if not layers:
        return {**empty, "root": root, "warnings": warnings}

    merged, provenance = merge_config_layers(layers, warnings)
    normalize_workspace_config(merged, warnings)
    settings = {knob: _nested_get(merged, dotted) for dotted, knob in KNOB_MAP.items() if _nested_get(merged, dotted) is not None}
    announced = [
        {"key": k, "value": v["value"], "source": v["source"]}
        for k, v in provenance.items()
        if "(workspace)" in str(v.get("source", ""))
        and (v.get("value") is False or k in ("peer.id", "peer.source") or k.startswith("bypass."))
    ]
    return {
        "settings": settings,
        "root": root,
        "provenance": provenance,
        "warnings": warnings,
        "announced": announced,
        "value": merged,
    }


def persist_workspace_peer(
    cwd: str,
    *,
    peer_id: Optional[str] = None,
    peer_source: Optional[Any] = None,
    target: str = "toml",
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    """Persist project-level peer identity/source into `.openviking.toml`, JSON layers, or local registry."""
    return persist_workspace_peer_with(
        cwd,
        read_file_fn=read_workspace_file,
        registry_dir_fn=registry_dir,
        slot_name_fn=slot_name,
        peer_id=peer_id,
        peer_source=peer_source,
        target=target,
        env=env,
    )
