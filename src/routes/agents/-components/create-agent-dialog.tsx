/**
 * create-agent-dialog.tsx
 * 新建智能体对话框组件 (Cockpit UI 规范)。
 * 严守单文件黄金甜点区、NO GREEN EVER 🚫、>= 12px 字体下限。
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CpuIcon,
  GlobeIcon,
  RotateCwIcon,
} from 'lucide-react'
import * as React from 'react'
import { toast } from 'sonner'
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
import type { CreateAgentInput } from '#/lib/admin'
import { createUserAgent } from '#/lib/admin'

export type CreateAgentDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function CreateAgentDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateAgentDialogProps) {
  const queryClient = useQueryClient()

  const [agentName, setAgentName] = React.useState('')
  const [roleDesc, setRoleDesc] = React.useState('')
  const [connectionMode, setConnectionMode] = React.useState('apiClient')

  const createMutation = useMutation({
    mutationFn: async (payload: CreateAgentInput) => {
      return createUserAgent('default', payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cluster-agents'] })
      queryClient.invalidateQueries({ queryKey: ['user-agents'] })
      toast.success('智能体创建成功')
      onOpenChange(false)
      setAgentName('')
      setRoleDesc('')
      onSuccess?.()
    },
    onError: (err: any) => {
      toast.error(`创建失败: ${err.message || '未知错误'}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!agentName.trim()) {
      toast.error('请输入智能体名称')
      return
    }
    createMutation.mutate({
      agent_name: agentName.trim(),
      role_desc: roleDesc.trim() || '智能体助手',
      connection_mode: connectionMode,
      icon: 'terminal',
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md border-border bg-background">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold text-foreground">
            新建集群智能体
          </DialogTitle>
          <DialogDescription className="font-mono text-xs text-muted-foreground">
            分配独立 Agent ID 与 MCP 访问身份，开箱即用。
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-mono">智能体名称</label>
            <Input
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="如：量化风控专家、代码审查员"
              className="h-8 text-xs font-mono"
              autoFocus
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-mono">职责描述</label>
            <Input
              value={roleDesc}
              onChange={(e) => setRoleDesc(e.target.value)}
              placeholder="简要说明该智能体的定位与工作内容"
              className="h-8 text-xs font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground font-mono">默认接入网络拓扑</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                className={`h-8 rounded-md px-2.5 text-xs font-mono transition-all flex items-center justify-center ${
                  connectionMode === 'realtimeApi'
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
                  connectionMode === 'apiClient'
                    ? 'border border-cyan-500/50 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 dark:bg-cyan-950/40 font-medium shadow-xs'
                    : 'border border-border/70 bg-background text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
                onClick={() => setConnectionMode('apiClient')}
              >
                <GlobeIcon className="mr-1.5 size-3.5" />
                公网穿透 (3070)
              </button>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 text-xs font-mono"
              onClick={() => onOpenChange(false)}
            >
              取消
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-8 gap-1 text-xs font-mono border border-cyan-500/40 bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending && (
                <RotateCwIcon className="mr-1 size-3 animate-spin" />
              )}
              立即创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
