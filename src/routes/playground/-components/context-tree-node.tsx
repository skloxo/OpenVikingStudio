import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronRightIcon,
  FileTextIcon,
  FolderIcon,
  Loader2Icon,
} from 'lucide-react'

import { cn } from '#/lib/utils'
import { useVikingFsList } from '#/routes/resources/-hooks/viking-fm'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import { sortTreeEntries, visibleContextEntries } from '../-lib/utils'

export const TREE_INDENT_WIDTH = 16
export const TREE_ROW_PADDING = 6
export const TREE_GUIDE_OFFSET = 8
export const TREE_CHILD_CONTENT_OFFSET = 26
export const TREE_CONTROL_SIZE = 16
export const TREE_CONTROL_GAP = 6

export function treeGuideLeft(index: number): string {
  return `${TREE_ROW_PADDING + index * TREE_INDENT_WIDTH + TREE_GUIDE_OFFSET}px`
}

export function treeRowPadding(level: number): string {
  return `${level * TREE_INDENT_WIDTH + TREE_ROW_PADDING}px`
}

function treeSelectionPadding(level: number, hasDisclosure: boolean): string {
  const disclosureOffset = hasDisclosure
    ? TREE_CONTROL_SIZE + TREE_CONTROL_GAP
    : 0
  return `${level * TREE_INDENT_WIDTH + TREE_ROW_PADDING + disclosureOffset}px`
}

export function treeChildContentPadding(level: number): string {
  return `${(level + 1) * TREE_INDENT_WIDTH + TREE_CHILD_CONTENT_OFFSET}px`
}

export function TreeIndentGuides({ level }: { level: number }) {
  if (level <= 0) return null

  return (
    <div className="pointer-events-none absolute inset-y-0 left-0 right-0 z-0">
      {Array.from({ length: level }, (_, index) => (
        <span
          key={index}
          className="absolute bottom-0 top-0 w-px bg-border/70"
          style={{ left: treeGuideLeft(index) }}
        />
      ))}
    </div>
  )
}

export interface ContextTreeNodeProps {
  currentUri: string
  entry: VikingFsEntry
  expandedKeys: Set<string>
  level: number
  onExpandedKeysChange: (next: Set<string>) => void
  onSelectDirectory: (entry: VikingFsEntry) => void
  onSelectFile: (entry: VikingFsEntry) => void
  selectedFileUri?: string | null
}

