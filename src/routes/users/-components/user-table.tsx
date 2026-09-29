/**
 * user-table.tsx
 * 用户管理列表表格组件。
 * 展示账户下的用户成员、角色配置、API 密钥以及身份切换和删除操作。
 */
import {
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
  onUseUserIdentity,
  serverMode,
  switchingIdentityKey,
  users,
}: UserTableProps) {
  const { t } = useTranslation('settings')

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

                  return (
                    <TableRow
                      key={identityKey}
                      className={isCurrentIdentity ? 'bg-primary/2.5' : ''}
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          {user.userId}
                          {isCurrentIdentity ? (
                            <Badge
                              variant="secondary"
                              className="gap-1 font-normal"
                            >
                              <CheckIcon />
                              {t('actions.currentIdentity')}
                            </Badge>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>
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
                              className="h-8 w-28"
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
                                <SelectItem key={role} value={role}>
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
                          >
                            {t(`roles.${user.role}`, {
                              defaultValue: user.role,
                            })}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex min-w-0 items-center gap-1">
                          <code className="max-w-[20rem] truncate rounded-md border bg-muted/40 px-2 py-1 font-mono text-xs">
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
                                <CopyIcon />
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
                                <RotateCwIcon />
                              </TooltipTrigger>
                              <TooltipContent>
                                {t('actions.regenerate')}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          {canSwitchIdentity ? (
                            <Button
                              type="button"
                              variant="secondary"
                              size="sm"
                              disabled={Boolean(switchingIdentityKey)}
                              onClick={() => onUseUserIdentity(user)}
                            >
                              {isSwitching ? (
                                <LoaderCircleIcon className="animate-spin" />
                              ) : (
                                <KeyRoundIcon />
                              )}
                              {t('actions.switchIdentity')}
                            </Button>
                          ) : isCurrentIdentity ? (
                            <span
                              aria-hidden="true"
                              className="px-3 text-muted-foreground/45"
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
                                className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                                aria-label={t('actions.removeUser', {
                                  user: user.userId,
                                })}
                                onClick={() => onInitiateRemove(user)}
                              >
                                <Trash2Icon />
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
