import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '#/lib/utils'
import { normalizeDirUri, parentUri as getParentUri } from '../-lib/normalize'
import {
  PALETTE_ROOT_URI,
  buildDirBrowseQuery,
  cycleSearchMode,
  isResetGlobalCommand,
} from '../-lib/palette-mode'
import type { PaletteSearchMode } from '../-lib/palette-mode'
import { usePaletteSearch } from '../-hooks/use-palette-search'
import { DirBrowser } from './dir-browser'
import { LazyFilePreview } from './lazy-file-preview'
import { DirResultList } from './dir-result-list'
import { FindPaletteHeader } from './find-palette-header'
import { FindPaletteFooter } from './find-palette-footer'
import { displayName, errorDescription } from './find-palette-utils'

export { DirResultList }
export { displayName, errorDescription }

export interface FindPaletteProps {
  open: boolean
  onClose: () => void
  onNavigate: (uri: string) => void
  onNavigateDir: (uri: string) => void
  scopeUri?: string
}

export function FindPalette({
  open,
  onClose,
  onNavigate,
  onNavigateDir,
  scopeUri,
}: FindPaletteProps) {
  const { t } = useTranslation(['resources', 'retrieval'])
  const [query, setQuery] = useState('')
  const [searchMode, setSearchMode] = useState<PaletteSearchMode>('name')
  const [findTargetUri, setFindTargetUri] = useState(() =>
    normalizeDirUri(scopeUri || PALETTE_ROOT_URI),
  )
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const composingRef = useRef(false)
  const wasOpenRef = useRef(false)

  const {
    mode,
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
  } = usePaletteSearch({
    query,
    searchMode,
    findTargetUri,
  })

  const focusInput = useCallback(() => {
    requestAnimationFrame(() => {
      inputRef.current?.focus()
      inputRef.current?.select()
    })
  }, [])

  useEffect(() => {
    if (open && !wasOpenRef.current) {
      setFindTargetUri(normalizeDirUri(scopeUri || PALETTE_ROOT_URI))
      reset()
      focusInput()
    }
    wasOpenRef.current = open
  }, [open, scopeUri, reset, focusInput])

  useEffect(() => {
    if (!open) return

    const restoreFocus = () => {
      if (document.visibilityState === 'visible') focusInput()
    }
    window.addEventListener('focus', focusInput)
    document.addEventListener('visibilitychange', restoreFocus)
    return () => {
      window.removeEventListener('focus', focusInput)
      document.removeEventListener('visibilitychange', restoreFocus)
    }
  }, [open, focusInput])

  useEffect(() => {
    if (!resultsRef.current) return
    const el = resultsRef.current.querySelector('[data-active="true"]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  const enterDir = useCallback((uri: string) => {
    setQuery(buildDirBrowseQuery(uri))
  }, [])

  const goToParent = useCallback(() => {
    if (mode.kind !== 'dirBrowse') return
    const parent = getParentUri(mode.uri)
    if (parent !== mode.uri) {
      setQuery(buildDirBrowseQuery(parent))
    }
  }, [mode])

  const confirmDirScope = useCallback((uri: string) => {
    setFindTargetUri(normalizeDirUri(uri))
    setQuery('')
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (composingRef.current) return

      // `//` + Enter resets scope to global root, regardless of mode.
      if (isResetGlobalCommand(query) && e.key === 'Enter') {
        e.preventDefault()
        setFindTargetUri(PALETTE_ROOT_URI)
        setQuery('')
        return
      }

      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }

      if (mode.kind === 'dirBrowse') {
        switch (e.key) {
          case 'ArrowDown':
            e.preventDefault()
            moveDown()
            return
          case 'ArrowUp':
            e.preventDefault()
            moveUp()
            return
          case 'ArrowRight':
          case 'Tab':
            e.preventDefault()
            if (activeEntry?.isDir) {
              enterDir(activeEntry.uri)
            } else if (e.key === 'Tab' && activeEntry) {
              onNavigate(activeEntry.uri)
              onClose()
            }
            return
          case 'ArrowLeft':
            e.preventDefault()
            goToParent()
            return
          case 'Enter':
            e.preventDefault()
            if (activeEntry && !activeEntry.isDir) {
              onNavigate(activeEntry.uri)
              onClose()
            } else if (dirListQuery.isSuccess) {
              confirmDirScope(mode.uri)
            }
            return
        }
        return
      }

      // Outside dirBrowse, Tab cycles the search mode (query is untouched).
      if (e.key === 'Tab') {
        e.preventDefault()
        setSearchMode((current) => cycleSearchMode(current, e.shiftKey))
        return
      }

      // search / idle list navigation
      if (visibleEntries.length === 0) return
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          moveDown()
          return
        case 'ArrowUp':
          e.preventDefault()
          moveUp()
          return
        case 'Enter':
          e.preventDefault()
          if (!activeEntry) return
          if (mode.kind === 'idle' && activeEntry.isDir) {
            confirmDirScope(activeEntry.uri)
          } else {
            onNavigate(activeEntry.uri)
            onClose()
          }
          return
      }
    },
    [
      query,
      mode,
      activeEntry,
      visibleEntries.length,
      dirListQuery.isSuccess,
      moveUp,
      moveDown,
      enterDir,
      goToParent,
      confirmDirScope,
      onNavigate,
      onClose,
    ],
  )

  if (!open) return null

  const showPreview = mode.kind !== 'dirBrowse' && activeEntry !== null
  const paletteWidth =
    mode.kind === 'idle' && !showPreview
      ? 'w-[min(90vw,45rem)]'
      : 'w-[min(92vw,67rem)]'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 sm:items-start sm:px-6 sm:pt-[12vh]"
      role="dialog"
      aria-modal="true"
      aria-label={t('searchPalette.ariaLabel')}
    >
      <div
        className="animate-palette-backdrop absolute inset-0 bg-background/60 backdrop-blur-sm"
        role="presentation"
        onClick={onClose}
      />

      <div
        className={cn(
          'animate-palette-in relative flex h-184 max-h-[calc(100svh-2rem)] max-w-full flex-col overflow-hidden rounded-xl border bg-background shadow-2xl shadow-black/20 transition-[width] duration-300 sm:max-h-[84vh]',
          paletteWidth,
        )}
        onKeyDown={handleKeyDown}
      >
        <FindPaletteHeader
          query={query}
          onQueryChange={setQuery}
          searchMode={searchMode}
          onSearchModeChange={setSearchMode}
          findTargetUri={findTargetUri}
          onResetScope={() => setFindTargetUri(PALETTE_ROOT_URI)}
          isDirBrowse={mode.kind === 'dirBrowse'}
          inputRef={inputRef}
          composingRef={composingRef}
        />

        {/* Body */}
        <div className="flex min-h-0 flex-1" ref={resultsRef}>
          {mode.kind === 'dirBrowse' ? (
            <DirBrowser
              currentUri={mode.uri}
              items={dirItems}
              activeIndex={activeIndex}
              loading={dirListQuery.isLoading}
              errored={dirListQuery.isError}
              onCursorChange={setIndex}
              onEnterDir={enterDir}
              onOpenFile={(uri) => {
                onNavigate(uri)
                onClose()
              }}
              onGoBack={goToParent}
            />
          ) : (
            <>
              {/* Results area */}
              <div
                className={cn(
                  'min-h-0 flex-1 overflow-hidden',
                  showPreview && 'border-r',
                )}
              >
                {mode.kind === 'idle' ? (
                  showIdleBrowse && idleBrowseQuery.isError ? (
                    <div
                      role="alert"
                      className="px-4 py-6 text-center text-xs text-destructive"
                    >
                      {t('dirBrowser.error')}
                    </div>
                  ) : showIdleBrowse && idleEntries.length > 0 ? (
                    <DirResultList
                      className="h-full"
                      items={idleEntries}
                      activeIndex={activeIndex}
                      onActiveChange={setIndex}
                      onSelect={(entry) => {
                        if (entry.isDir) {
                          confirmDirScope(entry.uri)
                        } else {
                          onNavigate(entry.uri)
                          onClose()
                        }
                      }}
                      onOpenDir={(entry) => {
                        onNavigateDir(getParentUri(entry.uri))
                        onClose()
                      }}
                    />
                  ) : (
                    <div className="animate-palette-in flex flex-col items-center gap-3 px-4 py-12 text-center">
                      <Search className="size-6 text-muted-foreground/30" />
                      <div>
                        <p className="text-sm text-muted-foreground/70">
                          {t('searchPalette.empty.title')}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground/50">
                          {t('searchPalette.browseDirHint.before')}{' '}
                          <kbd className="rounded border border-border bg-muted/50 px-1 py-0.5 font-mono text-xs text-foreground/70">
                            /
                          </kbd>{' '}
                          {t('searchPalette.browseDirHint.after')}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground/50">
                          {t('searchPalette.globalScopeHint.before')}{' '}
                          <kbd className="rounded border border-border bg-muted/50 px-1 py-0.5 font-mono text-xs text-foreground/70">
                            //
                          </kbd>{' '}
                          {t('searchPalette.globalScopeHint.after')}
                        </p>
                      </div>
                    </div>
                  )
                ) : searchQuery.isLoading ? (
                  <div className="flex flex-col items-center gap-3 py-12">
                    <Loader2 className="size-5 animate-spin text-muted-foreground/50" />
                    <p className="text-xs text-muted-foreground/60">
                      {t('searchPalette.scopeState.validatingTitle')}
                    </p>
                  </div>
                ) : searchQuery.error ? (
                  <div
                    role="alert"
                    className="flex flex-col items-center gap-1 px-4 py-6 text-center text-xs text-destructive"
                  >
                    <span>{t('searchPalette.error')}</span>
                    <span className="max-w-lg text-muted-foreground">
                      {errorDescription(searchQuery.error)}
                    </span>
                  </div>
                ) : !hasResults ? (
                  <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
                    <Search className="size-5 text-muted-foreground/25" />
                    <p className="text-sm text-muted-foreground/60">
                      {t('searchPalette.emptyResults.title')}
                    </p>
                    <p className="text-xs text-muted-foreground/40">
                      {t('searchPalette.emptyResults.subtitle')}
                    </p>
                  </div>
                ) : (
                  <DirResultList
                    className="h-full"
                    items={filteredEntries}
                    activeIndex={activeIndex}
                    onActiveChange={setIndex}
                    onSelect={(entry) => {
                      onNavigate(entry.uri)
                      onClose()
                    }}
                    onOpenDir={(entry) => {
                      onNavigateDir(getParentUri(entry.uri))
                      onClose()
                    }}
                  />
                )}
              </div>

              {/* Preview pane */}
              {showPreview && (
                <div className="animate-palette-preview flex h-full w-lg flex-col overflow-hidden">
                  <LazyFilePreview
                    file={previewEntry}
                    onClose={() => setIndex(-1)}
                    showCloseButton={false}
                  />
                </div>
              )}
            </>
          )}
        </div>

        <FindPaletteFooter
          isDirBrowse={mode.kind === 'dirBrowse'}
          hasResults={hasResults}
          visibleCount={visibleEntries.length}
        />
      </div>
    </div>
  )
}
