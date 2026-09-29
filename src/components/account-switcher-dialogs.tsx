import * as React from 'react'
import { CheckIcon, LoaderCircleIcon, PlusIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import type { UseMutationResult } from '@tanstack/react-query'

import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { DEFAULT_USER_ID } from '#/lib/admin-options'
import { PLAIN_INPUT_PROPS } from '#/lib/form-input'
import type { CreateAccountInput } from '#/lib/admin'

export interface ManualSwitchState {
  accountId: string
  apiKey: string
  userId: string
}

export interface ManualSwitchDialogProps {
  manualSwitch: ManualSwitchState | null
  onManualSwitchChange: (val: ManualSwitchState | null) => void
  switchingAccountId: string
  onSwitchingAccountIdChange: (id: string) => void
  switchIdentity: (params: {
    accountId: string
    apiKey: string
    userId: string
  }) => Promise<void>
  switchManagementAccount: (accountId: string) => Promise<void>
}

export function ManualSwitchDialog({
  manualSwitch,
  onManualSwitchChange,
  switchingAccountId,
  onSwitchingAccountIdChange,
  switchIdentity,
  switchManagementAccount,
}: ManualSwitchDialogProps) {
  const { t } = useTranslation('accountSwitcher')

  return (
    <Dialog
      open={Boolean(manualSwitch)}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && !switchingAccountId) {
          onManualSwitchChange(null)
        }
      }}
    >
      <DialogContent>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!manualSwitch?.apiKey.trim()) {
              return
            }
            const target = manualSwitch
            onSwitchingAccountIdChange(target.accountId)
            void switchIdentity({
              accountId: target.accountId,
              apiKey: target.apiKey,
              userId: target.userId,
            })
              .then(() => {
                toast.success(
                  t('toast.switched', { account: target.accountId }),
                )
                onManualSwitchChange(null)
              })
              .catch((error: unknown) => {
                toast.error(
                  error instanceof Error ? error.message : String(error),
                )
              })
              .finally(() => onSwitchingAccountIdChange(''))
          }}
        >
          <DialogHeader>
            <DialogTitle>{t('manualSwitch.title')}</DialogTitle>
            <DialogDescription>
              {t('manualSwitch.description', {
                account: manualSwitch?.accountId,
              })}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2 py-5">
            <label className="grid gap-2 text-sm font-medium">
              {t('manualSwitch.keyLabel')}
              <Input
                required
                type="password"
                value={manualSwitch?.apiKey ?? ''}
                onChange={(event) =>
                  onManualSwitchChange(
                    manualSwitch
                      ? { ...manualSwitch, apiKey: event.target.value }
                      : manualSwitch,
                  )
                }
                placeholder={t('manualSwitch.keyPlaceholder')}
                {...PLAIN_INPUT_PROPS}
              />
            </label>
            <p className="text-xs leading-5 text-muted-foreground">
              {t('manualSwitch.hint')}
            </p>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={Boolean(switchingAccountId)}
              onClick={() => {
                const targetAccountId = manualSwitch?.accountId
                if (!targetAccountId) {
                  return
                }
                onSwitchingAccountIdChange(targetAccountId)
                void switchManagementAccount(targetAccountId)
                  .then(() => {
                    onManualSwitchChange(null)
                    toast.success(
                      t('toast.managementSwitched', {
                        account: targetAccountId,
                      }),
                    )
                  })
                  .catch((error: unknown) => {
                    toast.error(
                      error instanceof Error ? error.message : String(error),
                    )
                  })
                  .finally(() => onSwitchingAccountIdChange(''))
              }}
            >
              {t('manualSwitch.manageOnly')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={Boolean(switchingAccountId)}
              onClick={() => onManualSwitchChange(null)}
            >
              {t('dialog.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={
                Boolean(switchingAccountId) || !manualSwitch?.apiKey.trim()
              }
            >
              {switchingAccountId ? (
                <LoaderCircleIcon className="animate-spin" />
              ) : (
                <CheckIcon />
              )}
              {t('manualSwitch.submit')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export interface CreateAccountDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  createDraft: CreateAccountInput
  onCreateDraftChange: React.Dispatch<
    React.SetStateAction<CreateAccountInput>
  >
  createAccountMutation: UseMutationResult<
    any,
    Error,
    CreateAccountInput,
    unknown
  >
}

export function CreateAccountDialog({
  open,
  onOpenChange,
  createDraft,
  onCreateDraftChange,
  createAccountMutation,
}: CreateAccountDialogProps) {
  const { t } = useTranslation('accountSwitcher')

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createAccountMutation.mutate(createDraft)
          }}
        >
          <DialogHeader>
            <DialogTitle>{t('dialog.title')}</DialogTitle>
            <DialogDescription>{t('dialog.description')}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-5">
            <label className="grid gap-2 text-sm font-medium">
              {t('dialog.accountLabel')}
              <Input
                required
                value={createDraft.accountId}
                onChange={(event) =>
                  onCreateDraftChange((current) => ({
                    ...current,
                    accountId: event.target.value,
                  }))
                }
                placeholder={t('dialog.accountPlaceholder')}
                {...PLAIN_INPUT_PROPS}
              />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              {t('dialog.adminLabel')}
              <Input
                required
                value={createDraft.adminUserId}
                onChange={(event) =>
                  onCreateDraftChange((current) => ({
                    ...current,
                    adminUserId: event.target.value,
                  }))
                }
                placeholder={DEFAULT_USER_ID}
                {...PLAIN_INPUT_PROPS}
              />
            </label>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              {t('dialog.cancel')}
            </Button>
            <Button type="submit" disabled={createAccountMutation.isPending}>
              {createAccountMutation.isPending ? (
                <LoaderCircleIcon className="animate-spin" />
              ) : (
                <PlusIcon />
              )}
              {t('dialog.submit')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
