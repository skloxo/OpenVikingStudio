/**
 * client-install-tab.tsx
 * 客户端一键安装接入与各平台配置补丁选项卡 (Client Install & Integration Tab).
 *
 * 核心架构哲学：
 * 1. 48 小时打磨的不可变官方标杆插件安装包动态加载 (fetchLatestClientBridge)；
 * 2. 极简两核心要素平权：服务地址 + 用户密钥 (零 agentId 概念)；
 * 3. 涵盖 DSH cordis.patch.yml 补丁、MCP JSON、npm 安装直链与自然语言认主提示词；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BoxesIcon,
  CheckIcon,
  CopyIcon,
  FileCode2Icon,
  KeyRoundIcon,
  LayersIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { AdminUser } from '#/lib/admin'
import { fetchLatestClientBridge } from '../../agents/-lib/capability-bundles'

export type ClientInstallTabProps = {
  user: AdminUser
  currentAccountId: string
}

export function ClientInstallTab({ user, currentAccountId }: ClientInstallTabProps) {
  const [networkMode, setNetworkMode] = React.useState<'public' | 'local'>('public')
  const [copiedItem, setCopiedItem] = React.useState<string | null>(null)
  const [bridgePkg, setBridgePkg] = React.useState<{
    packageName: string
    version: string
    packageUrl: string
    installCommand: string
  }>({
    packageName: 'dsh-plugin-openviking',
    version: '1.5.6',
    packageUrl: 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.6.tgz',
    installCommand: 'npm install https://vk.tide.red/studio/dsh-plugin-openviking-1.5.6.tgz',
  })

  // 动态同步最新服务端客户端插件包信息
  React.useEffect(() => {
    let active = true
    fetchLatestClientBridge(networkMode).then((info) => {
      if (active) setBridgePkg(info)
    })
    return () => {
      active = false
    }
  }, [networkMode])

  const isLocal = networkMode === 'local'
  const serviceAddress = isLocal ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  const userApiKey = user.apiKey || ''

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedItem(label)
      toast.success(`${label}已复制到剪贴板`)
      setTimeout(() => setCopiedItem(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  // 1. DSH / Cordis 完整 YAML 配置补丁
  const cordisPatchYaml = `plugins:
  '${bridgePkg.packageName}':
    version: '${bridgePkg.version}'
    resolved: '${bridgePkg.packageUrl}'
    config:
      serverUrl: '${serviceAddress}'
      userApiKey: '${userApiKey}'
      accountId: '${user.accountId || currentAccountId}'
      userId: '${user.userId}'`

  // 2. Claude Desktop / Cursor 标准 MCP JSON 配置
  const mcpConfigJson = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          url: `${serviceAddress}/mcp`,
          headers: {
            'X-API-Key': userApiKey,
            'X-Account-Id': user.accountId || currentAccountId,
            'X-User-Id': user.userId,
          },
        },
      },
    },
    null,
    2,
  )

  // 3. 给 Agent 一键复制的自然语言接入提示词
  const agentPrompt = `请帮我安装并接入 OpenViking 官方标杆客户端插件：
1. 插件 NPM 安装命令：${bridgePkg.installCommand}
2. 服务地址：${serviceAddress}
3. 用户密钥：${userApiKey}
4. 租户与用户：Account=${user.accountId || currentAccountId}, User=${user.userId}`

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* 极简两要素展示 */}
      <div className="space-y-2.5 rounded-md border border-border/70 bg-card/40 p-3">
        <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
          <LayersIcon className="size-3.5 text-cyan-500" />
          接入核心两要素 (人机平权统一接入凭据)
        </h4>

        {/* 1. 服务地址 */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">服务地址</span>
              <div className="inline-flex rounded-md border border-border/60 bg-muted/20 p-0.5 text-[12px]">
                <button
                  type="button"
                  onClick={() => setNetworkMode('public')}
                  className={`px-2 py-0.5 rounded transition-all ${
                    networkMode === 'public'
                      ? 'bg-background text-cyan-400 shadow-sm font-medium'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  公网 (vk.tide.red)
                </button>
                <button
                  type="button"
                  onClick={() => setNetworkMode('local')}
                  className={`px-2 py-0.5 rounded transition-all ${
                    networkMode === 'local'
                      ? 'bg-background text-cyan-400 shadow-sm font-medium'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  本地 (127.0.0.1:1933)
                </button>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
              onClick={() => handleCopy(serviceAddress, '服务地址')}
            >
              {copiedItem === '服务地址' ? (
                <CheckIcon className="size-3 text-cyan-400" />
              ) : (
                <CopyIcon className="size-3" />
              )}
              复制
            </Button>
          </div>
          <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
            {serviceAddress}
          </div>
        </div>

        {/* 2. 用户密钥 */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">用户密钥 (User API Key)</span>
            {userApiKey && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => handleCopy(userApiKey, '用户密钥')}
              >
                {copiedItem === '用户密钥' ? (
                  <CheckIcon className="size-3 text-cyan-400" />
                ) : (
                  <CopyIcon className="size-3" />
                )}
                复制
              </Button>
            )}
          </div>
          {userApiKey ? (
            <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground break-all select-all">
              {userApiKey}
            </div>
          ) : (
            <div className="rounded border border-border/40 bg-muted/20 p-2 text-xs text-muted-foreground flex items-center justify-between">
              <span>该用户当前未直接暴露明文密钥</span>
              <span className="text-[12px] text-cyan-400">可在用户列表点击“重置”重新签发</span>
            </div>
          )}
        </div>
      </div>

      {/* 48 小时打磨的不可变官方客户端插件包 (NPM 一键安装) */}
      <div className="space-y-2 rounded-md border border-cyan-500/40 bg-cyan-500/5 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
            <BoxesIcon className="size-3.5 text-cyan-500" />
            <span>官方标杆客户端插件 (NPM Tarball 直链)</span>
            <Badge variant="outline" className="font-mono text-[12px] border-cyan-500/30 text-cyan-500">
              v{bridgePkg.version}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-xs text-cyan-600 dark:text-cyan-400 hover:text-foreground gap-1"
            onClick={() => handleCopy(bridgePkg.installCommand, 'NPM 安装命令')}
          >
            {copiedItem === 'NPM 安装命令' ? (
              <CheckIcon className="size-3 text-cyan-400" />
            ) : (
              <CopyIcon className="size-3" />
            )}
            复制命令
          </Button>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          通过公网 CDN 不可变包直链极速安装到客户端环境中，零第三方 npm 仓库网络抖动风险。
        </p>
        <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-foreground break-all select-all">
          {bridgePkg.installCommand}
        </div>
      </div>

      {/* DSH / Cordis 完整 YAML 补丁 */}
      <div className="space-y-2 rounded-md border border-border/70 bg-card/40 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <FileCode2Icon className="size-3.5 text-cyan-500" />
            DSH 配置文件补丁 (cordis.patch.yml)
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
            onClick={() => handleCopy(cordisPatchYaml, 'DSH 配置 YAML')}
          >
            {copiedItem === 'DSH 配置 YAML' ? (
              <CheckIcon className="size-3 text-cyan-400" />
            ) : (
              <CopyIcon className="size-3" />
            )}
            复制 YAML
          </Button>
        </div>
        <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
          {cordisPatchYaml}
        </pre>
      </div>

      {/* 标准 MCP JSON 配置 */}
      <div className="space-y-2 rounded-md border border-border/70 bg-card/40 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <KeyRoundIcon className="size-3.5 text-cyan-500" />
            标准 MCP 客户端配置 (Claude Desktop / Cursor)
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
            onClick={() => handleCopy(mcpConfigJson, 'MCP 配置 JSON')}
          >
            {copiedItem === 'MCP 配置 JSON' ? (
              <CheckIcon className="size-3 text-cyan-400" />
            ) : (
              <CopyIcon className="size-3" />
            )}
            复制 JSON
          </Button>
        </div>
        <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
          {mcpConfigJson}
        </pre>
      </div>

      {/* 一键 Agent 接入提示词 */}
      <div className="space-y-2 rounded-md border border-border/70 bg-card/40 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <TerminalIcon className="size-3.5 text-cyan-500" />
            智能体一键认主接入提示词 (Agent Prompt)
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
            onClick={() => handleCopy(agentPrompt, 'Agent 接入提示词')}
          >
            {copiedItem === 'Agent 接入提示词' ? (
              <CheckIcon className="size-3 text-cyan-400" />
            ) : (
              <CopyIcon className="size-3" />
            )}
            复制提示词
          </Button>
        </div>
        <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
          {agentPrompt}
        </div>
      </div>
    </div>
  )
}
