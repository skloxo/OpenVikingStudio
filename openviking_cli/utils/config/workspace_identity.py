# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Workspace identity: zero-subprocess root discovery and Git normalization."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse

CONFIG_DIR_NAME = ".openviking"
TOML_FILE = ".openviking.toml"
TEAM_FILE = "config.json"
LOCAL_FILE = "config.local.json"

IDENTITY_CACHE_TTL_MS = 60_000
MAX_PEER_ID_LENGTH = 100

_NO_ROOT: Dict[str, Any] = {
    "root": "",
    "root_kind": "",
    "git": None,
    "git_root": "",
}


def _short_hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:12]


def state_dir(env: Optional[Mapping[str, str]] = None) -> Path:
    """Resolve OpenViking runtime state directory for short-TTL identity caches."""
    environ = env if env is not None else os.environ
    explicit = str(environ.get("OPENVIKING_STATE_DIR") or "").strip()
    if explicit:
        return Path(explicit)
    ov_home = str(environ.get("OPENVIKING_HOME") or "").strip()
    if ov_home:
        base = Path(os.path.expanduser(ov_home))
    else:
        base = Path.home() / ".openviking"
    return base / "state"


def legacy_sanitize(value: Optional[str]) -> str:
    """Byte-for-byte legacy path sanitation (matches `cwd.replace(/[^A-Za-z0-9]/g, '-')`)."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(value or ""))


def sanitize_peer_id(value: Optional[str]) -> str:
    """Sanitize normalized remotes, workspace directory names, or harness names."""
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
    if len(cleaned) > MAX_PEER_ID_LENGTH:
        prefix = cleaned[: MAX_PEER_ID_LENGTH - 13].rstrip("-.")
        cleaned = f"{prefix}-{_short_hash(raw)}"
    return cleaned


def normalize_git_remote(url: Optional[str]) -> str:
    """Normalize a Git remote URL to lowercase `host/path` stripping tokens and `.git`."""
    raw = str(url or "").strip()
    if not raw or re.match(r"^[A-Za-z]:[\\/]", raw):
        return ""

    host = ""
    path = ""
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
        host = parsed.hostname
        path = parsed.path or ""

    host = host.lower().strip("[]")
    path = path.strip("/")
    if path.lower().endswith(".git"):
        path = path[:-4]
    path = path.lower().strip("/")
    if not host or not path:
        return ""
    return f"{host}/{path}"


def _read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_git_remote_url(common_dir: str | Path, remote: str = "origin") -> str:
    """Read `[remote "<remote>"] url` from `<common_dir>/config` with zero subprocesses."""
    text = _read_text_or_empty(Path(common_dir) / "config")
    if not text:
        return ""

    in_section = False
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#") or trimmed.startswith(";"):
            continue
        section_match = re.match(r"^\[([^\]]+)\]", trimmed)
        if section_match:
            header = section_match.group(1).strip()
            quoted = re.match(r'^remote\s+"(.*)"$', header, re.IGNORECASE)
            in_section = bool(quoted and quoted.group(1) == remote)
            continue
        if not in_section:
            continue
        pair = re.match(r"^url\s*=\s*(.*)$", trimmed, re.IGNORECASE)
        if pair:
            raw_val = re.split(r"[#;]", pair.group(1), maxsplit=1)[0].strip()
            return raw_val.strip("\"'")
    return ""


def resolve_git_dir(root: str | Path) -> Optional[Dict[str, str]]:
    """Inspect `<root>/.git` without spawning git, converging linked worktrees."""
    root_path = Path(root)
    dot_git = root_path / ".git"
    if not dot_git.exists():
        return None
    if dot_git.is_dir():
        return {"git_dir": str(dot_git), "common_dir": str(dot_git), "kind": "repo"}
    if not dot_git.is_file():
        return None

    content = _read_text_or_empty(dot_git)
    pointer = re.search(r"^gitdir:\s*(.+)$", content, re.MULTILINE)
    if not pointer:
        return None
    git_dir = Path(pointer.group(1).strip())
    if not git_dir.is_absolute():
        git_dir = (root_path / git_dir).resolve()

    common_ref = _read_text_or_empty(git_dir / "commondir").strip()
    if common_ref:
        common_path = Path(common_ref)
        common_dir = common_path if common_path.is_absolute() else (git_dir / common_path).resolve()
    else:
        common_dir = git_dir

    normalized_common = common_dir.as_posix() + "/"
    if "/.git/modules/" in normalized_common:
        kind = "submodule"
    elif common_ref:
        kind = "worktree"
    else:
        kind = "repo"
    return {"git_dir": str(git_dir), "common_dir": str(common_dir), "kind": kind}


def has_workspace_marker(dir_path: Path) -> bool:
    """Return True if a directory explicitly marks itself via `.openviking.toml` or `.openviking/config*.json`."""
    try:
        if (dir_path / TOML_FILE).is_file():
            return True
        for name in (TEAM_FILE, LOCAL_FILE):
            if (dir_path / CONFIG_DIR_NAME / name).is_file():
                return True
    except OSError:
        return False
    return False


def _canonical_path(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return Path(os.path.abspath(str(path)))


def find_workspace_root(cwd: str | Path, env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """Walk upward from `cwd` to locate the nearest git repo or marked workspace root."""
    start = str(cwd or "").strip()
    if not start:
        return dict(_NO_ROOT)

    environ = env if env is not None else os.environ
    current = _canonical_path(Path(start))
    home_raw = str(environ.get("HOME") or environ.get("USERPROFILE") or "").strip()
    stop_at = _canonical_path(Path(home_raw)) if home_raw else _canonical_path(Path.home())
    fs_root = Path(current.anchor) if current.anchor else Path("/")

    if current == stop_at or current == fs_root:
        return dict(_NO_ROOT)

    found_root = ""
    found_kind = ""
    while current and current != fs_root and current != stop_at:
        git = resolve_git_dir(current)
        if git:
            return {
                "root": found_root or str(current),
                "root_kind": found_kind or "git",
                "git": git,
                "git_root": str(current),
            }
        if not found_root and has_workspace_marker(current):
            found_root = str(current)
            found_kind = "config"
        parent = current.parent
        if parent == current:
            break
        current = parent

    if found_root:
        return {"root": found_root, "root_kind": found_kind, "git": None, "git_root": ""}
    return dict(_NO_ROOT)


def _identity_cache_path(cwd: str, env: Optional[Mapping[str, str]]) -> Path:
    return state_dir(env) / f"ws-identity-{_short_hash(cwd)}.json"


def _read_identity_cache(path: Path, now_ms: float) -> Optional[Dict[str, Any]]:
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        ts = cached.get("ts")
        if not isinstance(ts, (int, float)) or ts > now_ms or (now_ms - ts) > IDENTITY_CACHE_TTL_MS:
            return None
        identity = cached.get("identity")
        if isinstance(identity, dict) and isinstance(identity.get("vars"), dict):
            return identity
    except Exception:
        return None
    return None


def _write_identity_cache(path: Path, identity: Dict[str, Any], now_ms: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"ts": now_ms, "identity": identity}), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(path)
    except OSError:
        pass


def identity_key(identity: Optional[Mapping[str, Any]]) -> str:
    """Return canonical key used for user-registry negative-evidence validation."""
    if not identity:
        return "path"
    remote = str(identity.get("remote") or "").strip()
    if remote:
        return f"remote:{remote}"
    if identity.get("is_git"):
        return f"git:{identity.get('git_common_dir') or ''}"
    return "path"


def resolve_workspace_identity(
    cwd: str = "",
    env: Optional[Mapping[str, str]] = None,
    cache: bool = True,
    now_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute workspace root, normalized remote, and peer substitution variables."""
    key = str(cwd or "")
    current_ms = float(now_ms) if now_ms is not None else time.time() * 1000.0
    cache_file = _identity_cache_path(key, env)
    if cache and key:
        hit = _read_identity_cache(cache_file, current_ms)
        if hit is not None:
            # Self-heal if `.git` was initialized after a non-git cache entry was written.
            if not hit.get("is_git") and hit.get("root") and (Path(hit["root"]) / ".git").exists():
                hit = None
            if hit is not None:
                return hit

    info = find_workspace_root(key, env)
    git = info.get("git")
    git_root = info.get("git_root", "")
    root = info.get("root", "")
    remote = normalize_git_remote(read_git_remote_url(git["common_dir"])) if git else ""
    dir_name = Path(root).name if root else ""

    identity: Dict[str, Any] = {
        "cwd": key,
        "root": root,
        "root_kind": info.get("root_kind", ""),
        "is_git": bool(git),
        "git_kind": git["kind"] if git else "",
        "git_common_dir": git["common_dir"] if git else "",
        "git_root": git_root,
        "remote": remote,
        "vars": {
            "git_remote": sanitize_peer_id(remote),
            "git_root": legacy_sanitize(git_root) if git else "",
            "cwd": legacy_sanitize(key),
            "dir": sanitize_peer_id(dir_name) if root else "",
        },
    }
    if cache and key:
        _write_identity_cache(cache_file, identity, current_ms)
    return identity
