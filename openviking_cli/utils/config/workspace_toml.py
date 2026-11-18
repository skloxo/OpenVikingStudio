# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TOML parsing, serialization, and peer persistence helpers for workspace configs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from .workspace_identity import (
    CONFIG_DIR_NAME,
    LOCAL_FILE,
    TEAM_FILE,
    TOML_FILE,
    find_workspace_root,
    identity_key,
    resolve_workspace_identity,
    state_dir,
)

try:
    import tomllib as _tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    try:
        import tomli as _tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        _tomllib = None  # type: ignore[assignment]

CONFIG_VERSION = 1


def _strip_inline_comment(line: str) -> str:
    in_quote: Optional[str] = None
    escaped = False
    for idx, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_quote == '"':
            escaped = True
            continue
        if ch in ('"', "'"):
            if in_quote == ch:
                in_quote = None
            elif in_quote is None:
                in_quote = ch
        elif ch == "#" and in_quote is None:
            return line[:idx]
    return line


def _parse_toml_scalar(raw: str) -> Any:
    val = raw.strip()
    if val in ("true", "false"):
        return val == "true"
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        inner = val[1:-1]
        if val.startswith('"'):
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    if val.startswith("[") and val.endswith("]"):
        body = val[1:-1].strip()
        return [_parse_toml_scalar(item) for item in body.split(",") if item.strip()] if body else []
    if re.match(r"^[+-]?\d+$", val):
        return int(val)
    if re.match(r"^[+-]?\d+\.\d+$", val):
        return float(val)
    raise ValueError(f"Unsupported TOML scalar: {raw!r}")


def parse_toml_safely(text: str) -> Dict[str, Any]:
    """Parse TOML without expanding `${VAR}` environment references."""
    if _tomllib is not None:
        return _tomllib.loads(text)
    result: Dict[str, Any] = {}
    current = result
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        cleaned = _strip_inline_comment(lines[idx]).strip()
        idx += 1
        if not cleaned:
            continue
        sec = re.match(r"^\[([a-zA-Z0-9_.-]+)\]$", cleaned)
        if sec:
            node = result
            for part in sec.group(1).split("."):
                node = node.setdefault(part, {})
            current = node
            continue
        if "=" not in cleaned:
            raise ValueError(f"Invalid TOML line: {cleaned}")
        key, val_part = cleaned.split("=", 1)
        val_str = val_part.strip()
        while val_str.startswith("[") and not val_str.endswith("]") and idx < len(lines):
            val_str += " " + _strip_inline_comment(lines[idx]).strip()
            idx += 1
        current[key.strip().strip("\"'")] = _parse_toml_scalar(val_str)
    return result


def _render_toml_value(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        return "[" + ", ".join(_render_toml_value(x) for x in val) + "]"
    return json.dumps(str(val), ensure_ascii=False)


def dump_simple_toml(data: Dict[str, Any]) -> str:
    """Serialize flat + single-section workspace configuration dicts into TOML."""
    lines: List[str] = []
    scalars = [(k, v) for k, v in data.items() if not isinstance(v, dict)]
    sections = [(k, v) for k, v in data.items() if isinstance(v, dict)]
    for k, v in scalars:
        lines.append(f"{k} = {_render_toml_value(v)}")
    for sec, body in sections:
        if lines:
            lines.append("")
        lines.append(f"[{sec}]")
        for k, v in body.items():
            if not isinstance(v, dict):
                lines.append(f"{k} = {_render_toml_value(v)}")
    return "\n".join(lines) + "\n"


def persist_workspace_peer_with(
    cwd: str,
    *,
    read_file_fn: Callable[..., Dict[str, Any]],
    registry_dir_fn: Callable[[Optional[Mapping[str, str]]], Path],
    slot_name_fn: Callable[[str, Optional[Mapping[str, Any]]], str],
    peer_id: Optional[str] = None,
    peer_source: Optional[Any] = None,
    target: str = "toml",
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    """Write peer configuration to `.openviking.toml`, JSON layers, or machine registry."""
    if not peer_id and peer_source is None:
        raise ValueError("Either peer_id or peer_source must be provided")

    try:
        for fp in state_dir(env).glob("ws-identity-*.json"):
            fp.unlink(missing_ok=True)
    except OSError:
        pass

    root_info = find_workspace_root(cwd, env)
    root_path = Path(root_info["root"] or os.path.abspath(cwd))
    identity = resolve_workspace_identity(cwd=str(root_path), env=env, cache=False)

    peer_patch: Dict[str, Any] = {}
    if peer_id:
        peer_patch["id"] = str(peer_id).strip()
    if peer_source is not None:
        peer_patch["source"] = peer_source

    if target == "registry":
        dest = registry_dir_fn(env) / slot_name_fn(str(root_path), identity)
        dest.parent.mkdir(parents=True, exist_ok=True)
        existing = read_file_fn(dest, layer="registry").get("data") or {}
        existing.update({"version": CONFIG_VERSION, "identity": identity_key(identity), "root": str(root_path)})
        existing["peer"] = {**(existing.get("peer") if isinstance(existing.get("peer"), dict) else {}), **peer_patch}
        tmp = dest.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(dest)
        return dest

    if target == "toml":
        dest = root_path / TOML_FILE
        existing = read_file_fn(dest, root=root_path, fmt="toml").get("data") or {}
        payload = {"version": CONFIG_VERSION, **existing}
        payload["peer"] = {**(payload.get("peer") if isinstance(payload.get("peer"), dict) else {}), **peer_patch}
        dest.write_text(dump_simple_toml(payload), encoding="utf-8")
        return dest

    if target in ("json", "local"):
        filename = TEAM_FILE if target == "json" else LOCAL_FILE
        dest = root_path / CONFIG_DIR_NAME / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        existing = read_file_fn(dest, root=root_path, fmt="json").get("data") or {}
        payload = {"version": CONFIG_VERSION, **existing}
        payload["peer"] = {**(payload.get("peer") if isinstance(payload.get("peer"), dict) else {}), **peer_patch}
        dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return dest

    raise ValueError(f"Unsupported persistence target: {target!r}")
