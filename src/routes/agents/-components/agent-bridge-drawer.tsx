/**
 * agent-bridge-drawer.tsx
 * 客户端轻量通信通道桥接入指引专属抽屉组件 (Cockpit UI 规范)。
 *
 * 核心架构哲学：
 * 1. 【三大核心凭证要素置顶】：请求地址 (Endpoint)、用户凭证 (User Key)、智能体 ID (Agent ID) 必须第一时间显著展示并支持一键独立复制；
 * 2. 【两大安装接入场景】：
 *    - 场景 1：支持直接安装 NPM 包 (以 DSH 为例，提供安装包地址、安装命令与配置)；
 *    - 场景 2：不支持直接安装 (通过引导提示词 Prompt 发给 Agent 自行接入)；
 *    - 场景 3：通用标准 MCP 配置 (Cursor / VS Code / Claude Desktop)；
 * 3. 遵行 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)；
 * 4. 严守单文件 100~300 行黄金甜点区规范。
 */

import * as React from 'react'
import {
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  GlobeIcon,
  KeyIcon,
  MessageSquareTextIcon,
  PackageIcon,
  ServerIcon,
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

export function AgentBridgeDrawer({
  agentId,
  userId,
  open,
  onClose,
}: AgentBridgeDrawerProps) {
  // 网络端点切换 (公网穿透 vs 本地局域网)
  const [networkMode, setNetworkMode] = React.useState<'public' | 'local'>('public')
  // 控制代码块折叠展开
  const [expandedPreview, setExpandedPreview] = React.useState<string | null>(null)

  // 实时从服务端动态查询的客户端桥梁元数据 (单一真实源 SSOT)
  const [liveBridgeMeta, setLiveBridgeMeta] = React.useState<ClientBridgePackageInfo | null>(null)

  const currentEndpointUrl = networkMode === 'local'
    ? 'http://127.0.0.1:1933/mcp'
    : 'https://vk.tide.red/mcp'

  // 从本地读取或默认 User Key
  const userKey = typeof window !== 'undefined'
    ? localStorage.getItem('ov_user_key') || 'ov_uk_live_master_key'
    : 'ov_uk_live_master_key'

  // 打开抽屉或切换网络时，实时向后端拉取最新的包元数据
  React.useEffect(() => {
    let active = true
    if (!open) return

    fetchLatestClientBridge(networkMode).then((info) => {
      if (active) {
        setLiveBridgeMeta(info)
      }
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

  // 点击复制时，实时现场向服务端查询最新的包与链接，杜绝页面初期缓存
  const handleCopyPackageUrl = async () => {
    const latest = await fetchLatestClientBridge(networkMode)
    setLiveBridgeMeta(latest)
    await copyToClipboard(latest.packageUrl, `最新 NPM 安装包链接 (v${latest.version})`)
  }

  const handleCopyInstallCommand = async () => {
    const latest = await fetchLatestClientBridge(networkMode)
    setLiveBridgeMeta(latest)
    await copyToClipboard(latest.installCommand, `最新 NPM 安装命令 (v${latest.version})`)
  }

  const currentDownloadUrl = liveBridgeMeta?.packageUrl || 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.4.tgz'

  // 1. DSH 配置补丁
  const dshYamlSnippet = React.useMemo(() => {
    return `# DeepSeek Harness (DSH) 插件补丁 (cordis.patch.yml)
# 安装桥梁: npm install ${currentDownloadUrl}
# 架构: 官方一体化通信通道桥 (动态 MCP 工具投影 + 先验记忆感知 Hook)
plugins:
  - id: openviking
    name: "dsh-plugin-openviking"
    config:
      endpointUrl: "${currentEndpointUrl}"
      userKey: "${userKey}"
      userKeyEnv: "OPENVIKING_USER_KEY"
      agentId: "${agentId}"
      userId: "${userId || 'default'}"
      enableMcp: true
      enableHook: true
      peer: "deepseek-harness@satellite"
`
  }, [currentEndpointUrl, userKey, agentId, userId, currentDownloadUrl])

  // 2. 引导提示词 (不支持直接安装的 Agent 使用)
  const agentPromptSnippet = React.useMemo(() => {
    return `【OpenViking 智能体接入指引与工程规约】
你的接入核心配置如下，请牢记并在后续会话中按此标准通信：
1. 请求端点 (Endpoint URL): ${currentEndpointUrl}
2. 用户凭据 (User Key): ${userKey}
3. 你的专属身份 (Agent ID): ${agentId}

【行为规约】：
- 所有的知识检索与记忆更新，通过 Streamable HTTP 协议请求上述端点，并在请求头附带 Authorization: Bearer ${userKey} 与参数 agent_id=${agentId}。
- 面对复杂工程与架构问题，开局主动向体外记忆检索 (find / search) 召回既往经验；解决复杂 Bug 后自动调用 record_lesson 沉淀教训。`
  }, [currentEndpointUrl, userKey, agentId])

  // 3. 通用 MCP JSON 配置 (Cursor / VS Code / Claude Desktop)
  const mcpJsonSnippet = React.useMemo(() => {
    return JSON.stringify(
      {
        mcpServers: {
          openviking: {
            url: `${currentEndpointUrl}?agent_id=${agentId}`,
            headers: {
              Authorization: `Bearer ${userKey}`,
            },
          },
        },
      },
      null,
      2
    )
  }, [currentEndpointUrl, userKey, agentId])

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
                智能体接入指引
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
            任何客户端或外部智能体接入，均需基于以下核心 3 要素完成握手。
          </SheetDescription>
        </SheetHeader>

        {/* 抽屉主体 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* ⭐ 核心 3 大要素置顶展示区 (Endpoint URL + User Key + Agent ID) */}
          <div className="rounded-lg border border-cyan-500/40 bg-cyan-500/5 dark:bg-cyan-950/20 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <KeyIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                接入三核心要素 (客户端打通必填项)
              </span>
              <span className="text-muted-foreground text-xs font-mono">点击直接复制</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-1 font-mono text-xs">
              {/* 要素 1: 请求端点 */}
              <div className="rounded border border-border/50 bg-background/80 p-2.5 flex flex-col justify-between">
                <div className="flex items-center justify-between text-muted-foreground mb-1">
                  <span className="flex items-center gap-1">
                    <ServerIcon className="size-3 text-cyan-500" />
                    请求地址 (Endpoint)
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(currentEndpointUrl, '请求地址')}
                    className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500"
                    title="复制请求地址"
                  >
                    <CopyIcon className="size-3" />
                  </button>
                </div>
                <div className="truncate font-medium text-foreground select-all" title={currentEndpointUrl}>
                  {currentEndpointUrl}
                </div>
              </div>

              {/* 要素 2: User Key */}
              <div className="rounded border border-border/50 bg-background/80 p-2.5 flex flex-col justify-between">
                <div className="flex items-center justify-between text-muted-foreground mb-1">
                  <span className="flex items-center gap-1">
                    <KeyIcon className="size-3 text-cyan-500" />
                    用户密钥 (User Key)
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(userKey, '用户密钥')}
                    className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500"
                    title="复制用户密钥"
                  >
                    <CopyIcon className="size-3" />
                  </button>
                </div>
                <div className="truncate font-medium text-foreground select-all" title={userKey}>
                  {userKey}
                </div>
              </div>

              {/* 要素 3: Agent ID */}
              <div className="rounded border border-border/50 bg-background/80 p-2.5 flex flex-col justify-between">
                <div className="flex items-center justify-between text-muted-foreground mb-1">
                  <span className="flex items-center gap-1">
                    <UserCheckIcon className="size-3 text-cyan-500" />
                    智能体 ID (Agent ID)
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(agentId, '智能体 ID')}
                    className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-500"
                    title="复制智能体 ID"
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

          {/* ⭐ 两种核心安装接入场景 + 通用 MCP */}
          <div className="space-y-3">
            {/* 场景 1: 支持直接安装 (以 DSH 为例通过 NPM 包安装) */}
            <div className="rounded-lg border border-border/60 bg-muted/10 p-3.5 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 font-semibold text-foreground text-xs">
                    <PackageIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                    <span>场景一：支持直接安装 (以 DSH 为例通过 NPM 包接入)</span>
                    <Badge variant="outline" className="border-cyan-500/30 text-cyan-600 dark:text-cyan-400 text-xs py-0">
                      代码/CLI 宿主
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    适用于支持直接下载并安装 NPM 插件包的 Agent 宿主（如 DeepSeek Harness、Node.js 运行时等）。
                  </p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCopyPackageUrl}
                    className="h-7 text-xs font-mono gap-1 border-border/60"
                  >
                    <CopyIcon className="size-3" />
                    复制包链接
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCopyInstallCommand}
                    className="h-7 text-xs font-mono gap-1 border-border/60"
                  >
                    <CopyIcon className="size-3" />
                    复制安装命令
                  </Button>
                </div>
              </div>

              <div className="pt-1 flex items-center justify-between border-t border-border/30 font-mono text-xs">
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
                <pre className="mt-2 p-2.5 rounded bg-background/90 border border-border/50 text-foreground font-mono text-xs overflow-x-auto leading-relaxed">
                  {dshYamlSnippet}
                </pre>
              )}
            </div>

            {/* 场景 2: 不支持直接安装 (通过提示词复制给 Agent 自主接入) */}
            <div className="rounded-lg border border-border/60 bg-muted/10 p-3.5 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 font-semibold text-foreground text-xs">
                    <MessageSquareTextIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                    <span>场景二：不支持直接安装 (提示词引导 Agent 自主接入)</span>
                    <Badge variant="outline" className="border-border/60 text-muted-foreground text-xs py-0">
                      纯对话 / 网页 Agent
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    适用于纯对话式 Agent 或无法直接运行命令的环境。直接复制以下提示词发给 Agent，即可完成引导接入。
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(agentPromptSnippet, '引导提示词')}
                  className="h-7 text-xs font-mono shrink-0 gap-1 border-border/60"
                >
                  <CopyIcon className="size-3" />
                  复制引导提示词
                </Button>
              </div>

              <div className="pt-1 flex items-center justify-between border-t border-border/30 font-mono text-xs">
                <span className="text-muted-foreground">
                  已内置端点、User Key 与专属 Agent ID
                </span>
                <button
                  type="button"
                  onClick={() => setExpandedPreview(expandedPreview === 'prompt' ? null : 'prompt')}
                  className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5"
                >
                  {expandedPreview === 'prompt' ? (
                    <>收起提示词预览 <ChevronUpIcon className="size-3" /></>
                  ) : (
                    <>查看完整提示词 <ChevronDownIcon className="size-3" /></>
                  )}
                </button>
              </div>

              {expandedPreview === 'prompt' && (
                <pre className="mt-2 p-2.5 rounded bg-background/90 border border-border/50 text-foreground font-mono text-xs overflow-x-auto leading-relaxed whitespace-pre-wrap">
                  {agentPromptSnippet}
                </pre>
              )}
            </div>

            {/* 场景 3: 通用 MCP 客户端 (Cursor / VS Code / Claude Desktop) */}
            <div className="rounded-lg border border-border/60 bg-muted/10 p-3.5 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 font-semibold text-foreground text-xs">
                    <GlobeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                    <span>通用 MCP 配置 (Cursor / VS Code / Claude Desktop)</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    标准 MCP JSON 格式，直接粘贴至 IDE 的 <code className="font-mono text-foreground">mcp.json</code> 即可。
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(mcpJsonSnippet, 'MCP JSON 配置')}
                  className="h-7 text-xs font-mono shrink-0 gap-1 border-border/60"
                >
                  <CopyIcon className="size-3" />
                  复制 JSON 配置
                </Button>
              </div>

              <div className="pt-1 flex items-center justify-between border-t border-border/30 font-mono text-xs">
                <span className="text-muted-foreground truncate max-w-sm" title={currentEndpointUrl}>
                  端点: {currentEndpointUrl}?agent_id={agentId}
                </span>
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
                <pre className="mt-2 p-2.5 rounded bg-background/90 border border-border/50 text-foreground font-mono text-xs overflow-x-auto leading-relaxed">
                  {mcpJsonSnippet}
                </pre>
              )}
            </div>
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
