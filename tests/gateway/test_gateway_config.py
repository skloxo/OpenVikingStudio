"""Tests for openviking_gateway config module."""

import os
import pytest
from openviking_gateway.config import GatewayConfig, get_gateway_config


def test_gateway_config_defaults():
    config = GatewayConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 1934
    assert config.upstream_protocol == "openai"
    assert config.enable_dual_track_translation is True
    assert config.timeout_seconds == 120.0


def test_gateway_config_from_env(monkeypatch):
    monkeypatch.setenv("OPENVIKING_GATEWAY_PORT", "1999")
    monkeypatch.setenv("OPENVIKING_GATEWAY_UPSTREAM_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("OPENVIKING_GATEWAY_UPSTREAM_KEY", "sk-test-key")
    monkeypatch.setenv("OPENVIKING_GATEWAY_DEFAULT_MODEL", "deepseek-chat")

    config = get_gateway_config(reload=True)
    assert config.port == 1999
    assert config.upstream_base_url == "https://api.deepseek.com/v1"
    assert config.upstream_api_key == "sk-test-key"
    assert config.default_model == "deepseek-chat"


def test_gateway_config_strip_trailing_slash():
    config = GatewayConfig(upstream_base_url="https://api.example.com/v1/")
    assert config.upstream_base_url == "https://api.example.com/v1"
