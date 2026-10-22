# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
openviking.service.privacy_masker

Forwarding facade to the unified SSOT PrivacyMasker in openviking.privacy.privacy_masker.
Maintains 100% backward compatibility for all existing imports.
"""

from __future__ import annotations

from typing import Sequence

from openviking.privacy.privacy_masker import (
    PrivacyMasker as _UnifiedPrivacyMasker,
    SensitiveFinding,
    get_privacy_masker,
    mask_text,
    contains_sensitive_data,
)


class PrivacyMasker:
    """Facade for the unified SSOT PrivacyMasker supporting classmethod invocation."""

    @classmethod
    def mask_text(cls, text: str, *, mask_private_endpoints: bool = False) -> str:
        """Redacts all detected sensitive credentials in the provided text string."""
        return _UnifiedPrivacyMasker.get_instance().mask_text(
            text, mask_private_endpoints=mask_private_endpoints
        )

    @classmethod
    def contains_sensitive(cls, text: str, *, check_endpoints: bool = False) -> bool:
        """Checks whether the text contains any high-confidence sensitive credential."""
        return _UnifiedPrivacyMasker.get_instance().contains_sensitive(text)

    @classmethod
    def scan_findings(
        cls, text: str, *, include_endpoints: bool = False
    ) -> Sequence[SensitiveFinding]:
        """Scans and extracts all sensitive finding ranges and categories."""
        return _UnifiedPrivacyMasker.get_instance().scan_findings(
            text, include_endpoints=include_endpoints
        )


def mask_sensitive_text(text: str, *, mask_private_endpoints: bool = False) -> str:
    """Convenience functional wrapper for PrivacyMasker.mask_text."""
    return PrivacyMasker.mask_text(text, mask_private_endpoints=mask_private_endpoints)


__all__ = [
    "PrivacyMasker",
    "SensitiveFinding",
    "mask_sensitive_text",
    "contains_sensitive_data",
    "get_privacy_masker",
    "mask_text",
]
