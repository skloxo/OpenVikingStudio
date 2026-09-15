# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Spec-Driven Abstract Workspace File System (AFS) & Physical Compression Whitelist.
(Card-Harness-DeepSeek-AgentScope-SpecDriven - v1.5.03)

Derived from DeepSeek-Harness & AgentScope Java 2.0:
1. Isolatability: Decouples static read-only specification assets (AGENTS.md, skills/)
   from dynamic session sandboxes (sessions/{session_id}/, MEMORY.md).
2. Physical Compression Exemption: Whitelists TaskPlan, SubAgentTracker, and AuthGrants
   from lossy context summarization and token truncation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class WorkspaceMode(str, Enum):
    """Operational mode for workspace storage access."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    SANDBOX = "sandbox"


class AbstractWorkspace(ABC):
    """Abstract interface defining the Workspace File System contract."""

    @abstractmethod
    def resolve_path(self, rel_path: str) -> Path:
        """Resolve a relative path against workspace boundaries safely."""
        pass

    @abstractmethod
    def is_read_only(self, rel_path: str) -> bool:
        """Determine if a relative path is protected as read-only."""
        pass

    @abstractmethod
    def read_text(self, rel_path: str) -> str:
        """Read content from a workspace file."""
        pass

    @abstractmethod
    def write_text(self, rel_path: str, content: str) -> None:
        """Write content into workspace sandbox. Throws PermissionError if read-only."""
        pass

    @abstractmethod
    def exists(self, rel_path: str) -> bool:
        """Check whether the path exists."""
        pass


class SpecWorkspace(AbstractWorkspace):
    """
    Guarantees Isolatability invariant.
    Decouples read-only static spec assets from session-isolated sandboxes.
    """

    READ_ONLY_PREFIXES: tuple[str, ...] = (
        "AGENTS.md",
        "BLUEPRINT.md",
        "skills/",
        ".agents/",
        "spec/",
    )

    def __init__(
        self,
        static_root: Path,
        sandbox_root: Path,
        session_id: str = "default",
    ) -> None:
        self.static_root = Path(static_root).resolve()
        self.sandbox_root = Path(sandbox_root).resolve()
        self.session_id = session_id
        self.session_dir = self.sandbox_root / "sessions" / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def is_read_only(self, rel_path: str) -> bool:
        """Check if relative path targets protected static specifications."""
        clean = rel_path.strip().lstrip("/\\")
        for ro_prefix in self.READ_ONLY_PREFIXES:
            if clean == ro_prefix or clean.startswith(ro_prefix):
                return True
        return False

    def resolve_path(self, rel_path: str) -> Path:
        """
        Resolve relative path. Static assets resolve to static_root,
        dynamic files resolve to session_dir. Traversal attempts raise ValueError.
        """
        clean = rel_path.strip().lstrip("/\\")
        if self.is_read_only(clean):
            target = (self.static_root / clean).resolve()
            if not str(target).startswith(str(self.static_root)):
                raise ValueError(f"Path traversal detected: {rel_path}")
            return target

        target = (self.session_dir / clean).resolve()
        if not str(target).startswith(str(self.session_dir)):
            raise ValueError(f"Path traversal detected: {rel_path}")
        return target

    def exists(self, rel_path: str) -> bool:
        """Check if file exists in either static root or session sandbox."""
        resolved = self.resolve_path(rel_path)
        return resolved.exists()

    def read_text(self, rel_path: str) -> str:
        """Read text from resolved path."""
        path = self.resolve_path(rel_path)
        if not path.exists():
            raise FileNotFoundError(f"Workspace file not found: {rel_path} -> {path}")
        return path.read_text(encoding="utf-8")

    def write_text(self, rel_path: str, content: str) -> None:
        """
        Write text to session sandbox.
        Strictly raises PermissionError if attempting to mutate static assets.
        """
        if self.is_read_only(rel_path):
            raise PermissionError(
                f"[SpecWorkspace Isolation Barrier] Cannot write to read-only static asset: {rel_path}"
            )
        path = self.resolve_path(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class WhitelistType(str, Enum):
    """Exemption categories protected from context compaction."""
    TASK_PLAN = "TaskPlan"
    SUBAGENT_TRACKER = "SubAgentTracker"
    AUTH_GRANTS = "AuthGrants"


@dataclass
class ProtectedPayload:
    """A strongly typed container protected from context compression."""
    payload_id: str
    whitelist_type: WhitelistType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_protected: bool = True


class CompressionWhitelist:
    """
    Guarantees Physical Compression Exemption Whitelist.
    Protects TaskPlan, SubAgentTracker, and AuthGrants from lossy compaction.
    """

    ALLOWED_WHITELIST_TYPES: Set[WhitelistType] = {
        WhitelistType.TASK_PLAN,
        WhitelistType.SUBAGENT_TRACKER,
        WhitelistType.AUTH_GRANTS,
    }

    def __init__(self) -> None:
        self._registry: Dict[str, ProtectedPayload] = {}

    @classmethod
    def is_exempt(cls, candidate_type: Any) -> bool:
        """Check if candidate type qualifies for compression exemption."""
        if isinstance(candidate_type, WhitelistType):
            return candidate_type in cls.ALLOWED_WHITELIST_TYPES
        try:
            enum_val = WhitelistType(str(candidate_type))
            return enum_val in cls.ALLOWED_WHITELIST_TYPES
        except ValueError:
            return False

    def register(
        self,
        payload_id: str,
        whitelist_type: WhitelistType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProtectedPayload:
        """Register a payload under physical compression protection."""
        if not self.is_exempt(whitelist_type):
            raise ValueError(f"Type {whitelist_type} is not an authorized whitelist type.")

        payload = ProtectedPayload(
            payload_id=payload_id,
            whitelist_type=whitelist_type,
            content=content,
            metadata=dict(metadata or {}),
            is_protected=True,
        )
        self._registry[payload_id] = payload
        return payload

    def get(self, payload_id: str) -> Optional[ProtectedPayload]:
        """Retrieve protected payload by ID."""
        return self._registry.get(payload_id)

    def filter_protected(self, payloads: List[ProtectedPayload]) -> List[ProtectedPayload]:
        """Filter and return only payloads that are actively protected."""
        return [p for p in payloads if p.is_protected and self.is_exempt(p.whitelist_type)]

    def list_by_type(self, whitelist_type: WhitelistType) -> List[ProtectedPayload]:
        """List all protected payloads of a given type."""
        return [p for p in self._registry.values() if p.whitelist_type == whitelist_type]

    def clear(self) -> None:
        """Clear the registry."""
        self._registry.clear()
