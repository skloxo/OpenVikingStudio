import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import {
  CableIcon,
  CopyIcon,
  FolderPlusIcon,
  FilePlus2Icon,
  Loader2Icon,
  PencilIcon,
  SaveIcon,
  Trash2Icon,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { NodeRelationsManager } from '#/routes/graph/-components/node-relations-manager'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import { readTextDocument, saveText } from '../-lib/api'
import { hashText } from '../-lib/doc'
import type { LiveContextMount, McpCatalogTool } from '../-lib/model'
import { LiveContextInspector } from './live-context'

export function NodeInspector({
  entry,
  rootUri,
  liveMount,
  catalogTools,
  mutationsBlocked,
  onNewDir,
  onNewFile,
  onMount,
  onEditMount,
  onCopy,
  onDelete,
  onSaved,
}: {
  entry: VikingFsEntry
  rootUri: string
  liveMount?: LiveContextMount
  catalogTools: McpCatalogTool[]
  mutationsBlocked: boolean
  onNewDir: () => void
  onNewFile: () => void
  onMount: () => void
  onEditMount: () => void
  onCopy: () => void
  onDelete: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation('arranger')
  const [content, setContent] = useState('')
  const [sha256, setSha256] = useState('')
  const [dirty, setDirty] = useState(false)

  const docQuery = useQuery({
    queryKey: ['arranger-doc', entry.uri],
    queryFn: () => readTextDocument(entry.uri),
    enabled: !entry.isDir,
    retry: false,
  })

  useEffect(() => {
    if (!docQuery.data) return
    setContent(docQuery.data.content)
    setSha256(docQuery.data.sha256)
    setDirty(false)
  }, [docQuery.data, entry.uri])

  const saveMutation = useMutation({
    mutationFn: async () => {
      await saveText(entry.uri, content, sha256)
      const nextHash = await hashText(content)
      setSha256(nextHash)
    },
    onSuccess: () => {
      setDirty(false)
      toast.success(t('save.saved'))
      onSaved()
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : t('save.error'))
    },
  })

  const boundTool = liveMount
    ? catalogTools.find((item) => item.uri === liveMount.tool_uri)
    : undefined
  const isRoot = entry.uri === rootUri

  return (
    <section className="flex h-full min-h-[520px] flex-col overflow-hidden rounded-xl border bg-card">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b p-4">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-sm font-semibold">
              {entry.name || entry.uri}
            </h2>
            {liveMount && (
              <Badge className="border-cyan-500/30 bg-cyan-500/15 text-xs text-cyan-600 dark:text-cyan-400">
                {t('live.badge')}
              </Badge>
            )}
            {dirty && (
              <Badge variant="outline" className="text-xs text-amber-500">
                {t('save.dirty')}
              </Badge>
            )}
          </div>
          <p className="truncate font-mono text-xs text-muted-foreground">
            {entry.uri}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {entry.isDir ? (
            <>
              <Button size="xs" variant="outline" onClick={onNewDir}>
                <FolderPlusIcon />
                {t('actions.newDirectory')}
              </Button>
              <Button size="xs" variant="outline" onClick={onNewFile}>
                <FilePlus2Icon />
                {t('actions.newFile')}
              </Button>
              <Button size="xs" onClick={onMount}>
                <CableIcon />
                {t('actions.mount')}
              </Button>
              <Link
                to="/resources"
                search={{ uri: entry.uri }}
                className="inline-flex h-6 items-center rounded-md border px-2 text-xs hover:bg-muted"
              >
                {t('actions.addResource')}
              </Link>
            </>
          ) : liveMount ? (
            <Button size="xs" variant="outline" onClick={onEditMount}>
              <PencilIcon />
              {t('actions.editMount')}
            </Button>
          ) : (
            <Button
              size="xs"
              disabled={!dirty || saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              {saveMutation.isPending ? (
                <Loader2Icon className="animate-spin" />
              ) : (
                <SaveIcon />
              )}
              {saveMutation.isPending ? t('save.saving') : t('actions.save')}
            </Button>
          )}

          {!isRoot && !liveMount && (
            <Button
              size="xs"
              variant="outline"
              disabled={mutationsBlocked}
              onClick={onCopy}
            >
              <CopyIcon />
              {t('actions.copy')}
            </Button>
          )}
          {!isRoot && (
            <Button
              size="xs"
              variant="destructive"
              disabled={!liveMount && mutationsBlocked}
              onClick={onDelete}
            >
              <Trash2Icon />
              {t('actions.delete')}
            </Button>
          )}
        </div>
      </header>

      {entry.isDir ? (
        <div className="flex flex-1 flex-col justify-between gap-4 p-4 text-xs">
          <div className="space-y-3">
            <p className="font-medium text-muted-foreground">{t('fields.summary')}</p>
            <p className="whitespace-pre-wrap leading-relaxed">
              {entry.abstract || entry.overview || t('emptySummary')}
            </p>
          </div>
          <NodeRelationsManager nodeId={entry.uri} onRelationChange={onSaved} />
        </div>
      ) : liveMount ? (
        <LiveContextInspector
          document={docQuery.data?.content || ''}
          mount={liveMount}
          tool={boundTool}
        />
      ) : docQuery.isLoading ? (
        <div className="flex items-center gap-2 p-4 text-xs text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin text-cyan-500" />
          {t('loading')}
        </div>
      ) : docQuery.isError ? (
        <p className="p-4 text-xs text-rose-500">{t('errors.read')}</p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
          <Textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value)
              setDirty(true)
            }}
            className="min-h-[280px] flex-1 font-mono text-xs leading-relaxed"
          />
          <NodeRelationsManager nodeId={entry.uri} onRelationChange={onSaved} />
        </div>
      )}
    </section>
  )
}
