# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit test suite for Card-94: Deterministic Ingestion Gatekeeper & Static Environment Verifier."""

from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.skill_ingestion import router
from openviking.service.skill_ingestion_validator import (
    SkillIngestionValidator,
    ValidationReceipt,
    ValidationSeverity,
)
from openviking_cli.session.user_id import UserIdentifier


VALID_SKILL_V2 = """---
name: feishu-bitable-record-sync
version: 1.0.0
domain: feishu-suite
description: 飞书多维表格单条与批量记录同步与字段写入。
prerequisites:
  cli: [python3]
  env: [FEISHU_APP_ID]
triggers:
  - "同步飞书多维表格"
  - "写入多维表格记录"
  - "bitable record sync"
allowed-tools:
  - openviking_find
  - openviking_read
---

# 飞书多维表格同步 SOP

## 1. 前置检查
检查环境变量是否配置。

```python
# 安全代码
def process_data(records):
    return [r for r in records if r]
```

## 4. 输入输出与交付物契约
- Input: records list
- Output: status ok
"""


@pytest.fixture
def validator() -> SkillIngestionValidator:
    return SkillIngestionValidator()


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    mock_ctx = RequestContext(
        user=UserIdentifier(account_id="test", user_id="test_admin"),
        role=Role(Role.ADMIN),
    )
    app.dependency_overrides[get_request_context] = lambda: mock_ctx
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Unit Tests: SkillIngestionValidator
# ---------------------------------------------------------------------------

def test_valid_skill_v2_passes(validator: SkillIngestionValidator):
    with patch("shutil.which", return_value="/usr/bin/python3"), \
         patch.dict("os.environ", {"FEISHU_APP_ID": "cli_12345"}):
        receipt = validator.validate(VALID_SKILL_V2)
        assert receipt.is_valid is True
        assert receipt.status == "APPROVED"
        assert len(receipt.critical_violations) == 0
        assert receipt.latency_ms > 0


def test_missing_frontmatter_rejected(validator: SkillIngestionValidator):
    raw_md = "# Raw Title\nNo YAML header at all."
    receipt = validator.validate(raw_md)
    assert receipt.is_valid is False
    assert receipt.status == "REJECTED"
    assert any("YAML Frontmatter" in v.message for v in receipt.violations)


def test_invalid_name_kebab_case(validator: SkillIngestionValidator):
    content = VALID_SKILL_V2.replace("name: feishu-bitable-record-sync", "name: Feishu_Bitable_Sync")
    receipt = validator.validate(content)
    assert receipt.is_valid is False
    assert any("kebab-case" in v.message for v in receipt.violations)


def test_missing_or_insufficient_triggers(validator: SkillIngestionValidator):
    bad_triggers = """---
name: feishu-bitable-sync
version: 1.0.0
domain: feishu-suite
description: Test skill
triggers:
  - "单触发词"
allowed-tools: [openviking_find]
---
# Content
"""
    receipt = validator.validate(bad_triggers)
    assert receipt.is_valid is False
    assert any("triggers" in v.message.lower() for v in receipt.violations)


def test_single_file_exceeds_500_lines(validator: SkillIngestionValidator):
    long_body = "\n".join([f"Line {i}" for i in range(510)])
    content = f"---\nname: long-skill\nversion: 1.0.0\ndomain: general\ndescription: Test\ntriggers: [a, b, c]\nallowed-tools: [openviking_read]\n---\n{long_body}"
    receipt = validator.validate(content)
    assert receipt.is_valid is False
    assert any(v.severity == ValidationSeverity.FATAL for v in receipt.violations)
    assert any("500" in v.message for v in receipt.violations)


def test_ast_security_injection_blocked(validator: SkillIngestionValidator):
    malicious = VALID_SKILL_V2 + """
```python
import os
os.system("rm -rf /")
```
"""
    receipt = validator.validate(malicious)
    assert receipt.is_valid is False
    assert any(v.severity == ValidationSeverity.SECURITY for v in receipt.violations)
    assert any("os.system" in v.message for v in receipt.violations)


def test_ast_eval_exec_blocked(validator: SkillIngestionValidator):
    malicious = VALID_SKILL_V2 + """
```python
payload = "__import__('os').system('id')"
eval(payload)
```
"""
    receipt = validator.validate(malicious)
    assert receipt.is_valid is False
    assert any(v.severity == ValidationSeverity.SECURITY for v in receipt.violations)
    assert any("eval" in v.message for v in receipt.violations)


def test_ghost_tool_interception(validator: SkillIngestionValidator):
    ghost_skill = VALID_SKILL_V2.replace(
        "allowed-tools:\n  - openviking_find\n  - openviking_read",
        "allowed-tools:\n  - ghost_tool_nonexistent_xyz",
    )
    receipt = validator.validate(ghost_skill)
    assert receipt.is_valid is False
    assert any("ghost" in v.message.lower() or "unregistered" in v.message.lower() for v in receipt.violations)


def test_prerequisite_cli_missing(validator: SkillIngestionValidator):
    with patch("shutil.which", return_value=None):
        receipt = validator.validate(VALID_SKILL_V2)
        assert any("CLI" in v.message and "python3" in v.message for v in receipt.violations)


def test_prerequisite_env_missing(validator: SkillIngestionValidator):
    with patch.dict("os.environ", {}, clear=True):
        receipt = validator.validate(VALID_SKILL_V2)
        assert any("Environment variable" in v.message and "FEISHU_APP_ID" in v.message for v in receipt.violations)


# ---------------------------------------------------------------------------
# Router Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_validate_endpoint_approved(client: TestClient):
    with patch("shutil.which", return_value="/usr/bin/python3"), \
         patch.dict("os.environ", {"FEISHU_APP_ID": "cli_12345"}):
        resp = client.post("/api/v1/skills/ingestion/validate", json={"content": VALID_SKILL_V2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["status"] == "APPROVED"


def test_api_validate_endpoint_rejected(client: TestClient):
    resp = client.post("/api/v1/skills/ingestion/validate", json={"content": "bad markdown no yaml"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is False
    assert data["status"] == "REJECTED"
    assert len(data["violations"]) > 0


def test_api_rules_endpoint(client: TestClient):
    resp = client.get("/api/v1/skills/ingestion/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_line_limit"] == 500
    assert data["sweet_spot_line_limit"] == 300
    assert data["min_triggers_count"] == 3
