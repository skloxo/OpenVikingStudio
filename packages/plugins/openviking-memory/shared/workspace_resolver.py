# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Self-contained workspace layered config and peer identity resolver for openviking-memory."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse

try:
    import tomllib as _tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    _tomllib = None  # type: ignore[assignment]

CONFIG_DIR_NAME = ".openviking"
TOML_FILE = ".openviking.toml"
TEAM_FILE = "config.json"
LOCAL_FILE = "config.local.json"
CONFIG_VERSION = 1
MAX_CONFIG_BYTES = 64 * 1024
MAX_PEER_LEN = 100

FORBIDDEN_KEYS = frozenset({
    "url", "base_url", "mcp_url", "api_key", "bearer_token", "root_api_key",
    "gateway_token", "oidc_token", "ldap_username", "ldap_password", "account",
    "account_id", "user", "user_id", "auth_mode", "extra_headers",
    "credential_source", "cli_config_file", "config_file", "baseUrl", "mcpUrl",
    "apiKey", "bearerToken", "rootApiKey", "gatewayToken", "accountId",
    "userId", "authMode", "extraHeaders", "credentialSource", "credentialPath",
    "configPath",
})
_UNSAFE_KEYS = frozenset({"__proto__", "constructor", "prototype", "__class__", "__dict__"})
_PRESETS = {"git": ["{git_remote}", "{git_root}"], "cwd": ["{cwd}"], "none": []}
_VAR_RE = re.compile(r"\{([a-z_]+)\}")


def _short_hash(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8", errors="replace")).hexdigest()[:12]


def legacy_sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(value or ""))


def sanitize_peer_id(value: str) -> str:
    raw = str(value or "").strip()
    cleaned = re.sub(r"[^a-zA-Z0-9_.@-]+", "-", raw)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-.")
    if not cleaned:
        return ""
    if "@" in cleaned:
        idx = cleaned.index("@")
        cleaned = cleaned[: idx + 1] + cleaned[idx + 1 :].replace("@", "-")
    if cleaned.startswith("ext-"):
        cleaned = f"x-{cleaned}"
    if cleaned == "__self":
        cleaned = "self"
    if cleaned in (".", ".."):
        return ""
    if len(cleaned) > MAX_PEER_LEN:
        cleaned = f"{cleaned[: MAX_PEER_LEN - 13].rstrip('-.')}-{_short_hash(raw)}"
    return cleaned


def normalize_git_remote(url: str) -> str:
    raw = str(url or "").strip()
    if not raw or re.match(r"^[A-Za-z]:[\\/]", raw):
        return ""
    scp = re.match(r"^(?:[^@/\\]+@)?([^:/\\]+):(?!\/)(.+)$", raw)
    if scp and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        host, path = scp.group(1), scp.group(2)
    else:
        try:
            parsed = urlparse(raw)
        except ValueError:
            return ""
        if parsed.scheme == "file" or not parsed.hostname:
            return ""
        host, path = parsed.hostname, parsed.path or ""
    host = host.lower().strip("[]")
    path = path.strip("/")
    if path.lower().endswith(".git"):
        path = path[:-4]
    path = path.lower().strip("/")
    return f"{host}/{path}" if host and path else ""


def _read_git_origin(common_dir: Path) -> str:
    try:
        text = (common_dir / "config").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    in_origin = False
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed[0] in ("#", ";"):
            continue
        sec = re.match(r"^\[([^\]]+)\]", trimmed)
        if sec:
            quoted = re.match(r'^remote\s+"(.*)"$', sec.group(1).strip(), re.IGNORECASE)
            in_origin = bool(quoted and quoted.group(1) == "origin")
            continue
        if in_origin:
            pair = re.match(r"^url\s*=\s*(.*)$", trimmed, re.IGNORECASE)
            if pair:
                return re.split(r"[#;]", pair.group(1), maxsplit=1)[0].strip().strip("\"'")
    return ""