export function ContextTreeNode({
  currentUri,
  entry,
  expandedKeys,
  level,
  onExpandedKeysChange,
  onSelectDirectory,
  onSelectFile,
  selectedFileUri,
}: ContextTreeNodeProps) {
  const { t } = useTranslation('playground')
  const isOpen = expandedKeys.has(entry.uri)
  const isFileSelected = !entry.isDir && selectedFileUri === entry.uri
  const isDirSelected =
    entry.isDir && currentUri === entry.uri && !selectedFileUri
  const isSelected = isDirSelected || isFileSelected
  const namespaceHint = level === 0 ? entry.abstract : ''
  const rowRef = useRef<HTMLDivElement>(null)
  const disclosureLabel = entry.isDir
    ? t(isOpen ? 'explorer.collapseDirectory' : 'explorer.expandDirectory', {
        name: entry.name,
      })
    : ''
  const shouldLoadChildren = entry.isDir && isOpen
  const listQuery = useVikingFsList(
    entry.uri,
    {
      output: 'agent',
      showAllHidden: true,
      nodeLimit: 200,
    },
    shouldLoadChildren,
  )
  const children = useMemo(
    () => sortTreeEntries(visibleContextEntries(listQuery.data?.entries ?? [])),
    [listQuery.data?.entries],
  )

  useEffect(() => {
    if (!isSelected) return

    window.requestAnimationFrame(() => {
      rowRef.current?.scrollIntoView({
        block: 'center',
        inline: 'nearest',
      })
    })
  }, [entry.uri, isSelected])

  const toggle = useCallback(() => {
    if (!entry.isDir) return
    const next = new Set(expandedKeys)
    if (isOpen) next.delete(entry.uri)
    else next.add(entry.uri)
    onExpandedKeysChange(next)
  }, [entry.isDir, entry.uri, expandedKeys, isOpen, onExpandedKeysChange])

  const select = useCallback(() => {
    if (entry.isDir) {
      onSelectDirectory(entry)
      if (!isOpen || isSelected) {
        toggle()
      }
    } else {
      onSelectFile(entry)
    }
  }, [entry, isOpen, isSelected, onSelectDirectory, onSelectFile, toggle])

  return (
    <li className="relative min-w-0 list-none">
      <TreeIndentGuides level={level} />
      <div
        ref={rowRef}
        className={cn(
          'group relative z-10 h-7 select-none rounded-md text-xs transition-colors',
          isSelected
            ? 'bg-muted text-foreground'
            : 'text-muted-foreground hover:bg-muted/55 hover:text-foreground',
        )}
      >
        {entry.isDir ? (
          <button
            type="button"
            aria-expanded={isOpen}
            aria-label={disclosureLabel}
            title={disclosureLabel}
            className="absolute top-1/2 z-20 inline-flex size-4 -translate-y-1/2 cursor-pointer items-center justify-center rounded-sm text-muted-foreground outline-none transition-colors group-hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
            style={{ left: treeRowPadding(level) }}
            onClick={toggle}
          >
            <ChevronRightIcon
              aria-hidden="true"
              className={cn(
                'size-3 transition-transform',
                isOpen && 'rotate-90',
              )}
            />
          </button>
        ) : null}
        <button
          type="button"
          aria-label={entry.name}
          aria-current={isSelected ? 'location' : undefined}
          className="absolute inset-0 z-10 flex min-w-0 cursor-pointer items-center gap-1.5 rounded-md pr-1.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
          style={{ paddingLeft: treeSelectionPadding(level, entry.isDir) }}
          onClick={select}
        >
          {!entry.isDir ? (
            <span aria-hidden="true" className="size-4 shrink-0" />
          ) : null}
          {entry.isDir ? (
            <FolderIcon
              aria-hidden="true"
              className={cn(
                'size-4 shrink-0',
                isOpen ? 'text-primary/80' : 'text-muted-foreground',
              )}
            />
          ) : (
            <FileTextIcon
              aria-hidden="true"
              className="size-4 shrink-0 text-muted-foreground"
            />
          )}
          <span
            className={cn(
              'truncate',
              namespaceHint ? 'shrink-0 text-foreground' : 'min-w-0 flex-1',
            )}
          >
            {entry.name}
          </span>
          {namespaceHint ? (
            <span className="min-w-0 flex-1 truncate font-sans text-xs text-muted-foreground">
              {namespaceHint}
            </span>
          ) : null}
          {entry.name === '_abstract.md' ? (
            <span className="shrink-0 rounded bg-muted px-1 font-sans text-xs text-muted-foreground">
              {t('explorer.abstractLevel')}
            </span>
          ) : entry.name === '_overview.md' ? (
            <span className="shrink-0 rounded bg-muted px-1 font-sans text-xs text-muted-foreground">
              {t('explorer.overviewLevel')}
            </span>
          ) : null}
        </button>
      </div>

      {entry.isDir && isOpen ? (
        listQuery.isLoading ? (
          <div
            className="relative flex h-7 items-center gap-2 px-1.5 text-xs text-muted-foreground"
            style={{ paddingLeft: treeChildContentPadding(level) }}
          >
            <TreeIndentGuides level={level + 1} />
            <Loader2Icon className="size-3 animate-spin" />
            {t('explorer.loading')}
          </div>
        ) : children.length > 0 ? (
          <ul role="list" className="m-0 min-w-0 list-none p-0">
            {children.map((child) => (
              <ContextTreeNode
                key={child.uri}
                currentUri={currentUri}
                entry={child}
                expandedKeys={expandedKeys}
                level={level + 1}
                onExpandedKeysChange={onExpandedKeysChange}
                onSelectDirectory={onSelectDirectory}
                onSelectFile={onSelectFile}
                selectedFileUri={selectedFileUri}
              />
            ))}
          </ul>
        ) : (
          <div
            className="relative h-7 px-1.5 text-xs leading-7 text-muted-foreground/60"
            style={{ paddingLeft: treeChildContentPadding(level) }}
          >
            <TreeIndentGuides level={level + 1} />
            {t('explorer.empty')}
          </div>
        )
      ) : null}
    </li>
  )
}
