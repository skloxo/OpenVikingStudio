import { CopyIcon, Loader2Icon, PencilIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

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

import {
  isValidTransferTarget,
  transferSharedResource,
  type ResourceTransferOperation,
} from '../-lib/resource-actions'

export function TransferResourceDialog({
  isDirectory,
  onCompleted,
  onOpenChange,
  open,
  operation,
  uri,
}: {
  isDirectory: boolean
  onCompleted: (targetUri: string) => void
  onOpenChange: (open: boolean) => void
  open: boolean
  operation: ResourceTransferOperation
  uri: string
}) {
  const { t } = useTranslation('resources')
  const sourceUri = uri.replace(/\/$/, '')
  const [targetUri, setTargetUri] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const isCopy = operation === 'copy'

  useEffect(() => {
    if (open) setTargetUri(isCopy ? `${sourceUri}-copy` : sourceUri)
  }, [isCopy, open, sourceUri])

  const handleSubmit = async () => {
    if (!isValidTransferTarget(sourceUri, targetUri) || isSubmitting) return
    setIsSubmitting(true)
    const normalizedTarget = targetUri.replace(/\/$/, '')
    try {
      await transferSharedResource(
        operation,
        sourceUri,
        normalizedTarget,
        isDirectory,
      )
      toast.success(
        t(
          isCopy
            ? 'transferResource.copySuccess'
            : 'transferResource.moveSuccess',
        ),
      )
      onOpenChange(false)
      onCompleted(normalizedTarget)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      toast.error(
        `${t(isCopy ? 'transferResource.copyFailed' : 'transferResource.moveFailed')}: ${msg}`,
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!isSubmitting) onOpenChange(nextOpen)
      }}
    >
      <DialogContent showCloseButton={!isSubmitting}>
        <DialogHeader>
          <DialogTitle>
            {t(
              isCopy
                ? 'transferResource.copyTitle'
                : 'transferResource.moveTitle',
            )}
          </DialogTitle>
          <DialogDescription>
            {t(
              isCopy
                ? 'transferResource.copyDescription'
                : 'transferResource.moveDescription',
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-md bg-muted p-3 font-mono text-xs break-all">
          {sourceUri}
        </div>
        <div className="space-y-2">
          <label htmlFor="transfer-resource-target" className="text-sm">
            {t('transferResource.targetLabel')}
          </label>
          <Input
            id="transfer-resource-target"
            value={targetUri}
            onChange={(event) => setTargetUri(event.target.value)}
            placeholder="viking://resources/..."
            disabled={isSubmitting}
          />
          <p className="text-xs text-muted-foreground">
            {t('transferResource.targetHint')}
          </p>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            {t('filePreview.cancel')}
          </Button>
          <Button
            onClick={() => void handleSubmit()}
            disabled={!isValidTransferTarget(sourceUri, targetUri) || isSubmitting}
          >
            {isSubmitting ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : isCopy ? (
              <CopyIcon className="size-4" />
            ) : (
              <PencilIcon className="size-4" />
            )}
            {t(
              isCopy
                ? 'transferResource.copyConfirm'
                : 'transferResource.moveConfirm',
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
