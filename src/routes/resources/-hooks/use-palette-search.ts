import { useEffect, useMemo } from 'react'

import { useRetrievalQuery } from '#/routes/retrieval/-hooks/use-retrieval-query'
import type { RetrievalMode } from '#/routes/retrieval/-types/retrieval'
import {
  filterResourceSearchEntries,
  getResourceSearchSpec,
  normalizeGlobPattern,
  retrievalItemsToEntries,
} from '../-lib/find-search'
import { PALETTE_ROOT_URI, parsePaletteMode } from '../-lib/palette-mode'
import type { PaletteSearchMode } from '../-lib/palette-mode'
import {
  useDebouncedValue,
  useVikingFsList,
  useVikingFsStat,
  useVikingFsTree,
} from './viking-fm'
import { useListNavigation } from './use-list-navigation'
import type { VikingFsEntry } from '../-types/viking-fm'

export interface UsePaletteSearchOptions {
  query: string
  searchMode: PaletteSearchMode
  findTargetUri: string
}

export function usePaletteSearch({
  query,
  searchMode,
  findTargetUri,
}: UsePaletteSearchOptions) {
  // Single parse entry point. No component code reads `query` structurally.
  const mode = useMemo(
    () => parsePaletteMode(query, findTargetUri),
    [query, findTargetUri],
  )
  const isRoot = findTargetUri === PALETTE_ROOT_URI
  const showIdleBrowse = mode.kind === 'idle' && !isRoot

  const searchSpec = useMemo(
    () =>
      mode.kind === 'search'
        ? getResourceSearchSpec(mode.query, findTargetUri)
        : null,
    [mode, findTargetUri],
  )

  const idleBrowseQuery = useVikingFsList(
    findTargetUri,
    { output: 'agent', showAllHidden: true },
    showIdleBrowse,
  )
  const idleEntries = useMemo(
    () => (showIdleBrowse ? idleBrowseQuery.data?.entries || [] : []),
    [showIdleBrowse, idleBrowseQuery.data?.entries],
  )

  const isNameMode = searchMode === 'name'
  const treeQuery = useVikingFsTree(
    searchSpec?.rootUri || PALETTE_ROOT_URI,
    { output: 'agent', showAllHidden: true, nodeLimit: 2000, levelLimit: 100 },
    isNameMode && mode.kind === 'search' && Boolean(searchSpec),
  )

  // 400ms debounce auto-fires find/search semantic retrieval
  const debouncedQuery = useDebouncedValue(
    mode.kind === 'search' ? mode.query : '',
    400,
  )
  const retrievalOptions = useMemo(
    () => ({
      contextTypes: [],
      customPathInput: '',
      ignoreCase: true,
      includeProvenance: false,
      levels: [],
      resultCount: 20,
      scope: 'custom' as const,
      tags: [],
      targetUri: isRoot ? undefined : findTargetUri,
      timeField: 'updated_at' as const,
    }),
    [isRoot, findTargetUri],
  )
  const retrievalQuery = useRetrievalQuery({
    enabled: mode.kind === 'search' && !isNameMode && debouncedQuery.length > 0,
    mode: searchMode as RetrievalMode,
    options: retrievalOptions,
    query:
      searchMode === 'glob'
        ? normalizeGlobPattern(debouncedQuery)
        : debouncedQuery,
  })

  const filteredEntries = useMemo(() => {
    if (mode.kind !== 'search') return []
    if (!isNameMode) return retrievalItemsToEntries(retrievalQuery.data)
    if (!treeQuery.data?.nodes) return []
    return filterResourceSearchEntries(treeQuery.data.nodes, searchSpec)
  }, [
    mode.kind,
    isNameMode,
    retrievalQuery.data,
    treeQuery.data?.nodes,
    searchSpec,
  ])
  const searchQuery = isNameMode ? treeQuery : retrievalQuery

  // Directory listing lifted up from DirBrowser so the cursor (activeIndex) and
  // keyboard handling can live in one place. DirBrowser is a pure view.
  const dirListQuery = useVikingFsList(
    mode.kind === 'dirBrowse' ? mode.uri : PALETTE_ROOT_URI,
    { output: 'agent', showAllHidden: true, nodeLimit: 200 },
    mode.kind === 'dirBrowse',
  )
  const dirItems = useMemo(() => {
    if (mode.kind !== 'dirBrowse') return []
    const entries = dirListQuery.data?.entries ?? []
    const dirs = entries.filter((e) => e.isDir)
    const files = entries.filter((e) => !e.isDir)
    const all = [...dirs, ...files]
    if (!mode.filter) return all
    const lower = mode.filter.toLowerCase()
    return all.filter((e) => e.name.toLowerCase().includes(lower))
  }, [mode, dirListQuery.data])

  const hasResults = filteredEntries.length > 0
  const visibleEntries = useMemo(() => {
    if (mode.kind === 'dirBrowse') return dirItems
    if (hasResults) return filteredEntries
    return idleEntries
  }, [mode.kind, dirItems, hasResults, filteredEntries, idleEntries])

  const {
    index: activeIndex,
    setIndex,
    moveUp,
    moveDown,
    reset,
  } = useListNavigation(visibleEntries.length)
  const activeEntry =
    activeIndex >= 0 ? (visibleEntries[activeIndex] ?? null) : null

  // Preview stat only for search / idle file cursor. Debounced to avoid storming.
  const statTargetUri =
    mode.kind !== 'dirBrowse' && activeEntry && !activeEntry.isDir
      ? activeEntry.uri
      : undefined
  const debouncedStatUri = useDebouncedValue(statTargetUri, 150)
  const statQuery = useVikingFsStat(debouncedStatUri)
  const previewEntry = useMemo(() => {
    if (!activeEntry) return null
    if (statQuery.data && debouncedStatUri === activeEntry.uri) {
      return {
        ...activeEntry,
        size: statQuery.data.size,
        sizeBytes: statQuery.data.sizeBytes,
        modTime: statQuery.data.modTime,
      }
    }
    return activeEntry
  }, [activeEntry, statQuery.data, debouncedStatUri])

  // Cursor resets on query change and whenever the visible list changes
  useEffect(() => {
    reset()
  }, [query, visibleEntries, reset])

  return {
    mode,
    isRoot,
    showIdleBrowse,
    idleBrowseQuery,
    idleEntries,
    searchQuery,
    filteredEntries,
    hasResults,
    dirListQuery,
    dirItems,
    visibleEntries,
    activeIndex,
    setIndex,
    moveUp,
    moveDown,
    reset,
    activeEntry,
    previewEntry,
  }
}
