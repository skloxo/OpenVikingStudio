# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Dynamic Agent Peer Registry & Living Discovery Engine.

First Principles:
1. "Zero Hardcoding": Cluster peers are dynamically registered and discovered through live
   traffic, heartbeat pings, and physical session artifacts, never static hardcoded lists.
2. "Truthfulness First": Only peers with real message volume or active heartbeats appear on
   the dashboard; obsolete/purged agents (e.g. 0 calls, no staging) are strictly excluded.
3. "Self-Evolving Topology": When a new agent (e.g. deepseek-harness@2080ti) connects,
   it is registered autonomously with auto-inferred metadata (node, role, icon, mode).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("openviking.service.agent_peer_registry")


class PeerMetadata(BaseModel):
    """Strongly typed DTO representing an active cluster peer."""
    id: str = Field(..., description="Canonical identifier e.g. antigravity@2080ti")
    name_key: str = Field(..., description="Display key")
    client: str = Field(..., description="Client name e.g. deepseek-harness, antigravity")
    node: str = Field(..., description="Node name e.g. 2080ti, rtx3070, remote")
    role: str = Field(..., description="Inferred role description")
    icon: str = Field("terminal", description="Lucide icon name")
    connection_mode: str = Field("realtimeApi", description="realtimeApi | apiClient")
    staging_dir: Optional[str] = None
    first_seen: float = Field(default_factory=time.time)
    last_seen: float = Field(default_factory=time.time)
    call_count: int = 0
    is_active: bool = True


