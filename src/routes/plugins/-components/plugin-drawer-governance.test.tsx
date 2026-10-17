// @vitest-environment jsdom

import * as React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { NativeBridgeIntegrationGuide } from './native-bridge-integration-guide'
import { PluginOverviewTab } from './plugin-overview-tab'
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

const mockPlugin: QuadPluginItem = {
  plugin_id: 'openviking-memory',
  name: '核心战地长程记忆 (openviking-memory)',
  description: '提供体外大脑长程语义检索与向量归档',
  version: '2.0.11',
  category: 'core',
  is_installed: true,
  health: {
    status: 'healthy',
    latency_ms: 0.12,
  },
  tools: [
    { name: 'openviking_search', description: '语义搜索', category: 'memory' },
    { name: 'openviking_read', description: '读取记忆', category: 'memory' },
    { name: 'openviking_system_status', description: '运维状态', category: 'ops' },
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
    sop_summary: '查库第一，高熵落盘',
    rules: ['禁止硬编码假密钥', '严格红绿测试'],
  },
}

describe('Card-148: Plugin Overview & Key Governance', () => {
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
      <NativeBridgeIntegrationGuide
        pluginId="openviking-memory"
        pluginName="核心战地长程记忆"
      />,
    )

    // 严禁包含 vk-user-key-xxxx 假占位符
    expect(container.textContent).not.toContain('vk-user-key-xxxx')

    // 应该展示未检测到密钥提示与前往用户中心链接
    expect(screen.getByText('未检测到活跃用户密钥 (User API Key)')).toBeDefined()
    const userLink = screen.getByRole('link', { name: /前往用户列表查看与复制专属密钥/ })
    expect(userLink.getAttribute('href')).toBe('/users')
  })

  it('displays real API key when provided', () => {
    connectionMock.apiKey = 'ov-real-user-key-9999'

    render(
      <NativeBridgeIntegrationGuide
        pluginId="openviking-memory"
        pluginName="核心战地长程记忆"
      />,
    )

    expect(screen.getByText('ov-real-user-key-9999')).toBeDefined()
    expect(screen.getByRole('button', { name: /复制真实密钥/ })).toBeDefined()
  })
})
