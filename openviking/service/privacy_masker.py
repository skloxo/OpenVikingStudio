"""Privacy Governance & Sensitive Credential Masking Engine (SSOT).

Provides high-performance, deterministic redaction of sensitive credentials,
API keys, authorization bearer tokens, and connection secrets before they
are dispatched to cluster agents or rendered on observability UIs.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final, Sequence

# High-precision sensitive patterns for LLM agent environments
OPENAI_KEY_PATTERN: Final[re.Pattern] = re.compile(
    r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_\-]{20,}\b"
)
GITHUB_TOKEN_PATTERN: Final[re.Pattern] = re.compile(
    r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"
)
JWT_BEARER_PATTERN: Final[re.Pattern] = re.compile(
    r"\bBearer\s+(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}(?:\.[A-Za-z0-9_\-]+)?)\b",
    re.IGNORECASE,
)
URI_PASSWORD_PATTERN: Final[re.Pattern] = re.compile(
    r"((?:postgres(?:ql)?|mysql|mongodb|redis|amqp):\/\/[^:\s/]+:)([^@\s/]+)(@)",
    re.IGNORECASE,
)
PRIVATE_IP_PORT_PATTERN: Final[re.Pattern] = re.compile(
    r"\b((?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}):\d{2,5})\b"
)


@dataclass(frozen=True)
class SensitiveFinding:
    """Strongly-typed DTO representing a discovered sensitive credential."""

    category: str
    redacted_preview: str
    start: int
    end: int


class PrivacyMasker:
    """Zero-dependency, synchronous sensitive information redaction engine."""

    @classmethod
    def mask_text(cls, text: str, *, mask_private_endpoints: bool = False) -> str:
        """Redacts all detected sensitive credentials in the provided text string.

        Args:
            text: Raw input text.
            mask_private_endpoints: If True, also redacts RFC1918 private IP:Port endpoints.

        Returns:
            Sanitized text safe for cluster agent dispatch and Web UI telemetry.
        """
        if not text:
            return text

        # 1. Redact OpenAI / Anthropic / Generic API keys
        sanitized = OPENAI_KEY_PATTERN.sub("sk-***[MASKED]***", text)

        # 2. Redact GitHub personal access tokens
        sanitized = GITHUB_TOKEN_PATTERN.sub("ghp_***[MASKED]***", sanitized)

        # 3. Redact JWT Bearer tokens
        sanitized = JWT_BEARER_PATTERN.sub(
            lambda m: f"Bearer eyJ***[MASKED]***{m.group(1)[-4:] if len(m.group(1)) > 8 else ''}",
            sanitized,
        )

        # 4. Redact database URI passwords
        sanitized = URI_PASSWORD_PATTERN.sub(r"\1***[PASSWORD_MASKED]***\3", sanitized)

        # 5. Optional private endpoint masking
        if mask_private_endpoints:
            sanitized = PRIVATE_IP_PORT_PATTERN.sub(
                r"***.***.***.***:***", sanitized
            )

        return sanitized

    @classmethod
    def contains_sensitive(cls, text: str, *, check_endpoints: bool = False) -> bool:
        """Checks whether the text contains any high-confidence sensitive credential."""
        if not text:
            return False

        if (
            OPENAI_KEY_PATTERN.search(text)
            or GITHUB_TOKEN_PATTERN.search(text)
            or JWT_BEARER_PATTERN.search(text)
            or URI_PASSWORD_PATTERN.search(text)
        ):
            return True

        if check_endpoints and PRIVATE_IP_PORT_PATTERN.search(text):
            return True

        return False

    @classmethod
    def scan_findings(
        cls, text: str, *, include_endpoints: bool = False
    ) -> Sequence[SensitiveFinding]:
        """Scans and extracts all sensitive finding ranges and categories."""
        findings: list[SensitiveFinding] = []
        if not text:
            return findings

        # OpenAI keys
        for match in OPENAI_KEY_PATTERN.finditer(text):
            raw = match.group()
            preview = f"{raw[:6]}...{raw[-4:]}"
            findings.append(
                SensitiveFinding("api_key", preview, match.start(), match.end())
            )

        # GitHub tokens
        for match in GITHUB_TOKEN_PATTERN.finditer(text):
            raw = match.group()
            preview = f"{raw[:4]}...{raw[-4:]}"
            findings.append(
                SensitiveFinding("github_token", preview, match.start(), match.end())
            )

        # JWT Bearer
        for match in JWT_BEARER_PATTERN.finditer(text):
            findings.append(
                SensitiveFinding(
                    "jwt_bearer", "Bearer eyJ...[MASKED]", match.start(), match.end()
                )
            )

        # URI Password
        for match in URI_PASSWORD_PATTERN.finditer(text):
            findings.append(
                SensitiveFinding(
                    "uri_password", "***[MASKED]***", match.start(2), match.end(2)
                )
            )

        # Endpoints
        if include_endpoints:
            for match in PRIVATE_IP_PORT_PATTERN.finditer(text):
                findings.append(
                    SensitiveFinding(
                        "private_endpoint",
                        "***.***:***",
                        match.start(),
                        match.end(),
                    )
                )

        return findings


# Module-level convenient pure functions
def mask_sensitive_text(text: str, *, mask_private_endpoints: bool = False) -> str:
    """Convenience functional wrapper for PrivacyMasker.mask_text."""
    return PrivacyMasker.mask_text(
        text, mask_private_endpoints=mask_private_endpoints
    )


def contains_sensitive_data(text: str) -> bool:
    """Convenience functional wrapper for PrivacyMasker.contains_sensitive."""
    return PrivacyMasker.contains_sensitive(text)
