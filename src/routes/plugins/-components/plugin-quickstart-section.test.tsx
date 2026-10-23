// @vitest-environment jsdom

import * as React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

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

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('#/lib/clipboard', () => ({
  copyTextToClipboard: vi.fn().mockResolvedValue(undefined),
}))

const mockPluginWithChannels: QuadPluginItem = {
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
  tools: [],
  hooks: [],
  skill: {
    skill_id: 'openviking-memory',
    name: '记忆体外大脑',
    description: '记忆操作',
    sop_summary: '查库第一',
    rules: [],
  },
  gui: {
    settings_fields: {},
    dashboard_route: '/plugins',
  },
  integration: {
    channels: [
      {
        id: 'antigravity',
        name: 'Google 反重力',
        install_cmd: 'powershell -ExecutionPolicy Bypass -Command "iwr -Uri \'{{ENDPOINT_URL}}/studio/openviking-memory-{{PLUGIN_VER}}.tgz\' -OutFile \'$env:TEMP\\openviking-memory.tgz\'; New-Item -ItemType Directory -Force -Path \\"$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-memory\\" | Out-Null; tar -xzf \'$env:TEMP\\openviking-memory.tgz\' -C \\"$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-memory\\"; python \\"$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-memory\\setup.py\\" --install --api {{ENDPOINT_URL}} --key {{USER_KEY}}"',
        agent_prompt: '请帮我将当前反重力客户端 (Antigravity IDE / Desktop) 接入 OpenViking 核心战地长程记忆：\n1. 目标包：{{ENDPOINT_URL}}/studio/openviking-memory-{{PLUGIN_VER}}.tgz\n2. 挂载目录：$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-memory\n3. 服务端：{{ENDPOINT_URL}}\n4. 凭据：{{USER_KEY}}',
        config_snippet: '{\n  "plugins": {\n    "openviking-memory": {\n      "version": "{{PLUGIN_VER}}"\n    }\n  }\n}',
        docs_markdown: '通过反重力 PowerShell 命令或认主提示词启用',
      },
      {
        id: 'dsh',
        name: 'DeepSeek Harness',
        install_cmd: 'npm install {{PACKAGE_URL}}',
        config_snippet: 'openviking-memory:\n  endpointUrl: "{{ENDPOINT_URL}}"\n  userKey: "{{USER_KEY}}"',
        docs_markdown: '在 DSH 客户端安装',
      },
      {
        id: 'universal-mcp',
        name: '通用 MCP 智能体',
        install_cmd: 'npx -y @openviking/mcp-gateway',
        config_snippet: '{\n  "url": "{{ENDPOINT_URL}}/mcp",\n  "key": "{{USER_KEY}}"\n}',
        docs_markdown: '兼容标准 MCP 客户端',
      },
    ],
  },
}

describe('Card-PLUG-04: PluginQuickstartSection Multi-channel & Dynamic Input Interpolation', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    connectionMock.apiKey = ''
  })

  it('renders all integration channels defined in plugin.json and displays agent prompt for antigravity', () => {
    render(<PluginQuickstartSection plugin={mockPluginWithChannels} />)

    expect(screen.getByText('全渠道智能体接入指引')).toBeDefined()
    expect(screen.getByText('Google 反重力')).toBeDefined()
    expect(screen.getByText('DeepSeek Harness')).toBeDefined()
    expect(screen.getByText('通用 MCP 智能体')).toBeDefined()
    expect(screen.getByText('智能体一键认主提示词 (发送给客户端对话框)')).toBeDefined()
  })

  it('dynamically interpolates custom endpoint into config snippets with static user key placeholder', () => {
    render(<PluginQuickstartSection plugin={mockPluginWithChannels} />)

    // 切换至 DSH 渠道
    fireEvent.click(screen.getByText('DeepSeek Harness'))

    // 获取服务中枢输入框
    const endpointInput = screen.getByPlaceholderText(/例如: https:\/\/vk.tide.red/) as HTMLInputElement

    // 修改为自定义内网地址
    fireEvent.change(endpointInput, { target: { value: 'http://192.168.1.100:1933' } })

    // 断言配置代码片段已即时动态插值
    expect(screen.getByText(/endpointUrl: "http:\/\/192.168.1.100:1933"/)).toBeDefined()
    expect(screen.getByText(/userKey: "<YOUR_USER_KEY>"/)).toBeDefined()
    expect(screen.getByText(/npm install http:\/\/192.168.1.100:1933\/studio\/dsh-plugin-openviking-memory-2.0.30.tgz/)).toBeDefined()
  })


  it('switches between local and public endpoint presets on click', () => {
    render(<PluginQuickstartSection plugin={mockPluginWithChannels} />)

    const publicBtn = screen.getByRole('button', { name: /公网云端:/ })
    fireEvent.click(publicBtn)

    const endpointInput = screen.getByPlaceholderText(/例如: https:\/\/vk.tide.red/) as HTMLInputElement
    expect(endpointInput.value).toBe('https://vk.tide.red')

    const localBtn = screen.getByRole('button', { name: /本地内网:/ })
    fireEvent.click(localBtn)
    expect(endpointInput.value).toContain(':1933')
  })

  it('gracefully handles plugins without explicit integration channels via default fallback', () => {
    const pluginWithoutIntegration: QuadPluginItem = {
      ...mockPluginWithChannels,
      integration: undefined,
    }

    render(<PluginQuickstartSection plugin={pluginWithoutIntegration} />)

    expect(screen.getByText('Google 反重力')).toBeDefined()
    expect(screen.getByText('DeepSeek Harness')).toBeDefined()
    expect(screen.getByText('通用 MCP 智能体')).toBeDefined()
  })

  it('handles copy button click and provides visual feedback', async () => {
    render(<PluginQuickstartSection plugin={mockPluginWithChannels} />)

    const copyButtons = screen.getAllByRole('button', { name: /复制/ })
    expect(copyButtons.length).toBeGreaterThan(0)

    fireEvent.click(copyButtons[0])
    expect(await screen.findByText('已复制')).toBeDefined()
  })
})
