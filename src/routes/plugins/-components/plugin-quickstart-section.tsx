/**
 * plugin-quickstart-section.tsx
 * 插件全渠道极速开箱与客户端接入指引组件 (ADR-003 解耦重构)。
 * 
 * 核心架构哲学:
 * 1. 【动态契约单一真相源】: 优先动态渲染母本 plugin.json / API 透传的 integration.channels；
 * 2. 【反过度工程化】: 提供透明的【服务地址】与【User Key】输入框，支持公网/内网与多Key自主指定；
 * 3. 【无状态单向插值】: 输入框内容即时插值至 install_cmd / config_snippet，用户复制即用；
 * 4. 【Cockpit UI 铁律】: NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)，6px 微圆角，高信息密度。
 */

import * as React from 'react'
import {
  BoxesIcon,
  CheckIcon,
  CopyIcon,
  GlobeIcon,
  LaptopIcon,
  LayersIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { copyTextToClipboard } from '#/lib/clipboard'
import type {
  IntegrationChannel,
  QuadPluginItem,
} from '../-lib/plugin-types'

export type PluginQuickstartSectionProps = {
  plugin: QuadPluginItem
}

export function PluginQuickstartSection({ plugin }: PluginQuickstartSectionProps) {
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  // 1. 服务中枢地址提供【本地内网】与【公网云端】双模预设
  const localPreset = typeof window !== 'undefined' && window.location.hostname !== 'vk.tide.red' && window.location.hostname
    ? `${window.location.protocol}//${window.location.hostname}:1933`
    : 'http://127.0.0.1:1933'
  const publicPreset = 'https://vk.tide.red'

  const [endpointUrl, setEndpointUrl] = React.useState<string>(() => {
    if (typeof window !== 'undefined' && window.location.origin) {
      if (window.location.origin.includes('vk.tide.red')) return publicPreset
      return window.location.origin
    }
    return 'http://127.0.0.1:1933'
  })

  const pid = plugin.plugin_id
  const version = plugin.version || '1.0.0'
  const agTarball = `${pid}-${version}.tgz`
  const dshTarball = `dsh-plugin-${pid}-${version}.tgz`

  // 2. 多渠道智能体接入列表 (母本 integration.channels 优先，缺省时优雅降级)
  const channels: IntegrationChannel[] = React.useMemo(() => {
    if (plugin.integration?.channels && plugin.integration.channels.length > 0) {
      return plugin.integration.channels
    }
    // 兼容无 integration 声明的旧插件
    return [
      {
        id: 'antigravity',
        name: 'Google 反重力',
        install_cmd: `powershell -ExecutionPolicy Bypass -Command "iwr -Uri '{{ENDPOINT_URL}}/studio/${agTarball}' -OutFile '$env:TEMP\\${pid}.tgz'; New-Item -ItemType Directory -Force -Path \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\" | Out-Null; tar -xzf '$env:TEMP\\${pid}.tgz' -C \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\"; python \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\setup.py\\" --install --api {{ENDPOINT_URL}} --key {{USER_KEY}}"`,
        agent_prompt: `请帮我将当前反重力客户端 (Antigravity IDE / Desktop) 接入 ${plugin.name} 插件：\n1. 目标包直链：{{ENDPOINT_URL}}/studio/${agTarball}\n2. 挂载目录：$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\n3. 服务中枢地址：{{ENDPOINT_URL}}\n4. 用户授权凭据：{{USER_KEY}}\n5. 执行：python setup.py --install --api {{ENDPOINT_URL}} --key {{USER_KEY}} 完成自举注册与 FastMCP 挂载。`,
        config_snippet: `{\n  "plugins": {\n    "${pid}": {\n      "installedFrom": {\n        "id": "antigravity/plugin/${pid}",\n        "marketplace": "openviking-studio",\n        "version": "${version}"\n      }\n    }\n  }\n}`,
        docs_markdown: '在 Windows PowerShell 中运行上述安装命令，自动完成下载解压、宿主注册与 FastMCP 双轨服务配置；亦可复制智能体认主提示词直接在反重力对话框中一键唤醒。',
      },
      {
        id: 'dsh',
        name: 'DeepSeek Harness',
        install_cmd: `npm install {{PACKAGE_URL}}`,
        config_snippet: `${pid}:\n  endpointUrl: "{{ENDPOINT_URL}}"\n  userKey: "{{USER_KEY}}"\n  enableMcp: true`,
        docs_markdown: '在 DSH 客户端插件市场安装，或在 profiles/desktop/node_modules 下解压加载',
      },
      {
        id: 'universal-mcp',
        name: '通用 MCP 智能体',
        install_cmd: `npx -y @openviking/mcp-gateway`,
        config_snippet: `{\n  "mcpServers": {\n    "${pid}": {\n      "url": "{{ENDPOINT_URL}}/mcp",\n      "headers": {\n        "Authorization": "Bearer {{USER_KEY}}"\n      }\n    }\n  }\n}`,
        docs_markdown: '兼容 Claude Desktop, Cursor, OpenClaw 等遵循标准 MCP 协议的智能体客户端',
      },
    ]
  }, [plugin, agTarball, pid, version])

  const [activeChannelId, setActiveChannelId] = React.useState<string>(channels[0]?.id || 'antigravity')

  React.useEffect(() => {
    if (channels.length > 0 && !channels.some((c) => c.id === activeChannelId)) {
      setActiveChannelId(channels[0].id)
    }
  }, [channels, activeChannelId])

  const activeChannel = channels.find((c) => c.id === activeChannelId) || channels[0]

  const effectiveAgentPrompt = activeChannel?.agent_prompt || (activeChannel?.id === 'antigravity'
    ? `请帮我将当前反重力客户端 (Antigravity IDE / Desktop) 接入 ${plugin.name} 插件：\n1. 目标包直链：{{ENDPOINT_URL}}/studio/${agTarball}\n2. 挂载目录：$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\n3. 服务中枢地址：{{ENDPOINT_URL}}\n4. 用户授权凭据：{{USER_KEY}}\n5. 执行：python setup.py --install --api {{ENDPOINT_URL}} --key {{USER_KEY}} 完成自举注册与 FastMCP 挂载。`
    : undefined)

  // 3. 动态占位符插值 (端点与包URL实时计算；User Key 保留占位符供用户手动替换)
  const interpolate = (template: string) => {
    if (!template) return ''
    const effectiveEndpoint = endpointUrl.trim().replace(/\/+$/, '') || '<ENDPOINT_URL>'
    const effectivePackageUrl = `${effectiveEndpoint}/studio/${dshTarball}`
    return template
      .replaceAll('{{ENDPOINT_URL}}', effectiveEndpoint)
      .replaceAll('{{USER_KEY}}', '<YOUR_USER_KEY>')
      .replaceAll('{{PACKAGE_URL}}', effectivePackageUrl)
      .replaceAll('{{PLUGIN_ID}}', pid)
      .replaceAll('{{PLUGIN_VER}}', version)
  }

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedKey(label)
      toast.success(`${label} 已复制`)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  const getChannelIcon = (id: string) => {
    if (id === 'antigravity') return <LaptopIcon className="size-3.5" />
    if (id === 'dsh') return <BoxesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
    return <LayersIcon className="size-3.5" />
  }

  return (
    <div className="space-y-3 font-sans text-xs">
      {/* 头部标题与开箱标识 */}
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <h4 className="flex items-center gap-1.5 font-semibold text-foreground">
          <TerminalIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          全渠道智能体接入指引
        </h4>
        <Badge variant="outline" className="text-xs font-mono border-border/60">
          v{version}
        </Badge>
      </div>

      {/* 服务地址输入 — 提供【本地内网】与【公网云端】双模预设与即时切换 */}
      <div className="rounded-md border border-border/50 bg-card/40 p-3 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="flex items-center gap-1.5 font-medium text-foreground text-xs">
            <GlobeIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
            服务中枢地址 (Endpoint URL)
          </label>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setEndpointUrl(localPreset)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors border cursor-pointer ${
                endpointUrl.includes('127.0.0.1') || endpointUrl.includes('localhost') || endpointUrl.includes(':1933')
                  ? 'border-cyan-500/50 bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-medium'
                  : 'border-border/40 bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              本地内网: {localPreset}
            </button>
            <button
              type="button"
              onClick={() => setEndpointUrl(publicPreset)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors border cursor-pointer ${
                endpointUrl.includes('vk.tide.red')
                  ? 'border-cyan-500/50 bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-medium'
                  : 'border-border/40 bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              公网云端: {publicPreset}
            </button>
          </div>
        </div>
        <Input
          value={endpointUrl}
          onChange={(e) => setEndpointUrl(e.target.value)}
          placeholder={`例如: ${publicPreset} 或 ${localPreset}`}
          className="h-7 text-xs font-mono px-2 bg-background/80"
        />
        <p className="text-xs text-muted-foreground">
          可直接点击上方标签在【本地内网】与【公网云端】间秒级切换，或输入自定义 IP。修改后安装命令中的下载地址自动同步。
        </p>
      </div>

      {/* 渠道切换 Tab 导航 */}
      {channels.length > 1 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {channels.map((ch) => {
            const isActive = ch.id === activeChannel?.id
            return (
              <Button
                key={ch.id}
                variant="ghost"
                size="sm"
                onClick={() => setActiveChannelId(ch.id)}
                className={`h-7 px-2.5 text-xs font-medium gap-1.5 rounded-md border transition-colors ${
                  isActive
                    ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 shadow-xs'
                    : 'border-border/40 bg-card/20 text-muted-foreground hover:text-foreground hover:bg-card/60'
                }`}
              >
                {getChannelIcon(ch.id)}
                <span>{ch.name}</span>
              </Button>
            )
          })}
        </div>
      )}

      {/* 激活渠道接入内容卡片 */}
      {activeChannel && (
        <div className="space-y-2.5 rounded-md border border-border/50 bg-card/30 p-3">
          {/* 安装命令块 */}
          {activeChannel.install_cmd && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                  <TerminalIcon className="size-3 text-muted-foreground" />
                  <span>安装与部署命令</span>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
                  onClick={() => handleCopy(interpolate(activeChannel.install_cmd!), `${activeChannel.name} 安装命令`)}
                >
                  {copiedKey === `${activeChannel.name} 安装命令` ? (
                    <>
                      <CheckIcon className="size-3 text-cyan-500" />
                      <span>已复制</span>
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3" />
                      <span>复制</span>
                    </>
                  )}
                </Button>
              </div>
              <pre className="rounded p-2 font-mono text-xs overflow-x-auto whitespace-pre-wrap break-all border border-border/40 bg-muted/40 text-foreground/90">
                {interpolate(activeChannel.install_cmd)}
              </pre>
            </div>
          )}

          {/* 智能体认主提示词块 (支持一键复制提示词发给反重力 / 智能体) */}
          {effectiveAgentPrompt && (
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                  <LaptopIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
                  <span>智能体一键认主提示词 (发送给客户端对话框)</span>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
                  onClick={() => handleCopy(interpolate(effectiveAgentPrompt), `${activeChannel.name} 认主提示词`)}
                >
                  {copiedKey === `${activeChannel.name} 认主提示词` ? (
                    <>
                      <CheckIcon className="size-3 text-cyan-500" />
                      <span>已复制</span>
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3" />
                      <span>复制</span>
                    </>
                  )}
                </Button>
              </div>
              <pre className="rounded p-2 font-mono text-xs overflow-x-auto whitespace-pre-wrap break-all border border-border/30 bg-muted/20 text-foreground/80">
                {interpolate(effectiveAgentPrompt)}
              </pre>
            </div>
          )}

          {/* 配置文件片段块 */}
          {activeChannel.config_snippet && (
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                  <LayersIcon className="size-3 text-muted-foreground" />
                  <span>客户端配置文件代码片段</span>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
                  onClick={() => handleCopy(interpolate(activeChannel.config_snippet!), `${activeChannel.name} 配置代码`)}
                >
                  {copiedKey === `${activeChannel.name} 配置代码` ? (
                    <>
                      <CheckIcon className="size-3 text-cyan-500" />
                      <span>已复制</span>
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3" />
                      <span>复制</span>
                    </>
                  )}
                </Button>
              </div>
              <pre className="rounded p-2 font-mono text-xs overflow-x-auto whitespace-pre-wrap break-all border border-border/30 bg-muted/20 text-foreground/80">
                {interpolate(activeChannel.config_snippet)}
              </pre>
            </div>
          )}

          {/* 渠道专属指引说明 */}
          {activeChannel.docs_markdown && (
            <div className="rounded border border-border/30 bg-muted/10 p-2 text-xs text-muted-foreground leading-relaxed">
              {interpolate(activeChannel.docs_markdown)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
