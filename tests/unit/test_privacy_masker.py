# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for PrivacyMasker & Pydantic V2 Schema Hardening (Card 13)."""

import warnings
from datetime import datetime
import pytest

from openviking.privacy.privacy_masker import (
    PrivacyMasker,
    get_privacy_masker,
    mask_text,
)
from openviking.resource.watch_manager import WatchTask
from openviking.storage.vectordb.service.app_models import ApiResponse


class TestPrivacyMasker:
    """Test suite for PrivacyMasker dynamic credential sanitizer."""

    @pytest.fixture(autouse=True)
    def _setup_teardown(self):
        PrivacyMasker.reset_instance()
        yield
        PrivacyMasker.reset_instance()

    def test_singleton_instance(self):
        masker1 = get_privacy_masker()
        masker2 = PrivacyMasker.get_instance()
        assert masker1 is masker2

    def test_mask_api_keys(self):
        fake_key = "sk-" + "a1b2c3d4e5f6" * 3
        text = f"My OpenAI key is {fake_key} and my test is fine."
        sanitized = mask_text(text)
        assert "sk-***[REDACTED_API_KEY]" in sanitized
        assert fake_key not in sanitized

    def test_mask_github_tokens(self):
        fake_token = "ghp_" + "ABCDEFGHIJKL" * 3
        text = f"Clone with {fake_token} to fetch repo."
        sanitized = mask_text(text)
        assert "ghp_***[REDACTED_TOKEN]" in sanitized
        assert fake_token not in sanitized

    def test_mask_aws_keys(self):
        fake_aws = "AKIA" + "1234567890ABCDEF"
        text = f"AWS config: aws_access_key_id = {fake_aws}"
        sanitized = mask_text(text)
        assert "AKIA***[REDACTED_AWS_KEY]" in sanitized
        assert fake_aws not in sanitized

    def test_mask_bearer_token(self):
        fake_bearer = "Bearer " + "jwt_token_sample_" * 2
        text = f"Authorization: {fake_bearer}"
        sanitized = mask_text(text)
        assert "Bearer ***[REDACTED_TOKEN]" in sanitized
        assert "jwt_token_sample" not in sanitized

    def test_mask_private_key_block(self):
        key_block = (
            "-----BEGIN " + "RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA0Y1+abcdef...\n"
            "-----END " + "RSA PRIVATE KEY-----"
        )
        text = f"Here is the deploy key:\n{key_block}\nPlease keep it safe."
        sanitized = mask_text(text)
        assert "[REDACTED_PRIVATE_KEY_BLOCK]" in sanitized
        assert "BEGIN RSA PRIVATE KEY" not in sanitized

    def test_mask_sensitive_assignments(self):
        text = 'password = "my_super_secret_123"\nsecret: "topsecret12345"'
        sanitized = mask_text(text)
        assert 'password = "***[REDACTED]***"' in sanitized
        assert 'secret: "***[REDACTED]***"' in sanitized
        assert "my_super_secret_123" not in sanitized
        assert "topsecret12345" not in sanitized

    def test_contains_sensitive(self):
        masker = get_privacy_masker()
        fake_key = "sk-" + "a1b2c3d4e5f6" * 3
        assert masker.contains_sensitive(f"Use {fake_key}") is True
        assert masker.contains_sensitive("password = 'some_secret_password'") is True
        assert masker.contains_sensitive("This is a clean and regular message.") is False

    def test_mask_nested_dict(self):
        masker = get_privacy_masker()
        fake_key = "sk-" + "a1b2c3d4e5f6" * 3
        fake_gh = "ghp_" + "1234567890ABCDEF" * 2
        payload = {
            "service": "openai",
            "api_key": fake_key,
            "configs": {
                "admin_password": "super_secret_value",
                "normal_field": "hello world",
                "tokens": [fake_gh, "plain text"],
            },
        }
        sanitized = masker.mask_dict(payload)
        assert sanitized["configs"]["admin_password"] == "***[REDACTED]***"
        assert sanitized["configs"]["normal_field"] == "hello world"
        assert "ghp_***[REDACTED_TOKEN]" in sanitized["configs"]["tokens"][0]
        assert sanitized["configs"]["tokens"][1] == "plain text"

    def test_pydantic_v2_watch_task_clean(self):
        with warnings.catch_warnings(record=True) as recorded_warnings:
            warnings.simplefilter("always")
            task = WatchTask(
                path="/tmp/test_watch",
                to_uri="viking://resources/test",
                created_at=datetime.now(),
            )
            d = task.to_dict()
            assert d["path"] == "/tmp/test_watch"
            assert task.model_config.get("extra") == "ignore"
            # Ensure no PydanticDeprecatedSince20 warnings
            pydantic_warnings = [
                w for w in recorded_warnings if "PydanticDeprecatedSince20" in str(w.message)
            ]
            assert len(pydantic_warnings) == 0

    def test_pydantic_v2_base_response_clean(self):
        with warnings.catch_warnings(record=True) as recorded_warnings:
            warnings.simplefilter("always")
            resp = ApiResponse(
                code=200,
                message="OK",
                data={"key": "val"},
                **{"time_cost(second)": 0.05},
            )
            assert resp.code == 200
            assert resp.time_cost == 0.05
            pydantic_warnings = [
                w for w in recorded_warnings if "PydanticDeprecatedSince20" in str(w.message)
            ]
            assert len(pydantic_warnings) == 0

    def test_client_exports_and_sync_async_importability(self):
        from openviking.client import LocalClient, Session
        from openviking.async_client import AsyncOpenViking
        from openviking.sync_client import SyncOpenViking

        assert LocalClient is not None
        assert Session is not None
        assert AsyncOpenViking is not None
        assert SyncOpenViking is not None

