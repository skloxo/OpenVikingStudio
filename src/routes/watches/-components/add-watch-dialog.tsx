import * as React from 'react'
import { LoaderCircleIcon, PlusIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Textarea } from '#/components/ui/textarea'

import type { CreateWatchInput } from '../-lib/api'

export function AddWatchDialog({
  open,
  pending,
  onOpenChange,
  onSubmit,
}: {
  open: boolean
  pending: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (input: CreateWatchInput) => void
}) {
  const { t } = useTranslation('watchesPage')
  const [path, setPath] = React.useState('')
  const [to, setTo] = React.useState('viking://resources/')
  const [interval, setInterval] = React.useState('60')
  const [reason, setReason] = React.useState('')
  const [instruction, setInstruction] = React.useState('')

  React.useEffect(() => {
    if (open) {
      setPath('')
      setTo('viking://resources/')
      setInterval('60')
      setReason('')
      setInstruction('')
    }
  }, [open])

  const parsedInterval = Number(interval)
  const canSubmit =
    path.trim().length > 0 &&
    Number.isFinite(parsedInterval) &&
    parsedInterval >= 1 &&
    !pending

  return (
    <Dialog open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('addDialog.title')}</DialogTitle>
          <DialogDescription>{t('addDialog.description')}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="watch-add-path">{t('addDialog.sourceUrl')}</Label>
            <Input
              id="watch-add-path"
              placeholder={t('addDialog.sourcePlaceholder')}
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="watch-add-to">{t('addDialog.targetUri')}</Label>
            <Input
              id="watch-add-to"
              placeholder={t('addDialog.targetPlaceholder')}
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="watch-add-interval">{t('editDialog.interval')}</Label>
            <Input
              id="watch-add-interval"
              type="number"
              min="1"
              step="1"
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {t('editDialog.intervalHint')}
            </p>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="watch-add-reason">{t('editDialog.reason')}</Label>
            <Textarea
              id="watch-add-reason"
              rows={2}
              placeholder={t('editDialog.reasonPlaceholder')}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="watch-add-instruction">
              {t('editDialog.instruction')}
            </Label>
            <Textarea
              id="watch-add-instruction"
              rows={2}
              placeholder={t('editDialog.instructionPlaceholder')}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            disabled={pending}
            onClick={() => onOpenChange(false)}
          >
            {t('cancel')}
          </Button>
          <Button
            type="button"
            disabled={!canSubmit}
            onClick={() =>
              onSubmit({
                path: path.trim(),
                to: to.trim() || undefined,
                watchInterval: Math.floor(parsedInterval),
                reason: reason.trim() || undefined,
                instruction: instruction.trim() || undefined,
              })
            }
          >
            {pending ? (
              <LoaderCircleIcon className="size-4 animate-spin" />
            ) : (
              <PlusIcon className="size-4" />
            )}
            {pending ? t('adding') : t('addDialog.submit')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
