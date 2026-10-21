# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Card-212 Regression Tests: Studio Connection Architecture & Trusted Identity Directory Decoupling."""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestTracer1StudioIdentityDirectoryDecoupling:
    """Tracer-1: SetupIdentityDirectory component architecture & visual bounds."""

    def test_component_exists_and_within_sweet_spot(self):
        comp_file = REPO_ROOT / "src" / "components" / "setup-identity-directory.tsx"
        assert comp_file.is_file(), "setup-identity-directory.tsx must exist"
        
        lines = comp_file.read_text(encoding="utf-8").splitlines()
        line_count = len(lines)
        assert 100 <= line_count <= 350, (
            f"setup-identity-directory.tsx should be in the sweet spot (100-300 lines), got {line_count}"
        )

    def test_strictly_no_green_and_minimum_font_size(self):
        comp_file = REPO_ROOT / "src" / "components" / "setup-identity-directory.tsx"
        content = comp_file.read_text(encoding="utf-8")

        # 100% 封杀绿色
        assert not re.search(r"text-emerald|bg-emerald|border-emerald|text-green|bg-green|border-green", content, re.I), (
            "setup-identity-directory.tsx must strictly obey NO GREEN EVER rule"
        )

        # 封杀 < 12px 微字
        assert not re.search(r"text-\[([0-9]|10|11)px\]", content), (
            "setup-identity-directory.tsx must strictly enforce minimum font size >= 12px"
        )

    def test_legacy_current_user_menu_physically_deleted(self):
        legacy_files = [
            REPO_ROOT / "src" / "components" / "current-user-menu.tsx",
            REPO_ROOT / "src" / "components" / "current-user-menu.test.ts",
            REPO_ROOT / "src" / "components" / "current-user-menu.interaction.test.tsx",
        ]
        for f in legacy_files:
            assert not f.exists(), f"Legacy component {f.name} must be physically deleted"


class TestTracer2IdentitySyncAndAdminExport:
    """Tracer-2: Connection identity synchronization and admin directory export."""

    def test_admin_api_directory_export_exists(self):
        admin_file = REPO_ROOT / "src" / "lib" / "admin.ts"
        assert admin_file.is_file()
        content = admin_file.read_text(encoding="utf-8")
        assert "export const fetchAdminUserDirectory = fetchAdminUsers" in content, (
            "admin.ts must export fetchAdminUserDirectory alias for trusted identity directory"
        )

    def test_connection_utils_guards_against_admin_key_flush(self):
        utils_file = REPO_ROOT / "src" / "hooks" / "app-connection-utils.ts"
        assert utils_file.is_file()
        content = utils_file.read_text(encoding="utf-8")
        assert "(!connection.apiKey && Boolean(connection.adminApiKey))" in content, (
            "app-connection-utils.ts must guard against control-key flushing selected data identity"
        )


class TestTracer3SettingsIntegrationAndInventory:
    """Tracer-3: Connection card integration and inventory SSOT alignment."""

    def test_connection_card_integration_and_size_bounds(self):
        card_file = (
            REPO_ROOT
            / "src"
            / "routes"
            / "settings"
            / "-components"
            / "general"
            / "connection-card.tsx"
        )
        assert card_file.is_file()
        content = card_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert "SetupIdentityDirectory" in content, (
            "connection-card.tsx must integrate SetupIdentityDirectory component"
        )
        assert len(lines) < 500, (
            f"connection-card.tsx must not exceed 500 lines hard limit, got {len(lines)}"
        )

    def test_component_inventory_alignment(self):
        inventory_file = (
            REPO_ROOT
            / "docs"
            / "architecture"
            / "COMPONENT_AND_WHEEL_INVENTORY.md"
        )
        assert inventory_file.is_file()
        content = inventory_file.read_text(encoding="utf-8")

        assert "SetupIdentityDirectory" in content, (
            "COMPONENT_AND_WHEEL_INVENTORY.md must register SetupIdentityDirectory"
        )
        assert "CurrentUserMenu" not in content, (
            "COMPONENT_AND_WHEEL_INVENTORY.md must not retain deleted CurrentUserMenu"
        )


class TestTracer4I18nSynchronization:
    """Tracer-4: Bilingual i18n synchronization for identity directory."""

    def test_i18n_keys_present_in_both_locales(self):
        zh_file = REPO_ROOT / "src" / "i18n" / "locales" / "zh-CN" / "settings.ts"
        en_file = REPO_ROOT / "src" / "i18n" / "locales" / "en" / "settings.ts"
        assert zh_file.is_file()
        assert en_file.is_file()

        zh_content = zh_file.read_text(encoding="utf-8")
        en_content = en_file.read_text(encoding="utf-8")

        required_keys = [
            "directoryHint",
            "directoryAdminHint",
            "directoryLoadFailed",
            "directoryIdentityMismatch",
            "directoryKeyHint",
            "directoryAccount",
            "directoryUser",
            "selectAccount",
            "selectUser",
        ]

        for k in required_keys:
            assert k in zh_content, f"Key '{k}' missing from zh-CN/settings.ts"
            assert k in en_content, f"Key '{k}' missing from en/settings.ts"
