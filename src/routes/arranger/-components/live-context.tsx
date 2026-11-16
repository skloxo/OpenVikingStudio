import { useMutation, useQuery } from '@tanstack/react-query'
import {
  BracesIcon,
  CableIcon,
  Clock3Icon,
  FileTextIcon,
  Loader2Icon,
  PlayIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  TagIcon,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import { invokeMcpToolDirect, readLiveContext } from '../-lib/api'
import { formatLiveContextResult, parseLiveContextMetadata } from '../-lib/doc'
import type { LiveContextMount, McpCatalogTool } from '../-lib/model'

export function LiveContextInspector({
  document,
  mount,
  tool,
}: {
  document: string
  mount: LiveContextMount
  tool?: McpCatalogTool
}) {
  const { t, i18n } = useTranslation('arranger')
  const [tab, setTab] = useState<'result' | 'overview' | 'raw'>('result')
  const argumentEntries = Object.entries(mount.arguments || {})
  const annotations = tool?.tool.annotations || {}
  const metadata = parseLiveContextMetadata(document)
  const nodeTitle = metadata?.title || mount.title
  const nodeDescription = metadata?.description || mount.description

  const resultQuery = useQuery({
    enabled: false,
    queryKey: ['arranger-live-result', mount.node_uri],
    queryFn: () => readLiveContext(mount.node_uri),
    retry: false,
  })

  const invokeMutation = useMutation({
    mutationFn: () => invokeMcpToolDirect(mount.tool_uri, mount.arguments || {}),
  })

  const activeData =
    invokeMutation.data !== undefined ? invokeMutation.data : resultQuery.data
  const result =
    activeData === undefined ? null : formatLiveContextResult(activeData)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        role="tablist"
        className="flex h-10 shrink-0 items-center gap-1 border-b px-4"
      >
        {(['result', 'overview', 'raw'] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              tab === key
                ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {t(
              key === 'result'
                ? 'live.result'
                : key === 'overview'
                  ? 'live.overview'
                  : 'live.rawConfig',
            )}
          </button>
        ))}
      </div>

      {tab === 'result' && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-wrap items-center gap-2 border-b p-4">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{t('live.result')}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {resultQuery.dataUpdatedAt
                  ? t('live.updatedAt', {
                      value: new Date(resultQuery.dataUpdatedAt).toLocaleTimeString(
                        i18n.language,
                      ),
                    })
                  : t('live.resultDescription')}
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              disabled={invokeMutation.isPending}
              onClick={() => invokeMutation.mutate()}
            >
              {invokeMutation.isPending ? (
                <Loader2Icon className="animate-spin" />
              ) : (
                <PlayIcon />
              )}
              {t('actions.invoke')}
            </Button>
            <Button
              size="sm"
              disabled={resultQuery.isFetching}
              onClick={() => void resultQuery.refetch()}
            >
              {resultQuery.isFetching ? (
                <Loader2Icon className="animate-spin" />
              ) : (
                <RefreshCwIcon />
              )}
              {result ? t('live.refreshResult') : t('live.loadResult')}
            </Button>
          </div>

          {resultQuery.error || invokeMutation.error ? (
            <div className="p-4 text-sm leading-6 text-rose-500">
              {String(
                (resultQuery.error || invokeMutation.error) instanceof Error
                  ? ((resultQuery.error || invokeMutation.error) as Error).message
                  : resultQuery.error || invokeMutation.error,
              )}
            </div>
          ) : result ? (
            <pre
              className={cn(
                'whitespace-pre-wrap break-words p-4 font-mono text-xs leading-6',
                result.isError ? 'text-rose-500' : 'text-foreground',
              )}
            >
              {result.text}
            </pre>
          ) : (
            <p className="p-4 text-xs text-muted-foreground">
              {t('live.resultEmpty')}
            </p>
          )}
        </div>
      )}

      {tab === 'overview' && (
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-xs">
          <div className="space-y-1.5 rounded-lg border p-3">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FileTextIcon className="size-3.5" />
              <span>{t('live.nodeInfo')}</span>
            </div>
            <p className="text-sm font-medium">{nodeTitle}</p>
            {nodeDescription && (
              <p className="text-muted-foreground">{nodeDescription}</p>
            )}
          </div>

          <div className="space-y-1.5 rounded-lg border p-3">
            <div className="flex items-center gap-2 text-muted-foreground">
              <CableIcon className="size-3.5 text-cyan-500" />
              <span>{t('live.boundTool')}</span>
            </div>
            <p className="font-mono break-all">{mount.tool_uri}</p>
            {tool?.tool.description && (
              <p className="text-muted-foreground">{tool.tool.description}</p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="gap-1 text-xs">
              <Clock3Icon className="size-3" />
              {t('live.timeoutValue', { value: mount.timeout_seconds })}
            </Badge>
            <Badge variant="outline" className="gap-1 text-xs">
              <ShieldCheckIcon className="size-3 text-cyan-500" />
              {annotations.destructiveHint
                ? t('live.destructiveHint')
                : t('live.readOnlyHint')}
            </Badge>
            {(mount.tags || []).map((tag) => (
              <Badge key={tag} variant="secondary" className="gap-1 text-xs">
                <TagIcon className="size-3" />
                {tag}
              </Badge>
            ))}
          </div>

          {argumentEntries.length > 0 && (
            <div className="space-y-1.5 rounded-lg border p-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <BracesIcon className="size-3.5" />
                <span>{t('fields.arguments')}</span>
              </div>
              <pre className="overflow-x-auto font-mono text-xs">
                {JSON.stringify(mount.arguments, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {tab === 'raw' && (
        <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-5">
          {document || JSON.stringify(mount, null, 2)}
        </pre>
      )}
    </div>
  )
}
