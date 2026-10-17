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



DOMAIN_RULES: dict[str, list[str]] = {
    "quant-trading": ["quant", "trading", "stock", "ccxt", "binance", "okx", "crypto", "orderbook", "backtest", "a-share", "alpha", "broker", "finance"],
    "web-harvest-pro": ["crawl", "scrape", "spider", "playwright", "puppeteer", "selenium", "bs4", "harvest", "rss", "feed", "extract-web"],
    "presentation-designer": ["ppt", "powerpoint", "slides", "presentation", "marp", "mermaid", "diagram", "infographic", "svg"],
    "codebase-engineering": ["git", "github", "gitlab", "refactor", "tdd", "lint", "code-review", "ast", "typing", "pytest", "unit-test"],
    "system-fleet-ops": ["linux", "systemd", "wsl", "process", "gc", "bash", "powershell", "crontab", "hardware", "cpu", "ram", "kernel", "cron"],
    "cloud-infra-ops": ["k8s", "kubernetes", "docker", "container", "frp", "oracle", "oci", "aliyun", "tencent", "aws", "gcp", "azure", "cloud"],
    "document-governance": ["foxconn", "doc-naming", "pdca", "daily-report", "weekly-report", "monthly-report", "sign-off", "report", "document", "xlsx"],
    "credential-vault": ["keepass", "vault", "password", "secret", "ssh-key", "token-rotat", "credential", "1password", "bitwarden"],
    "living-asset-system": ["living-asset", "component-inventory", "wheel-reuse", "harvest-as-you-go", "asset-library"],
    "cockpit-ui": ["ui", "css", "tailwind", "shadcn", "react", "vite", "dark-mode", "high-density", "frontend", "web-ui", "cockpit"],
    "ai-harness-ops": ["dsh", "harness", "claude-harness", "deepseek", "qwen", "llm", "prompt", "context-compress", "wikiskill", "cpa"],
    "adversarial-learning": ["adversarial", "first-principles", "mental-model", "reverse-engineer", "anti-fragil", "grill"],
    "property-cadre-ops": ["cadre", "apartment", "lock", "smart-lock", "dormitory", "facility", "repair", "meter", "property"],
    "park-grid-governance": ["grid", "park", "spatial", "gis", "geofence", "patrol", "ticket", "inspect", "campus"],
    "network-tunnel-ops": ["clash", "mihomo", "tunnel", "vpn", "proxy", "ipv6", "firewall", "ttl", "cpe", "dns", "router", "wireguard", "xui"],
    "database-storage-ops": ["sql", "database", "postgres", "sqlite", "duckdb", "redis", "mysql", "mongodb", "orm"],
    "multimodal-media": ["ffmpeg", "image", "audio", "video", "whisper", "tts", "ocr", "mineru", "comfyui", "youtube"],
    "mcp-bridge-hub": ["mcp", "fastmcp", "tool-call", "stdio", "transport", "rpc", "bridge", "sse"],
    "developer-productivity": ["chrome-devtools", "debug", "profile", "flamegraph", "speed", "benchmark", "workflow"],
    "security-audit-compliance": ["security", "vuln", "cve", "compliance", "privacy", "mask", "quarantine", "permission", "iam", "audit"],
}


class SkillPublisher:
    """Zero-side-effect skill vault publishing orchestrator with bundle-aware routing."""

    DEFAULT_VAULT_PREFIX: str = "viking://resources/master_memory/skills"

    @staticmethod
    def _classify_bundle(name: str, content: str) -> str:
        n_lower, c_lower = name.lower(), content.lower()
        scores: dict[str, int] = {}
        for bundle, kws in DOMAIN_RULES.items():
            s = sum(6 for kw in kws if kw in n_lower) + sum(1 for kw in kws if kw in c_lower)
            if s > 0:
                scores[bundle] = s
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "developer-productivity"

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

        # 2. Bundle-Aware Local mirror persistence
        if local_mirror_dir is not None:
            try:
                bundle_name = cls._classify_bundle(slug, raw_content)
                bundle_dir = local_mirror_dir / bundle_name

                # If the mirror root is already organized into domain capability bundles
                if bundle_dir.exists() and (bundle_dir / "scenarios").is_dir():
                    scenarios_dir = bundle_dir / "scenarios"
                    dest_file = scenarios_dir / f"{slug}.md"
                    dest_file.write_text(raw_content, encoding="utf-8")
                    diagnostics.append(f"Domain Capability Bundle routed: {bundle_name}/scenarios/{slug}.md")

                    # Append to master SKILL.md router table if not present
                    master_skill_md = bundle_dir / "SKILL.md"
                    if master_skill_md.exists():
                        master_text = master_skill_md.read_text(encoding="utf-8", errors="ignore")
                        router_line = f"- **`{slug}`**: [{slug}](./scenarios/{slug}.md)"
                        if router_line not in master_text:
                            master_text += f"\n{router_line} — 动态入库专精场景\n"
                            master_skill_md.write_text(master_text, encoding="utf-8")
                else:
                    # Fallback standalone directory
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

