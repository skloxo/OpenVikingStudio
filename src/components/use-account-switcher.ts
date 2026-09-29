import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { useAppConnection } from '#/hooks/use-app-connection'
import {
  createAdminAccount,
  fetchAdminAccounts,
  fetchAdminUsers,
} from '#/lib/admin'
import type {
  AdminConnection,
  AdminUser,
  CreateAccountInput,
} from '#/lib/admin'
import { DEFAULT_USER_ID } from '#/lib/admin-options'
import { resolveStudioManagementCapabilities } from '#/lib/studio-permissions'
import type { ManualSwitchState } from './account-switcher-dialogs'

export function selectAccountUser(
  users: readonly AdminUser[],
  _currentUserId: string,
  requireApiKey: boolean,
): AdminUser | undefined {
  const candidates = requireApiKey
    ? users.filter((user) => Boolean(user.apiKey))
    : [...users]
  return candidates[0]
}

export function useAccountSwitcher() {
  const { t } = useTranslation('accountSwitcher')
  const queryClient = useQueryClient()
  const {
    connection,
    connectionRole,
    isConnectionRoleLoading,
    setGeneratedCredential,
    serverMode,
    switchIdentity,
    switchManagementAccount,
  } = useAppConnection()

  const [open, setOpen] = React.useState(false)
  const [createOpen, setCreateOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')
  const [switchingAccountId, setSwitchingAccountId] = React.useState('')
  const [manualSwitch, setManualSwitch] =
    React.useState<ManualSwitchState | null>(null)
  const [createDraft, setCreateDraft] = React.useState<CreateAccountInput>({
    accountId: '',
    adminUserId: DEFAULT_USER_ID,
  })

  const { canManageAccounts } = resolveStudioManagementCapabilities({
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

  const accountsQuery = useQuery({
    enabled: canManageAccounts && open && serverMode !== 'dev',
    queryFn: () => fetchAdminAccounts(adminConnection),
    queryKey: [
      'account-switcher',
      adminConnection.baseUrl,
      adminConnection.apiKey,
    ],
    retry: false,
  })

  const filteredAccounts = React.useMemo(() => {
    if (serverMode === 'dev') {
      return [{ accountId: connection.accountId || 'default', userCount: 1 }]
    }
    const normalizedSearch = search.trim().toLowerCase()
    const accounts = accountsQuery.data ?? []
    if (!normalizedSearch) {
      return accounts
    }
    return accounts.filter((account) =>
      account.accountId.toLowerCase().includes(normalizedSearch),
    )
  }, [accountsQuery.data, connection.accountId, search, serverMode])

  async function selectAccount(accountId: string): Promise<void> {
    if (accountId === connection.accountId) {
      setOpen(false)
      return
    }

    setSwitchingAccountId(accountId)
    try {
      const users = await fetchAdminUsers(adminConnection, accountId)
      const firstUser = selectAccountUser(users, connection.userId, false)
      if (!firstUser) {
        throw new Error(t('errors.noUsers'))
      }

      const candidates =
        serverMode === 'api_key'
          ? users.filter((user) => Boolean(user.apiKey))
          : [firstUser]
      let switchError: unknown
      for (const user of candidates) {
        try {
          await switchIdentity({
            accountId,
            allowLegacyIdentityFallback: true,
            apiKey: user.apiKey || '',
            userId: user.userId,
          })
          setOpen(false)
          toast.success(
            t('toast.switched', {
              account: accountId,
            }),
          )
          return
        } catch (error) {
          switchError = error
        }
      }

      if (serverMode === 'api_key') {
        setOpen(false)
        setManualSwitch({
          accountId,
          apiKey: '',
          userId: firstUser.userId,
        })
        return
      }
      throw switchError
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error))
    } finally {
      setSwitchingAccountId('')
    }
  }

  const createAccount = useMutation({
    mutationFn: (input: CreateAccountInput) =>
      createAdminAccount(adminConnection, input),
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : String(error)),
    onSuccess: async (result, input) => {
      const accountId = result.accountId || input.accountId
      const userId = result.userId || input.adminUserId
      if (result.apiKey) {
        setGeneratedCredential({
          accountId,
          apiKey: result.apiKey,
          userId,
        })
      }
      setCreateOpen(false)
      setOpen(false)
      setCreateDraft({ accountId: '', adminUserId: DEFAULT_USER_ID })
      void queryClient.invalidateQueries({ queryKey: ['account-switcher'] })

      if (!result.apiKey && serverMode === 'api_key') {
        await switchManagementAccount(accountId)
        toast.warning(t('errors.noCreatedKey'))
        return
      }

      try {
        await switchIdentity({
          accountId,
          allowLegacyIdentityFallback: true,
          apiKey: result.apiKey,
          userId,
        })
        toast.success(t('toast.created', { account: input.accountId }))
      } catch (error) {
        await switchManagementAccount(accountId)
        toast.error(
          t('toast.createdSwitchFailed', {
            account: input.accountId,
            error: error instanceof Error ? error.message : String(error),
          }),
        )
      }
    },
  })

  const hasAuthKeys = Boolean(
    connection.adminApiKey.trim() || connection.apiKey.trim(),
  )
  const accountLabel = hasAuthKeys
    ? connection.accountId || 'default'
    : t('unset', { defaultValue: '未验证身份 (Unauthenticated)' })

  return {
    connection,
    canManageAccounts,
    accountLabel,
    open,
    setOpen,
    createOpen,
    setCreateOpen,
    search,
    setSearch,
    switchingAccountId,
    setSwitchingAccountId,
    manualSwitch,
    setManualSwitch,
    createDraft,
    setCreateDraft,
    accountsQuery,
    filteredAccounts,
    selectAccount,
    createAccount,
    switchIdentity,
    switchManagementAccount,
  }
}
