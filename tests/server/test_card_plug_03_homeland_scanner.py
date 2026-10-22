# -*- coding: utf-8 -*-
"""
Unit test for Card-PLUG-03: Homeland scanning and integration channels extraction.
SSOT: docs/architecture/ADR-003
"""

import pytest
from openviking.service.plugin_scanner import scan_local_plugins


def test_homeland_scanning_and_integration_extraction():
    plugins, aliases, tool_map = scan_local_plugins()

    # 1. 查找 openviking-memory
    mem_plugin = next((p for p in plugins if p.plugin_id == 'openviking-memory'), None)
    assert mem_plugin is not None, 'openviking-memory must be discovered by scanner'

    # 2. 校验版本是否来自于统一母港 packages/plugins/ (v2.0.30)
    assert mem_plugin.version == '2.0.30', f'Expected v2.0.30 from homeland, got {mem_plugin.version}'

    # 3. 校验 integration channels 结构化字段
    assert mem_plugin.integration is not None, 'integration field must be parsed'
    channels = mem_plugin.integration.channels
    assert len(channels) == 3, f'Expected 3 channels, got {len(channels)}'

    channel_ids = [c.id for c in channels]
    assert 'antigravity' in channel_ids
    assert 'dsh' in channel_ids
    assert 'universal-mcp' in channel_ids

    # 4. 校验具体渠道字段内容
    dsh_ch = next(c for c in channels if c.id == 'dsh')
    assert 'npm install' in dsh_ch.install_cmd
    assert 'endpointUrl' in dsh_ch.config_snippet

    mcp_ch = next(c for c in channels if c.id == 'universal-mcp')
    assert 'mcpServers' in mcp_ch.config_snippet
    assert '{{ENDPOINT_URL}}' in mcp_ch.config_snippet

    # 5. 校验无重复实例
    all_mem_ids = [p.plugin_id for p in plugins if p.plugin_id == 'openviking-memory']
    assert len(all_mem_ids) == 1, 'Duplicate openviking-memory discovered!'