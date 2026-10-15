// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UserAgentItem } from '#/lib/admin'
import { AgentItem } from './agent-item'

describe('AgentItem Tool Grants Persistence Test', () => {
  const mockAgent: UserAgentItem = {
    agent_id: 'ag_test123',
    agent_name: '测试智能体',
    user_id: 'user_123',
    role_desc: '测试角色描述',
    icon: 'bot',
    connection_mode: 'bridge',
    status: 'active',
    total_messages: 10,
    last_seen: Date.now(),
    created_at: Date.now(),
    allowed_tools: ['read', 'write', 'edit'],
  }

  const mockOnUpdate = vi.fn().mockResolvedValue({})
  const mockOnDelete = vi.fn()
  const mockOnActivate = vi.fn()
  const mockOnToggleExpand = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('triggers onUpdate directly from "保存工具配置" button without clicking "编辑名称"', async () => {
    render(
      <AgentItem
        agent={mockAgent}
        userId="user_123"
        isExpanded={true}
        onToggleExpand={mockOnToggleExpand}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
        onActivate={mockOnActivate}
        isUpdating={false}
      />
    )

    // 确认卡片已展开，且直接出现「保存工具配置」按钮
    const saveToolsBtn = screen.getByRole('button', { name: /保存工具配置/i })
    expect(saveToolsBtn).toBeDefined()

    // 用户在没有点击右上角「编辑」的情况下，直接点击「保存工具配置」
    fireEvent.click(saveToolsBtn)

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledTimes(1)
    })

    // 验证调用参数：必须包含 allowed_tools 和 plugin_grants，无需依赖 agent_name 编辑
    expect(mockOnUpdate).toHaveBeenCalledWith(
      'ag_test123',
      expect.objectContaining({
        allowed_tools: expect.arrayContaining(['read', 'write', 'edit']),
        plugin_grants: expect.objectContaining({
          'openviking-memory': expect.arrayContaining(['read', 'write']),
        }),
      })
    )
  })

  it('triggers onUpdate when opening plugin drawer and clicking "保存并完成"', async () => {
    render(
      <AgentItem
        agent={mockAgent}
        userId="user_123"
        isExpanded={true}
        onToggleExpand={mockOnToggleExpand}
        onUpdate={mockOnUpdate}
        onDelete={mockOnDelete}
        onActivate={mockOnActivate}
        isUpdating={false}
      />
    )

    // 点击第一个插件瓦片（OpenViking 核心战地记忆插件）打开抽屉
    const pluginTile = screen.getByText(/OpenViking.*记忆插件/i)
    fireEvent.click(pluginTile)

    // 验证抽屉内出现「保存并完成」按钮
    const saveAndDoneBtn = await screen.findByRole('button', { name: /保存并完成/i })
    expect(saveAndDoneBtn).toBeDefined()

    // 点击抽屉内的「保存并完成」
    fireEvent.click(saveAndDoneBtn)

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledTimes(1)
    })

    expect(mockOnUpdate).toHaveBeenCalledWith(
      'ag_test123',
      expect.objectContaining({
        allowed_tools: expect.any(Array),
        plugin_grants: expect.any(Object),
      })
    )
  })
})
