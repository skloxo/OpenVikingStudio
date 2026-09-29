import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Check,
  History,
  Loader2,
  RotateCcw,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import {
  fetchSnapshotDiff,
  fetchSnapshotLog,
  fetchSnapshotShow,
  restoreSnapshotCommit,
  type SnapshotCommit,
} from '../-lib/api'
import type { VikingFsEntry } from '../-types/viking-fm'
import { VersionTimelineList } from './version-timeline-list'
import { parseUnifiedDiff } from './version-timeline-utils'
import { VersionTimelineViewer } from './version-timeline-viewer'

export { formatCommitTime, formatRelativeTime } from './version-timeline-utils'

export interface VersionTimelineDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  file: VikingFsEntry
  onRestored?: () => void
}

export function VersionTimelineDialog({
  open,
  onOpenChange,
  file,
  onRestored,
}: VersionTimelineDialogProps) {
  const { t } = useTranslation(['resources', 'common'])
  const queryClient = useQueryClient()
  const [filterScope, setFilterScope] = useState<'file' | 'all'>('file')
  const [selectedOid, setSelectedOid] = useState<string | null>(null)
  const [viewTab, setViewTab] = useState<'diff' | 'source'>('diff')
  const [showConfirmRestore, setShowConfirmRestore] = useState(false)

  // 1. Fetch file-specific commit logs
  const {
    data: fileCommits = [],
    isLoading: isLoadingFileLogs,
    isError: isErrorFileLogs,
    error: fileLogsError,
  } = useQuery({
    queryKey: ['snapshot-log', file.uri],
    queryFn: () => fetchSnapshotLog(file.uri, 30),
    enabled: open && Boolean(file.uri),
    staleTime: 10_000,
  })

  // 2. Fetch all repository snapshots (for fallback / global view)
  const {
    data: allCommits = [],
    isLoading: isLoadingAllLogs,
    isError: isErrorAllLogs,
    error: allLogsError,
  } = useQuery({
    queryKey: ['snapshot-log-all'],
    queryFn: () => fetchSnapshotLog(undefined, 30),
    enabled: open,
    staleTime: 10_000,
  })

  // Determine effective commit list
  const commits: SnapshotCommit[] = useMemo(() => {
    if (filterScope === 'file') {
      if (fileCommits.length > 0) return fileCommits
      return allCommits
    }
    return allCommits
  }, [filterScope, fileCommits, allCommits])

  const isLoadingLogs =
    filterScope === 'file' ? isLoadingFileLogs : isLoadingAllLogs
  const isErrorLogs = filterScope === 'file' ? isErrorFileLogs : isErrorAllLogs
  const logsError = filterScope === 'file' ? fileLogsError : allLogsError
  const isFallbackToAll =
    filterScope === 'file' &&
    fileCommits.length === 0 &&
    allCommits.length > 0

  // Set active commit
  const activeCommit = useMemo(() => {
    if (!commits.length) return null
    if (selectedOid) {
      return commits.find((c) => c.oid === selectedOid) || commits[0]
    }
    return commits[0]
  }, [commits, selectedOid])

  const activeOid = activeCommit?.oid || ''

  // 3. Fetch diff for selected commit vs HEAD
  const { data: diffContent = '', isLoading: isLoadingDiff } = useQuery({
    queryKey: ['snapshot-diff', file.uri, activeOid],
    queryFn: () => fetchSnapshotDiff(file.uri, activeOid, 'HEAD'),
    enabled: open && Boolean(file.uri && activeOid && viewTab === 'diff'),
    staleTime: 30_000,
  })

  // 4. Fetch historical file content for selected commit
  const { data: historicalContent = '', isLoading: isLoadingSource } = useQuery({
    queryKey: ['snapshot-show', file.uri, activeOid],
    queryFn: () => fetchSnapshotShow(activeOid, file.uri),
    enabled: open && Boolean(file.uri && activeOid && viewTab === 'source'),
    staleTime: 30_000,
  })

  // Reset states when file changes
  useEffect(() => {
    if (open) {
      setSelectedOid(null)
      setShowConfirmRestore(false)
      setViewTab('diff')
    }
  }, [open, file.uri])

  // 5. Restore mutation
  const restoreMutation = useMutation({
    mutationFn: async (targetOid: string) => {
      return await restoreSnapshotCommit(
        targetOid,
        file.uri,
        `Rollback ${file.name} to ${targetOid.slice(0, 8)}`,
      )
    },
    onSuccess: () => {
      toast.success(
        t('versionTimeline.restoreSuccess', { oid: activeOid.slice(0, 8) }),
      )
      queryClient.invalidateQueries({
        queryKey: ['viking-file-read', file.uri],
      })
      queryClient.invalidateQueries({ queryKey: ['viking-fs-stat', file.uri] })
      queryClient.invalidateQueries({ queryKey: ['snapshot-log', file.uri] })
      queryClient.invalidateQueries({ queryKey: ['snapshot-log-all'] })
      setShowConfirmRestore(false)
      if (onRestored) {
        onRestored()
      }
      onOpenChange(false)
    },
    onError: (err: any) => {
      toast.error(err?.message || t('versionTimeline.restoreFailed'))
    },
  })

  const parsedDiffLines = useMemo(
    () => parseUnifiedDiff(diffContent),
    [diffContent],
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!w-[94vw] sm:!w-[94vw] !max-w-6xl sm:!max-w-6xl p-0 gap-0 overflow-hidden h-[86vh] max-h-[86vh] flex flex-col bg-background border border-border shadow-2xl rounded-xl">
        {/* Header */}
        <DialogHeader className="p-4 border-b border-border flex-shrink-0 bg-muted/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="size-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <History className="size-4.5" />
              </div>
              <div>
                <DialogTitle className="text-sm font-bold flex items-center gap-2.5 text-foreground">
                  {t('versionTimeline.title')}
                  <Badge
                    variant="outline"
                    className="font-mono text-xs px-2 py-0.5 border-cyan-500/30 text-cyan-400 bg-cyan-500/5"
                  >
                    {file.name}
                  </Badge>
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground font-mono truncate max-w-2xl mt-0.5">
                  {file.uri}
                </DialogDescription>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {activeCommit && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs border-cyan-500/40 text-cyan-400 hover:bg-cyan-500/10 hover:text-cyan-300 transition-colors"
                  onClick={() => setShowConfirmRestore(true)}
                  disabled={
                    restoreMutation.isPending || commits[0]?.oid === activeOid
                  }
                >
                  <RotateCcw className="mr-1.5 size-3.5" />
                  {t('versionTimeline.restoreToVersion')}
                </Button>
              )}
            </div>
          </div>
        </DialogHeader>

        {/* Restore Confirmation Inline Alert */}
        {showConfirmRestore && activeCommit && (
          <div className="bg-amber-500/10 border-b border-amber-500/30 p-3 px-4 flex items-center justify-between text-xs animate-in fade-in slide-in-from-top-1">
            <div className="flex items-center gap-2.5 text-amber-300">
              <AlertCircle className="size-4 shrink-0 text-amber-400" />
              <span>
                {t('versionTimeline.confirmRestoreDesc', {
                  oid: activeOid.slice(0, 8),
                  name: file.name,
                })}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs px-2.5 text-muted-foreground hover:text-foreground"
                onClick={() => setShowConfirmRestore(false)}
                disabled={restoreMutation.isPending}
              >
                {t('common.cancel') || '取消'}
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs px-3 bg-amber-600 hover:bg-amber-500 text-white"
                onClick={() => restoreMutation.mutate(activeOid)}
                disabled={restoreMutation.isPending}
              >
                {restoreMutation.isPending ? (
                  <Loader2 className="mr-1.5 size-3 animate-spin" />
                ) : (
                  <Check className="mr-1.5 size-3" />
                )}
                {t('versionTimeline.confirmRollback')}
              </Button>
            </div>
          </div>
        )}

        {/* Main Body: 2-Column Responsive Layout */}
        <div className="grid grid-cols-1 md:grid-cols-12 flex-1 min-h-0 divide-y md:divide-y-0 md:divide-x divide-border">
          <VersionTimelineList
            commits={commits}
            activeOid={activeOid}
            filterScope={filterScope}
            onFilterScopeChange={setFilterScope}
            isFallbackToAll={isFallbackToAll}
            isLoadingLogs={isLoadingLogs}
            isErrorLogs={isErrorLogs}
            logsError={logsError}
            onSelectCommit={(oid) => {
              setSelectedOid(oid)
              setShowConfirmRestore(false)
            }}
          />

          <VersionTimelineViewer
            activeCommit={activeCommit}
            activeOid={activeOid}
            viewTab={viewTab}
            onViewTabChange={setViewTab}
            isLoadingDiff={isLoadingDiff}
            diffContent={diffContent}
            parsedDiffLines={parsedDiffLines}
            isLoadingSource={isLoadingSource}
            historicalContent={historicalContent}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}
