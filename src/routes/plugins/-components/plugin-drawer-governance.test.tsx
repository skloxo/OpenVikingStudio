// @vitest-environment jsdom

import * as React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PluginOverviewTab } from './plugin-overview-tab'
import { PluginQuickstartSection } from './plugin-quickstart-section'
import type { QuadPluginItem } from '../-lib/plugin-types'

const connectionMock = vi.hoisted(() => ({
  apiKey: '',
  baseUrl: 'http://localhost:1933',
}))

vi.mock('#/hooks/use-app-connection', () => ({
  useAppConnection: () => ({
    connection: connectionMock,
    connectionRole: 'admin',
  }),
}))

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('#/lib/clipboard', () => ({
  copyTextToClipboard: vi.fn().mockResolvedValue(undefined),
}))

const mockPlugin: QuadPluginItem = {
  plugin_id: 'openviking-memory',
  name: '核心战地长程记忆 (openviking-memory)',
  description: '提供体外大脑长程语义检索与向量归档',
  version: '2.0.30',
  category: 'platform',
  health: {
    status: 'healthy',
    latency_ms: 0.12,
    message: 'OK',
    checked_at: 1000,
  },
  tools: [
    { name: 'openviking_search', description: '语义搜索', category: 'memory', is_dangerous: false },
    { name: 'openviking_read', description: '读取记忆', category: 'memory', is_dangerous: false },
    { name: 'openviking_system_status', description: '运维状态', category: 'ops', is_dangerous: false },
  ],
  hooks: [
    {
      hook_id: 'pre-invocation-prefetch',
      name: '记忆预取反射',
      trigger_event: 'PreInvocation',
      description: '执行前自动召回历史上下文',
    },
  ],
  skill: {
    skill_id: 'openviking-memory',
    name: '体外大脑操作导轨',
    description: '记忆操作',
    sop_summary: '查库第一，高熵落盘',
    rules: ['禁止硬编码假密钥', '严格红绿测试'],
  },
  gui: {
    settings_fields: {},
    dashboard_route: '/plugins',
  },
}

describe('Card-148 & Card-PLUG-04: Plugin Drawer & Key Governance', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    connectionMock.apiKey = ''
  })

  it('renders overview 4-grid capabilities and triggers tab navigation', () => {
    const handleNavigate = vi.fn()

    render(
      <PluginOverviewTab
        plugin={mockPlugin}
        privilege={{ isAllowed: true }}
        connectionRole="admin"
        onNavigateTab={handleNavigate}
      />,
    )

    // 检查 4-Grid 卡片渲染
    expect(screen.getByText('MCP 工具能力池')).toBeDefined()
    expect(screen.getByText('3 项')).toBeDefined()
    expect(screen.getByText('Hook 拦截神经反射')).toBeDefined()
    expect(screen.getByText('1 处')).toBeDefined()
    expect(screen.getByText('技能认知导轨规约')).toBeDefined()
    expect(screen.getByText('客户端接入指南')).toBeDefined()

    // 点击 MCP 工具卡片
    fireEvent.click(screen.getByText('MCP 工具能力池'))
    expect(handleNavigate).toHaveBeenCalledWith('tools')

    // 点击 Hook 卡片
    fireEvent.click(screen.getByText('Hook 拦截神经反射'))
    expect(handleNavigate).toHaveBeenCalledWith('hooks')
  })

  it('never displays fake key placeholder when connection has no active key', () => {
    connectionMock.apiKey = ''

    const { container } = render(
      <PluginQuickstartSection plugin={mockPlugin} />,
    )

    // 严禁包含 vk-user-key-xxxx 假占位符
    expect(container.textContent).not.toContain('vk-user-key-xxxx')

    // 用户密钥输入框应为空
    const keyInput = screen.getByPlaceholderText(/输入或粘贴你的专属 User Key/) as HTMLInputElement
    expect(keyInput.value).toBe('')
  })

  it('displays and binds real API key when connection provides it', () => {
    connectionMock.apiKey = 'ov-real-user-key-9999'

    render(
      <PluginQuickstartSection plugin={mockPlugin} />,
    )

    const keyInput = screen.getByPlaceholderText(/输入或粘贴你的专属 User Key/) as HTMLInputElement
    expect(keyInput.value).toBe('ov-real-user-key-9999')
    expect(screen.getByText('已填入专属密钥')).toBeDefined()
  })
})