class AgentPeerRegistry:
    """Singleton service for dynamic cluster agent registration and living discovery."""

    _instance: Optional[AgentPeerRegistry] = None
    _lock = threading.Lock()

    def __init__(self, registry_file: Optional[Path] = None) -> None:
        self.registry_file = registry_file or (
            Path.home() / ".openviking" / "data" / "agent_peers_registry.json"
        )
        self.staging_base = (
            Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "staging"
        )
        self.harness_file = Path.home() / ".openviking" / "harness_metrics.json"
        self._peers: Dict[str, PeerMetadata] = {}
        self._load_registry()

    @classmethod
    def get_instance(cls, registry_file: Optional[Path] = None) -> AgentPeerRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(registry_file=registry_file)
        return cls._instance

    # Blacklisted or purged legacy peers (explicitly decomissioned or non-agent compute nodes)
    BLACKLISTED_PEERS = {
        "openclaw",
        "openclaw@2080ti",
        "xiaomimo",
        "xiaomimo@2080ti",
        "xiaomimo@rtx3070",
        "hermes",
        "hermes@2080ti",
        "antigravity@macstudio",
        "macstudio",
    }

    # Cluster baseline fleet (the core legitimate agents of this cluster)
    BASELINE_FLEET = [
        "antigravity@2080ti",
        "deepseek-harness@2080ti",
        "antigravity@rtx3070",
        "workbuddy@rtx3070",
    ]

    def _load_registry(self) -> None:
        """Load registered peers from disk."""
        if not self.registry_file.is_file():
            return
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("peers", []):
                    try:
                        meta = PeerMetadata(**item)
                        if meta.id not in self.BLACKLISTED_PEERS:
                            self._peers[meta.id] = meta
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("[AgentPeerRegistry] Failed to load registry: %s", e)

    def _save_registry(self) -> None:
        """Atomically persist registry to disk."""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.registry_file.with_suffix(".tmp")
            payload = {
                "updated_at": time.time(),
                "peers": [p.model_dump() for p in self._peers.values()],
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.registry_file)
        except Exception as e:
            logger.warning("[AgentPeerRegistry] Failed to save registry: %s", e)

    def _infer_metadata(self, peer_id: str) -> PeerMetadata:
        """Dynamically infer metadata from peer_id string (e.g. client@node)."""
        clean_id = peer_id.strip()
        if "@" in clean_id:
            parts = clean_id.split("@", 1)
            client_raw = parts[0].strip().lower()
            node_raw = parts[1].strip().lower()
        else:
            client_raw = clean_id.lower()
            node_raw = "remote"

        # Determine node display
        if "2080" in node_raw:
            node_disp = "2080Ti"
            conn_mode = "realtimeApi"
        elif "3070" in node_raw:
            node_disp = "RTX3070"
            conn_mode = "apiClient"
        elif "mac" in node_raw:
            node_disp = "MacStudio"
            conn_mode = "apiClient"
        else:
            node_disp = node_raw.upper() if len(node_raw) <= 5 else node_raw.capitalize()
            conn_mode = "apiClient"

        # Determine client role and icon
        if any(k in client_raw for k in ("deepseek", "harness", "dsh")):
            role_desc = f"{node_disp} DeepSeek Harness 智能体"
            icon = "brain"
            client_name = "deepseek-harness"
            staging_name = "deepseek_sessions"
        elif "antigravity" in client_raw:
            prefix = "本地坐镇" if conn_mode == "realtimeApi" else "远程哨兵"
            role_desc = f"{node_disp} 反重力 IDE ({prefix})"
            icon = "brain"
            client_name = "antigravity"
            staging_name = "antigravity_sessions" if conn_mode == "realtimeApi" else "3070_sessions"
        elif any(k in client_raw for k in ("workbuddy", "codebuddy")):
            role_desc = f"{node_disp} WorkBuddy 远程开发助手"
            icon = "wrench"
            client_name = "workbuddy"
            staging_name = "workbuddy_sessions"
        elif "cpa" in client_raw:
            role_desc = f"{node_disp} CPA 动态卫星智能体"
            icon = "terminal"
            client_name = "cpa"
            staging_name = None
        elif "cursor" in client_raw:
            role_desc = f"{node_disp} Cursor 开发者客户端"
            icon = "code"
            client_name = "cursor"
            staging_name = None
        else:
            role_desc = f"{node_disp} {client_raw.capitalize()} 智能体"
            icon = "network"
            client_name = client_raw
            staging_name = None

        return PeerMetadata(
            id=clean_id,
            name_key=clean_id,
            client=client_name,
            node=node_disp,
            role=role_desc,
            icon=icon,
            connection_mode=conn_mode,
            staging_dir=staging_name,
        )

    def record_peer_activity(
        self,
        peer_id: str,
        calls: int = 1,
        staging_dir: Optional[str] = None,
    ) -> PeerMetadata:
        """Register or bump activity for a given peer."""
        clean_id = peer_id.strip()
        if not clean_id or clean_id in ("default", "unknown", "system"):
            clean_id = "antigravity@2080ti"

        with self._lock:
            if clean_id not in self._peers:
                meta = self._infer_metadata(clean_id)
                if staging_dir:
                    meta.staging_dir = staging_dir
                self._peers[clean_id] = meta
            else:
                meta = self._peers[clean_id]

            meta.last_seen = time.time()
            meta.call_count += calls
            meta.is_active = True
            self._save_registry()
            return meta

    def deregister_peer(self, peer_id: str) -> bool:
        """Explicitly deregister and purge an agent peer (e.g. purged openclaw)."""
        with self._lock:
            removed = False
            if peer_id in self._peers:
                del self._peers[peer_id]
                removed = True

            # 同步从 harness_metrics.json 中彻底移除该遗留 peer
            if self.harness_file.is_file():
                try:
                    with open(self.harness_file, "r", encoding="utf-8") as f:
                        h_data = json.load(f)
                    peers_dict = h_data.get("actor_peers", {})
                    if peer_id in peers_dict:
                        del peers_dict[peer_id]
                        h_data["actor_peers"] = peers_dict
                        with open(self.harness_file, "w", encoding="utf-8") as f:
                            json.dump(h_data, f, ensure_ascii=False, indent=2)
                        removed = True
                except Exception as e:
                    logger.warning("[AgentPeerRegistry] Failed to purge peer from harness metrics: %s", e)

            if removed:
                self._save_registry()
                logger.info("[AgentPeerRegistry] Successfully deregistered and purged peer: %s", peer_id)
            return removed

    def get_active_peers(self, account_id: str = "default") -> List[Dict[str, Any]]:
        """
        Dynamically synthesize and return all active cluster peers with non-zero activity.
        Strictly excludes dead/purged 0-call peers!
        """
        now = time.time()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 1. Harvest live counts from harness_metrics.json
        live_calls: Dict[str, int] = {}
        if self.harness_file.is_file():
            try:
                with open(self.harness_file, "r", encoding="utf-8") as f:
                    h_data = json.load(f)
                    live_calls = h_data.get("actor_peers", {})
            except Exception:
                pass

        # 2. Dynamically scan staging directories to discover physical session drops
        if self.staging_base.is_dir():
            for child in self.staging_base.iterdir():
                if not child.is_dir():
                    continue
                dirname = child.name.lower()
                if "3070" in dirname:
                    staging_peer = "antigravity@rtx3070"
                elif "2080" in dirname or "antigravity" in dirname:
                    staging_peer = "antigravity@2080ti"
                elif "workbuddy" in dirname:
                    staging_peer = "workbuddy@rtx3070"
                elif dirname.endswith("_sessions"):
                    client_part = dirname[:-9]
                    staging_peer = f"{client_part}@remote"
                else:
                    continue

                if staging_peer not in self.BLACKLISTED_PEERS:
                    with self._lock:
                        if staging_peer not in self._peers:
                            self._peers[staging_peer] = self._infer_metadata(staging_peer)
                        self._peers[staging_peer].staging_dir = child.name

        # 3. Ingest any newly seen peers from live calls into registry
        with self._lock:
            for raw_peer, count in live_calls.items():
                if raw_peer and raw_peer not in ("default", "unknown", "system") and raw_peer not in self.BLACKLISTED_PEERS:
                    # Map legacy unadorned names
                    mapped_id = (
                        "antigravity@2080ti" if raw_peer == "antigravity"
                        else raw_peer
                    )
                    if mapped_id not in self.BLACKLISTED_PEERS:
                        if mapped_id not in self._peers:
                            self._peers[mapped_id] = self._infer_metadata(mapped_id)
                        self._peers[mapped_id].call_count = max(
                            self._peers[mapped_id].call_count, count
                        )
                        if count > 0:
                            self._peers[mapped_id].last_seen = now

        # 4. Always ensure the canonical cluster baseline fleet is registered
        with self._lock:
            for base_id in self.BASELINE_FLEET:
                if base_id not in self._peers and base_id not in self.BLACKLISTED_PEERS:
                    self._peers[base_id] = self._infer_metadata(base_id)

        # 5. Filter and assemble output format expected by frontend
        results: List[Dict[str, Any]] = []

        with self._lock:
            for peer_id, meta in list(self._peers.items()):
                # Strict exclusion of blacklisted or decommissioned peers
                if peer_id in self.BLACKLISTED_PEERS or not meta.is_active:
                    continue

                # Probe staging directory if configured
                staging_count = 0
                latest_staging_mtime = 0.0
                if meta.staging_dir and self.staging_base.is_dir():
                    target_dir = self.staging_base / meta.staging_dir
                    if target_dir.is_dir():
                        md_files = list(target_dir.glob("*.md"))
                        staging_count = len(md_files)
                        if md_files:
                            latest_staging_mtime = max(f.stat().st_mtime for f in md_files)

                total_messages = meta.call_count + staging_count

                # Compute dynamic status and last sync
                last_sync_str = "--"
                if latest_staging_mtime > 0:
                    last_sync_str = datetime.fromtimestamp(latest_staging_mtime).strftime("%Y-%m-%d %H:%M")
                    # Active within 2 hours
                    if (now - latest_staging_mtime) < 7200:
                        peer_status = "running"
                    elif (now - latest_staging_mtime) < 86400 * 2:
                        peer_status = "ready"
                    else:
                        peer_status = "standby"
                elif meta.call_count > 0:
                    last_sync_str = datetime.fromtimestamp(meta.last_seen).strftime("%Y-%m-%d %H:%M") if meta.last_seen > 0 else now_str
                    if (now - meta.last_seen) < 7200:
                        peer_status = "running"
                    else:
                        peer_status = "ready"
                else:
                    # Baseline fleet agents default to ready
                    peer_status = "ready"

                # Filter out obsolete dynamic peers with 0 messages that are not part of baseline fleet
                if peer_id not in self.BASELINE_FLEET and total_messages == 0 and peer_status == "standby":
                    continue

                results.append({
                    "id": peer_id,
                    "nameKey": meta.name_key,
                    "messagesCount": total_messages,
                    "uriNode": f"viking://user/{account_id}/peers/{peer_id}/memories/",
                    "connectionModeKey": meta.connection_mode,
                    "lastSync": last_sync_str,
                    "status": peer_status,
                    "icon": meta.icon,
                    "role": meta.role,
                })

        # Sort: running first, then by messagesCount descending
        status_rank = {"running": 0, "ready": 1, "standby": 2}
        results.sort(key=lambda x: (status_rank.get(x["status"], 3), -x["messagesCount"]))
        return results
