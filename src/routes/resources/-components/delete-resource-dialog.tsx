import { Loader2Icon, Trash2Icon } from 'lucide-react'
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

import { deleteSharedResource } from '../-lib/resource-actions'

export function DeleteResourceDialog({
  isDirectory,
  onDeleted,
  onOpenChange,
  open,
  uri,
}: {
  isDirectory: boolean
  onDeleted: (result: { semanticStatus?: string }) => void
  onOpenChange: (open: boolean) => void
  open: boolean
  uri: string
}) {
  const { t } = useTranslation('resources')
  const [confirmation, setConfirmation] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const normalizedUri = uri.replace(/\/$/, '')

  useEffect(() => {
    if (open) setConfirmation('')
  }, [open, uri])

  const handleDelete = async () => {
    if (confirmation !== normalizedUri || isDeleting) return
    setIsDeleting(true)
    try {
      const result = await deleteSharedResource(normalizedUri, isDirectory)
      toast.success(t('deleteResource.success'))
      onOpenChange(false)
      onDeleted(result)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      toast.error(`${t('deleteResource.failed')}: ${msg}`)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!isDeleting) onOpenChange(nextOpen)
      }}
    >
      <DialogContent showCloseButton={!isDeleting}>
        <DialogHeader>
          <DialogTitle>{t('deleteResource.title')}</DialogTitle>
          <DialogDescription>
            {t(
              isDirectory
                ? 'deleteResource.directoryDescription'
                : 'deleteResource.fileDescription',
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-md bg-muted p-3 font-mono text-xs break-all">
          {normalizedUri}
        </div>
        <div className="space-y-2">
          <label htmlFor="delete-resource-confirmation" className="text-sm">
            {t('deleteResource.confirmLabel')}
          </label>
          <Input
            id="delete-resource-confirmation"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            placeholder={normalizedUri}
            disabled={isDeleting}
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            {t('filePreview.cancel')}
          </Button>
          <Button
            variant="destructive"
            onClick={() => void handleDelete()}
            disabled={confirmation !== normalizedUri || isDeleting}
          >
            {isDeleting ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <Trash2Icon className="size-4" />
            )}
            {t('deleteResource.confirm')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
