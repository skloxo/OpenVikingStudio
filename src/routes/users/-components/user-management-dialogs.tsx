/**
 * user-management-dialogs.tsx
 * 用户管理确认弹窗集合：
 * 包含重新生成 API Key、修改用户角色、删除用户的确认弹窗。
 */
import { LoaderCircleIcon, RotateCwIcon, Trash2Icon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '#/components/ui/alert-dialog'
import type { AdminUser, UpdateUserRoleInput } from '#/lib/admin'

export type UserManagementDialogsProps = {
  isRegenerating: boolean
  isRemoving: boolean
  isUpdatingRole: boolean
  onConfirmRegenerate: (user: AdminUser) => void
  onConfirmRemove: (user: AdminUser) => void
  onConfirmRoleChange: (input: UpdateUserRoleInput) => void
  onPendingRegenerateChange: (user: AdminUser | null) => void
  onPendingRemoveChange: (user: AdminUser | null) => void
  onPendingRoleChange: (input: UpdateUserRoleInput | null) => void
  pendingRegenerateUser: AdminUser | null
  pendingRemoveUser: AdminUser | null
  pendingRoleChange: UpdateUserRoleInput | null
}

export function UserManagementDialogs({
  isRegenerating,
  isRemoving,
  isUpdatingRole,
  onConfirmRegenerate,
  onConfirmRemove,
  onConfirmRoleChange,
  onPendingRegenerateChange,
  onPendingRemoveChange,
  onPendingRoleChange,
  pendingRegenerateUser,
  pendingRemoveUser,
  pendingRoleChange,
}: UserManagementDialogsProps) {
  const { t } = useTranslation('settings')

  return (
    <>
      <AlertDialog
        open={Boolean(pendingRegenerateUser)}
        onOpenChange={(open) => {
          if (!open) {
            onPendingRegenerateChange(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('dialogs.regenerate.title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('dialogs.regenerate.description', {
                account: pendingRegenerateUser?.accountId,
                user: pendingRegenerateUser?.userId,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (pendingRegenerateUser) {
                  onConfirmRegenerate(pendingRegenerateUser)
                }
              }}
              disabled={isRegenerating}
            >
              <RotateCwIcon />
              {t('actions.regenerate')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={Boolean(pendingRoleChange)}
        onOpenChange={(open) => {
          if (!open && !isUpdatingRole) {
            onPendingRoleChange(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('dialogs.changeRole.title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('dialogs.changeRole.description', {
                account: pendingRoleChange?.accountId,
                role: pendingRoleChange
                  ? t(`roles.${pendingRoleChange.role}`)
                  : '',
                user: pendingRoleChange?.userId,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isUpdatingRole}>
              {t('actions.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={isUpdatingRole}
              onClick={(event) => {
                event.preventDefault()
                if (pendingRoleChange) {
                  onConfirmRoleChange(pendingRoleChange)
                }
              }}
            >
              {isUpdatingRole ? (
                <LoaderCircleIcon className="animate-spin" />
              ) : null}
              {t('actions.confirmRoleChange')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={Boolean(pendingRemoveUser)}
        onOpenChange={(open) => {
          if (!open && !isRemoving) {
            onPendingRemoveChange(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('dialogs.removeUser.title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('dialogs.removeUser.description', {
                account: pendingRemoveUser?.accountId,
                user: pendingRemoveUser?.userId,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRemoving}>
              {t('actions.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={isRemoving}
              onClick={(event) => {
                event.preventDefault()
                if (pendingRemoveUser) {
                  onConfirmRemove(pendingRemoveUser)
                }
              }}
            >
              {isRemoving ? (
                <LoaderCircleIcon className="animate-spin" />
              ) : (
                <Trash2Icon />
              )}
              {t('actions.confirmRemoveUser')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
