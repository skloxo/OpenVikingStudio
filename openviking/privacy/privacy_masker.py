# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Dynamic Privacy Masker & Credential Sanitizer (SSOT).

Enforces Zero-Secret & Credential Isolation across skills, searches, and logs.
Provides high-performance compiled regex masks for API keys, tokens, and credentials.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional, Pattern, Union


class PrivacyMasker:
    """Thread-safe dynamic privacy masking engine."""

    _instance: Optional[PrivacyMasker] = None
    _lock = threading.Lock()

    # Pre-compiled high-performance regex patterns
    PATTERNS: List[tuple[str, Pattern, str]] = [
        # 1. API Keys (OpenAI, DeepSeek, Claude, generic sk-)
        ("openai_api_key", re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,})\b"), "sk-***[REDACTED_API_KEY]"),
        # 2. GitHub Personal Access & App Tokens
        ("github_token", re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr|github_pat)_[a-zA-Z0-9_]{20,})\b"), "ghp_***[REDACTED_TOKEN]"),
        # 3. AWS Access Key IDs
        ("aws_access_key", re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "AKIA***[REDACTED_AWS_KEY]"),
        # 4. Bearer Authorization Tokens
        ("bearer_token", re.compile(r"\b(Bearer\s+)([a-zA-Z0-9_.\-]{24,})\b", flags=re.IGNORECASE), r"\1***[REDACTED_TOKEN]"),
        # 5. Private Key blocks (RSA, EC, OPENSSH, DSA, etc.)
        (
            "private_key_block",
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
            "[REDACTED_PRIVATE_KEY_BLOCK]",
        ),
        # 6. Sensitive parameter assignments in configs/code: password, secret, token, api_key
        (
            "sensitive_assignment",
            re.compile(
                r'\b(password|passwd|secret|api_key|private_key|auth_token)\b(\s*[:=]\s*["\']?)([^"\'\s,;]{6,})(["\']?)',
                flags=re.IGNORECASE,
            ),
            r"\1\2***[REDACTED]***\4",
        ),
        # 7. Internal known node IPs / infrastructure addresses
        ("internal_ip_fwd", re.compile(r"\b8\.129\.0\.26\b"), "127.0.0.1"),
        ("tailscale_node_ip", re.compile(r"\b100\.78\.64\.128\b"), "100.x.x.x"),
    ]

    # Quick detection regex (single OR regex for fast checks)
    _DETECT_PATTERN = re.compile(
        r"(?:sk-[a-zA-Z0-9_\-]{20,}|(?:ghp|gho|ghu|ghs|ghr|github_pat)_[a-zA-Z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|\b(?:password|passwd|secret|api_key|private_key|auth_token)\b\s*[:=]\s*[\"']?[^\"'\s,;]{6,})",
        flags=re.IGNORECASE,
    )

    @classmethod
    def get_instance(cls) -> PrivacyMasker:
        """Get or initialize singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (used in test teardown)."""
        with cls._lock:
            cls._instance = None

    def mask_text(self, text: str) -> str:
        """Sanitize and mask all sensitive credentials in text."""
        if not text:
            return ""
        result = text
        for _name, pattern, replacement in self.PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def contains_sensitive(self, text: str) -> bool:
        """Fast check whether text contains any known sensitive patterns."""
        if not text:
            return False
        return bool(self._DETECT_PATTERN.search(text))

    def mask_dict(self, data: Any) -> Any:
        """Recursively mask sensitive values in dicts, lists, and strings."""
        if isinstance(data, str):
            return self.mask_text(data)
        elif isinstance(data, dict):
            masked_dict: Dict[str, Any] = {}
            for k, v in data.items():
                # If key name itself matches sensitive pattern, mask the value
                if isinstance(k, str) and re.search(
                    r"(password|passwd|secret|token|credential|api_key|private_key)",
                    k,
                    flags=re.IGNORECASE,
                ):
                    if isinstance(v, str):
                        masked_dict[k] = "***[REDACTED]***"
                    else:
                        masked_dict[k] = self.mask_dict(v)
                else:
                    masked_dict[k] = self.mask_dict(v)
            return masked_dict
        elif isinstance(data, list):
            return [self.mask_dict(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self.mask_dict(item) for item in data)
        return data


def get_privacy_masker() -> PrivacyMasker:
    """Convenience helper to retrieve singleton PrivacyMasker."""
    return PrivacyMasker.get_instance()


def mask_text(text: str) -> str:
    """Convenience helper to mask text using singleton PrivacyMasker."""
    return get_privacy_masker().mask_text(text)
