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
  KeyIcon,
  LaptopIcon,
  LayersIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import { copyTextToClipboard } from '#/lib/clipboard'
import type {
  IntegrationChannel,
  QuadPluginItem,
} from '../-lib/plugin-types'

export type PluginQuickstartSectionProps = {
  plugin: QuadPluginItem
}

export function PluginQuickstartSection({ plugin }: PluginQuickstartSectionProps) {
  const { connection } = useAppConnection()
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  // 1. 服务地址与密钥由用户自主掌控 (反过度工程化，支持内网与公网自主填写)
  const defaultEndpoint = typeof window !== 'undefined' && window.location.origin
    ? window.location.origin
    : 'https://vk.tide.red'
  const [endpointUrl, setEndpointUrl] = React.useState<string>(defaultEndpoint)
  const [userKey, setUserKey] = React.useState<string>(connection?.apiKey || '')

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
        install_cmd: `powershell -ExecutionPolicy Bypass -Command "iwr -Uri '{{ENDPOINT_URL}}/studio/${agTarball}' -OutFile '$env:TEMP\\${pid}.tgz'; New-Item -ItemType Directory -Force -Path \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\" | Out-Null; tar -xzf '$env:TEMP\\${pid}.tgz' -C \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\"; python \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\setup.py\\" --install"`,
        config_snippet: `{\n  "plugins": [\n    "${pid}"\n  ]\n}`,
        docs_markdown: '通过反重力 IDE / Desktop 插件市场加载，或解压至 ~/.gemini/config/plugins/',
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

  // 3. 动态占位符安全插值 (端点、密钥、版本与包URL)
  const interpolate = (template: string) => {
    if (!template) return ''
    const effectiveEndpoint = endpointUrl.trim().replace(/\/+$/, '') || '<ENDPOINT_URL>'
    const effectiveKey = userKey.trim() || '<YOUR_USER_KEY>'
    const effectivePackageUrl = `${effectiveEndpoint}/studio/${dshTarball}`
    return template
      .replaceAll('{{ENDPOINT_URL}}', effectiveEndpoint)
      .replaceAll('{{USER_KEY}}', effectiveKey)
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

      {/* 参数输入面板: 服务地址 + User Key (透明自主填写，即时插值) */}
      <div className="rounded-md border border-border/50 bg-card/40 p-3 space-y-2.5">
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <div className="space-y-1">
            <label className="flex items-center gap-1.5 font-medium text-foreground text-xs">
              <GlobeIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
              服务中枢地址 (Endpoint URL)
            </label>
            <Input
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              placeholder="例如: https://vk.tide.red 或 http://127.0.0.1:1933"
              className="h-7 text-xs font-mono px-2 bg-background/80"
            />
          </div>

          <div className="space-y-1">
            <label className="flex items-center gap-1.5 font-medium text-foreground text-xs">
              <KeyIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
              用户凭据密钥 (User Key)
            </label>
            <Input
              value={userKey}
              onChange={(e) => setUserKey(e.target.value)}
              placeholder="输入或粘贴你的专属 User Key (例如: vk-usr-xxxx)"
              className="h-7 text-xs font-mono px-2 bg-background/80"
            />
          </div>
        </div>
        <div className="text-xs text-muted-foreground flex items-center justify-between pt-0.5">
          <span>修改地址或密钥后，下方各渠道命令与配置文件将自动同步插值，复制即用。</span>
          {userKey && (
            <Badge variant="outline" className="text-xs font-mono px-1.5 py-0 border-cyan-500/30 text-cyan-700 dark:text-cyan-400 bg-cyan-500/10">
              已填入专属密钥
            </Badge>
          )}
        </div>
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
