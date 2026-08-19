import { useState, useMemo, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  History,
  GitCommit,
  RotateCcw,
  Clock,
  User,
  FileCode,
  FileDiff,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Sparkles,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '#/components/ui/dialog'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { ScrollArea } from '#/components/ui/scroll-area'
import {
  fetchSnapshotLog,
  fetchSnapshotDiff,
  fetchSnapshotShow,
  restoreSnapshotCommit,
} from '../-lib/api'
import type { SnapshotCommit } from '../-lib/api'
import type { VikingFsEntry } from '../-types/viking-fm'

interface VersionTimelineDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  file: VikingFsEntry
  onRestored?: () => void
}

function formatCommitTime(timeSeconds?: number): string {
  if (!timeSeconds) return '--'
  const date = new Date(timeSeconds * 1000)
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatRelativeTime(timeSeconds?: number): string {
  if (!timeSeconds) return ''
  const diffSec = Math.floor(Date.now() / 1000 - timeSeconds)
  if (diffSec < 60) return '刚刚'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`
  return `${Math.floor(diffSec / 86400)} 天前`
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
  const [copiedOid, setCopiedOid] = useState(false)
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
      // Fallback to all commits if file-specific has no records yet
      return allCommits
    }
    return allCommits
  }, [filterScope, fileCommits, allCommits])

  const isLoadingLogs = filterScope === 'file' ? isLoadingFileLogs : isLoadingAllLogs
  const isErrorLogs = filterScope === 'file' ? isErrorFileLogs : isErrorAllLogs
  const logsError = filterScope === 'file' ? fileLogsError : allLogsError

  const isFallbackToAll = filterScope === 'file' && fileCommits.length === 0 && allCommits.length > 0

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
  const {
    data: diffContent = '',
    isLoading: isLoadingDiff,
  } = useQuery({
    queryKey: ['snapshot-diff', file.uri, activeOid],
    queryFn: () => fetchSnapshotDiff(file.uri, activeOid, 'HEAD'),
    enabled: open && Boolean(file.uri && activeOid && viewTab === 'diff'),
    staleTime: 30_000,
  })

  // 4. Fetch historical file content for selected commit
  const {
    data: historicalContent = '',
    isLoading: isLoadingSource,
  } = useQuery({
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
      toast.success(t('versionTimeline.restoreSuccess', { oid: activeOid.slice(0, 8) }))
      queryClient.invalidateQueries({ queryKey: ['viking-file-read', file.uri] })
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

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedOid(true)
    setTimeout(() => setCopiedOid(false), 1500)
    toast.success(t('common.copied') || '已复制')
  }

  // Parse unified diff lines for color highlighting (NO GREEN EVER)
  const parsedDiffLines = useMemo(() => {
    if (!diffContent || typeof diffContent !== 'string') return []
    return diffContent.split('\n').map((line, idx) => {
      let type: 'add' | 'del' | 'meta' | 'normal' = 'normal'
      if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
        type = 'meta'
      } else if (line.startsWith('+')) {
        type = 'add'
      } else if (line.startsWith('-')) {
        type = 'del'
      }
      return { line, type, key: idx }
    })
  }, [diffContent])

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
                  <Badge variant="outline" className="font-mono text-xs px-2 py-0.5 border-cyan-500/30 text-cyan-400 bg-cyan-500/5">
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
                  disabled={restoreMutation.isPending || commits[0]?.oid === activeOid}
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
          {/* Left Column: Timeline List (5 cols / 42% width) */}
          <div className="md:col-span-5 flex flex-col min-h-0 bg-muted/10">
            {/* Timeline Filter Toolbar */}
            <div className="p-3 border-b border-border flex items-center justify-between text-xs bg-muted/30 flex-shrink-0">
              <div className="flex items-center gap-1.5 font-medium text-foreground">
                <GitCommit className="size-3.5 text-cyan-400" />
                <span>{t('versionTimeline.commitHistory')}</span>
                <span className="font-mono text-[11px] text-muted-foreground ml-1">
                  ({commits.length} {t('versionTimeline.commitsCount')})
                </span>
              </div>

              <div className="inline-flex rounded border border-border/70 p-0.5 bg-background">
                <button
                  type="button"
                  onClick={() => setFilterScope('file')}
                  className={`px-2 py-0.5 text-[11px] rounded transition-all ${
                    filterScope === 'file'
                      ? 'bg-muted font-semibold text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {t('versionTimeline.filterFileOnly')}
                </button>
                <button
                  type="button"
                  onClick={() => setFilterScope('all')}
                  className={`px-2 py-0.5 text-[11px] rounded transition-all ${
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
              <div className="px-3 py-1.5 bg-cyan-500/10 border-b border-cyan-500/20 text-[11px] text-cyan-400 flex items-center gap-1.5">
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
                  <span>{logsError instanceof Error ? logsError.message : t('versionTimeline.loadFailed')}</span>
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
                        onClick={() => {
                          setSelectedOid(commit.oid)
                          setShowConfirmRestore(false)
                        }}
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
                              <Badge className="text-[11px] px-1.5 py-0 bg-cyan-500/20 text-cyan-400 border-cyan-500/30 font-medium">
                                HEAD (最新)
                              </Badge>
                            )}
                          </div>
                          <span className="text-[11px] font-medium text-muted-foreground">
                            {formatRelativeTime(commit.author?.time_seconds)}
                          </span>
                        </div>

                        <p className="text-xs text-foreground font-medium line-clamp-2 leading-relaxed">
                          {commit.message || t('versionTimeline.noMessage')}
                        </p>

                        <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1.5 border-t border-border/40">
                          <span className="flex items-center gap-1 truncate max-w-35">
                            <User className="size-3 shrink-0" />
                            {commit.author?.name || 'viking-bot'}
                          </span>
                          <span className="flex items-center gap-1 font-mono text-[11px]">
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

          {/* Right Column: Diff & Content Preview (7 cols / 58% width) */}
          <div className="md:col-span-7 flex flex-col min-h-0 bg-background">
            {/* View Switcher & Details Bar */}
            {activeCommit ? (
              <div className="p-3 border-b border-border flex items-center justify-between flex-shrink-0 bg-muted/15">
                <div className="flex items-center gap-2">
                  <div className="inline-flex rounded-md border border-border p-0.5 bg-muted/50">
                    <button
                      type="button"
                      onClick={() => setViewTab('diff')}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs transition-all ${
                        viewTab === 'diff'
                          ? 'bg-background font-semibold text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <FileDiff className="size-3.5 text-cyan-400" />
                      {t('versionTimeline.tabDiff')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewTab('source')}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs transition-all ${
                        viewTab === 'source'
                          ? 'bg-background font-semibold text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <FileCode className="size-3.5 text-cyan-400" />
                      {t('versionTimeline.tabSource')}
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => copyToClipboard(activeOid)}
                    className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground px-2.5 py-1 rounded border border-border hover:bg-muted/50 transition-colors"
                    title={activeOid}
                  >
                    {copiedOid ? <Check className="size-3 text-cyan-400" /> : <Copy className="size-3" />}
                    <span>{activeOid.slice(0, 10)}</span>
                  </button>
                </div>
              </div>
            ) : null}

            {/* Viewer Panel */}
            <div className="flex-1 min-h-0 relative">
              {!activeCommit ? (
                <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                  {t('versionTimeline.selectVersionPrompt')}
                </div>
              ) : viewTab === 'diff' ? (
                isLoadingDiff ? (
                  <div className="flex h-full items-center justify-center text-xs text-muted-foreground gap-2">
                    <Loader2 className="size-4 animate-spin text-cyan-400" />
                    <span>{t('versionTimeline.loadingDiff')}</span>
                  </div>
                ) : !diffContent || diffContent.trim() === '' ? (
                  <div className="flex flex-col h-full items-center justify-center text-xs text-muted-foreground gap-2 p-8 text-center">
                    <Sparkles className="size-8 text-cyan-400/70" />
                    <span className="font-semibold text-sm text-foreground">{t('versionTimeline.noDiffTitle')}</span>
                    <span className="text-xs text-muted-foreground max-w-sm">{t('versionTimeline.noDiffDesc')}</span>
                  </div>
                ) : (
                  <ScrollArea className="h-full font-mono text-xs">
                    <div className="p-3 space-y-0.5 select-text">
                      {parsedDiffLines.map(({ line, type, key }) => {
                        let lineStyle = 'text-foreground/85 hover:bg-muted/30'
                        if (type === 'add') {
                          lineStyle = 'text-cyan-400 bg-cyan-500/10 font-semibold border-l-2 border-cyan-500'
                        } else if (type === 'del') {
                          lineStyle = 'text-rose-400 bg-rose-500/10 font-semibold border-l-2 border-rose-500'
                        } else if (type === 'meta') {
                          lineStyle = 'text-muted-foreground font-semibold bg-muted/60'
                        }
                        return (
                          <div
                            key={key}
                            className={`px-2.5 py-0.5 rounded-sm whitespace-pre-wrap break-all ${lineStyle}`}
                          >
                            {line || ' '}
                          </div>
                        )
                      })}
                    </div>
                  </ScrollArea>
                )
              ) : (
                /* Historical Source View */
                isLoadingSource ? (
                  <div className="flex h-full items-center justify-center text-xs text-muted-foreground gap-2">
                    <Loader2 className="size-4 animate-spin text-cyan-400" />
                    <span>{t('versionTimeline.loadingSource')}</span>
                  </div>
                ) : (
                  <ScrollArea className="h-full font-mono text-xs">
                    <pre className="p-4 text-foreground/95 whitespace-pre-wrap break-all select-text leading-relaxed font-mono">
                      {historicalContent || t('versionTimeline.emptyContent')}
                    </pre>
                  </ScrollArea>
                )
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
