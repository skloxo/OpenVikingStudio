import { useTranslation } from 'react-i18next'
import {
  ClipboardListIcon,
  FolderTreeIcon,
  PanelRightClose,
  PanelRightOpen,
  PlusIcon,
  RefreshCcwIcon,
  SearchIcon,
} from 'lucide-react'

import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'

export interface ContextExplorerHeaderProps {
  activeTaskCount: number
  hasActiveTasks: boolean
  hasTasks: boolean
  isFocusCanvas?: boolean
  isRefreshing: boolean
  isRefreshingTasks: boolean
  onAddResource: () => void
  onOpenProcessingTasks: () => void
  onOpenSearch: () => void
  onRefresh: () => void
  onToggleFocusCanvas?: () => void
}

export function ContextExplorerHeader({
  activeTaskCount,
  hasActiveTasks,
  hasTasks,
  isFocusCanvas = false,
  isRefreshing,
  isRefreshingTasks,
  onAddResource,
  onOpenProcessingTasks,
  onOpenSearch,
  onRefresh,
  onToggleFocusCanvas,
}: ContextExplorerHeaderProps) {
  const { t } = useTranslation(['playground', 'resources'])
  const showProcessingTasks = hasTasks || isRefreshingTasks

  return (
    <div className="border-b px-3 py-3">
      <div className="flex items-center gap-2">
        <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <FolderTreeIcon className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold">{t('explorer.title')}</div>
        </div>
        {showProcessingTasks ? (
          <Button
            type="button"
            size="icon-sm"
            variant="ghost"
            className="relative"
            title={t('processingTasks.title', { ns: 'resources' })}
            onClick={onOpenProcessingTasks}
          >
            <ClipboardListIcon
              className={cn(
                'size-4',
                (hasActiveTasks || isRefreshingTasks) && 'text-primary',
              )}
            />
            {activeTaskCount > 0 ? (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-xs font-semibold leading-none text-primary-foreground">
                {activeTaskCount}
              </span>
            ) : null}
          </Button>
        ) : null}
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          title={t('explorer.search')}
          onClick={onOpenSearch}
        >
          <SearchIcon className="size-4" />
        </Button>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          title={t('explorer.addResource')}
          onClick={onAddResource}
        >
          <PlusIcon className="size-4" />
        </Button>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          title={t('explorer.refresh')}
          onClick={onRefresh}
        >
          <RefreshCcwIcon
            className={cn('size-4', isRefreshing && 'animate-spin')}
          />
        </Button>
        {onToggleFocusCanvas ? (
          <Button
            type="button"
            size="icon-sm"
            variant="ghost"
            title={
              isFocusCanvas
                ? t('explorer.restoreLayout', { defaultValue: '恢复三栏工作台' })
                : t('explorer.focusCanvas', { defaultValue: '全屏/聚焦文件画布' })
            }
            onClick={onToggleFocusCanvas}
            className={cn(isFocusCanvas && 'text-primary bg-primary/10')}
          >
            {isFocusCanvas ? (
              <PanelRightOpen className="size-4" />
            ) : (
              <PanelRightClose className="size-4" />
            )}
          </Button>
        ) : null}
      </div>
    </div>
  )
}
