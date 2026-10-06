/**
 * user-overview-card.tsx
 * 用户基础信息与凭据概览卡片 (User Overview Card).
 * 采用任务中心 / 技能中心的高密 DetailMetric 风格，平齐对齐，零臃肿装饰。
 */
import {
  CopyIcon,
  KeyRoundIcon,
  RotateCwIcon,
  ShieldIcon,
  UserCheckIcon,
  UsersIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '#/components/ui/button'
import type { AdminUser } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'

export type UserOverviewCardProps = {
  user: AdminUser | null
  isCurrentIdentity: boolean
  onSwitchIdentity?: (user: AdminUser) => void
  onRegenerateKey?: (user: AdminUser) => void
}

export function UserOverviewCard({
  user,
  isCurrentIdentity,
  onSwitchIdentity,
  onRegenerateKey,
}: UserOverviewCardProps) {
  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      toast.success(`已复制 ${label}`)
    } catch {
      toast.error('复制失败')
    }
  }

  const rawKey = user?.apiKey || ''
  const displayKey = rawKey || (user?.keyPrefix ? `${user.keyPrefix}••••••••` : '未暴露明文 (trusted 模式)')

  return (
    <div className="rounded-md border border-border/60 bg-muted/20 p-3 space-y-2.5 font-sans">
      <div className="flex items-center justify-between pb-1.5 border-b border-border/40">
        <span className="text-xs font-semibold text-foreground/90 flex items-center gap-1.5">
          <KeyRoundIcon className="size-3.5 text-cyan-500" />
          用户基础凭据
        </span>
        <div className="flex items-center gap-1.5">
          {!isCurrentIdentity && onSwitchIdentity && user && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-6.5 px-2 text-xs"
              onClick={() => onSwitchIdentity(user)}
            >
              <UserCheckIcon className="size-3 mr-1 text-cyan-500" />
              切换身份
            </Button>
          )}
          {onRegenerateKey && user && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-6.5 px-2 text-xs hover:border-amber-500/50"
              onClick={() => onRegenerateKey(user)}
            >
              <RotateCwIcon className="size-3 mr-1" />
              重置密钥
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        <div className="flex items-center justify-between rounded border border-border/40 bg-background/50 px-2.5 py-1.5">
          <span className="text-muted-foreground flex items-center gap-1.5">
            <UsersIcon className="size-3 text-muted-foreground/80" />
            所属账号:
          </span>
          <span className="font-mono font-medium text-foreground">{user?.accountId || 'default'}</span>
        </div>

        <div className="flex items-center justify-between rounded border border-border/40 bg-background/50 px-2.5 py-1.5">
          <span className="text-muted-foreground flex items-center gap-1.5">
            <ShieldIcon className="size-3 text-muted-foreground/80" />
            用户角色:
          </span>
          <span className="font-mono font-semibold text-foreground uppercase">{user?.role || 'USER'}</span>
        </div>

        <div className="sm:col-span-2 flex items-center justify-between rounded border border-border/40 bg-background/50 px-2.5 py-1.5 gap-2">
          <span className="text-muted-foreground shrink-0 flex items-center gap-1.5">
            <KeyRoundIcon className="size-3 text-muted-foreground/80" />
            API Key:
          </span>
          <code className="font-mono text-xs text-foreground/90 truncate flex-1 text-right select-all">
            {displayKey}
          </code>
          {rawKey ? (
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="size-5 shrink-0"
              onClick={() => handleCopy(rawKey, 'API Key')}
              title="复制 API Key"
            >
              <CopyIcon className="size-3" />
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
