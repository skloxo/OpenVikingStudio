// @vitest-environment jsdom

import * as React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PluginDetailDrawer } from './plugin-detail-drawer'
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

  it('renders detail drawer tabs and navigates between skills, MCP tools, and hooks', () => {
    const handleClose = vi.fn()

    render(<PluginDetailDrawer plugin={mockPlugin} onClose={handleClose} />)

    expect(screen.getByRole('dialog')).toBeDefined()
    expect(screen.getByText('概览')).toBeDefined()
    expect(screen.getByText('技能')).toBeDefined()
    expect(screen.getByText('MCP')).toBeDefined()
    expect(screen.getByText('钩子')).toBeDefined()

    // Switch to Skills tab
    fireEvent.click(screen.getByText('技能'))
    expect(screen.getByText('体外大脑操作导轨')).toBeDefined()
    expect(screen.getByText('查库第一，高熵落盘')).toBeDefined()

    // Switch to MCP tools tab
    fireEvent.click(screen.getByText('MCP'))
    expect(screen.getByText('共 3 项算子')).toBeDefined()
    expect(screen.getByText('openviking_search')).toBeDefined()

    // Switch to Hooks tab
    fireEvent.click(screen.getByText('钩子'))
    expect(screen.getByText('PreInvocation')).toBeDefined()
    expect(screen.getByText('记忆预取反射')).toBeDefined()
  })

  it('never displays fake key placeholder in quickstart snippets', () => {
    connectionMock.apiKey = ''

    const { container } = render(
      <PluginQuickstartSection plugin={mockPlugin} />,
    )

    // 严禁包含 vk-user-key-xxxx 假占位符
    expect(container.textContent).not.toContain('vk-user-key-xxxx')
    // 包含标准化占位符
    expect(container.textContent).toContain('<YOUR_USER_KEY>')
  })
})

