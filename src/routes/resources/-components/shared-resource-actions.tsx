import { useState } from 'react'
import { CopyIcon, FolderInputIcon, Trash2Icon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'

import { useInvalidateVikingFs } from '../-hooks/viking-fm'
import {
  isSharedResourceUri,
  type ResourceTransferOperation,
} from '../-lib/resource-actions'
import type { VikingFsEntry } from '../-types/viking-fm'
import { DeleteResourceDialog } from './delete-resource-dialog'
import { TransferResourceDialog } from './transfer-resource-dialog'

export function SharedResourceActions({
  file,
  onNavigate,
  onDeleted,
}: {
  file: VikingFsEntry
  onNavigate?: (uri: string) => void
  onDeleted?: () => void
}) {
  const { t } = useTranslation('resources')
  const { invalidateList, invalidateTree, invalidatePreview } =
    useInvalidateVikingFs()
  const [transferOp, setTransferOp] =
    useState<ResourceTransferOperation | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)

  if (!isSharedResourceUri(file.uri)) {
    return null
  }

  const refreshAll = () => {
    void invalidateList()
    void invalidateTree()
    void invalidatePreview(file.uri)
  }

  return (
    <>
      <div className="flex items-center gap-1">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          title={t('filePreview.copyResource')}
          onClick={() => setTransferOp('copy')}
        >
          <CopyIcon className="mr-1 size-3.5" />
          {t('filePreview.copyResource')}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          title={t('filePreview.moveResource')}
          onClick={() => setTransferOp('move')}
        >
          <FolderInputIcon className="mr-1 size-3.5" />
          {t('filePreview.moveResource')}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="text-rose-500 hover:bg-rose-500/10 hover:text-rose-500"
          title={t('filePreview.deleteResource')}
          onClick={() => setDeleteOpen(true)}
        >
          <Trash2Icon className="mr-1 size-3.5" />
          {t('filePreview.deleteResource')}
        </Button>
      </div>

      {transferOp ? (
        <TransferResourceDialog
          open={Boolean(transferOp)}
          operation={transferOp}
          uri={file.uri}
          isDirectory={file.isDir}
          onOpenChange={(open) => {
            if (!open) setTransferOp(null)
          }}
          onCompleted={(targetUri) => {
            refreshAll()
            if (onNavigate) onNavigate(targetUri)
          }}
        />
      ) : null}

      <DeleteResourceDialog
        open={deleteOpen}
        uri={file.uri}
        isDirectory={file.isDir}
        onOpenChange={setDeleteOpen}
        onDeleted={() => {
          refreshAll()
          if (onDeleted) onDeleted()
        }}
      />
    </>
  )
}
