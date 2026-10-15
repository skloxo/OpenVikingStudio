/**
 * agent-card.tsx
 * 智能体专属高密座舱卡片组件 (Cockpit UI 规范)。
 * 严禁绿色 🚫，字号 >= 12px，等宽数字，底边物理平齐 mt-auto，6px 微圆角。
 */
import {
  BotIcon,
  CheckIcon,
  ChevronRightIcon,
  CopyIcon,
  CpuIcon,
  GlobeIcon,
  KeyRoundIcon,
  LayersIcon,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import type { UserAgentItem } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'
import { BIG_THREE_PLUGIN_MAPPINGS } from '#/routes/users/-constants/agent-tools'

export type AgentCardProps = {
  agent: UserAgentItem
  onSelect: (agent: UserAgentItem) => void
}

export function AgentCard({ agent, onSelect }: AgentCardProps) {
  const [copiedKey, setCopiedKey] = useState(false)
  const isLocal = agent.connection_mode === 'realtimeApi'
  const isActive = agent.status === 'active'

  const handleCopyEndpoint = async (e: React.MouseEvent) => {
    e.stopPropagation()
    const targetUrl = isLocal
      ? `http://127.0.0.1:1933/mcp?agent_id=${agent.agent_id}`
      : `https://vk.tide.red/mcp?agent_id=${agent.agent_id}&key=\${OPENVIKING_API_KEY}`
    const success = await copyTextToClipboard(targetUrl)
    if (success) {
      setCopiedKey(true)
      toast.success('MCP 专属端点 URL 已复制至剪贴板')
      setTimeout(() => setCopiedKey(false), 2000)
    }
  }

  // 检查三大插件授权状态
  const grants = agent.plugin_grants || {}
  const authorizedPlugins = BIG_THREE_PLUGIN_MAPPINGS.filter((p) => {
    const list = grants[p.pluginId]
    return Array.isArray(list) && list.length > 0
  })

  return (
    <Card className="flex flex-col border-border/70 bg-card/60 p-3.5 transition-colors hover:border-border hover:bg-card/90">
      {/* 头部：名称、ID 与状态指示器 */}
      <div className="flex items-start justify-between gap-2">
        <div className="grid gap-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground tracking-tight">
              {agent.agent_name}
            </h3>
            <Badge
              variant="outline"
              className="text-xs font-mono border-border/60 bg-muted/30 px-1 py-0 text-muted-foreground"
            >
              {agent.user_id}
            </Badge>
          </div>
          <p className="font-mono text-xs text-muted-foreground/80">
            {agent.agent_id}
          </p>
        </div>

        {/* 运行态就绪胶囊 (性冷淡中性底色 + 状态指示点) */}
        <div className="flex items-center gap-1.5 rounded-md border border-border/70 bg-muted/40 px-2 py-0.5 text-xs font-mono tabular-nums text-foreground">
          <span
            className={`size-1.5 rounded-full shrink-0 ${
              isActive ? 'bg-cyan-500' : 'bg-muted-foreground/50'
            }`}
          />
          <span className="text-muted-foreground font-mono">
            {isActive ? '运行就绪' : '已暂停'}
          </span>
        </div>
      </div>

      {/* 角色与定位说明 */}
      <p className="mt-2 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
        {agent.role_desc || '暂无专属角色说明'}
      </p>

      {/* 核心网络拓扑与插件授权网格 */}
      <div className="mt-3.5 grid grid-cols-2 gap-2 border-y border-border/40 py-2.5">
        {/* 1. 接入拓扑 */}
        <div className="flex items-center gap-2 rounded bg-muted/30 px-2 py-1.5">
          {isLocal ? (
            <CpuIcon className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <GlobeIcon className="size-3.5 shrink-0 text-cyan-600 dark:text-cyan-400" />
          )}
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground font-mono">网络拓扑</div>
            <div className="truncate text-xs font-medium text-foreground">
              {isLocal ? '本地直连 (2080Ti)' : '公网穿透 (3070)'}
            </div>
          </div>
        </div>

        {/* 2. 工具池规模 */}
        <div className="flex items-center gap-2 rounded bg-muted/30 px-2 py-1.5">
          <LayersIcon className="size-3.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground font-mono">工具授权</div>
            <div className="truncate text-xs font-medium text-foreground">
              {agent.allowed_tools.length} 项工具算子
            </div>
          </div>
        </div>
      </div>

      {/* 授权标杆插件标签栏 */}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground font-mono">插件映射:</span>
        {authorizedPlugins.length === 0 ? (
          <span className="text-xs text-muted-foreground/60 font-mono">无插件授权</span>
        ) : (
          authorizedPlugins.map((p) => (
            <Badge
              key={p.pluginId}
              variant="secondary"
              className="border-border/40 bg-muted/50 px-1.5 py-0 text-xs font-mono text-foreground"
            >
              {p.label}
            </Badge>
          ))
        )}
      </div>

      {/* 底部按钮栏：底边物理平齐 */}
      <div className="mt-auto pt-3 flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs font-mono text-muted-foreground hover:text-foreground"
          onClick={handleCopyEndpoint}
        >
          {copiedKey ? (
            <CheckIcon className="mr-1 size-3 text-cyan-500" />
          ) : (
            <CopyIcon className="mr-1 size-3" />
          )}
          复制专属 MCP 端点
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs font-mono"
          onClick={() => onSelect(agent)}
        >
          权限与配置
          <ChevronRightIcon className="ml-1 size-3" />
        </Button>
      </div>
    </Card>
  )
}
