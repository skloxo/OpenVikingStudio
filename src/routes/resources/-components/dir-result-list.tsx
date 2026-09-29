import { FileIcon, FolderIcon, FolderOpen } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '#/lib/utils'
import { useTransientScrollbar } from '#/hooks/use-transient-scrollbar'
import type { VikingFsEntry } from '../-types/viking-fm'
import { displayName } from './find-palette-utils'

export interface DirResultListProps {
  className?: string
  items: VikingFsEntry[]
  activeIndex: number
  onActiveChange: (index: number) => void
  onSelect: (entry: VikingFsEntry) => void
  onOpenDir: (entry: VikingFsEntry) => void
}

export function DirResultList({
  className,
  items,
  activeIndex,
  onActiveChange,
  onSelect,
  onOpenDir,
}: DirResultListProps) {
  const { t } = useTranslation('resources')
  const { isScrolling, onScroll } = useTransientScrollbar()

  return (
    <div
      className={cn(
        'scrollbar-fade min-h-0 flex-1 overflow-y-auto overscroll-contain',
        className,
      )}
      data-scrolling={isScrolling || undefined}
      onScroll={onScroll}
    >
      {items.map((entry, i) => {
        const { name, parent } = displayName(entry.uri)
        const isActive = i === activeIndex
        const EntryIcon = entry.isDir ? FolderIcon : FileIcon

        return (
          <div
            key={`${entry.uri}#${i}`}
            data-active={isActive}
            className={cn(
              'animate-palette-row group relative flex w-full items-start gap-3 border-b border-border/50 px-4 py-3 text-left transition-colors last:border-b-0',
              isActive
                ? 'bg-primary/8 text-foreground'
                : 'text-foreground/80 hover:bg-muted/40',
            )}
            style={{ animationDelay: `${i * 24}ms` }}
            onMouseEnter={() => onActiveChange(i)}
          >
            {isActive && (
              <span className="absolute inset-y-0 left-0 w-0.5 rounded-r bg-primary" />
            )}
            <button
              type="button"
              className="flex min-w-0 flex-1 items-start gap-3 text-left outline-none"
              onFocus={() => onActiveChange(i)}
              onClick={() => onSelect(entry)}
            >
              <EntryIcon
                className={cn(
                  'mt-0.5 size-4 shrink-0',
                  entry.isDir ? 'text-blue-500/70' : 'text-muted-foreground/70',
                )}
              />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{name}</div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground/80">
                  {entry.abstract.trim() ? entry.abstract : parent}
                </div>
              </div>
            </button>
            {entry.size && (
              <span className="shrink-0 text-xs tabular-nums text-muted-foreground/60">
                {entry.size}
              </span>
            )}
            <button
              type="button"
              title={t('searchPalette.openContainingDirectory')}
              className="shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring group-hover:opacity-100 data-[active=true]:opacity-100"
              data-active={isActive}
              onClick={(e) => {
                e.stopPropagation()
                onOpenDir(entry)
              }}
            >
              <FolderOpen className="size-3.5" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
