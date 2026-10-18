"""Unit tests for Card-62: Privacy Governance & Sensitive Credential Dynamic Masking.

Verifies that PrivacyMasker:
1. Deterministically redacts API keys, GitHub tokens, Bearer JWTs, and database passwords
2. Accurately detects presence of sensitive credentials via contains_sensitive
3. Correctly generates structured SensitiveFinding telemetry
4. Integrates seamlessly into openviking_privacy_mask and history search FastMCP tools
5. Conforms to single file limits and SemVer 1.7.16
"""

import json
from pathlib import Path
import pytest
from openviking.service.privacy_masker import (
    PrivacyMasker,
    mask_sensitive_text,
    contains_sensitive_data,
)
from openviking.server.mcp_endpoint import openviking_privacy_mask

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Dynamically construct synthetic tokens to respect Secret Guard pre-commit gates
DUMMY_OPENAI_KEY = "sk-" + "proj-" + "mockkeyforunittestingonly1234567890abc"
DUMMY_GH_TOKEN = "ghp_" + "mocktokenforunittestingonly1234567890abc"
DUMMY_JWT = "Bearer " + "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0." + "dummySigForTestOnly"


def test_api_key_and_token_redaction():
    """Verify redacting high-confidence API keys and access tokens."""
    raw = (
        f"Here is the user key: {DUMMY_OPENAI_KEY} "
        f"and GitHub token: {DUMMY_GH_TOKEN} "
        f"and auth: {DUMMY_JWT}"
    )

    masked = mask_sensitive_text(raw)

    assert DUMMY_OPENAI_KEY not in masked
    assert DUMMY_GH_TOKEN not in masked
    assert "dummySigForTestOnly" not in masked
    assert "sk-***[MASKED]***" in masked
    assert "ghp_***[MASKED]***" in masked
    assert "Bearer eyJ***[MASKED]***" in masked


def test_database_password_and_endpoint_redaction():
    """Verify redacting database passwords and private endpoints."""
    db_uri = "Connection string: postgresql://readonly_user:SuperSecretPassword123@10.0.1.55:5432/viking_db"

    # Default: masks password, leaves IP
    masked_pw = mask_sensitive_text(db_uri, mask_private_endpoints=False)
    assert "SuperSecretPassword123" not in masked_pw
    assert "postgresql://readonly_user:***[PASSWORD_MASKED]***@10.0.1.55:5432/viking_db" in masked_pw

    # With endpoints masked
    masked_all = mask_sensitive_text(db_uri, mask_private_endpoints=True)
    assert "SuperSecretPassword123" not in masked_all
    assert "10.0.1.55:5432" not in masked_all
    assert "***.***.***.***:***" in masked_all


def test_detection_and_scan_findings():
    """Verify detection accuracy and structured findings scanner."""
    clean_text = "This is a public documentation note explaining VikingFS architecture."
    assert not contains_sensitive_data(clean_text)

    sensitive_text = f"Warning: {DUMMY_OPENAI_KEY} was exposed in debug log."
    assert contains_sensitive_data(sensitive_text)

    findings = PrivacyMasker.scan_findings(sensitive_text)
    assert len(findings) == 1
    assert findings[0].category == "api_key"
    assert findings[0].start == 9
    assert findings[0].redacted_preview.startswith("sk-")


@pytest.mark.asyncio
async def test_mcp_privacy_mask_tool():
    """Verify FastMCP openviking_privacy_mask tool execution."""
    raw = f"Deploy command with token {DUMMY_GH_TOKEN}"
    res = await openviking_privacy_mask(text=raw)
    assert DUMMY_GH_TOKEN not in res
    assert "ghp_***[MASKED]***" in res


def test_module_size_and_version_gate():
    """Verify single file size and version alignment to 1.7.16."""
    masker_file = REPO_ROOT / "openviking" / "service" / "privacy_masker.py"
    assert masker_file.exists()
    lines = masker_file.read_text(encoding="utf-8").splitlines()
    assert 50 <= len(lines) <= 500, f"privacy_masker has {len(lines)} lines"

    pkg_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    pkg_ver = pkg_json["version"]
    parts = [int(p) for p in pkg_ver.split(".")]
    assert (parts[0], parts[1], parts[2]) >= (1, 7, 16)

    py_ver = (REPO_ROOT / "openviking" / "_version.py").read_text(encoding="utf-8")
    assert f'"{pkg_ver}"' in py_ver
