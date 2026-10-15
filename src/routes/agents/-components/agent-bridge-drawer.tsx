/**
 * agent-bridge-drawer.tsx
 * 客户端轻量通信通道桥接入指引专属抽屉组件 (Cockpit UI 规范).
 *
 * 核心架构哲学：
 * 1. 【三大核心凭证要素置顶】：请求地址 (Endpoint)、用户凭证 (User Key)、智能体 ID (Agent ID) 第一时间展示并一键复制；
 * 2. 【三大官方标杆渠道平权并立 (开箱即用)】：
 *    - 渠道 1：Google 反重力 (Antigravity IDE / CLI 官方标准插件)
 *    - 渠道 2：DeepSeek Harness (DSH npm 直链包与 cordis.patch.yml)
 *    - 渠道 3：标准通用智能体 (Cursor / Claude Code / Windsurf / Universal MCP)
 * 3. 遵行 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)；
 * 4. 严守单文件 100~300 行黄金甜点区规范。
 */

import * as React from 'react'
import {
  BotIcon,
  BoxesIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  GlobeIcon,
  KeyIcon,
  MessageSquareTextIcon,
  PackageIcon,
  ServerIcon,
  SparklesIcon,
  TerminalIcon,
  UserCheckIcon,
  XIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { fetchLatestClientBridge } from '../-lib/capability-bundles'
import type { ClientBridgePackageInfo } from '../-lib/capability-bundles'

export type AgentBridgeDrawerProps = {
  agentId: string
  userId: string
  open: boolean
  onClose: () => void
}

type ChannelType = 'antigravity' | 'dsh' | 'universal-mcp'

export function AgentBridgeDrawer({
  agentId,
  userId,
  open,
  onClose,
}: AgentBridgeDrawerProps) {
  // 网络端点切换 (公网穿透 vs 本地局域网)
  const [networkMode, setNetworkMode] = React.useState<'public' | 'local'>('public')
  const [activeChannel, setActiveChannel] = React.useState<ChannelType>('antigravity')
  const [expandedPreview, setExpandedPreview] = React.useState<string | null>(null)
  const [liveBridgeMeta, setLiveBridgeMeta] = React.useState<ClientBridgePackageInfo | null>(null)

  const isLocal = networkMode === 'local'
  const currentBaseUrl = isLocal ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  const currentEndpointUrl = `${currentBaseUrl}/mcp`

  // 从本地读取或默认 User Key
  const userKey = typeof window !== 'undefined'
    ? localStorage.getItem('ov_user_key') || 'ov_uk_live_master_key'
    : 'ov_uk_live_master_key'

  React.useEffect(() => {
    let active = true
    if (!open) return

    fetchLatestClientBridge(networkMode).then((info) => {
      if (active) setLiveBridgeMeta(info)
    })

    return () => {
      active = false
    }
  }, [open, networkMode])

  const copyToClipboard = async (text: string, title: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(`已复制 ${title}`)
    } catch {
      toast.error('复制失败')
    }
  }

  const currentDownloadUrl = liveBridgeMeta?.packageUrl || 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.6.tgz'

  // 1. 反重力开箱即用提示词
  const antigravityAgentPrompt = React.useMemo(() => {
    return `请帮我将当前反重力开发座舱 (Antigravity IDE) 接入 OpenViking 官方核心记忆插件：
1. 插件挂载规范目录：~/.gemini/config/plugins/openviking-memory/
2. 插件源码物理路径：OpenVikingStudio/integrations/antigravity/openviking-memory
3. 服务端接入地址：${currentBaseUrl}
4. 专属授权凭据：${userKey}
5. 专用账户身份：User=${userId || 'default'} (AgentID: ${agentId})
6. 执行要求：
   - 将插件源码通过目录软链挂载至全局 plugins 目录；
   - 运行 python setup.py --api ${currentBaseUrl} --key "${userKey}" 完成凭据落盘；
   - 清理工作区项目内可能残留的历史 hooks.json，交由全局插件声明式 hooks.json 统一管理；
   - 激活 PreInvocation（记忆预取）、PreToolUse（沙箱守卫）与 Stop（会话归档）三大完整能力。`
  }, [currentBaseUrl, userKey, userId, agentId])

  // 2. DSH 配置补丁与提示词
  const dshYamlSnippet = React.useMemo(() => {
    return `plugins:
  'dsh-plugin-openviking':
    version: '${liveBridgeMeta?.version || '1.5.6'}'
    resolved: '${currentDownloadUrl}'
    config:
      serverUrl: '${currentBaseUrl}'
      userApiKey: '${userKey}'
      agentId: '${agentId}'
      userId: '${userId || 'default'}'
      enableMcp: true
      enableHook: true`
  }, [currentBaseUrl, userKey, agentId, userId, currentDownloadUrl, liveBridgeMeta])

  const dshAgentPrompt = React.useMemo(() => {
    return `请帮我安装并接入 OpenViking 客户端插件：
1. NPM 安装命令：npm install ${currentDownloadUrl}
2. 服务地址：${currentBaseUrl}
3. 专属凭据：${userKey}
4. 专属身份：User=${userId || 'default'}, AgentID=${agentId}
5. 请将上述配置写入 cordis.patch.yml 并重启 Harness 服务。`
  }, [currentDownloadUrl, currentBaseUrl, userKey, userId, agentId])

  // 3. 通用 MCP 配置
  const mcpHttpSnippet = React.useMemo(() => {
    return JSON.stringify(
      {
        mcpServers: {
          openviking: {
            url: `${currentEndpointUrl}?agent_id=${agentId}`,
            headers: {
              Authorization: `Bearer ${userKey}`,
              'X-API-Key': userKey,
              'X-OpenViking-User': userId || 'default',
            },
          },
        },
      },
      null,
      2
    )
  }, [currentEndpointUrl, userKey, userId, agentId])

  const universalAgentPrompt = React.useMemo(() => {
    return `请帮我将 OpenViking 体外大脑作为通用 MCP 工具接入当前环境：
1. MCP 服务协议端点：${currentEndpointUrl}?agent_id=${agentId} (Streamable HTTP 模式)
2. 认证请求头：Authorization: Bearer ${userKey}
3. 专属用户标识：${userId || 'default'} (AgentID: ${agentId})
4. 请根据当前客户端环境（Cursor / Claude Code / Windsurf / Cline），将上述配置写入对应的 MCP 配置文件（如 .cursor/mcp.json 或 claude_desktop_config.json），并验证连通性。`
  }, [currentEndpointUrl, userKey, userId, agentId])

  return (
    <Sheet open={open} onOpenChange={(val) => !val && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl md:max-w-3xl border-l border-border/80 bg-background p-0 font-sans text-xs flex flex-col shadow-2xl"
      >
        {/* 抽屉头部 */}
        <SheetHeader className="border-b border-border/60 p-4 space-y-2 bg-muted/10">
          <div className="flex items-center justify-between pr-8">
            <div className="flex items-center gap-2">
              <TerminalIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
              <SheetTitle className="text-sm font-semibold text-foreground">
                智能体一键接入指引
              </SheetTitle>
              <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
                {agentId}
              </Badge>
            </div>

            {/* 网络端点切换 */}
            <div className="flex items-center rounded border border-border/60 bg-background p-0.5 font-mono text-xs">
              <button
                type="button"
                onClick={() => setNetworkMode('public')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  networkMode === 'public'
                    ? 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 font-medium'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                公网穿透
              </button>
              <button
                type="button"
                onClick={() => setNetworkMode('local')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  networkMode === 'local'
                    ? 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 font-medium'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                同机内网
              </button>
            </div>
          </div>
          <SheetDescription className="text-xs text-muted-foreground leading-relaxed">
            支持三大官方标杆渠道接入：复制专属提示词丢给对应 Agent，即可秒级自愈开箱即用，零手工调整。
          </SheetDescription>
        </SheetHeader>

        {/* 抽屉主体 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* ⭐ 核心 3 大要素置顶展示区 */}
          <div className="rounded-lg border border-cyan-500/40 bg-cyan-500/5 dark:bg-cyan-950/20 p-3 space-y-2">
            <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <KeyIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                接入三核心要素 (人机平权统一接入凭据)
              </span>
              <span className="text-muted-foreground text-[12px] font-mono">点击直接复制</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 font-mono text-xs">
              {/* 要素 1: 服务端点 */}
              <div className="rounded border border-border/50 bg-background/80 p-2 flex flex-col justify-between">
                <div className="flex items-center justify-between text-muted-foreground mb-1 text-[12px]">
                  <span className="flex items-center gap-1">
                    <ServerIcon className="size-3 text-cyan-500" />
                    服务端点
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(currentEndpointUrl, '请求地址')}
                    className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500"
                  >
                    <CopyIcon className="size-3" />
                  </button>
                </div>
                <div className="truncate font-medium text-foreground select-all" title={currentEndpointUrl}>
                  {currentEndpointUrl}
                </div>
              </div>

              {/* 要素 2: User Key */}
              <div className="rounded border border-border/50 bg-background/80 p-2 flex flex-col justify-between">
                <div className="flex items-center justify-between text-muted-foreground mb-1 text-[12px]">
                  <span className="flex items-center gap-1">
                    <KeyIcon className="size-3 text-cyan-500" />
                    用户密钥
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(userKey, '用户密钥')}
                    className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500"
                  >
                    <CopyIcon className="size-3" />
                  </button>
                </div>
                <div className="truncate font-medium text-foreground select-all" title={userKey}>
                  {userKey}
                </div>
              </div>

              {/* 要素 3: Agent ID */}
              <div className="rounded border border-border/50 bg-background/80 p-2 flex flex-col justify-between">
                <div className="flex items-center justify-between text-muted-foreground mb-1 text-[12px]">
                  <span className="flex items-center gap-1">
                    <UserCheckIcon className="size-3 text-cyan-500" />
                    智能体 ID
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(agentId, '智能体 ID')}
                    className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500"
                  >
                    <CopyIcon className="size-3" />
                  </button>
                </div>
                <div className="truncate font-medium text-foreground select-all" title={agentId}>
                  {agentId}
                </div>
              </div>
            </div>
          </div>

          {/* ─────────────────────────────────────────────────────────────
              三大官方标杆渠道切换 (Channel Switcher)
             ───────────────────────────────────────────────────────────── */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-border/50 pb-2">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <SparklesIcon className="size-3.5 text-cyan-500" />
                选择接入宿主渠道:
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setActiveChannel('antigravity')}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                    activeChannel === 'antigravity'
                      ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-400'
                      : 'border-border/50 bg-card text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <BotIcon className="size-3 text-cyan-400" />
                  Google 反重力
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChannel('dsh')}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                    activeChannel === 'dsh'
                      ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-400'
                      : 'border-border/50 bg-card text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <BoxesIcon className="size-3 text-cyan-400" />
                  DeepSeek Harness
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChannel('universal-mcp')}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                    activeChannel === 'universal-mcp'
                      ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-400'
                      : 'border-border/50 bg-card text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <GlobeIcon className="size-3 text-cyan-400" />
                  通用 MCP
                </button>
              </div>
            </div>

            {/* 渠道 1：Google 反重力 */}
            {activeChannel === 'antigravity' && (
              <div className="space-y-3 rounded-lg border border-cyan-500/30 bg-muted/10 p-3.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 font-semibold text-foreground text-xs">
                      <BotIcon className="size-3.5 text-cyan-400" />
                      <span>Google 反重力 (Antigravity IDE 官方标准插件规范)</span>
                      <Badge variant="outline" className="border-cyan-500/40 text-cyan-400 text-[12px] py-0">
                        原生 Plugin
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                      基于 Google Gemini Agent 插件标准封装，开箱即用集成预取、沙箱与归档三大 Hook。
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(antigravityAgentPrompt, '反重力一键认主提示词')}
                    className="h-7 text-xs font-mono shrink-0 gap-1 border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
                  >
                    <CopyIcon className="size-3" />
                    复制认主提示词
                  </Button>
                </div>

                <div className="rounded border border-border/60 bg-background/90 p-2.5 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
                  {antigravityAgentPrompt}
                </div>
              </div>
            )}

            {/* 渠道 2：DeepSeek Harness */}
            {activeChannel === 'dsh' && (
              <div className="space-y-3 rounded-lg border border-cyan-500/30 bg-muted/10 p-3.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 font-semibold text-foreground text-xs">
                      <BoxesIcon className="size-3.5 text-cyan-400" />
                      <span>DeepSeek Harness (Cordis 插件与配置补丁)</span>
                      <Badge variant="outline" className="border-cyan-500/40 text-cyan-400 text-[12px] py-0">
                        NPM 直链
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                      适用于 DSH Node.js 运行时，支持动态 MCP 工具投影与先验记忆感知 Hook。
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(dshAgentPrompt, 'DSH 一键认主提示词')}
                      className="h-7 text-xs font-mono gap-1 border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
                    >
                      <CopyIcon className="size-3" />
                      复制认主提示词
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(dshYamlSnippet, 'Cordis 配置补丁')}
                      className="h-7 text-xs font-mono gap-1 border-border/60"
                    >
                      复制 YAML
                    </Button>
                  </div>
                </div>

                <div className="pt-1 flex items-center justify-between border-t border-border/30 font-mono text-[12px]">
                  <span className="text-muted-foreground truncate max-w-sm" title={currentDownloadUrl}>
                    安装包: {currentDownloadUrl}
                  </span>
                  <button
                    type="button"
                    onClick={() => setExpandedPreview(expandedPreview === 'dsh' ? null : 'dsh')}
                    className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5"
                  >
                    {expandedPreview === 'dsh' ? (
                      <>收起配置补丁 <ChevronUpIcon className="size-3" /></>
                    ) : (
                      <>查看配置补丁 <ChevronDownIcon className="size-3" /></>
                    )}
                  </button>
                </div>

                {expandedPreview === 'dsh' && (
                  <pre className="mt-2 p-2.5 rounded bg-background/90 border border-border/50 text-foreground font-mono text-[12px] overflow-x-auto leading-relaxed">
                    {dshYamlSnippet}
                  </pre>
                )}
              </div>
            )}

            {/* 渠道 3：通用 MCP */}
            {activeChannel === 'universal-mcp' && (
              <div className="space-y-3 rounded-lg border border-cyan-500/30 bg-muted/10 p-3.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 font-semibold text-foreground text-xs">
                      <GlobeIcon className="size-3.5 text-cyan-400" />
                      <span>通用 MCP 智能体 (Cursor / Claude / Windsurf / Cline)</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                      国际标准 Model Context Protocol，支持 Streamable-HTTP 远程挂载。
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(universalAgentPrompt, '通用 Agent 认主提示词')}
                      className="h-7 text-xs font-mono gap-1 border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
                    >
                      <CopyIcon className="size-3" />
                      复制认主提示词
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(mcpHttpSnippet, 'MCP JSON 配置')}
                      className="h-7 text-xs font-mono gap-1 border-border/60"
                    >
                      复制 JSON
                    </Button>
                  </div>
                </div>

                <div className="rounded border border-border/60 bg-background/90 p-2.5 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
                  {universalAgentPrompt}
                </div>

                <div className="pt-1 flex items-center justify-between border-t border-border/30 font-mono text-[12px]">
                  <span className="text-muted-foreground">标准 JSON 结构</span>
                  <button
                    type="button"
                    onClick={() => setExpandedPreview(expandedPreview === 'mcp' ? null : 'mcp')}
                    className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5"
                  >
                    {expandedPreview === 'mcp' ? (
                      <>收起 JSON 预览 <ChevronUpIcon className="size-3" /></>
                    ) : (
                      <>展开 JSON 预览 <ChevronDownIcon className="size-3" /></>
                    )}
                  </button>
                </div>

                {expandedPreview === 'mcp' && (
                  <pre className="mt-2 p-2.5 rounded bg-background/90 border border-border/50 text-foreground font-mono text-[12px] overflow-x-auto leading-relaxed">
                    {mcpHttpSnippet}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 抽屉底部 */}
        <div className="border-t border-border/60 p-3 bg-muted/10 flex items-center justify-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            className="h-7 text-xs font-mono border-border/60"
          >
            <XIcon className="size-3 mr-1" />
            关闭
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
