# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for The Big Three Quad Plugins manifests (TASK-ASST-01, 02, 03).
"""

import pytest
from openviking.service.plugin_registry import PluginRegistry


@pytest.fixture
def registry():
    PluginRegistry.reset_instance()
    reg = PluginRegistry.get_instance()
    yield reg


def test_openviking_memory_quad_integrity(registry: PluginRegistry):
    """Verify openviking-memory has all 4 dimensions: tools, hooks, skill, gui."""
    plugin = registry.get_plugin("openviking-memory")
    assert plugin is not None
    assert plugin.plugin_id == "openviking-memory"
    assert len(plugin.tools) >= 5
    assert len(plugin.hooks) >= 2
    assert plugin.skill is not None
    assert plugin.gui is not None
    assert isinstance(plugin.gui.settings_fields, dict)

    hook_events = [h.trigger_event for h in plugin.hooks]
    assert "before_prompt_submit" in hook_events
    assert "after_response" in hook_events


def test_keepass_vault_quad_integrity(registry: PluginRegistry):
    """Verify keepass-vault has tools, credential hook, skill, and GUI."""
    plugin = registry.get_plugin("keepass-vault")
    assert plugin is not None
    assert plugin.plugin_id == "keepass-vault"
    assert len(plugin.tools) >= 8
    assert len(plugin.hooks) >= 1
    assert plugin.skill is not None
    assert plugin.gui is not None
    assert isinstance(plugin.gui.settings_fields, dict)


def test_network_search_quad_integrity(registry: PluginRegistry):
    """Verify network-search has 2 tools, hook, skill, and GUI."""
    plugin = registry.get_plugin("network-search")
    assert plugin is not None
    assert plugin.plugin_id == "network-search"
    assert len(plugin.tools) >= 2
    assert len(plugin.hooks) >= 1
    assert plugin.skill is not None
    assert plugin.gui is not None
    assert isinstance(plugin.gui.settings_fields, dict)