def _resolve_git_dir(root: Path) -> Optional[Dict[str, str]]:
    dot_git = root / ".git"
    if not dot_git.exists():
        return None
    if dot_git.is_dir():
        return {"common_dir": str(dot_git), "kind": "repo"}
    if not dot_git.is_file():
        return None
    try:
        ptr = re.search(r"^gitdir:\s*(.+)$", dot_git.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    except OSError:
        return None
    if not ptr:
        return None
    git_dir = Path(ptr.group(1).strip())
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    try:
        common_ref = (git_dir / "commondir").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        common_ref = ""
    common_dir = (Path(common_ref) if Path(common_ref).is_absolute() else (git_dir / common_ref).resolve()) if common_ref else git_dir
    kind = "submodule" if "/.git/modules/" in (common_dir.as_posix() + "/") else ("worktree" if common_ref else "repo")
    return {"common_dir": str(common_dir), "kind": kind}


def find_workspace_root(cwd: str, env: Mapping[str, str]) -> Dict[str, Any]:
    if not str(cwd or "").strip():
        return {"root": "", "git": None, "git_root": ""}
    try:
        current = Path(cwd).resolve()
    except OSError:
        return {"root": "", "git": None, "git_root": ""}
    home_raw = str(env.get("HOME") or env.get("USERPROFILE") or "").strip()
    try:
        stop_at = Path(home_raw).resolve() if home_raw else Path.home().resolve()
    except OSError:
        stop_at = Path.home()
    fs_root = Path(current.anchor) if current.anchor else Path("/")
    if current == stop_at or current == fs_root:
        return {"root": "", "git": None, "git_root": ""}

    marked = ""
    while current and current != fs_root and current != stop_at:
        git = _resolve_git_dir(current)
        if git:
            return {"root": marked or str(current), "git": git, "git_root": str(current)}
        if not marked and (
            (current / TOML_FILE).is_file()
            or (current / CONFIG_DIR_NAME / TEAM_FILE).is_file()
            or (current / CONFIG_DIR_NAME / LOCAL_FILE).is_file()
        ):
            marked = str(current)
        if current.parent == current:
            break
        current = current.parent
    return {"root": marked, "git": None, "git_root": ""}


def _parse_toml_fallback(text: str) -> Dict[str, Any]:
    if _tomllib is not None:
        return _tomllib.loads(text)
    out: Dict[str, Any] = {}
    cur = out
    for raw_line in text.splitlines():
        line = re.split(r"(?<!\\)#", raw_line, maxsplit=1)[0].strip()
        if not line:
            continue
        sec = re.match(r"^\[([a-zA-Z0-9_.-]+)\]$", line)
        if sec:
            node = out
            for part in sec.group(1).split("."):
                node = node.setdefault(part, {})
            cur = node
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            val_s = v.strip()
            if val_s in ("true", "false"):
                cur[k.strip()] = val_s == "true"
            elif (val_s.startswith('"') and val_s.endswith('"')) or (val_s.startswith("'") and val_s.endswith("'")):
                cur[k.strip()] = val_s[1:-1]
            elif val_s.startswith("[") and val_s.endswith("]"):
                inner = val_s[1:-1].strip()
                cur[k.strip()] = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
            elif re.match(r"^[+-]?\d+$", val_s):
                cur[k.strip()] = int(val_s)
            elif re.match(r"^[+-]?\d+\.\d+$", val_s):
                cur[k.strip()] = float(val_s)
    return out


def _strip_banned(obj: Any, layer: str) -> Any:
    if isinstance(obj, list):
        return [_strip_banned(x, layer) for x in obj]
    if not isinstance(obj, dict):
        return obj
    banned = FORBIDDEN_KEYS if layer == "registry" else FORBIDDEN_KEYS | {"cli_config_profile"}
    out: Dict[str, Any] = {}
    for k, v in obj.items():
        if k in _UNSAFE_KEYS or k in banned:
            continue
        out[k] = v if k == "labels" else _strip_banned(v, layer)
    return out


def _read_layer_file(path: Path, root: Optional[Path], layer: str, fmt: str) -> Optional[Dict[str, Any]]:
    try:
        st = path.lstat()
        if not path.is_file() or st.st_size > MAX_CONFIG_BYTES:
            return None
        if root is not None:
            path.resolve().relative_to(root.resolve())
        text = path.read_text(encoding="utf-8-sig" if fmt == "json" else "utf-8")
        parsed = _parse_toml_fallback(text) if fmt == "toml" else json.loads(text)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    ver = CONFIG_VERSION if (fmt == "toml" and parsed.get("version") is None) else parsed.get("version")
    if ver != CONFIG_VERSION or isinstance(ver, bool):
        return None
    return _strip_banned(parsed, layer)


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if k in _UNSAFE_KEYS:
            continue
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        elif isinstance(v, dict):
            dst[k] = dict(v)
        elif isinstance(v, list):
            reset = bool(v and v[0] == "!reset")
            items = v[1:] if reset else v
            base = [] if reset or not isinstance(dst.get(k), list) else list(dst[k])
            for item in items:
                if item not in base:
                    base.append(item)
            dst[k] = base
        else:
            dst[k] = v


def _identity_key(info: Dict[str, Any], remote: str) -> str:
    if remote:
        return f"remote:{remote}"
    if info.get("git"):
        return f"git:{info['git']['common_dir']}"
    return "path"


def resolve_workspace_runtime(
    cwd: str = "",
    plugin_config: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
    harness: str = "antigravity",
) -> Dict[str, Any]:
    """Resolve effective peer, recall toggles, and provenance for standalone plugin runtime."""
    environ = env if env is not None else os.environ
    effective_cwd = str(cwd or environ.get("OPENVIKING_WORKSPACE") or os.getcwd())
    info = find_workspace_root(effective_cwd, environ)
    root = info["root"]
    git = info["git"]
    remote = normalize_git_remote(_read_git_origin(Path(git["common_dir"]))) if git else ""

    merged: Dict[str, Any] = {}
    if root:
        root_path = Path(root)
        for layer, fp, fmt in (
            ("toml", root_path / TOML_FILE, "toml"),
            ("team", root_path / CONFIG_DIR_NAME / TEAM_FILE, "json"),
            ("local", root_path / CONFIG_DIR_NAME / LOCAL_FILE, "json"),
        ):
            data = _read_layer_file(fp, root_path, layer, fmt)
            if data:
                _deep_merge(merged, data)

        id_key = _identity_key(info, remote)
        reg_source = root if id_key == "path" else id_key
        reg_label = id_key.rsplit("/", 1)[-1] if id_key.startswith("remote:") else root_path.name
        safe_label = re.sub(r"[^a-zA-Z0-9._-]+", "-", reg_label).strip("-")[:40]
        slot = f"{safe_label}-{_short_hash(reg_source)}.json" if safe_label else f"{_short_hash(reg_source)}.json"
        ov_home = str(environ.get("OPENVIKING_HOME") or "").strip()
        ws_dir = (Path(os.path.expanduser(ov_home)) if ov_home else Path.home() / ".openviking") / "workspaces"
        reg_data = _read_layer_file(ws_dir / slot, None, "registry", "json")
        if reg_data:
            stored = str(reg_data.get("identity") or "")
            if not stored or stored == id_key:
                if isinstance(reg_data.get("settings"), dict):
                    _deep_merge(merged, reg_data["settings"])
                if isinstance(reg_data.get("peer"), dict):
                    _deep_merge(merged, {"peer": reg_data["peer"]})

    peer_cfg = merged.get("peer") if isinstance(merged.get("peer"), dict) else {}
    recall_cfg = merged.get("recall") if isinstance(merged.get("recall"), dict) else {}
    capture_cfg = merged.get("capture") if isinstance(merged.get("capture"), dict) else {}

    ws_switch = str(environ.get("OPENVIKING_WORKSPACE_PEER") or "").strip().lower()
    env_peer_id = str(environ.get("OPENVIKING_PEER_ID") or "").strip()
    raw_actor_env = str(environ.get("OPENVIKING_ACTOR_PEER") or "").strip()
    raw_cfg_peer = str((plugin_config or {}).get("actor_peer") or "").strip()

    def _is_machine_fallback(val: str) -> bool:
        return val.startswith("antigravity@")

    explicit_env_actor = raw_actor_env if (raw_actor_env and not _is_machine_fallback(raw_actor_env)) else ""
    explicit_cfg_actor = raw_cfg_peer if (raw_cfg_peer and not _is_machine_fallback(raw_cfg_peer)) else ""
    fallback_machine_peer = raw_actor_env or raw_cfg_peer
    ws_explicit_peer = str(peer_cfg.get("id") or "").strip()

    peer_scope = str(environ.get("OPENVIKING_RECALL_PEER_SCOPE") or recall_cfg.get("peer_scope") or "all").strip()
    if peer_scope not in ("all", "actor"):
        peer_scope = "all"

    out_base = {
        "workspace_root": root,
        "recall_enabled": True if recall_cfg.get("enabled") is None else bool(recall_cfg.get("enabled")),
        "capture_enabled": True if capture_cfg.get("enabled") is None else bool(capture_cfg.get("enabled")),
        "peer_scope": peer_scope,
        "score_threshold": recall_cfg.get("score_threshold"),
    }

    chosen_explicit = env_peer_id or explicit_env_actor or ws_explicit_peer or explicit_cfg_actor
    if chosen_explicit:
        return {**out_base, "peer_id": chosen_explicit, "peer_source": "explicit", "peer_origin": "explicit", "legacy_peer_id": ""}
    if ws_switch in ("0", "false", "no", "off"):
        return {**out_base, "peer_id": "", "peer_source": "none", "peer_origin": "disabled", "legacy_peer_id": ""}

    src = environ.get("OPENVIKING_PEER_SOURCE") or peer_cfg.get("source") or "git"
    templates = [str(x) for x in src if str(x).strip()] if isinstance(src, list) else (
        _PRESETS[str(src).strip()] if str(src).strip() in _PRESETS else ([str(src).strip()] if "{" in str(src) else _PRESETS["git"])
    )
    if not templates:
        return {**out_base, "peer_id": "", "peer_source": "none", "peer_origin": "none", "legacy_peer_id": ""}

    variables = {
        "git_remote": sanitize_peer_id(remote),
        "git_root": legacy_sanitize(info["git_root"]) if git else "",
        "cwd": legacy_sanitize(effective_cwd),
        "dir": sanitize_peer_id(Path(root).name) if root else "",
        "harness": sanitize_peer_id(harness),
    }
    legacy_id = legacy_sanitize(effective_cwd)
    for tmpl in templates:
        parts_ok = True

        def _sub(match: re.Match[str]) -> str:
            nonlocal parts_ok
            v = variables.get(match.group(1), "")
            if not v:
                parts_ok = False
            return v

        rendered = _VAR_RE.sub(_sub, tmpl)
        if parts_ok and rendered:
            return {
                **out_base,
                "peer_id": rendered,
                "peer_source": "workspace",
                "peer_origin": tmpl,
                "legacy_peer_id": "" if rendered == legacy_id else legacy_id,
            }

    if fallback_machine_peer and str(src).strip() != "git":
        return {**out_base, "peer_id": fallback_machine_peer, "peer_source": "fallback", "peer_origin": "machine_default", "legacy_peer_id": legacy_id}
    return {**out_base, "peer_id": "", "peer_source": "none", "peer_origin": "unresolved", "legacy_peer_id": legacy_id}
