/**
 * agent-detail-drawer.tsx
 * 智能体专属高密配置与插件授权抽屉 (Cockpit UI 规范)。
 * 严守单文件黄金甜点区 (<= 300 行)、NO GREEN EVER 🚫、>= 12px 字体下限。
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckIcon,
  CopyIcon,
  CpuIcon,
  GlobeIcon,
  RotateCwIcon,
} from 'lucide-react'
import * as React from 'react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import type { UpdateAgentInput, UserAgentItem } from '#/lib/admin'
import { updateUserAgent } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'
import { ToolACLMatrix } from '#/routes/users/-components/tool-acl-matrix'
import { BIG_THREE_PLUGIN_MAPPINGS } from '#/routes/users/-constants/agent-tools'

export type AgentDetailDrawerProps = {
  agent: UserAgentItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function AgentDetailDrawer({
  agent,
  open,
  onOpenChange,
  onSuccess,
}: AgentDetailDrawerProps) {
  const queryClient = useQueryClient()

  const [agentName, setAgentName] = React.useState('')
  const [roleDesc, setRoleDesc] = React.useState('')
  const [connectionMode, setConnectionMode] = React.useState('apiClient')
  const [selectedTools, setSelectedTools] = React.useState<string[]>([])
  const [copiedKey, setCopiedKey] = React.useState(false)

  // 同步初始化状态
  React.useEffect(() => {
    if (agent) {
      setAgentName(agent.agent_name || agent.agent_id)
      setRoleDesc(agent.role_desc || '')
      setConnectionMode(agent.connection_mode || 'apiClient')
      setSelectedTools(agent.allowed_tools)
    }
  }, [agent])

  const updateMutation = useMutation({
    mutationFn: async (payload: UpdateAgentInput) => {
      if (!agent) return
      return updateUserAgent(
        agent.user_id,
        agent.agent_id,
        payload,
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cluster-agents'] })
      queryClient.invalidateQueries({ queryKey: ['user-agents'] })
      toast.success('智能体配置与插件授权已更新 (50ms 零重启热生效)')
      onOpenChange(false)
      onSuccess?.()
    },
    onError: (err: any) => {
      toast.error(`更新失败: ${err.message || '未知错误'}`)
    },
  })

  if (!agent) return null

  const isLocal = connectionMode === 'realtimeApi'
  const endpointUrl = isLocal
    ? `http://127.0.0.1:1933/mcp?agent_id=${agent.agent_id}`
    : `https://vk.tide.red/mcp?agent_id=${agent.agent_id}&key=\${OPENVIKING_API_KEY}`

  const handleCopyEndpoint = async () => {
    try {
      await copyTextToClipboard(endpointUrl)
      setCopiedKey(true)
      toast.success('专属 MCP 端点已复制')
      setTimeout(() => setCopiedKey(false), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  const handleSave = () => {
    updateMutation.mutate({
      agent_name: agentName,
      role_desc: roleDesc,
      connection_mode: connectionMode,
      allowed_tools: selectedTools,
    })
  }

  // 快捷切换单个插件全量工具
  const handleTogglePlugin = (toolNames: string[]) => {
    const hasAll = toolNames.every((t) => selectedTools.includes(t))
    if (hasAll) {
      // 取消该插件所有工具
      setSelectedTools((prev) => prev.filter((t) => !toolNames.includes(t)))
    } else {
      // 补齐该插件所有工具
      setSelectedTools((prev) => Array.from(new Set([...prev, ...toolNames])))
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 border-l border-border/80 bg-background p-0 sm:max-w-xl"
      >
        {/* 抽屉头部 */}
        <SheetHeader className="border-b border-border/60 p-4">
          <div className="flex items-center justify-between gap-2">
            <SheetTitle className="text-sm font-semibold tracking-tight text-foreground">
              智能体配置与权限中枢
            </SheetTitle>
            <Badge
              variant="outline"
              className="text-xs font-mono border-border/60 bg-muted/30 px-1 py-0 text-muted-foreground"
            >
              {agent.user_id}
            </Badge>
          </div>
          <SheetDescription className="font-mono text-xs text-muted-foreground">
            Agent ID: {agent.agent_id}
          </SheetDescription>
        </SheetHeader>

        {/* 抽屉滚动正文 */}
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {/* 1. 基础展示设置 */}
          <div className="space-y-3 rounded-md border border-border/60 bg-card/40 p-3">
            <h4 className="text-xs font-semibold text-foreground">身份与定位</h4>
            <div className="grid gap-2">
              <div>
                <label className="text-xs text-muted-foreground font-mono">显示名称</label>
                <Input
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  className="mt-1 h-8 text-xs font-mono"
                  placeholder="智能体名称"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground font-mono">角色说明</label>
                <Input
                  value={roleDesc}
                  onChange={(e) => setRoleDesc(e.target.value)}
                  className="mt-1 h-8 text-xs font-mono"
                  placeholder="职责与定位"
                />
              </div>
            </div>
          </div>

          {/* 2. 拓扑模式选择 */}
          <div className="space-y-2 rounded-md border border-border/60 bg-card/40 p-3">
            <h4 className="text-xs font-semibold text-foreground">网络接入拓扑</h4>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                className={`h-8 rounded-md px-2.5 text-xs font-mono transition-all flex items-center justify-center ${
                  isLocal
                    ? 'border border-cyan-500/50 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 dark:bg-cyan-950/40 font-medium shadow-xs'
                    : 'border border-border/70 bg-background text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
                onClick={() => setConnectionMode('realtimeApi')}
              >
                <CpuIcon className="mr-1.5 size-3.5" />
                本地直连 (2080Ti)
              </button>
              <button
                type="button"
                className={`h-8 rounded-md px-2.5 text-xs font-mono transition-all flex items-center justify-center ${
                  !isLocal
                    ? 'border border-cyan-500/50 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 dark:bg-cyan-950/40 font-medium shadow-xs'
                    : 'border border-border/70 bg-background text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
                onClick={() => setConnectionMode('apiClient')}
              >
                <GlobeIcon className="mr-1.5 size-3.5" />
                公网远程 (3070)
              </button>
            </div>
          </div>

          {/* 3. 三大标杆插件快捷开关 */}
          <div className="space-y-2 rounded-md border border-border/60 bg-card/40 p-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-foreground">三大标杆插件授权绑定</h4>
              <span className="text-xs text-muted-foreground font-mono">
                {selectedTools.length} 项工具已选
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(BIG_THREE_PLUGIN_MAPPINGS).map(([pluginId, cfg]) => {
                const isFullyGranted = cfg.tools.every((t) => selectedTools.includes(t))
                const isPartiallyGranted =
                  !isFullyGranted && cfg.tools.some((t) => selectedTools.includes(t))

                return (
                  <Button
                    key={pluginId}
                    type="button"
                    variant={isFullyGranted ? 'default' : 'outline'}
                    size="sm"
                    className="h-8 text-xs font-mono truncate"
                    onClick={() => handleTogglePlugin(cfg.tools)}
                  >
                    {isFullyGranted ? (
                      <CheckIcon className="mr-1 size-3" />
                    ) : isPartiallyGranted ? (
                      <span className="mr-1 text-cyan-500 font-bold">~</span>
                    ) : null}
                    {cfg.name}
                  </Button>
                )
              })}
            </div>
          </div>

          {/* 4. 二级树状工具矩阵 */}
          <div className="space-y-2 rounded-md border border-border/60 bg-card/40 p-3">
            <h4 className="text-xs font-semibold text-foreground">细粒度工具 ACL 矩阵</h4>
            <ToolACLMatrix
              selectedTools={selectedTools}
              onChange={setSelectedTools}
              userRole="admin"
            />
          </div>

          {/* 5. 专属端点与复制 */}
          <div className="space-y-2 rounded-md border border-border/60 bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground">专属 MCP 端点</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs font-mono"
                onClick={handleCopyEndpoint}
              >
                {copiedKey ? (
                  <CheckIcon className="mr-1 size-3 text-cyan-500" />
                ) : (
                  <CopyIcon className="mr-1 size-3" />
                )}
                复制
              </Button>
            </div>
            <div className="rounded bg-background p-2 font-mono text-xs text-muted-foreground break-all border border-border/50">
              {endpointUrl}
            </div>
          </div>
        </div>

        {/* 抽屉底部保存栏 */}
        <div className="border-t border-border/60 p-4 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs font-mono"
            onClick={() => onOpenChange(false)}
          >
            取消
          </Button>
          <Button
            size="sm"
            className="h-8 gap-1 text-xs font-mono border border-cyan-500/40 bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50"
            onClick={handleSave}
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending && (
              <RotateCwIcon className="mr-1 size-3 animate-spin" />
            )}
            保存并热生效
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
