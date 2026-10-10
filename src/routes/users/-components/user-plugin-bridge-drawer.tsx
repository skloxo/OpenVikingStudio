/**
 * user-plugin-bridge-drawer.tsx
 * 用户/智能体插件接入与客户端配置专属抽屉 (人机平权 SSOT)。
 * 极简两要素：【服务地址】+【用户密钥】。彻底切除 agentId 与生硬英文 endpoint。
 * 遵循 Agent 编码规范黄金甜点区 (<= 280 行)、NO GREEN EVER 🚫、>= 12px 字体下限。
 */
import {
  BoxesIcon,
  CheckIcon,
  CopyIcon,
  CpuIcon,
  GlobeIcon,
  KeyRoundIcon,
  LayersIcon,
  TerminalIcon,
} from 'lucide-react'
import * as React from 'react'
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
import type { AdminUser } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'

export type UserPluginBridgeDrawerProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: AdminUser | null
  currentAccountId: string
}

export function UserPluginBridgeDrawer({
  open,
  onOpenChange,
  user,
  currentAccountId,
}: UserPluginBridgeDrawerProps) {
  const [connectionMode, setConnectionMode] = React.useState<'public' | 'local'>('public')
  const [copiedItem, setCopiedItem] = React.useState<string | null>(null)

  if (!user) return null

  const isLocal = connectionMode === 'local'
  const serviceAddress = isLocal ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  const userApiKey = user.apiKey || ''
  const pluginTarballUrl = 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.5.tgz'

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

  // 1. 给 Agent 一键复制的自然语言接入提示词
  const agentPrompt = `请帮我安装并接入 OpenViking 官方标杆客户端插件：
1. 插件安装包：${pluginTarballUrl}
2. 服务地址：${serviceAddress}
3. 用户密钥：${userApiKey}`

  // 2. Claude Desktop / Cursor 标准 MCP JSON 配置
  const mcpConfigJson = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          url: `${serviceAddress}/mcp`,
          headers: {
            'X-API-Key': userApiKey,
          },
        },
      },
    },
    null,
    2,
  )

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 border-l border-border/80 bg-background p-0 sm:max-w-xl"
      >
        {/* 抽屉头部 */}
        <SheetHeader className="border-b border-border/60 p-4">
          <div className="flex items-center justify-between gap-2">
            <SheetTitle className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-2">
              <BoxesIcon className="size-4 text-cyan-500" />
              插件接入与客户端配置
            </SheetTitle>
            <div className="flex items-center gap-1.5">
              <Badge
                variant="outline"
                className="text-xs font-mono border-cyan-500/30 text-cyan-400 bg-cyan-950/20"
              >
                {user.role.toUpperCase()}
              </Badge>
              <Badge
                variant="outline"
                className="text-xs font-mono border-border/60 bg-muted/30 text-muted-foreground"
              >
                {user.accountId || currentAccountId}
              </Badge>
            </div>
          </div>
          <SheetDescription className="font-mono text-xs text-muted-foreground">
            用户成员标识 (User ID): <span className="text-foreground font-semibold">{user.userId}</span>
          </SheetDescription>
        </SheetHeader>

        {/* 抽屉正文 */}
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {/* 网络模式双选 */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-foreground">接入网络拓扑</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setConnectionMode('public')}
                className={`flex items-start gap-2.5 rounded-md border p-2.5 text-left transition-all ${
                  connectionMode === 'public'
                    ? 'border-cyan-500/60 bg-cyan-950/20 text-cyan-400'
                    : 'border-border/60 bg-card/40 text-muted-foreground hover:bg-card/70'
                }`}
              >
                <GlobeIcon className="size-4 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <div className="text-xs font-medium">公网远程模式</div>
                  <div className="text-[12px] opacity-80 truncate">vk.tide.red (推荐)</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setConnectionMode('local')}
                className={`flex items-start gap-2.5 rounded-md border p-2.5 text-left transition-all ${
                  connectionMode === 'local'
                    ? 'border-cyan-500/60 bg-cyan-950/20 text-cyan-400'
                    : 'border-border/60 bg-card/40 text-muted-foreground hover:bg-card/70'
                }`}
              >
                <CpuIcon className="size-4 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <div className="text-xs font-medium">本地宿主直连</div>
                  <div className="text-[12px] opacity-80 truncate">127.0.0.1:1933</div>
                </div>
              </button>
            </div>
          </div>

          {/* 极简两要素展示 */}
          <div className="space-y-3 rounded-md border border-border/70 bg-card/40 p-3">
            <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <LayersIcon className="size-3.5 text-cyan-500" />
              接入两核心要素 (极简平权 SSOT)
            </h4>

            {/* 1. 服务地址 */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">服务地址</span>
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

          {/* 一键 Agent 接入提示词 */}
          <div className="space-y-2 rounded-md border border-border/70 bg-card/40 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <TerminalIcon className="size-3.5 text-cyan-500" />
                智能体一键接入提示词 (DSH / Agent Prompt)
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
                复制
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
              {agentPrompt}
            </div>
          </div>

          {/* MCP JSON 配置 */}
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
                复制
              </Button>
            </div>
            <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
              {mcpConfigJson}
            </pre>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
