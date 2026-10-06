/**
 * agent-form-dialog.tsx
 * 智能体身份牌签发与工具权限配置对话框 (Create / Edit Modal)。
 * 严守 NO GREEN EVER 🚫、>= 12px 字体下限与单文件黄金甜点区。
 */
import * as React from 'react'
import { CheckIcon, GlobeIcon, LaptopIcon, ShieldCheckIcon } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import type { CreateAgentInput, UpdateAgentInput, UserAgentItem } from '#/lib/admin'
import { DEFAULT_TOOL_IDS, TOOL_CATEGORIES } from '../-constants/agent-tools'

export type AgentFormDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  userId: string
  initialAgent?: UserAgentItem | null
  isPending: boolean
  onSubmit: (data: { create?: CreateAgentInput; update?: UpdateAgentInput }) => void
}

export function AgentFormDialog({
  open,
  onOpenChange,
  userId,
  initialAgent,
  isPending,
  onSubmit,
}: AgentFormDialogProps) {
  const isEditing = Boolean(initialAgent)

  const [agentName, setAgentName] = React.useState('')
  const [roleDesc, setRoleDesc] = React.useState('')
  const [connectionMode, setConnectionMode] = React.useState<'realtimeApi' | 'apiClient'>('apiClient')
  const [selectedTools, setSelectedTools] = React.useState<string[]>(DEFAULT_TOOL_IDS)

  React.useEffect(() => {
    if (open) {
      if (initialAgent) {
        setAgentName(initialAgent.agent_name || initialAgent.agent_id)
        setRoleDesc(initialAgent.role_desc)
        setConnectionMode(initialAgent.connection_mode === 'realtimeApi' ? 'realtimeApi' : 'apiClient')
        setSelectedTools(initialAgent.allowed_tools.length > 0 ? initialAgent.allowed_tools : DEFAULT_TOOL_IDS)
      } else {
        setAgentName('')
        setRoleDesc('')
        setConnectionMode('apiClient')
        setSelectedTools(DEFAULT_TOOL_IDS)
      }
    }
  }, [open, initialAgent])

  const toggleTool = (toolId: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId],
    )
  }

  const toggleCategory = (catToolIds: string[]) => {
    const allSelected = catToolIds.every((id) => selectedTools.includes(id))
    if (allSelected) {
      setSelectedTools((prev) => prev.filter((id) => !catToolIds.includes(id)))
    } else {
      setSelectedTools((prev) => Array.from(new Set([...prev, ...catToolIds])))
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!agentName.trim()) {
      toast.error('请输入智能体自定义名称')
      return
    }

    if (isEditing && initialAgent) {
      onSubmit({
        update: {
          agent_name: agentName.trim(),
          role_desc: roleDesc.trim(),
          connection_mode: connectionMode,
          allowed_tools: selectedTools,
        },
      })
    } else {
      onSubmit({
        create: {
          agent_name: agentName.trim(),
          role_desc: roleDesc.trim() || (connectionMode === 'realtimeApi' ? '本地宿主助手' : '远程卫星助手'),
          connection_mode: connectionMode,
          allowed_tools: selectedTools,
        },
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto bg-card border-border text-card-foreground">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold">
              {isEditing ? '配置智能体信息与工具权限' : '签发新智能体身份牌'}
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              归属租户用户：<span className="font-mono text-foreground font-medium">{userId}</span>
              {isEditing && initialAgent && (
                <span className="ml-2">
                  (系统唯一身份证: <code className="font-mono text-foreground">{initialAgent.agent_id}</code>)
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            {/* 智能体自定义名称 */}
            <div className="space-y-1.5">
              <Label htmlFor="form-agent-name" className="text-xs text-foreground">
                智能体名称 (自定义可改) <span className="text-rose-500">*</span>
              </Label>
              <Input
                id="form-agent-name"
                placeholder="例如 前端结对助手、RTX 3070 巡检小助手"
                className="h-8 text-xs"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                autoFocus
              />
            </div>

            {/* 唯一身份证提示 */}
            {!isEditing && (
              <div className="p-2.5 rounded-md bg-muted/40 border border-border/80 text-xs text-muted-foreground flex items-center justify-between">
                <div>
                  <span className="font-medium text-foreground">系统唯一身份 ID：</span>
                  <span className="ml-1 font-mono">创建时自动生成（不可变更）</span>
                </div>
                <Badge variant="outline" className="text-xs font-mono">ag_auto</Badge>
              </div>
            )}

            {/* 角色定位 */}
            <div className="space-y-1.5">
              <Label htmlFor="form-role-desc" className="text-xs text-foreground">
                角色定位 / 职能描述
              </Label>
              <Input
                id="form-role-desc"
                placeholder="例如 自动化编译巡检、代码审查"
                className="h-8 text-xs"
                value={roleDesc}
                onChange={(e) => setRoleDesc(e.target.value)}
              />
            </div>

            {/* 拓扑方式 */}
            <div className="space-y-1.5">
              <Label className="text-xs text-foreground">接入拓扑方式</Label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setConnectionMode('realtimeApi')}
                  className={`flex flex-col items-start p-2.5 rounded-md border text-left transition-colors ${
                    connectionMode === 'realtimeApi'
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                      : 'border-border bg-background text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    <LaptopIcon className="size-3.5" />
                    <span>本地宿主直连</span>
                  </div>
                  <span className="text-xs text-muted-foreground mt-0.5">同一主机 / 本地进程直连 (1933)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setConnectionMode('apiClient')}
                  className={`flex flex-col items-start p-2.5 rounded-md border text-left transition-colors ${
                    connectionMode === 'apiClient'
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                      : 'border-border bg-background text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    <GlobeIcon className="size-3.5" />
                    <span>网络远程卫星</span>
                  </div>
                  <span className="text-xs text-muted-foreground mt-0.5">跨机器 / 远程节点网关</span>
                </button>
              </div>
            </div>

            {/* 工具权限分类勾选矩阵 (Tool ACL) */}
            <div className="space-y-2 pt-1 border-t border-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <ShieldCheckIcon className="size-3.5 text-cyan-500" />
                  <Label className="text-xs font-medium text-foreground">
                    工具授权矩阵 (Tool ACL)
                  </Label>
                </div>
                <span className="text-xs font-mono text-muted-foreground">
                  已勾选 {selectedTools.length} 项工具
                </span>
              </div>

              <div className="space-y-2.5">
                {TOOL_CATEGORIES.map((cat) => {
                  const catToolIds = cat.tools.map((t) => t.id)
                  const isAllCatSelected = catToolIds.every((id) => selectedTools.includes(id))

                  return (
                    <div key={cat.id} className="p-2.5 rounded-md border border-border bg-muted/20 space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-xs font-medium text-foreground">{cat.name}</div>
                          <div className="text-xs text-muted-foreground">{cat.description}</div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 px-1.5 text-xs text-cyan-600 hover:text-cyan-700 hover:bg-cyan-500/10"
                          onClick={() => toggleCategory(catToolIds)}
                        >
                          {isAllCatSelected ? '取消该类' : '全选该类'}
                        </Button>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                        {cat.tools.map((tool) => {
                          const isChecked = selectedTools.includes(tool.id)
                          return (
                            <button
                              key={tool.id}
                              type="button"
                              onClick={() => toggleTool(tool.id)}
                              className={`flex items-start gap-2 p-1.5 rounded border text-left transition-colors text-xs ${
                                isChecked
                                  ? 'border-cyan-500/40 bg-cyan-500/5 text-foreground'
                                  : 'border-border/60 bg-background text-muted-foreground hover:bg-muted/40'
                              }`}
                            >
                              <div
                                className={`size-3.5 rounded flex items-center justify-center border mt-0.5 shrink-0 ${
                                  isChecked
                                    ? 'bg-cyan-500 border-cyan-500 text-white'
                                    : 'border-border bg-background'
                                }`}
                              >
                                {isChecked && <CheckIcon className="size-2.5 stroke-3" />}
                              </div>
                              <div className="min-w-0">
                                <div className="font-mono font-medium truncate">{tool.name}</div>
                                <div className="text-xs text-muted-foreground truncate">{tool.description}</div>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 pt-2 border-t border-border/60">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-xs h-8"
              onClick={() => onOpenChange(false)}
            >
              取消
            </Button>
            <Button
              type="submit"
              size="sm"
              className="text-xs h-8"
              disabled={isPending}
            >
              {isPending
                ? '保存中...'
                : isEditing
                  ? '保存配置'
                  : '确认签发并获取接入令'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
