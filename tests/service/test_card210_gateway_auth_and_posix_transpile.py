# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-210 Regression Tests: Gateway Tolerant Types, Trusted Group Header, OIDC, and Windows POSIX Shim."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from openviking_cli.exceptions import InvalidArgumentError


class TestTracer1GatewayTolerantTypes:
    """Tracer-1: Client history non-string type fault tolerance."""

    def test_string_type_and_text_content(self):
        from openviking_gateway.protocols import _extract_text_content, string_type

        # Valid string type
        assert string_type({"type": "text"}) == "text"
        assert string_type({"type": "image"}) == "image"

        # Malformed object types (e.g. JSON Schema fragment)
        assert string_type({"type": {"type": "string"}}) == ""
        assert string_type({"type": None}) == ""
        assert string_type({"type": 123}) == ""
        assert string_type("not_a_dict") == ""

        # _extract_text_content should tolerate object types without raising
        content_with_object = [
            {"type": {"type": "string"}, "text": "ignored"},
            {"type": "text", "text": "valid content"},
            {"type": "text", "text": {"nested": "not_string"}},
        ]
        result = _extract_text_content(content_with_object)
        assert "valid content" in result


class TestTracer2TrustedGroupHeader:
    """Tracer-2: X-OpenViking-Groups header parsing and identity propagation."""

    @pytest.mark.asyncio
    async def test_trusted_group_header_parsing(self):
        from openviking.server.auth.plugins.trusted import (
            TrustedAuthPlugin,
            _group_ids_from_header,
        )

        # 1. Parsing and deduplication
        mock_req = MagicMock()
        mock_req.headers = {"X-OpenViking-Groups": "dev-team, security, dev-team, ops "}
        groups = _group_ids_from_header(mock_req)
        assert groups == ("dev-team", "security", "ops")

        # 2. Empty header returns empty tuple
        mock_req.headers = {"X-OpenViking-Groups": " , "}
        assert _group_ids_from_header(mock_req) == ()

        # 3. Invalid group_id (containing slash) raises InvalidArgumentError
        mock_req.headers = {"X-OpenViking-Groups": "valid, invalid/group"}
        with pytest.raises(InvalidArgumentError, match="Invalid group_id"):
            _group_ids_from_header(mock_req)

        # 4. Identity resolution carries group_ids
        mock_req.headers = {
            "X-OpenViking-Groups": "admin-team, audit",
            "X-OpenViking-Account": "acme",
            "X-OpenViking-User": "alice",
        }
        mock_req.url = SimpleNamespace(path="/api/v1/resources")
        mock_req.app.state = SimpleNamespace(config=SimpleNamespace(root_api_key=None), api_key_manager=None)

        plugin = TrustedAuthPlugin()
        identity = await plugin.resolve_identity(
            mock_req,
            x_openviking_account="acme",
            x_openviking_user="alice",
        )
        assert identity.group_ids == ("admin-team", "audit")


class TestTracer3OIDCIssuerTrailingSlash:
    """Tracer-3: OIDC issuer exact matching and discovery URL construction."""

    def test_oidc_issuer_preserves_trailing_slash_and_discovery_strips(self):
        from openviking.server.auth.oidc_config import OIDCConfig
        from openviking.server.auth.plugins.oidc import _DISCOVERY_PATH

        # Preserves exact trailing slash
        cfg1 = OIDCConfig(issuer="https://sso.test/auth/")
        assert cfg1.issuer == "https://sso.test/auth/"

        # Discovery URL construction strips trailing slash
        discovery_url = f"{cfg1.issuer.rstrip('/')}{_DISCOVERY_PATH}"
        assert discovery_url == f"https://sso.test/auth{_DISCOVERY_PATH}"
        assert "//.well-known" not in discovery_url

        # Empty issuer validation
        with pytest.raises(ValueError, match="issuer cannot be empty"):
            OIDCConfig(issuer="///")


class TestTracer4WindowsPOSIXCompileShim:
    """Tracer-4: Windows direct sandbox POSIX command translation."""

    def test_prepare_windows_shell_env_extraction(self):
        from bot.vikingbot.sandbox.backends.direct import _prepare_windows_shell

        cmd = (
            "unset OPENVIKING_URL OPENVIKING_API_KEY; "
            "export OPENVIKING_CLI_CONFIG_FILE='C:\\work\\ovcli.conf'; "
            'python -c "print(123)"'
        )
        clean_cmd, child_env = _prepare_windows_shell(cmd)
        assert clean_cmd == 'python -c "print(123)"'
        assert child_env is not None
        assert child_env["OPENVIKING_CLI_CONFIG_FILE"] == "C:\\work\\ovcli.conf"
        assert "OPENVIKING_URL" not in child_env
        assert "OPENVIKING_API_KEY" not in child_env

    def test_mkdir_operands_parsing(self):
        from bot.vikingbot.sandbox.backends.direct import _mkdir_operands

        # -p with directory
        paths, restricted = _mkdir_operands(["mkdir", "-p", "output/dir"])
        assert paths == ["output/dir"]
        assert restricted is False

        # -m 700 with directory
        paths, restricted = _mkdir_operands(["mkdir", "-m", "700", "-p", "secret/dir"])
        assert paths == ["secret/dir"]
        assert restricted is True

    @pytest.mark.asyncio
    async def test_translate_windows_posix_mkdir(self, tmp_path):
        from bot.vikingbot.sandbox.backends.direct import _translate_windows_posix

        test_dir = tmp_path / "sub" / "target"
        cmd = f'mkdir -p "{test_dir}"'
        res = await _translate_windows_posix(cmd, str(tmp_path))
        assert res == "(no output)"
        assert test_dir.is_dir()


class TestTracer5CompileWorkspaceRootAbsolute:
    """Tracer-5: Compile sandbox workspace root resolves to absolute path."""

    def test_compile_sandbox_parent_path_resolution(self, tmp_path, monkeypatch):
        from bot.vikingbot.compile.sandbox import CompileSandboxManager
        from bot.vikingbot.config.schema import Config

        state_root = tmp_path / "state"
        state_root.mkdir()
        monkeypatch.chdir(state_root)

        cfg = Config(storage_workspace="rel_data")
        cfg.ov_server.set_effective_auth_mode("dev")

        mgr = CompileSandboxManager(
            cfg,
            "rel_sandbox_parent",
            tmp_path / "source",
            connection={},
        )
        assert Path(mgr.workspace).is_absolute()
        assert Path(mgr.workspace) == (state_root / "rel_sandbox_parent").resolve()
