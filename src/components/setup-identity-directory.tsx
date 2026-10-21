import * as React from 'react'
import { AlertCircle, RefreshCw, ShieldCheck, UserCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { ConnectionDraft } from '#/hooks/app-connection-types'
import { createConnectionHealthHeaders } from '#/hooks/app-connection-utils'
import { fetchServerHealth } from '#/hooks/use-server-mode'
import { Alert, AlertDescription, AlertTitle } from '#/components/ui/alert'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Label } from '#/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  fetchAdminAccounts,
  fetchAdminUserDirectory,
  type AdminAccount,
  type AdminUser,
} from '#/lib/admin'

export interface SetupIdentityDirectoryProps {
  connection: ConnectionDraft
  disabled?: boolean
  onChange: (patch: Partial<ConnectionDraft>) => void
}

export function SetupIdentityDirectory({
  connection,
  disabled = false,
  onChange,
}: SetupIdentityDirectoryProps) {
  const { t } = useTranslation('settings')
  const [accounts, setAccounts] = React.useState<AdminAccount[]>([])
  const [users, setUsers] = React.useState<AdminUser[]>([])
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [identityMismatch, setIdentityMismatch] = React.useState(false)

  const adminApiKey = connection.adminApiKey?.trim() || ''
  const baseUrl = connection.baseUrl?.trim() || ''
  const accountId = connection.accountId?.trim() || ''
  const userId = connection.userId?.trim() || ''

  const loadDirectory = React.useCallback(async () => {
    if (!baseUrl || !adminApiKey) {
      setAccounts([])
      setUsers([])
      setError(null)
      setIdentityMismatch(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const adminConn = {
        baseUrl,
        apiKey: adminApiKey,
        accountId: 'root',
        userId: 'admin',
      }

      // 1. 获取所有账户
      const accountList = await fetchAdminAccounts(adminConn)
      setAccounts(accountList)

      // 2. 检查或选定有效账户
      const targetAccountId =
        accountId && accountList.some((acc) => acc.accountId === accountId)
          ? accountId
          : accountList[0]?.accountId || ''

      if (targetAccountId && targetAccountId !== accountId) {
        onChange({ accountId: targetAccountId })
      }

      // 3. 获取目标账户下用户
      if (targetAccountId) {
        const userList = await fetchAdminUserDirectory(adminConn, targetAccountId)
        setUsers(userList)

        const targetUserId =
          userId && userList.some((u) => u.userId === userId)
            ? userId
            : userList[0]?.userId || ''

        if (targetUserId && targetUserId !== userId) {
          onChange({ userId: targetUserId })
        }
      } else {
        setUsers([])
      }

      // 4. 验证受信任身份一致性 (Health check)
      try {
        const headers = createConnectionHealthHeaders(connection, 'admin')
        const health = await fetchServerHealth(baseUrl, headers)
        if (health?.mode === 'multi_user' && health?.admin_user) {
          const isMismatch =
            Boolean(accountId && accountId !== health.admin_user.account_id) ||
            Boolean(userId && userId !== health.admin_user.user_id)
          setIdentityMismatch(isMismatch)
        } else {
          setIdentityMismatch(false)
        }
      } catch {
        // 健康检查异常不阻断目录展示
        setIdentityMismatch(false)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [adminApiKey, baseUrl, accountId, userId, connection, onChange])

  React.useEffect(() => {
    void loadDirectory()
  }, [adminApiKey, baseUrl])

  if (!adminApiKey) {
    return null
  }

  return (
    <div className="space-y-4 rounded-lg border border-border/60 bg-muted/20 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-cyan-500" />
          <span className="text-xs font-semibold text-foreground">
            {t('connectionPage.directoryHint', '受信任身份目录 (Trusted Identity Directory)')}
          </span>
          <Badge
            variant="outline"
            className="border-cyan-500/30 bg-cyan-500/10 text-xs font-mono text-cyan-400"
          >
            RBAC Ready
          </Badge>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
          disabled={disabled || loading}
          onClick={() => void loadDirectory()}
        >
          <RefreshCw className={`mr-1 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('refresh', '刷新')}
        </Button>
      </div>

      <div className="text-xs text-muted-foreground">
        {t(
          'connectionPage.directoryAdminHint',
          '使用管理秘钥 (Admin Key) 探测多租户目录，直接点选目标账户与数据归属用户。',
        )}
      </div>

      {error ? (
        <Alert variant="destructive" className="py-2 text-xs">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle className="text-xs font-medium">
            {t('connectionPage.directoryLoadFailed', '加载身份目录失败')}
          </AlertTitle>
          <AlertDescription className="text-xs">{error}</AlertDescription>
        </Alert>
      ) : null}

      {identityMismatch ? (
        <Alert className="border-amber-500/30 bg-amber-500/10 py-2 text-xs text-amber-300">
          <AlertCircle className="h-4 w-4 text-amber-400" />
          <AlertTitle className="text-xs font-medium">
            {t('connectionPage.directoryIdentityMismatch', '当前选择的身份与管理令牌默认身份不一致')}
          </AlertTitle>
          <AlertDescription className="text-xs">
            {t(
              'connectionPage.directoryKeyHint',
              '此模式将以所选受信任身份执行数据操作。请确认该身份在服务端具备足够权限。',
            )}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-foreground">
            {t('connectionPage.directoryAccount', '目标账户 (Account)')}
          </Label>
          <Select
            disabled={disabled || loading || accounts.length === 0}
            value={accountId}
            onValueChange={(val) => {
              onChange({ accountId: val, userId: '' })
            }}
          >
            <SelectTrigger className="h-8 text-xs font-mono">
              <SelectValue placeholder={t('connectionPage.selectAccount', '选择账户...')} />
            </SelectTrigger>
            <SelectContent>
              {accounts.map((acc) => (
                <SelectItem key={acc.accountId} value={acc.accountId} className="text-xs font-mono">
                  {acc.accountId} ({acc.userCount ?? 0} users)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-foreground">
            {t('connectionPage.directoryUser', '归属用户 (User)')}
          </Label>
          <Select
            disabled={disabled || loading || users.length === 0}
            value={userId}
            onValueChange={(val) => {
              onChange({ userId: val })
            }}
          >
            <SelectTrigger className="h-8 text-xs font-mono">
              <SelectValue placeholder={t('connectionPage.selectUser', '选择用户...')} />
            </SelectTrigger>
            <SelectContent>
              {users.map((u) => (
                <SelectItem key={u.userId} value={u.userId} className="text-xs font-mono">
                  <div className="flex items-center gap-1.5">
                    <UserCheck className="h-3 w-3 text-cyan-500" />
                    <span>{u.userId}</span>
                    <span className="text-muted-foreground">({u.role})</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )
}
