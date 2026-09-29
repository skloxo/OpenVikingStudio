import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2Icon } from 'lucide-react'

import { useVikingFsList } from '#/routes/resources/-hooks/viking-fm'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import { ROOT_URI } from '../-lib/constants'
import { visibleContextEntries } from '../-lib/utils'

import {
  ContextTreeNode,
  TreeIndentGuides,
  treeChildContentPadding,
  treeGuideLeft,
  treeRowPadding,
} from './context-tree-node'
import { ContextExplorerHeader } from './context-explorer-header'
import { PanelTab, PlaygroundResizeHandle } from './playground-resize-handle'

export {
  ContextExplorerHeader,
  ContextTreeNode,
  PanelTab,
  PlaygroundResizeHandle,
  TreeIndentGuides,
  treeChildContentPadding,
  treeGuideLeft,
  treeRowPadding,
}

const NAMESPACE_DESCRIPTION_KEYS: Partial<
  Record<
    string,
    | 'explorer.namespaces.agent'
    | 'explorer.namespaces.resources'
    | 'explorer.namespaces.user'
  >
> = {
  agent: 'explorer.namespaces.agent',
  resources: 'explorer.namespaces.resources',
  user: 'explorer.namespaces.user',
} as const

const NAMESPACE_ORDER: Partial<Record<string, number>> = {
  user: 0,
  resources: 1,
  agent: 2,
}

export function ContextTree({
  currentUri,
  expandedKeys,
  onExpandedKeysChange,
  onSelectDirectory,
  onSelectFile,
  selectedFileUri,
}: {
  currentUri: string
  expandedKeys: Set<string>
  onExpandedKeysChange: (next: Set<string>) => void
  onSelectDirectory: (entry: VikingFsEntry) => void
  onSelectFile: (entry: VikingFsEntry) => void
  selectedFileUri?: string | null
}) {
  const { t } = useTranslation('playground')
  const rootQuery = useVikingFsList(ROOT_URI, {
    output: 'agent',
    showAllHidden: true,
    nodeLimit: 200,
    sortBy: 'name',
    sortOrder: 'asc',
  })
  const namespaces = useMemo(
    () =>
      [...visibleContextEntries(rootQuery.data?.entries ?? [])].sort(
        (left, right) => {
          const leftOrder =
            NAMESPACE_ORDER[left.name.toLowerCase()] ?? Number.POSITIVE_INFINITY
          const rightOrder =
            NAMESPACE_ORDER[right.name.toLowerCase()] ??
            Number.POSITIVE_INFINITY
          return leftOrder - rightOrder || left.name.localeCompare(right.name)
        },
      ),
    [rootQuery.data?.entries],
  )

  return (
    <div className="h-full overflow-auto px-2 py-2 font-mono">
      {rootQuery.isLoading ? (
        <div className="flex h-7 items-center gap-2 px-1.5 text-xs text-muted-foreground">
          <Loader2Icon className="size-3 animate-spin" />
          {t('explorer.loading')}
        </div>
      ) : rootQuery.isError ? (
        <div className="px-1.5 text-xs leading-7 text-destructive">
          {t('dirBrowser.error', { ns: 'resources' })}
        </div>
      ) : namespaces.length === 0 ? (
        <div className="px-1.5 text-xs leading-7 text-muted-foreground/60">
          {t('explorer.empty')}
        </div>
      ) : (
        <ul
          role="list"
          aria-label={t('explorer.title')}
          className="m-0 min-w-0 list-none p-0"
        >
          {namespaces.map((entry) => {
            const normalizedName = entry.name.toLowerCase()
            const descriptionKey = NAMESPACE_DESCRIPTION_KEYS[normalizedName]

            return (
              <ContextTreeNode
                key={entry.uri}
                currentUri={currentUri}
                entry={{
                  ...entry,
                  name: entry.name,
                  abstract: descriptionKey ? t(descriptionKey) : entry.abstract,
                }}
                expandedKeys={expandedKeys}
                level={0}
                onExpandedKeysChange={onExpandedKeysChange}
                onSelectDirectory={onSelectDirectory}
                onSelectFile={onSelectFile}
                selectedFileUri={selectedFileUri}
              />
            )
          })}
        </ul>
      )}
    </div>
  )
}
