import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  FolderIcon,
  FileTextIcon,
  GitForkIcon,
  ListTreeIcon,
  Loader2Icon,
  RefreshCwIcon,
  SearchIcon,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import { cn } from '#/lib/utils'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import { MountToolDialog } from './-components/mount-tool-dialog'
import { ContextGraph, type ArrangerGraphItem } from './-components/context-graph'
import { ArrangerNodeDialog, type ArrangerDialogKind } from './-components/node-dialogs'
import { NodeInspector } from './-components/node-inspector'
import {
  createDirectory,
  isNotFoundError,
  listDirectory,
  loadLiveMounts,
  loadMcpCatalog,
  statResource,
} from './-lib/api'
import { normalizeVikingUri, toggleExpandedUri } from './-lib/uri'

export const Route = createFileRoute('/arranger')({
  validateSearch: (search: Record<string, unknown>): { uri?: string } => ({
    uri: typeof search.uri === 'string' && search.uri.trim() ? search.uri.trim() : undefined,
  }),
  component: ArrangerPage,
})

function ArrangerPage() {
  const { t } = useTranslation('arranger')
  const { identityScopeKey } = useAppConnection()
  const { uri: urlUri } = Route.useSearch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const defaultRoot = 'viking://resources'
  const activeRoot = useMemo(() => {
    try {
      return normalizeVikingUri(urlUri || defaultRoot)
    } catch {
      return defaultRoot
    }
  }, [urlUri])

  const [uriInput, setUriInput] = useState(activeRoot)
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph')
  const [filterText, setFilterText] = useState('')
  const [selectedUri, setSelectedUri] = useState(activeRoot)
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set([activeRoot]))
  const [dialog, setDialog] = useState<ArrangerDialogKind>(null)
  const [mountModal, setMountModal] = useState<{
    open: boolean
    parentUri: string
    mount?: Awaited<ReturnType<typeof loadLiveMounts>>['mounts'] extends Map<string, infer M> ? M : never
  }>({ open: false, parentUri: activeRoot })

  const rootQuery = useQuery({
    queryKey: ['arranger-root', identityScopeKey, activeRoot],
    queryFn: () => statResource(activeRoot),
    retry: false,
  })

  const mountsQuery = useQuery({
    queryKey: ['arranger-mounts', identityScopeKey, activeRoot],
    queryFn: () => loadLiveMounts(activeRoot),
    enabled: Boolean(rootQuery.data?.isDir),
  })

  const catalogQuery = useQuery({
    queryKey: ['arranger-mcp-catalog', identityScopeKey],
    queryFn: loadMcpCatalog,
    staleTime: 30_000,
  })

  const expandedList = useMemo(
    () => (rootQuery.data?.isDir ? [...expanded] : []),
    [expanded, rootQuery.data?.isDir],
  )

  const dirQueries = useQueries({
    queries: expandedList.map((dirUri) => ({
      queryKey: ['arranger-ls', identityScopeKey, dirUri],
      queryFn: () => listDirectory(dirUri, 0, 200, false),
    })),
  })

  const refreshWorkspace = async () => {
    await queryClient.invalidateQueries({ queryKey: ['arranger-root', identityScopeKey] })
    await queryClient.invalidateQueries({ queryKey: ['arranger-mounts', identityScopeKey] })
    await queryClient.invalidateQueries({ queryKey: ['arranger-ls', identityScopeKey] })
  }

  const { items, entryMap } = useMemo(() => {
    const map = new Map<string, VikingFsEntry>()
    const list: ArrangerGraphItem[] = []
    if (rootQuery.data) {
      const rootNorm = normalizeVikingUri(rootQuery.data.uri)
      map.set(rootNorm, rootQuery.data)
      list.push({
        entry: rootQuery.data,
        parentUri: null,
        liveMount: mountsQuery.data?.mounts.get(rootNorm),
      })
    }
    expandedList.forEach((parent, idx) => {
      const children = dirQueries[idx]?.data?.entries || []
      for (const child of children) {
        const norm = normalizeVikingUri(child.uri)
        map.set(norm, child)
        list.push({
          entry: child,
          parentUri: normalizeVikingUri(parent),
          liveMount: mountsQuery.data?.mounts.get(norm),
        })
      }
    })
    return { items: list, entryMap: map }
  }, [rootQuery.data, expandedList, dirQueries, mountsQuery.data])

  const filteredItems = useMemo(() => {
    const q = filterText.trim().toLowerCase()
    if (!q) return items
    return items.filter(
      (item) =>
        item.entry.name.toLowerCase().includes(q) ||
        item.entry.uri.toLowerCase().includes(q),
    )
  }, [items, filterText])

  const selectedEntry =
    entryMap.get(normalizeVikingUri(selectedUri || activeRoot)) || rootQuery.data
  const liveIndex = mountsQuery.data ?? { complete: false, mounts: new Map() }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-sm text-muted-foreground">{t('description')}</p>
        </div>

        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            try {
              const norm = normalizeVikingUri(uriInput)
              setSelectedUri(norm)
              setExpanded(new Set([norm]))
              void navigate({ to: '/arranger', search: { uri: norm } })
            } catch (err) {
              toast.error(err instanceof Error ? err.message : String(err))
            }
          }}
        >
          <Input
            aria-label={t('pathLabel')}
            className="w-72 font-mono text-xs"
            value={uriInput}
            onChange={(e) => setUriInput(e.target.value)}
            placeholder={t('start.pathHint')}
          />
          <Button type="submit" size="sm">
            {t('actions.load')}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void refreshWorkspace()}
          >
            <RefreshCwIcon />
            {t('actions.refresh')}
          </Button>
        </form>
      </header>

      {rootQuery.isLoading ? (
        <div className="flex items-center gap-2 py-12 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin text-cyan-500" />
          {t('loading')}
        </div>
      ) : rootQuery.isError ? (
        <div className="space-y-3 rounded-xl border p-6">
          <p className="text-sm text-rose-500">{t('errors.loadRoot')}</p>
          {isNotFoundError(rootQuery.error) && (
            <Button
              size="sm"
              onClick={async () => {
                await createDirectory(activeRoot)
                await refreshWorkspace()
              }}
            >
              {t('actions.createRoot')}
            </Button>
          )}
        </div>
      ) : !rootQuery.data?.isDir ? (
        <p className="rounded-xl border p-6 text-sm text-rose-500">
          {t('errors.rootNotDirectory')}
        </p>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.9fr)]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="relative flex-1 min-w-48">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-8 text-xs"
                  placeholder={t('searchPlaceholder')}
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                />
              </div>
              <div className="inline-flex gap-1 rounded-lg bg-muted p-1">
                <Button
                  type="button"
                  size="xs"
                  variant={viewMode === 'graph' ? 'secondary' : 'ghost'}
                  onClick={() => setViewMode('graph')}
                >
                  <GitForkIcon />
                  {t('views.graph')}
                </Button>
                <Button
                  type="button"
                  size="xs"
                  variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                  onClick={() => setViewMode('list')}
                >
                  <ListTreeIcon />
                  {t('views.list')}
                </Button>
              </div>
            </div>

            {viewMode === 'graph' ? (
              <ContextGraph
                rootUri={activeRoot}
                items={filteredItems}
                selectedUri={selectedEntry?.uri || activeRoot}
                onSelect={setSelectedUri}
                onToggleExpand={(dirUri) =>
                  setExpanded((prev) => toggleExpandedUri(prev, dirUri))
                }
              />
            ) : (
              <ul className="max-h-[520px] divide-y overflow-y-auto rounded-xl border bg-card">
                {filteredItems.map((item) => {
                  const norm = normalizeVikingUri(item.entry.uri)
                  const isExp = expanded.has(norm)
                  const isSel = normalizeVikingUri(selectedEntry?.uri || '') === norm
                  return (
                    <li
                      key={norm}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 text-xs hover:bg-muted/40',
                        isSel && 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
                      )}
                    >
                      {item.entry.isDir ? (
                        <button
                          type="button"
                          onClick={() =>
                            setExpanded((prev) => toggleExpandedUri(prev, norm))
                          }
                          className="p-0.5 text-muted-foreground hover:text-foreground"
                        >
                          {isExp ? (
                            <ChevronDownIcon className="size-3.5" />
                          ) : (
                            <ChevronRightIcon className="size-3.5" />
                          )}
                        </button>
                      ) : (
                        <span className="w-4" />
                      )}
                      {item.entry.isDir ? (
                        <FolderIcon className="size-3.5 shrink-0 text-slate-400" />
                      ) : (
                        <FileTextIcon className="size-3.5 shrink-0 text-slate-400" />
                      )}
                      <button
                        type="button"
                        className="min-w-0 flex-1 truncate text-left font-medium"
                        onClick={() => setSelectedUri(norm)}
                      >
                        {item.entry.name || norm}
                      </button>
                      {item.liveMount && (
                        <Badge className="border-cyan-500/30 bg-cyan-500/15 text-xs text-cyan-600 dark:text-cyan-400">
                          {t('live.badge')}
                        </Badge>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          {selectedEntry && (
            <NodeInspector
              entry={selectedEntry}
              rootUri={activeRoot}
              liveMount={mountsQuery.data?.mounts.get(normalizeVikingUri(selectedEntry.uri))}
              catalogTools={catalogQuery.data?.tools || []}
              mutationsBlocked={!liveIndex.complete}
              onNewDir={() => setDialog({ type: 'mkdir', parentUri: selectedEntry.uri })}
              onNewFile={() => setDialog({ type: 'file', parentUri: selectedEntry.uri })}
              onMount={() =>
                setMountModal({ open: true, parentUri: selectedEntry.uri })
              }
              onEditMount={() => {
                const mount = mountsQuery.data?.mounts.get(
                  normalizeVikingUri(selectedEntry.uri),
                )
                if (mount) {
                  setMountModal({
                    open: true,
                    parentUri: selectedEntry.uri,
                    mount,
                  })
                }
              }}
              onCopy={() => setDialog({ type: 'copy', entry: selectedEntry })}
              onDelete={() =>
                setDialog({
                  type: 'delete',
                  entry: selectedEntry,
                  liveMount: mountsQuery.data?.mounts.get(
                    normalizeVikingUri(selectedEntry.uri),
                  ),
                })
              }
              onSaved={() => void refreshWorkspace()}
            />
          )}
        </div>
      )}

      <ArrangerNodeDialog
        dialog={dialog}
        rootUri={activeRoot}
        liveIndex={liveIndex}
        onClose={() => setDialog(null)}
        onCompleted={(nextUri) => {
          if (nextUri) setSelectedUri(nextUri)
          else setSelectedUri(activeRoot)
          void refreshWorkspace()
        }}
      />

      <MountToolDialog
        open={mountModal.open}
        onOpenChange={(open) => setMountModal((prev) => ({ ...prev, open }))}
        parentUri={mountModal.parentUri}
        catalog={catalogQuery.data}
        initialMount={mountModal.mount}
        onSuccess={(nodeUri) => {
          setSelectedUri(nodeUri)
          void refreshWorkspace()
        }}
      />
    </main>
  )
}
