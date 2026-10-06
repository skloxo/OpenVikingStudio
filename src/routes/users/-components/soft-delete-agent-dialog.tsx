/**
 * soft-delete-agent-dialog.tsx
 * 智能体软删除确认对话框。
 * 明确告知软删除安全机制：历史数据存档，新调用报 ID 不存在或凭证失效。
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

export type SoftDeleteAgentDialogProps = {
  agent: UserAgentItem | null
  isPending: boolean
  onClose: () => void
  onConfirm: (agentId: string) => void
}

export function SoftDeleteAgentDialog({
  agent,
  isPending,
  onClose,
  onConfirm,
}: SoftDeleteAgentDialogProps) {
  return (
    <Dialog open={Boolean(agent)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border text-card-foreground">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold text-rose-500">
            确认下线并软删除此智能体？
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground mt-1.5 space-y-2">
            <div>
              正在软删除：
              <span className="font-semibold text-foreground">
                {agent?.agent_name || agent?.agent_id}
              </span>{' '}
              (永久身份证: <code className="font-mono text-foreground">{agent?.agent_id}</code>)
            </div>
            <div className="p-2.5 rounded-md bg-muted/40 border border-border text-xs leading-relaxed">
              🛡️ <span className="font-medium text-foreground">软删除物理防线：</span>
              删除后，历史交互数据与审计记录将被完整安全存档；该智能体若继续使用此唯一身份证和密钥请求 MCP，系统将直接响应{' '}
              <code className="text-rose-500 font-mono">ID 不存在或凭证失效</code>。
            </div>
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
            {isPending ? '正在下线...' : '确认软删除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
