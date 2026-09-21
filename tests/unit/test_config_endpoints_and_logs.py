# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for endpoint resolution and structured logging across services."""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openviking.service.endpoint_resolver import DEFAULT_OPENVIKING_ENDPOINT, get_openviking_endpoint
from openviking.service.entropy_watchdog import EntropyWatchdog, _resolve_api_key
from openviking.service.gatekeeper_prober import probe_nearest_vector


class TestEndpointResolver:
    """Tests for get_openviking_endpoint resolution order."""

    def test_default_fallback(self, monkeypatch):
        """Should fall back to default endpoint when no env vars or config exist."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.delenv("OPENVIKING_URL", raising=False)
        monkeypatch.delenv("OPENVIKING_API", raising=False)
        monkeypatch.delenv("OPENVIKING_PORT", raising=False)

        with patch("pathlib.Path.exists", return_value=False):
            assert get_openviking_endpoint() == DEFAULT_OPENVIKING_ENDPOINT

    def test_custom_default(self, monkeypatch):
        """Should respect custom default argument."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.delenv("OPENVIKING_URL", raising=False)
        monkeypatch.delenv("OPENVIKING_API", raising=False)
        monkeypatch.delenv("OPENVIKING_PORT", raising=False)

        with patch("pathlib.Path.exists", return_value=False):
            assert get_openviking_endpoint(default="http://localhost:8080/") == "http://localhost:8080"

    def test_openviking_endpoint_env(self, monkeypatch):
        """OPENVIKING_ENDPOINT takes highest priority and strips trailing slash."""
        monkeypatch.setenv("OPENVIKING_ENDPOINT", "http://node-gpu:1933/")
        monkeypatch.setenv("OPENVIKING_URL", "http://ignored:1933")
        monkeypatch.setenv("OPENVIKING_PORT", "9999")

        assert get_openviking_endpoint() == "http://node-gpu:1933"

    def test_openviking_url_env(self, monkeypatch):
        """OPENVIKING_URL is recognized if OPENVIKING_ENDPOINT is unset."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.setenv("OPENVIKING_URL", "http://192.168.1.50:1933/")
        monkeypatch.setenv("OPENVIKING_PORT", "9999")

        assert get_openviking_endpoint() == "http://192.168.1.50:1933"

    def test_openviking_api_env(self, monkeypatch):
        """OPENVIKING_API is recognized if OPENVIKING_ENDPOINT and OPENVIKING_URL are unset."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.delenv("OPENVIKING_URL", raising=False)
        monkeypatch.setenv("OPENVIKING_API", "http://api-cluster:1933")

        assert get_openviking_endpoint() == "http://api-cluster:1933"

    def test_openviking_port_env(self, monkeypatch):
        """OPENVIKING_PORT constructs loopback URL if no direct URL env var is present."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.delenv("OPENVIKING_URL", raising=False)
        monkeypatch.delenv("OPENVIKING_API", raising=False)
        monkeypatch.setenv("OPENVIKING_PORT", "1935")

        assert get_openviking_endpoint() == "http://127.0.0.1:1935"

    def test_ov_conf_server_url(self, monkeypatch, tmp_path):
        """Should parse server_url from ov.conf file."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.delenv("OPENVIKING_URL", raising=False)
        monkeypatch.delenv("OPENVIKING_API", raising=False)
        monkeypatch.delenv("OPENVIKING_PORT", raising=False)

        conf_file = tmp_path / "ov.conf"
        conf_file.write_text("server_url = http://my-ov-host:1933/\n")

        with patch("pathlib.Path.home", return_value=tmp_path):
            (tmp_path / ".openviking").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".openviking" / "ov.conf").write_text("server_url = http://my-ov-host:1933/\n")
            assert get_openviking_endpoint() == "http://my-ov-host:1933"

    def test_ov_conf_port(self, monkeypatch, tmp_path):
        """Should parse port from ov.conf file if no explicit server_url."""
        monkeypatch.delenv("OPENVIKING_ENDPOINT", raising=False)
        monkeypatch.delenv("OPENVIKING_URL", raising=False)
        monkeypatch.delenv("OPENVIKING_API", raising=False)
        monkeypatch.delenv("OPENVIKING_PORT", raising=False)

        with patch("pathlib.Path.home", return_value=tmp_path):
            (tmp_path / ".openviking").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".openviking" / "ov.conf").write_text("port = 2026\n")
            assert get_openviking_endpoint() == "http://127.0.0.1:2026"


class TestGatekeeperProberDynamicEndpoint:
    """Test gatekeeper_prober uses resolved endpoint."""

    @pytest.mark.asyncio
    async def test_probe_calls_resolved_endpoint(self, monkeypatch):
        """Probe fallback should issue HTTP request to dynamic endpoint URL."""
        monkeypatch.setenv("OPENVIKING_ENDPOINT", "http://custom-node:18790")

        # Mock internal memory service to force HTTP fallback
        with patch("openviking.server.dependencies.get_service", return_value=None):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "result": {
                    "resources": [{"uri": "viking://matched", "score": 0.88, "abstract": "Snippet"}]
                }
            }

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                score, matched_uri, snippet = await probe_nearest_vector("Some test content", "viking://curr")
                assert score == 0.88
                assert matched_uri == "viking://matched"
                # Verify URL sent to httpx
                called_url = mock_client.post.call_args[0][0]
                assert called_url == "http://custom-node:18790/api/v1/search/find"


class TestEntropyWatchdogDynamicEndpointAndLogs:
    """Test entropy_watchdog uses dynamic endpoint and logs errors cleanly."""

    @pytest.mark.asyncio
    async def test_watchdog_eval_calls_resolved_endpoint(self, monkeypatch):
        """Watchdog evaluation loop should query dynamic endpoint."""
        monkeypatch.setenv("OPENVIKING_ENDPOINT", "http://watchdog-host:1933")

        watchdog = EntropyWatchdog.get_instance()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": {"resources": []}}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await watchdog._run_real_evaluation()
            assert len(results) > 0
            called_url = mock_client.post.call_args[0][0]
            assert called_url == "http://watchdog-host:1933/api/v1/search/find"

    def test_resolve_api_key_logs_debug_on_invalid_json(self, monkeypatch):
        """Corrupted mcp_config.json should not silently pass; should log debug message."""
        monkeypatch.delenv("OPENVIKING_API_KEY", raising=False)

        from openviking.service.entropy_watchdog import logger as watchdog_logger

        with patch("pathlib.Path.exists", return_value=True), \
             patch("json.load", side_effect=ValueError("Corrupt JSON syntax")), \
             patch("builtins.open", MagicMock()), \
             patch.object(watchdog_logger, "debug") as mock_debug:
            key = _resolve_api_key()
            assert key == ""
            mock_debug.assert_called()
            called_format = mock_debug.call_args[0][0]
            assert "Failed reading API key from mcp_config.json" in called_format
