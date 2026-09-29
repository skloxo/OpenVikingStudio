import {
  AlertCircle,
  Clock,
  GitCommit,
  Loader2,
  Sparkles,
  User,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { ScrollArea } from '#/components/ui/scroll-area'
import type { SnapshotCommit } from '../-lib/api'
import { formatCommitTime, formatRelativeTime } from './version-timeline-utils'

export interface VersionTimelineListProps {
  commits: SnapshotCommit[]
  activeOid: string
  filterScope: 'file' | 'all'
  onFilterScopeChange: (scope: 'file' | 'all') => void
  isFallbackToAll: boolean
  isLoadingLogs: boolean
  isErrorLogs: boolean
  logsError: unknown
  onSelectCommit: (oid: string) => void
}

export function VersionTimelineList({
  commits,
  activeOid,
  filterScope,
  onFilterScopeChange,
  isFallbackToAll,
  isLoadingLogs,
  isErrorLogs,
  logsError,
  onSelectCommit,
}: VersionTimelineListProps) {
  const { t } = useTranslation('resources')

  return (
    <div className="md:col-span-5 flex flex-col min-h-0 bg-muted/10">
      {/* Timeline Filter Toolbar */}
      <div className="p-3 border-b border-border flex items-center justify-between text-xs bg-muted/30 flex-shrink-0">
        <div className="flex items-center gap-1.5 font-medium text-foreground">
          <GitCommit className="size-3.5 text-cyan-400" />
          <span>{t('versionTimeline.commitHistory')}</span>
          <span className="font-mono text-xs text-muted-foreground ml-1">
            ({commits.length} {t('versionTimeline.commitsCount')})
          </span>
        </div>

        <div className="inline-flex rounded border border-border/70 p-0.5 bg-background">
          <button
            type="button"
            onClick={() => onFilterScopeChange('file')}
            className={`px-2 py-0.5 text-xs rounded transition-all ${
              filterScope === 'file'
                ? 'bg-muted font-semibold text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t('versionTimeline.filterFileOnly')}
          </button>
          <button
            type="button"
            onClick={() => onFilterScopeChange('all')}
            className={`px-2 py-0.5 text-xs rounded transition-all ${
              filterScope === 'all'
                ? 'bg-muted font-semibold text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t('versionTimeline.filterAllSnapshots')}
          </button>
        </div>
      </div>

      {/* Hint if fallen back to all */}
      {isFallbackToAll && (
        <div className="px-3 py-1.5 bg-cyan-500/10 border-b border-cyan-500/20 text-xs text-cyan-400 flex items-center gap-1.5">
          <Sparkles className="size-3 shrink-0" />
          <span>该文件在快照历史中为全局导入，已为您展示全库历史快照</span>
        </div>
      )}

      {/* Commit List Area */}
      <ScrollArea className="flex-1">
        {isLoadingLogs ? (
          <div className="p-8 text-center text-xs text-muted-foreground flex flex-col items-center gap-2">
            <Loader2 className="size-5 animate-spin text-cyan-400" />
            <span>{t('versionTimeline.loadingHistory')}</span>
          </div>
        ) : isErrorLogs ? (
          <div className="p-6 text-center text-xs text-destructive flex flex-col items-center gap-2">
            <AlertCircle className="size-5" />
            <span>
              {logsError instanceof Error
                ? logsError.message
                : t('versionTimeline.loadFailed')}
            </span>
          </div>
        ) : commits.length === 0 ? (
          <div className="p-8 text-center text-xs text-muted-foreground flex flex-col items-center gap-2">
            <GitCommit className="size-6 text-muted-foreground/40" />
            <span>{t('versionTimeline.noHistory')}</span>
          </div>
        ) : (
          <div className="p-3 space-y-2">
            {commits.map((commit, index) => {
              const isSelected = commit.oid === activeOid
              const isLatest = index === 0
              return (
                <button
                  key={commit.oid}
                  type="button"
                  onClick={() => onSelectCommit(commit.oid)}
                  className={`w-full text-left p-3 rounded-lg border transition-all flex flex-col gap-2 relative ${
                    isSelected
                      ? 'border-cyan-500/70 bg-cyan-500/10 shadow-sm ring-1 ring-cyan-500/30'
                      : 'border-border/70 bg-background/80 hover:bg-muted/40 hover:border-border'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/80">
                        {commit.oid.slice(0, 8)}
                      </span>
                      {isLatest && (
                        <Badge className="text-xs px-1.5 py-0 bg-cyan-500/20 text-cyan-400 border-cyan-500/30 font-medium">
                          HEAD (最新)
                        </Badge>
                      )}
                    </div>
                    <span className="text-xs font-medium text-muted-foreground">
                      {formatRelativeTime(commit.author?.time_seconds)}
                    </span>
                  </div>

                  <p className="text-xs text-foreground font-medium line-clamp-2 leading-relaxed">
                    {commit.message || t('versionTimeline.noMessage')}
                  </p>

                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1.5 border-t border-border/40">
                    <span className="flex items-center gap-1 truncate max-w-35">
                      <User className="size-3 shrink-0" />
                      {commit.author?.name || 'viking-bot'}
                    </span>
                    <span className="flex items-center gap-1 font-mono text-xs">
                      <Clock className="size-3 shrink-0" />
                      {formatCommitTime(commit.author?.time_seconds)}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
