/**
 * add-agent-dialog.tsx
 * 签发新智能体身份牌对话框组件。
 * 严守 NO GREEN EVER 🚫、>= 12px 字体下限与单文件黄金甜点区。
 */
import * as React from 'react'
import { GlobeIcon, LaptopIcon } from 'lucide-react'
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
import { Label } from '#/components/ui/label'
import type { CreateAgentInput } from '#/lib/admin'

export type AddAgentDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  userId: string
  isPending: boolean
  onSubmit: (input: CreateAgentInput) => void
}

export function AddAgentDialog({
  open,
  onOpenChange,
  userId,
  isPending,
  onSubmit,
}: AddAgentDialogProps) {
  const [newAgentId, setNewAgentId] = React.useState('')
  const [newRoleDesc, setNewRoleDesc] = React.useState('')
  const [newConnectionMode, setNewConnectionMode] = React.useState<'realtimeApi' | 'apiClient'>('apiClient')

  React.useEffect(() => {
    if (open) {
      setNewAgentId('')
      setNewRoleDesc('')
      setNewConnectionMode('apiClient')
    }
  }, [open])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newAgentId.trim()) {
      toast.error('请输入智能体标识')
      return
    }
    onSubmit({
      agent_id: newAgentId.trim(),
      role_desc:
        newRoleDesc.trim() ||
        (newConnectionMode === 'realtimeApi' ? '本地主控开发助手' : '远程卫星智能体'),
      connection_mode: newConnectionMode,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-card border-border text-card-foreground">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold">签发新智能体身份牌</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              为用户 <span className="font-mono text-foreground font-medium">{userId}</span> 分配新的在籍 Agent 标识。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 py-3">
            <div className="space-y-1.5">
              <Label htmlFor="sheet-agent-id" className="text-xs text-foreground">
                智能体标识 (Agent ID) <span className="text-rose-500">*</span>
              </Label>
              <Input
                id="sheet-agent-id"
                placeholder="例如 cursor@macbook 或 test-bot@node"
                className="h-8 text-xs font-mono"
                value={newAgentId}
                onChange={(e) => setNewAgentId(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="sheet-role-desc" className="text-xs text-foreground">
                角色定位 / 职能描述
              </Label>
              <Input
                id="sheet-role-desc"
                placeholder="例如 自动化测试哨兵、前端结对助手"
                className="h-8 text-xs"
                value={newRoleDesc}
                onChange={(e) => setNewRoleDesc(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-foreground">接入拓扑方式</Label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setNewConnectionMode('realtimeApi')}
                  className={`flex flex-col items-start p-2.5 rounded-md border text-left transition-colors ${
                    newConnectionMode === 'realtimeApi'
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                      : 'border-border bg-background text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    <LaptopIcon className="size-3.5" />
                    <span>本地宿主直连</span>
                  </div>
                  <span className="text-xs text-muted-foreground mt-0.5">同一主机 / WSL 本地直连</span>
                </button>

                <button
                  type="button"
                  onClick={() => setNewConnectionMode('apiClient')}
                  className={`flex flex-col items-start p-2.5 rounded-md border text-left transition-colors ${
                    newConnectionMode === 'apiClient'
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                      : 'border-border bg-background text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    <GlobeIcon className="size-3.5" />
                    <span>网络远程卫星</span>
                  </div>
                  <span className="text-xs text-muted-foreground mt-0.5">跨机器 / 远程节点反代网关</span>
                </button>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2">
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
              {isPending ? '正在签发...' : '确认签发并获取接入令'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
