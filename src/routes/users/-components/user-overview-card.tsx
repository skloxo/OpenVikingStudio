/**
 * user-overview-card.tsx
 * 用户基础信息与凭据概览卡片 (User Overview Card).
 * 展示所属账号、用户角色、API Key 以及切换身份与重置密钥操作。
 */
import * as React from 'react'
import {
  CopyIcon,
  KeyRoundIcon,
  RotateCwIcon,
  UserCheckIcon,
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

  return (
    <div className="p-3.5 rounded-md border border-border bg-muted/20 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
          <KeyRoundIcon className="size-3.5 text-cyan-500" />
          用户基础凭据
        </span>
        <div className="flex items-center gap-1.5">
          {!isCurrentIdentity && onSwitchIdentity && user && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => onSwitchIdentity(user)}
            >
              <UserCheckIcon className="size-3.5 mr-1 text-cyan-500" />
              切换为此身份
            </Button>
          )}
          {onRegenerateKey && user && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs hover:border-amber-500/50"
              onClick={() => onRegenerateKey(user)}
            >
              <RotateCwIcon className="size-3.5 mr-1" />
              重置密钥
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">所属账号 (Account):</span>
          <p className="font-mono font-medium text-foreground mt-0.5">{user?.accountId || 'default'}</p>
        </div>
        <div>
          <span className="text-muted-foreground">用户角色 (Role):</span>
          <p className="font-medium text-foreground mt-0.5">{user?.role || 'member'}</p>
        </div>
        <div className="sm:col-span-2">
          <span className="text-muted-foreground">API Key:</span>
          <div className="flex items-center gap-2 mt-1">
            <code className="px-2 py-1 rounded bg-background border font-mono text-xs flex-1 truncate">
              {user?.apiKey || (user?.keyPrefix ? `${user.keyPrefix}••••••••` : '暂未配置密钥')}
            </code>
            {user?.apiKey && (
              <Button
                size="icon-xs"
                variant="ghost"
                onClick={() => handleCopy(user.apiKey || '', 'API Key')}
                title="复制 API Key"
              >
                <CopyIcon className="size-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
