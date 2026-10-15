/**
 * route.tsx
 * Playground 路由入口与工作台主容器。
 * 遵循 Agent 编码规范与黄金甜点区（<= 500 行，目标 300 行）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { useAppConnection } from '#/hooks/use-app-connection'
import { LazyFilePreview } from '#/routes/resources/-components/lazy-file-preview'
import {
  ResourceUploadProvider,
  useResourceUpload,
} from '#/routes/resources/-hooks/use-resource-upload'
import {
  useInvalidateVikingFs,
  useVikingFsList,
} from '#/routes/resources/-hooks/viking-fm'
import { fetchFsStat } from '#/routes/resources/-lib/api'
import {
  fileNameFromUri,
  normalizeDirUri,
  normalizeFileUri,
  parentUri,
} from '#/routes/resources/-lib/normalize'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'

import {
  ContextExplorerHeader,
  ContextTree,
  PlaygroundResizeHandle,
} from './-components/context-explorer'
import { ROOT_URI } from './-lib/constants'
import type {
  PlaygroundPanel,
  PlaygroundSearch,
  ResourceOpenHandler,
} from './-lib/types'
import {
  cleanVikingUri,
  createEntryFromUri,
  getAncestorUris,
  getErrorMessage,
  isDirectoryLevelFile,
  mergeExpanded,
  normalizePlaygroundResourceUri,
  readPlaygroundExpandedUris,
  visibleContextEntries,
  writePlaygroundExpandedUris,
} from './-lib/utils'
import {
  PlaygroundActionPanel,
  useIsCompactPlaygroundLayout,
} from './-components/playground-action-panel'
import { PlaygroundDialogs } from './-components/playground-dialogs'
import { PlaygroundMainToolbar } from './-components/playground-main-toolbar'
import { usePlaygroundLayout } from './-hooks/use-playground-layout'

export const Route = createFileRoute('/playground')({
  validateSearch: (search: Record<string, unknown>): PlaygroundSearch => ({
    file: typeof search.file === 'string' ? search.file : undefined,
    panel:
      search.panel === 'agent' || search.panel === 'terminal'
        ? search.panel
        : undefined,
    session: typeof search.session === 'string' ? search.session : undefined,
    upload: search.upload === true || search.upload === 'true',
    uri: typeof search.uri === 'string' ? search.uri : undefined,
  }),
  component: PlaygroundRoute,
})

function PlaygroundRoute() {
  return (
    <ResourceUploadProvider>
      <PlaygroundWorkbench />
    </ResourceUploadProvider>
  )
}

function PlaygroundWorkbench() {
  const { t } = useTranslation(['playground', 'resources'])
  const { identityScopeKey } = useAppConnection()
  const search = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const initialCurrentUri = useMemo(
    () =>
      search.file
        ? normalizeDirUri(parentUri(search.file))
        : normalizeDirUri(search.uri || ROOT_URI),
    [search.file, search.uri],
  )

  const [currentUri, setCurrentUri] = useState(initialCurrentUri)
  const [selectedFile, setSelectedFile] = useState<VikingFsEntry | null>(() =>
    search.file && !isDirectoryLevelFile(search.file)
      ? createEntryFromUri(search.file, false)
      : createEntryFromUri(initialCurrentUri, true),
  )
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() =>
    mergeExpanded(
      new Set(readPlaygroundExpandedUris(identityScopeKey)),
      getAncestorUris(initialCurrentUri),
    ),
  )
  const [activePanel, setActivePanel] = useState<PlaygroundPanel>(
    search.panel ?? 'agent',
  )
  const [actionPanelOpen, setActionPanelOpen] = useState(false)
  const isCompactLayout = useIsCompactPlaygroundLayout()
  const [uploadDialogOpen, setUploadDialogOpen] = useState(
    () => search.upload ?? false,
  )
  const [findPaletteOpen, setFindPaletteOpen] = useState(false)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [openingUri, setOpeningUri] = useState<string | null>(null)

  const {
    handleResizeStart,
    handleToggleFocusCanvas,
    isFocusCanvas,
    layoutRef,
    layoutStyle,
    resizingPane,
    rightCollapsed,
    toggleRightCollapsed,
  } = usePlaygroundLayout()

  const listQuery = useVikingFsList(currentUri, {
    output: 'agent',
    showAllHidden: true,
    nodeLimit: 500,
  })

  const {
    activeTaskCount,
    clearTasks,
    hasActiveTasks,
    isRefreshingTasks,
    refreshTasks,
    tasks,
  } = useResourceUpload()

  const { invalidateList } = useInvalidateVikingFs()

  const syncSearch = useCallback(
    (next: {
      file?: string
      panel?: PlaygroundPanel
      session?: string
      upload?: boolean
      uri?: string
    }) => {
      navigate({
        replace: true,
        search: (prev) => {
          const merged: Record<string, unknown> = { ...prev, ...next }
          return Object.fromEntries(
            Object.entries(merged).filter(([, value]) => value !== undefined),
          )
        },
      })
    },
    [navigate],
  )

  useEffect(() => {
    setExpandedKeys(
      mergeExpanded(
        new Set(readPlaygroundExpandedUris(identityScopeKey)),
        getAncestorUris(initialCurrentUri),
      ),
    )
  }, [identityScopeKey, initialCurrentUri])

  const handleExpandedKeysChange = useCallback(
    (updater: Set<string> | ((prev: Set<string>) => Set<string>)) => {
      setExpandedKeys((prev) => {
        const next = typeof updater === 'function' ? updater(prev) : updater
        writePlaygroundExpandedUris(identityScopeKey, Array.from(next))
        return next
      })
    },
    [identityScopeKey],
  )

  const handleUploadDialogOpenChange = useCallback(
    (open: boolean) => {
      setUploadDialogOpen(open)
      syncSearch({ upload: open ? true : undefined })
    },
    [syncSearch],
  )

  const handlePanelChange = useCallback(
    (panel: PlaygroundPanel) => {
      setActivePanel(panel)
      syncSearch({ panel })
    },
    [syncSearch],
  )

  const handleOpenActionPanel = useCallback(
    (panel: PlaygroundPanel) => {
      handlePanelChange(panel)
      setActionPanelOpen(true)
    },
    [handlePanelChange],
  )

  const revealResource: ResourceOpenHandler = useCallback(
    async (rawUri: string) => {
      const cleaned = cleanVikingUri(rawUri)
      if (!cleaned) return

      setOpeningUri(cleaned)
      const targetUri = normalizePlaygroundResourceUri(cleaned)
      try {
        const stat = await fetchFsStat(targetUri, { throwOnError: true })
        const isDir = stat.isDir || targetUri.endsWith('/')
        const normalized = isDir
          ? normalizeDirUri(targetUri)
          : normalizeFileUri(targetUri)
        const nextCurrentUri = isDir
          ? normalizeDirUri(normalized)
          : normalizeDirUri(parentUri(normalized))

        setCurrentUri(nextCurrentUri)
        setSelectedFile({
          ...stat,
          isDir,
          name: stat.name || fileNameFromUri(normalized),
          uri: normalized,
        })
        setExpandedKeys((prev) =>
          mergeExpanded(prev, getAncestorUris(nextCurrentUri)),
        )
        syncSearch({
          file: isDir ? undefined : normalized,
          uri: nextCurrentUri,
        })
      } catch (error) {
        const fallbackIsDir = targetUri.endsWith('/')
        const normalized = fallbackIsDir
          ? normalizeDirUri(targetUri)
          : normalizeFileUri(targetUri)
        const nextCurrentUri = fallbackIsDir
          ? normalized
          : normalizeDirUri(parentUri(normalized))

        setCurrentUri(nextCurrentUri)
        setSelectedFile(null)
        setExpandedKeys((prev) =>
          mergeExpanded(prev, getAncestorUris(nextCurrentUri)),
        )
        syncSearch({
          file: undefined,
          uri: nextCurrentUri,
        })
        toast.error(getErrorMessage(error) || t('readFailed', { uri: cleaned }))
      } finally {
        setOpeningUri(null)
      }
    },
    [syncSearch, t],
  )

  const handleSelectDirectory = useCallback(
    (entry: VikingFsEntry) => {
      const normalized = normalizeDirUri(entry.uri)
      setCurrentUri(normalized)
      setSelectedFile({ ...entry, isDir: true, uri: normalized })
      setExpandedKeys((prev) =>
        mergeExpanded(prev, getAncestorUris(normalized)),
      )
      syncSearch({ file: undefined, uri: normalized })
    },
    [syncSearch],
  )

  const handleSelectFile = useCallback(
    (entry: VikingFsEntry) => {
      const normalized = normalizeFileUri(entry.uri)
      if (isDirectoryLevelFile(normalized)) {
        const dirUri = normalizeDirUri(parentUri(normalized))
        setCurrentUri(dirUri)
        setSelectedFile(createEntryFromUri(dirUri, true))
        setExpandedKeys((prev) => mergeExpanded(prev, getAncestorUris(dirUri)))
        syncSearch({ file: undefined, uri: dirUri })
        return
      }

      const nextCurrentUri = normalizeDirUri(parentUri(normalized))
      setCurrentUri(nextCurrentUri)
      setSelectedFile({ ...entry, isDir: false, uri: normalized })
      setExpandedKeys((prev) =>
        mergeExpanded(prev, getAncestorUris(nextCurrentUri)),
      )
      syncSearch({ file: normalized, uri: nextCurrentUri })
    },
    [syncSearch],
  )

  const handleOpenProcessingTasks = useCallback(() => {
    setTaskDialogOpen(true)
    void refreshTasks()
  }, [refreshTasks])

  const handleOpenSearch = useCallback(() => {
    setFindPaletteOpen(true)
  }, [])

  const handleNavigateDirectory = useCallback(
    (rawUri: string) => {
      const normalized = normalizeDirUri(rawUri)
      setCurrentUri(normalized)
      setSelectedFile(createEntryFromUri(normalized, true))
      setExpandedKeys((prev) =>
        mergeExpanded(prev, getAncestorUris(normalized)),
      )
      syncSearch({ file: undefined, uri: normalized })
    },
    [syncSearch],
  )

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setFindPaletteOpen((open) => !open)
        return
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'f') {
        if ((event.target as HTMLElement | null)?.closest('.cm-editor')) return
        event.preventDefault()
        setFindPaletteOpen(true)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const selectedUri = selectedFile?.uri ?? currentUri
  const displayUri =
    selectedUri === ROOT_URI ? selectedUri : selectedUri.replace(/\/$/, '')
  const entries = visibleContextEntries(listQuery.data?.entries ?? [])

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100svh-3rem)] min-h-0 flex-col bg-background md:-mx-6">
      <div
        ref={layoutRef}
        className="flex min-h-0 flex-1 flex-col bg-background lg:flex-row"
        style={layoutStyle}
      >
        <aside className="flex min-h-45 min-w-0 shrink-0 basis-[36%] flex-col border-b bg-muted/20 lg:min-h-0 lg:w-(--playground-left-width) lg:min-w-(--playground-left-width) lg:basis-auto lg:border-b-0">
          <ContextExplorerHeader
            activeTaskCount={activeTaskCount}
            hasActiveTasks={hasActiveTasks}
            hasTasks={tasks.length > 0}
            isFocusCanvas={isFocusCanvas}
            isRefreshing={listQuery.isFetching}
            isRefreshingTasks={isRefreshingTasks}
            onAddResource={() => setUploadDialogOpen(true)}
            onOpenProcessingTasks={handleOpenProcessingTasks}
            onOpenSearch={handleOpenSearch}
            onRefresh={() => {
              void invalidateList(currentUri)
              void listQuery.refetch()
            }}
            onToggleFocusCanvas={handleToggleFocusCanvas}
          />
          <div className="min-h-0 flex-1">
            <ContextTree
              currentUri={currentUri}
              selectedFileUri={
                selectedFile && !selectedFile.isDir ? selectedFile.uri : null
              }
              expandedKeys={expandedKeys}
              onExpandedKeysChange={handleExpandedKeysChange}
              onSelectDirectory={handleSelectDirectory}
              onSelectFile={handleSelectFile}
            />
          </div>
        </aside>

        <PlaygroundResizeHandle
          active={resizingPane === 'context'}
          label={t('resizeContext')}
          onPointerDown={(event) => handleResizeStart('context', event)}
        />

        <main className="flex min-h-0 min-w-0 flex-1 flex-col lg:border-b-0">
          <PlaygroundMainToolbar
            activePanel={activePanel}
            displayUri={displayUri}
            isFocusCanvas={isFocusCanvas}
            onOpenActionPanel={handleOpenActionPanel}
            onRevealResource={revealResource}
            onToggleRightCollapsed={toggleRightCollapsed}
            rightCollapsed={rightCollapsed}
            selectedUri={selectedUri}
            t={t}
          />
          <div className="min-h-0 flex-1">
            <LazyFilePreview
              file={selectedFile}
              hideDirectoryHeader
              onClose={() => setSelectedFile(null)}
              showCloseButton={false}
            />
          </div>
        </main>

        {!isFocusCanvas && !rightCollapsed && (
          <PlaygroundResizeHandle
            active={resizingPane === 'action'}
            label={t('resizeAction')}
            onPointerDown={(event) => handleResizeStart('action', event)}
          />
        )}

        {!isFocusCanvas && !isCompactLayout && !rightCollapsed ? (
          <aside className="hidden min-h-0 min-w-0 flex-col bg-muted/15 lg:flex lg:w-(--playground-right-width) lg:min-w-(--playground-right-width)">
            <PlaygroundActionPanel
              activePanel={activePanel}
              currentUri={currentUri}
              entries={entries}
              onCollapse={toggleRightCollapsed}
              onOpenAddResource={() => setUploadDialogOpen(true)}
              onOpenResource={revealResource}
              onPanelChange={handlePanelChange}
              onSessionChange={(sessionId) =>
                syncSearch({ session: sessionId })
              }
              openingUri={openingUri}
              sessionId={search.session}
            />
          </aside>
        ) : null}
      </div>

      <PlaygroundDialogs
        actionPanelOpen={actionPanelOpen}
        activePanel={activePanel}
        currentUri={currentUri}
        entries={entries}
        findPaletteOpen={findPaletteOpen}
        isCompactLayout={isCompactLayout}
        onClearTasks={clearTasks}
        onCloseActionPanel={() => setActionPanelOpen(false)}
        onCloseFindPalette={() => setFindPaletteOpen(false)}
        onInvalidateList={() => void invalidateList()}
        onNavigateDirectory={handleNavigateDirectory}
        onOpenAddResource={() => setUploadDialogOpen(true)}
        onOpenResource={revealResource}
        onPanelChange={handlePanelChange}
        onSessionChange={(sessionId) => syncSearch({ session: sessionId })}
        onSetTaskDialogOpen={setTaskDialogOpen}
        onUploadDialogOpenChange={handleUploadDialogOpenChange}
        openingUri={openingUri}
        sessionId={search.session}
        t={t}
        taskDialogOpen={taskDialogOpen}
        tasks={tasks}
        uploadDialogOpen={uploadDialogOpen}
      />
    </div>
  )
}
