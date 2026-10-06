/**
 * user-table.tsx
 * 用户管理列表表格组件。
 * 展示账户下的用户成员、在册智能体概览、角色配置、API 密钥以及身份切换和删除操作。
 * 点击整行直接滑出用户专属详情与资产抽屉。
 */
import { useQuery } from '@tanstack/react-query'
import {
  BotIcon,
  CheckIcon,
  CopyIcon,
  KeyRoundIcon,
  LoaderCircleIcon,
  RotateCwIcon,
  Trash2Icon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '#/components/ui/tooltip'
import type { AdminUser, UpdateUserRoleInput } from '#/lib/admin'
import { fetchUserAgentCounts } from '#/lib/admin'
import {
  USER_ROLE_OPTIONS,
  getErrorMessage,
  isAdminUserRole,
  resolveKeyLabel,
} from '../-lib/user-utils'

export type UserTableProps = {
  canManageAccounts: boolean
  connection: { accountId: string; userId: string }
  error: unknown
  isError: boolean
  isLoading: boolean
  isRegeneratePending: boolean
  isRemovePending: boolean
  isRoleUpdating: boolean
  managerCount: number
  onCopyKey: (key: string | undefined) => void
  onInitiateRegenerate: (user: AdminUser) => void
  onInitiateRemove: (user: AdminUser) => void
  onInitiateRoleChange: (input: UpdateUserRoleInput) => void
  onSelectUser?: (user: AdminUser) => void
  onUseUserIdentity: (user: AdminUser) => void
  serverMode?: string
  switchingIdentityKey: string
  users: AdminUser[]
}

export function UserTable({
  canManageAccounts,
  connection,
  error,
  isError,
  isLoading,
  isRegeneratePending,
  isRemovePending,
  isRoleUpdating,
  managerCount,
  onCopyKey,
  onInitiateRegenerate,
  onInitiateRemove,
  onInitiateRoleChange,
  onSelectUser,
  onUseUserIdentity,
  serverMode,
  switchingIdentityKey,
  users,
}: UserTableProps) {
  const { t } = useTranslation('settings')

  // 动态读取每个用户的在册智能体数量
  const { data: agentCounts = {} } = useQuery({
    queryKey: ['user-agent-counts'],
    queryFn: fetchUserAgentCounts,
    staleTime: 10_000,
  })

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b bg-muted/20">
        <CardTitle>{t('management.memberListTitle')}</CardTitle>
        <CardDescription>
          {t(
            canManageAccounts
              ? 'management.memberListDescriptionRoot'
              : 'management.memberListDescription',
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin" />
            {t('loading')}
          </div>
        ) : isError ? (
          <div className="flex min-h-56 flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="font-medium">{t('empty.adminTitle')}</p>
            <p className="max-w-lg text-sm text-muted-foreground">
              {getErrorMessage(error)}
            </p>
          </div>
        ) : users.length === 0 ? (
          <div className="flex min-h-56 flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="font-medium">{t('empty.usersTitle')}</p>
            <p className="text-sm text-muted-foreground">
              {t('empty.usersDescription')}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20 hover:bg-muted/20">
                  <TableHead>{t('table.user')}</TableHead>
                  <TableHead className="w-36">{t('table.agents')}</TableHead>
                  <TableHead>{t('table.role')}</TableHead>
                  <TableHead>{t('table.apiKey')}</TableHead>
                  <TableHead className="text-right">
                    {t('table.actions')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => {
                  const identityKey = `${user.accountId}:${user.userId}`
                  const isCurrentIdentity =
                    user.accountId === connection.accountId &&
                    user.userId === connection.userId
                  const canSwitchIdentity =
                    !isCurrentIdentity &&
                    (serverMode === 'trusted' || Boolean(user.apiKey))
                  const isSwitching = switchingIdentityKey === identityKey
                  const isLastManager =
                    (user.role === 'admin' || user.role === 'root') &&
                    managerCount <= 1
                  const removeDisabled =
                    isCurrentIdentity || isLastManager || isRemovePending
                  const removeDisabledReason = isCurrentIdentity
                    ? t('management.cannotRemoveCurrentIdentity')
                    : isLastManager
                      ? t('management.cannotRemoveLastManager')
                      : t('actions.removeUser', { user: user.userId })

                  const count = agentCounts[user.userId] ?? 0

                  return (
                    <TableRow
                      key={identityKey}
                      className={`cursor-pointer transition-colors hover:bg-muted/40 ${
                        isCurrentIdentity ? 'bg-primary/2.5' : ''
                      }`}
                      onClick={() => onSelectUser?.(user)}
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground hover:underline">
                            {user.userId}
                          </span>
                          {isCurrentIdentity ? (
                            <Badge
                              variant="secondary"
                              className="gap-1 font-normal text-xs"
                            >
                              <CheckIcon className="size-3" />
                              {t('actions.currentIdentity')}
                            </Badge>
                          ) : null}
                        </div>
                      </TableCell>

                      <TableCell>
                        <Badge
                          variant="outline"
                          className="text-xs font-mono h-5.5 px-2 border-cyan-500/30 text-cyan-600 dark:text-cyan-400 bg-cyan-500/5 hover:bg-cyan-500/10 transition-colors"
                        >
                          <BotIcon className="size-3 mr-1 text-cyan-500" />
                          {t('table.activeAgents', { count })}
                        </Badge>
                      </TableCell>

                      <TableCell onClick={(e) => e.stopPropagation()}>
                        {canManageAccounts && isAdminUserRole(user.role) ? (
                          <Select
                            value={user.role}
                            disabled={isRoleUpdating}
                            onValueChange={(role) => {
                              if (
                                role &&
                                isAdminUserRole(role) &&
                                role !== user.role
                              ) {
                                onInitiateRoleChange({
                                  accountId: user.accountId,
                                  role,
                                  userId: user.userId,
                                })
                              }
                            }}
                          >
                            <SelectTrigger
                              className="h-8 w-28 text-xs"
                              aria-label={t('actions.changeRole', {
                                user: user.userId,
                              })}
                            >
                              <SelectValue>
                                {t(`roles.${user.role}`)}
                              </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                              {USER_ROLE_OPTIONS.map((role) => (
                                <SelectItem key={role} value={role} className="text-xs">
                                  {t(`roles.${role}`)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge
                            variant={
                              user.role === 'admin' ? 'secondary' : 'outline'
                            }
                            className="text-xs"
                          >
                            {t(`roles.${user.role}`, {
                              defaultValue: user.role,
                            })}
                          </Badge>
                        )}
                      </TableCell>

                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex min-w-0 items-center gap-1">
                          <code className="max-w-[18rem] truncate rounded-md border bg-muted/40 px-2 py-1 font-mono text-xs">
                            {resolveKeyLabel(user)}
                          </code>
                          {user.apiKey ? (
                            <Tooltip>
                              <TooltipTrigger
                                render={
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon-xs"
                                    aria-label={t('actions.copy')}
                                    onClick={() => onCopyKey(user.apiKey)}
                                  />
                                }
                              >
                                <CopyIcon className="size-3" />
                              </TooltipTrigger>
                              <TooltipContent>
                                {t('actions.copy')}
                              </TooltipContent>
                            </Tooltip>
                          ) : null}
                          <div className="ml-1 flex items-center border-l border-border/70 pl-1.5">
                            <Tooltip>
                              <TooltipTrigger
                                render={
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon-xs"
                                    aria-label={t('actions.regenerate')}
                                    onClick={() => onInitiateRegenerate(user)}
                                    disabled={
                                      isRegeneratePending ||
                                      Boolean(switchingIdentityKey)
                                    }
                                  />
                                }
                              >
                                <RotateCwIcon className="size-3" />
                              </TooltipTrigger>
                              <TooltipContent>
                                {t('actions.regenerate')}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </div>
                      </TableCell>

                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          {canSwitchIdentity ? (
                            <Button
                              type="button"
                              variant="secondary"
                              size="sm"
                              className="text-xs h-7 gap-1"
                              disabled={Boolean(switchingIdentityKey)}
                              onClick={() => onUseUserIdentity(user)}
                            >
                              {isSwitching ? (
                                <LoaderCircleIcon className="size-3 animate-spin" />
                              ) : (
                                <KeyRoundIcon className="size-3" />
                              )}
                              {t('actions.switchIdentity')}
                            </Button>
                          ) : isCurrentIdentity ? (
                            <span
                              aria-hidden="true"
                              className="px-3 text-muted-foreground/45 text-xs"
                            >
                              —
                            </span>
                          ) : null}
                          <Tooltip>
                            <TooltipTrigger
                              render={
                                <span
                                  className="inline-flex"
                                  title={removeDisabledReason}
                                />
                              }
                            >
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon-sm"
                                disabled={removeDisabled}
                                className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive size-7"
                                aria-label={t('actions.removeUser', {
                                  user: user.userId,
                                })}
                                onClick={() => onInitiateRemove(user)}
                              >
                                <Trash2Icon className="size-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              {removeDisabledReason}
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
