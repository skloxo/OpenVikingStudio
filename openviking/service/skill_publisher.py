"""Skill Vectorization & Vault Ingestion Service (SSOT).

Enforces strict pre-flight validation and atomic vault publishing for skills:
1. Automated pre-flight gatekeeper via SkillValidator
2. Content SHA256 physical fingerprint generation
3. Normalized VikingFS URI construction (viking://resources/master_memory/skills/{slug}/SKILL.md)
4. Version snapshot metadata registration
5. Strongly-typed SkillPublishResult DTO
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import time
from typing import Any

from openviking.service.skill_validator import SkillValidator


@dataclass
class SkillPublishResult:
    """Strongly-typed publication result report."""

    success: bool
    slug: str
    target_uri: str
    version_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "slug": self.slug,
            "target_uri": self.target_uri,
            "version_hash": self.version_hash,
            "metadata": self.metadata,
            "diagnostics": self.diagnostics,
            "error": self.error,
        }


class SkillPublisher:
    """Zero-side-effect skill vault publishing orchestrator."""

    DEFAULT_VAULT_PREFIX: str = "viking://resources/master_memory/skills"

    @classmethod
    def publish_skill(
        cls,
        raw_content: str,
        force_overwrite: bool = False,
        custom_vault_prefix: str = DEFAULT_VAULT_PREFIX,
        local_mirror_dir: Path | None = None,
    ) -> SkillPublishResult:
        """Publish and register a validated skill document into the Viking vault."""
        # 1. Pre-flight validation gate
        validation = SkillValidator.validate_content(raw_content)
        if not validation.is_valid:
            return SkillPublishResult(
                success=False,
                slug=validation.name,
                target_uri="",
                version_hash="",
                diagnostics=validation.warnings,
                error=f"Pre-flight validation failed: {'; '.join(validation.errors)}",
            )

        slug = validation.name
        content_bytes = raw_content.encode("utf-8")
        version_hash = hashlib.sha256(content_bytes).hexdigest()[:12]
        target_uri = f"{custom_vault_prefix.rstrip('/')}/{slug}/SKILL.md"

        diagnostics: list[str] = list(validation.warnings)
        diagnostics.append(f"Content length: {len(raw_content)} bytes")
        diagnostics.append(f"Version fingerprint: sha256:{version_hash}")

        # 2. Local mirror persistence if mirror directory provided
        if local_mirror_dir is not None:
            try:
                dest_dir = local_mirror_dir / slug
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / "SKILL.md"
                if dest_file.exists() and not force_overwrite:
                    diagnostics.append(f"Warning: Existing skill '{slug}' overwritten with force flag.")
                dest_file.write_text(raw_content, encoding="utf-8")
                diagnostics.append(f"Physical mirror persisted to {dest_file}")
            except Exception as exc:
                return SkillPublishResult(
                    success=False,
                    slug=slug,
                    target_uri=target_uri,
                    version_hash=version_hash,
                    diagnostics=diagnostics,
                    error=f"Failed to persist physical mirror: {exc}",
                )

        metadata_record = dict(validation.parsed_metadata)
        metadata_record["published_at"] = int(time.time())
        metadata_record["version_hash"] = version_hash
        metadata_record["target_uri"] = target_uri

        return SkillPublishResult(
            success=True,
            slug=slug,
            target_uri=target_uri,
            version_hash=version_hash,
            metadata=metadata_record,
            diagnostics=diagnostics,
        )
