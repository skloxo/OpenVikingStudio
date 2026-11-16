import { useMutation } from '@tanstack/react-query'
import { Loader2Icon } from 'lucide-react'
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
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import {
  createDirectory,
  createText,
  mutateOrdinaryResource,
  unmountLiveContext,
} from '../-lib/api'
import type { LiveContextMount, LiveMountIndex } from '../-lib/model'
import { joinVikingUri } from '../-lib/uri'

export type ArrangerDialogKind =
  | { type: 'mkdir'; parentUri: string }
  | { type: 'file'; parentUri: string }
  | { type: 'copy'; entry: VikingFsEntry }
  | { type: 'delete'; entry: VikingFsEntry; liveMount?: LiveContextMount }
  | null

export function ArrangerNodeDialog({
  dialog,
  rootUri,
  liveIndex,
  onClose,
  onCompleted,
}: {
  dialog: ArrangerDialogKind
  rootUri: string
  liveIndex: LiveMountIndex
  onClose: () => void
  onCompleted: (targetUri?: string) => void
}) {
  const { t } = useTranslation('arranger')
  const [inputValue, setInputValue] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!dialog) return
    setError('')
    if (dialog.type === 'copy') setInputValue(`${dialog.entry.uri}-copy`)
    else setInputValue('')
  }, [dialog])

  const mutation = useMutation({
    mutationFn: async () => {
      if (!dialog) return undefined
      if (dialog.type === 'mkdir') {
        const uri = joinVikingUri(dialog.parentUri, inputValue)
        await createDirectory(uri)
        return uri
      }
      if (dialog.type === 'file') {
        const uri = joinVikingUri(dialog.parentUri, inputValue)
        await createText(uri, '')
        return uri
      }
      if (dialog.type === 'copy') {
        await mutateOrdinaryResource({
          kind: 'copy',
          rootUri,
          source: dialog.entry,
          target: inputValue.trim(),
          liveIndex,
        })
        return inputValue.trim()
      }
      if (dialog.type === 'delete') {
        if (dialog.liveMount) {
          await unmountLiveContext(dialog.entry.uri)
        } else {
          await mutateOrdinaryResource({
            kind: 'delete',
            rootUri,
            source: dialog.entry,
            liveIndex,
          })
        }
        return undefined
      }
      return undefined
    },
    onSuccess: (nextUri) => {
      toast.success(
        dialog?.type === 'delete' ? t('messages.deleted') : t('save.saved'),
      )
      onCompleted(nextUri)
      onClose()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : String(err))
    },
  })

  if (!dialog) return null

  const titleText =
    dialog.type === 'mkdir'
      ? t('dialogs.mkdir.title')
      : dialog.type === 'file'
        ? t('dialogs.file.title')
        : dialog.type === 'copy'
          ? t('dialogs.copy.title')
          : t('dialogs.delete.title', { name: dialog.entry.name || dialog.entry.uri })

  const descText =
    dialog.type === 'mkdir'
      ? t('dialogs.mkdir.description')
      : dialog.type === 'file'
        ? t('dialogs.file.description')
        : dialog.type === 'copy'
          ? t('dialogs.copy.description')
          : dialog.liveMount
            ? t('dialogs.delete.liveDescription')
            : dialog.entry.isDir
              ? t('dialogs.delete.directoryDescription')
              : t('dialogs.delete.fileDescription')

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{titleText}</DialogTitle>
          <DialogDescription>{descText}</DialogDescription>
        </DialogHeader>

        {dialog.type !== 'delete' && (
          <div className="space-y-1.5">
            <span className="text-xs font-medium">
              {dialog.type === 'copy' ? t('fields.targetUri') : t('fields.name')}
            </span>
            <Input
              className="font-mono text-xs"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
          </div>
        )}

        {error && <p className="text-xs text-rose-500">{error}</p>}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            {t('actions.cancel')}
          </Button>
          <Button
            type="button"
            variant={dialog.type === 'delete' ? 'destructive' : 'default'}
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending && <Loader2Icon className="animate-spin" />}
            {dialog.type === 'delete'
              ? mutation.isPending
                ? t('dialogs.delete.deleting')
                : t('dialogs.delete.confirm')
              : t('actions.confirm')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
