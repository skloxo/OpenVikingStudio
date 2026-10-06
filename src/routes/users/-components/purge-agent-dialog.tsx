/**
 * purge-agent-dialog.tsx
 * 彻底物理删除智能体确认对话框组件。
 * 严守 NO GREEN EVER 🚫、>= 12px 字体下限与单文件黄金甜点区。
 */

import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import type { UserAgentItem } from '#/lib/admin'

export type PurgeAgentDialogProps = {
  agent: UserAgentItem | null
  isPending: boolean
  onClose: () => void
  onConfirm: (agentId: string) => void
}

export function PurgeAgentDialog({
  agent,
  isPending,
  onClose,
  onConfirm,
}: PurgeAgentDialogProps) {
  return (
    <Dialog open={Boolean(agent)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-sm bg-card border-border text-card-foreground">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold text-rose-500">
            确认彻底删除智能体？
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground mt-1">
            将从数据库中物理抹除{' '}
            <span className="font-mono text-foreground font-semibold">
              {agent?.agent_id}
            </span>{' '}
            的授权凭牌记录。此操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 mt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="text-xs h-8"
            onClick={onClose}
          >
            取消
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            className="text-xs h-8"
            disabled={isPending}
            onClick={() => agent && onConfirm(agent.agent_id)}
          >
            {isPending ? '正在删除...' : '彻底物理删除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
