/**
 * route.tsx
 * 用户管理路由入口与控制台容器。
 * 遵循 Agent 编码规范与黄金甜点区（<= 300 行）。
 */
import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import {
  KeyRoundIcon,
  LoaderCircleIcon,
  PlusIcon,
  RefreshCwIcon,
  UsersRoundIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { useAppConnection } from '#/hooks/use-app-connection'
import {
  createAdminUser,
  fetchAdminUsers,
  regenerateAdminUserKey,
  removeAdminUser,
  updateAdminUserRole,
} from '#/lib/admin'
import type {
  AdminConnection,
  AdminUser,
  CreateUserInput,
  KeyResult,
  UpdateUserRoleInput,
} from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'
import { resolveStudioManagementCapabilities } from '#/lib/studio-permissions'

import { AddUserDialog } from './-components/add-user-dialog'
import { UserManagementDialogs } from './-components/user-management-dialogs'
import { UserTable } from './-components/user-table'
import { getErrorMessage } from './-lib/user-utils'

export const Route = createFileRoute('/users')({
  component: UserManagementRoute,
})

function UserManagementRoute() {
  const { t } = useTranslation('settings')
  const queryClient = useQueryClient()
  const {
    connection,
    connectionRole,
    isConnectionRoleLoading,
    serverMode,
    setGeneratedCredential,
    switchIdentity,
  } = useAppConnection()

  const [addUserOpen, setAddUserOpen] = React.useState(false)
  const [pendingRegenerateUser, setPendingRegenerateUser] =
    React.useState<AdminUser | null>(null)
  const [pendingRemoveUser, setPendingRemoveUser] =
    React.useState<AdminUser | null>(null)
  const [pendingRoleChange, setPendingRoleChange] =
    React.useState<UpdateUserRoleInput | null>(null)
  const [switchingIdentityKey, setSwitchingIdentityKey] = React.useState('')

  const { canManageAccounts, canManageUsers } =
    resolveStudioManagementCapabilities({
      hasControlCredential: Boolean(connection.adminApiKey.trim()),
      isRoleLoading: isConnectionRoleLoading,
      role: connectionRole,
      serverMode,
    })

  const adminConnection = React.useMemo<AdminConnection>(
    () => ({
      accountId: connection.accountId,
      apiKey: connection.adminApiKey,
      baseUrl: connection.baseUrl,
      userId: connection.userId,
    }),
    [
      connection.accountId,
      connection.adminApiKey,
      connection.baseUrl,
      connection.userId,
    ],
  )

  const usersQuery = useQuery<AdminUser[], Error>({
    enabled: canManageUsers && Boolean(connection.accountId),
    queryFn: () => fetchAdminUsers(adminConnection, connection.accountId),
    queryKey: [
      'managed-users',
      adminConnection.baseUrl,
      adminConnection.apiKey,
      connection.accountId,
    ],
    retry: false,
  })

  const createUser = useMutation({
    mutationFn: (input: CreateUserInput) =>
      createAdminUser(adminConnection, input),
    onError: (error) => toast.error(getErrorMessage(error)),
    onSuccess: async (result, input) => {
      setGeneratedCredential(result)
      setAddUserOpen(false)
      if (result.apiKey) {
        try {
          await switchIdentity({
            accountId: result.accountId || input.accountId,
            allowLegacyIdentityFallback: true,
            apiKey: result.apiKey,
            userId: result.userId || input.userId,
          })
        } catch (error) {
          toast.error(getErrorMessage(error))
        }
      }
      toast.success(t('toast.userCreated'))
      await queryClient.invalidateQueries({ queryKey: ['managed-users'] })
      await queryClient.invalidateQueries({ queryKey: ['account-switcher'] })
    },
  })

  const regenerateKey = useMutation({
    mutationFn: (user: AdminUser) =>
      regenerateAdminUserKey(adminConnection, user.accountId, user.userId),
    onError: (error) => toast.error(getErrorMessage(error)),
    onSuccess: async (result, user) => {
      setGeneratedCredential(result)
      setPendingRegenerateUser(null)
      if (
        user.accountId === connection.accountId &&
        user.userId === connection.userId &&
        result.apiKey
      ) {
        await switchIdentity({
          accountId: user.accountId,
          allowLegacyIdentityFallback: true,
          apiKey: result.apiKey,
          userId: user.userId,
        })
      }
      toast.success(t('toast.keyRegenerated'))
      await queryClient.invalidateQueries({ queryKey: ['managed-users'] })
    },
  })

  const updateRole = useMutation({
    mutationFn: (input: UpdateUserRoleInput) =>
      updateAdminUserRole(adminConnection, input),
    onError: (error) => toast.error(getErrorMessage(error)),
    onSuccess: async (_, input) => {
      setPendingRoleChange(null)
      toast.success(
        t('toast.roleUpdated', {
          role: t(`roles.${input.role}`),
          user: input.userId,
        }),
      )
      await queryClient.invalidateQueries({ queryKey: ['managed-users'] })
    },
  })

  const removeUser = useMutation({
    mutationFn: (user: AdminUser) =>
      removeAdminUser(adminConnection, user.accountId, user.userId),
    onError: (error) => toast.error(getErrorMessage(error)),
    onSuccess: async (_, user) => {
      setPendingRemoveUser(null)
      toast.success(t('toast.userRemoved', { user: user.userId }))
      await queryClient.invalidateQueries({ queryKey: ['managed-users'] })
      await queryClient.invalidateQueries({ queryKey: ['account-switcher'] })
    },
  })

  async function copyKey(value: string | undefined): Promise<void> {
    if (!value) return
    try {
      await copyTextToClipboard(value)
      toast.success(t('toast.copied'))
    } catch {
      toast.error(t('toast.copyFailed'))
    }
  }

  async function useUserIdentity(user: AdminUser | KeyResult): Promise<void> {
    if (serverMode !== 'trusted' && !user.apiKey) {
      toast.error(t('management.noUsableKey'))
      return
    }
    const accountId = user.accountId || connection.accountId
    const userId = user.userId || connection.userId
    const identityKey = `${accountId}:${userId}`
    setSwitchingIdentityKey(identityKey)
    try {
      await switchIdentity({
        accountId,
        allowLegacyIdentityFallback: true,
        apiKey: user.apiKey || '',
        userId,
      })
      toast.success(t('toast.dataKeySelected'))
    } catch (error) {
      toast.error(getErrorMessage(error))
    } finally {
      setSwitchingIdentityKey('')
    }
  }

  if (isConnectionRoleLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center gap-2 text-sm text-muted-foreground">
        <LoaderCircleIcon className="size-4 animate-spin" />
        {t('loading')}
      </div>
    )
  }

  if (serverMode === 'dev' || usersQuery.isError) {
    return (
      <Card className="mx-auto mt-8 w-full max-w-xl rounded border border-border/70 p-6 text-center shadow-xs">
        <CardHeader className="items-center p-0">
          <div className="mb-3 flex size-12 items-center justify-center rounded-xs border border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <KeyRoundIcon className="size-5" />
          </div>
          <CardTitle className="text-base font-semibold">
            {t('management.devModeNoticeTitle', {
              defaultValue: '当前运行于单用户开发模式 (Dev Mode)',
            })}
          </CardTitle>
          <CardDescription className="mt-2 text-xs leading-relaxed text-muted-foreground">
            {t('management.devModeNoticeDesc', {
              defaultValue:
                'OpenViking 服务端目前处于开发模式 (auth_mode = "dev")，开发模式下所有 API 开箱即用无需凭证校验，但不提供多租户 API Key 与用户增删改查。如需体验多用户与密钥管理，请在 ov.conf 中配置 server.auth_mode = "api_key" 并重启后端。',
            })}
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-4 flex justify-center p-0">
          <Button
            size="sm"
            variant="outline"
            className="rounded-xs text-xs"
            nativeButton={false}
            render={<Link to="/settings" />}
          >
            <KeyRoundIcon className="size-3.5" />
            {t('management.openConnection')}
          </Button>
        </CardContent>
      </Card>
    )
  }

  const users = usersQuery.data ?? []
  const managerCount = users.filter(
    (user) => user.role === 'admin' || user.role === 'root',
  ).length
  const visibleKeys = users.filter(
    (user) => user.apiKey || user.keyPrefix,
  ).length

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {t('management.title')}
            </h1>
            <Badge variant="secondary" className="max-w-72 truncate font-mono">
              {connection.accountId}
            </Badge>
          </div>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            {t('management.currentAccountDescription', {
              account: connection.accountId,
            })}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => void usersQuery.refetch()}
            disabled={usersQuery.isFetching}
          >
            <RefreshCwIcon
              className={usersQuery.isFetching ? 'animate-spin' : undefined}
            />
            {t('actions.refresh')}
          </Button>
          <Button type="button" onClick={() => setAddUserOpen(true)}>
            <PlusIcon />
            {t('actions.addUser')}
          </Button>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="bg-card/70 py-4">
          <CardContent className="flex items-center justify-between gap-4 px-5">
            <div>
              <p className="text-sm text-muted-foreground">
                {t('stats.users')}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {users.length || '-'}
              </p>
            </div>
            <div className="flex size-10 items-center justify-center rounded-md border bg-background/70 text-primary">
              <UsersRoundIcon className="size-4" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/70 py-4">
          <CardContent className="flex items-center justify-between gap-4 px-5">
            <div>
              <p className="text-sm text-muted-foreground">
                {t('stats.apiKeys')}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {visibleKeys || '-'}
              </p>
            </div>
            <div className="flex size-10 items-center justify-center rounded-md border bg-background/70 text-primary">
              <KeyRoundIcon className="size-4" />
            </div>
          </CardContent>
        </Card>
      </div>

      <UserTable
        canManageAccounts={canManageAccounts}
        connection={connection}
        error={usersQuery.error}
        isError={usersQuery.isError}
        isLoading={usersQuery.isLoading}
        isRegeneratePending={regenerateKey.isPending}
        isRemovePending={removeUser.isPending}
        isRoleUpdating={updateRole.isPending}
        managerCount={managerCount}
        onCopyKey={(key) => void copyKey(key)}
        onInitiateRegenerate={(user) => setPendingRegenerateUser(user)}
        onInitiateRemove={(user) => setPendingRemoveUser(user)}
        onInitiateRoleChange={(input) => setPendingRoleChange(input)}
        onUseUserIdentity={(user) => void useUserIdentity(user)}
        serverMode={serverMode}
        switchingIdentityKey={switchingIdentityKey}
        users={users}
      />

      <AddUserDialog
        open={addUserOpen}
        onOpenChange={setAddUserOpen}
        accountId={connection.accountId}
        isPending={createUser.isPending}
        onCreate={(input) => createUser.mutate(input)}
      />

      <UserManagementDialogs
        isRegenerating={regenerateKey.isPending}
        isRemoving={removeUser.isPending}
        isUpdatingRole={updateRole.isPending}
        onConfirmRegenerate={(user) => regenerateKey.mutate(user)}
        onConfirmRemove={(user) => removeUser.mutate(user)}
        onConfirmRoleChange={(input) => updateRole.mutate(input)}
        onPendingRegenerateChange={setPendingRegenerateUser}
        onPendingRemoveChange={setPendingRemoveUser}
        onPendingRoleChange={setPendingRoleChange}
        pendingRegenerateUser={pendingRegenerateUser}
        pendingRemoveUser={pendingRemoveUser}
        pendingRoleChange={pendingRoleChange}
      />
    </div>
  )
}
