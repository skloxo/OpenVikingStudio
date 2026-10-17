import { FolderOpen, Search, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '#/lib/utils'
import {
  PALETTE_ROOT_URI,
  PALETTE_SEARCH_MODES,
} from '../-lib/palette-mode'
import type { PaletteSearchMode } from '../-lib/palette-mode'

const KEY_TAB_LABEL = 'Tab'

export interface FindPaletteHeaderProps {
  query: string
  onQueryChange: (query: string) => void
  searchMode: PaletteSearchMode
  onSearchModeChange: (mode: PaletteSearchMode) => void
  findTargetUri: string
  onResetScope: () => void
  isDirBrowse: boolean
  inputRef: React.RefObject<HTMLInputElement | null>
  composingRef: React.MutableRefObject<boolean>
}

export function FindPaletteHeader({
  query,
  onQueryChange,
  searchMode,
  onSearchModeChange,
  findTargetUri,
  onResetScope,
  isDirBrowse,
  inputRef,
  composingRef,
}: FindPaletteHeaderProps) {
  const { t } = useTranslation(['resources', 'retrieval'])
  const isRoot = findTargetUri === PALETTE_ROOT_URI

  return (
    <>
      {/* Search input bar */}
      <div className="flex items-center gap-3 border-b px-4">
        <Search className="size-4 shrink-0 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          placeholder={
            searchMode === 'name'
              ? t('searchPalette.placeholder')
              : t(`placeholders.${searchMode}`, { ns: 'retrieval' })
          }
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onCompositionStart={() => {
            composingRef.current = true
          }}
          onCompositionEnd={() => {
            composingRef.current = false
          }}
          className="h-12 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground/70 md:text-sm"
        />
        {query && (
          <button
            type="button"
            className="rounded-md p-1 text-muted-foreground/70 transition-colors hover:text-foreground"
            onClick={() => onQueryChange('')}
          >
            <X className="size-3.5" />
          </button>
        )}
        <span className="flex items-center gap-1 text-xs text-muted-foreground/70">
          {isRoot ? (
            t('searchPalette.scope.global')
          ) : (
            <button
              type="button"
              className="flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:bg-muted hover:text-foreground"
              title={t('searchPalette.scope.resetToGlobal')}
              onClick={onResetScope}
            >
              <FolderOpen className="size-3" />
              {t('searchPalette.scope.current', {
                name: findTargetUri.split('/').filter(Boolean).pop(),
              })}
              <X className="size-3" />
            </button>
          )}
        </span>
      </div>

      {/* Search mode switcher */}
      {!isDirBrowse && (
        <div className="flex items-center gap-1 border-b px-4 py-1.5">
          {PALETTE_SEARCH_MODES.map((item) => (
            <button
              key={item}
              type="button"
              className={cn(
                'rounded px-1.5 py-0.5 font-mono text-xs transition-colors',
                searchMode === item
                  ? 'bg-muted text-foreground'
                  : 'text-muted-foreground/60 hover:text-foreground',
              )}
              onClick={() => onSearchModeChange(item)}
            >
              {item === 'name'
                ? t('searchPalette.modes.name')
                : t(`controls.modes.${item}`, { ns: 'retrieval' })}
            </button>
          ))}
          <span className="ml-auto text-xs text-muted-foreground/50">
            <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
              {KEY_TAB_LABEL}
            </kbd>{' '}
            {t('searchPalette.modes.switchHint')}
          </span>
        </div>
      )}
    </>
  )
}
