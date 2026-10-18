# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Unit tests for Card-84: Playground visual action launcher cockpit."""

from __future__ import annotations

import pathlib


def test_visual_action_launcher_source_and_integration():
    """Verify visual action launcher exists, mounted in PlaygroundActionPanel, and follows Cockpit UI rules."""
    project_root = pathlib.Path(__file__).parents[2]
    launcher_path = project_root / "src/routes/playground/-components/visual-action-launcher.tsx"
    panel_path = project_root / "src/routes/playground/-components/playground-action-panel.tsx"
    types_path = project_root / "src/routes/playground/-lib/types.ts"
    zh_i18n_path = project_root / "src/i18n/locales/zh-CN/playground.ts"
    en_i18n_path = project_root / "src/i18n/locales/en/playground.ts"

    assert launcher_path.exists(), "VisualActionLauncher component file must exist"
    assert panel_path.exists(), "PlaygroundActionPanel file must exist"
    assert types_path.exists(), "Playground types file must exist"

    launcher_content = launcher_path.read_text(encoding="utf-8")
    panel_content = panel_path.read_text(encoding="utf-8")
    types_content = types_path.read_text(encoding="utf-8")
    zh_content = zh_i18n_path.read_text(encoding="utf-8")
    en_content = en_i18n_path.read_text(encoding="utf-8")

    # Line count must be <= 300 lines
    lines = len(launcher_content.splitlines())
    assert lines <= 300, f"VisualActionLauncher must be <= 300 lines, got {lines}"

    # Types must include visualLauncher in PlaygroundPanel
    assert "'visualLauncher'" in types_content

    # Action panel must mount VisualActionLauncher and declare visualLauncher tab
    assert "VisualActionLauncher" in panel_content
    assert "<VisualActionLauncher />" in panel_content
    assert "activePanel === 'visualLauncher'" in panel_content

    # Visual launcher must use unified ovClient
    assert "ovClient.instance.get" in launcher_content
    assert "ovClient.instance.post" in launcher_content

    # Cockpit UI rules: NO GREEN EVER
    assert "text-green" not in launcher_content
    assert "bg-green" not in launcher_content

    # Preset coverage
    assert "ACTION_PRESETS" in launcher_content
    assert "/api/v1/rsi/bootstrap/health/run" in launcher_content
    assert "/api/v1/queue/sync-metrics" in launcher_content
    assert "/api/v1/snapshot/log" in launcher_content
    assert "/api/v1/system/consistency" in launcher_content

    # Bilingual i18n
    assert "visualLauncher:" in zh_content
    assert "visualLauncher:" in en_content
    assert "btnRun:" in zh_content
    assert "btnRun:" in en_content
