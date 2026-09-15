import { useCallback, useMemo, useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import type { SessionListItem } from '@ov-server/api/v1/sessions'
import {
  ArchiveIcon,
  LoaderCircleIcon,
  MessageSquareIcon,
  PlusIcon,
  Trash2Icon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '#/components/ui/alert-dialog'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import {
  useCreateSession,
  useDeleteSession,
  useSessionListByRecency,
} from '#/lib/sessions/use-sessions'
import { useSessionTitles } from '#/lib/sessions/use-session-titles'
import { cn } from '#/lib/utils'

interface ThreadListProps {
  activeSessionId?: string
  isQuarantineActive?: boolean
}

export function isHeartbeatSession(
  session: SessionListItem,
  title?: string,
): boolean {
  if (session.is_heartbeat || session.category === 'heartbeat') return true
  const id = session.session_id.toLowerCase()
  if (
    id.startsWith('cron_') ||
    id.startsWith('heartbeat_') ||
    id.startsWith('probe_') ||
    id.startsWith('ping_') ||
    id.startsWith('memory-store-') ||
    id === 'heartbeat-baseline'
  ) {
    return true
  }
  if (title) {
    const lowerTitle = title.toLowerCase()
    if (
      lowerTitle.includes('heartbeat') ||
      lowerTitle.includes('cron') ||
      lowerTitle.includes('巡检') ||
      lowerTitle.includes('心跳') ||
      lowerTitle.includes('探针') ||
      lowerTitle.includes('[openclaw heartbeat')
    ) {
      return true
    }
  }
  return false
}

export function ThreadList({ activeSessionId, isQuarantineActive }: ThreadListProps) {
  const { i18n, t } = useTranslation('sessions')
  const { identityScopeKey } = useAppConnection()
  const navigate = useNavigate()
  const { data: sessions, isLoading } = useSessionListByRecency()
  const { getTitle, removeTitle, setTitle } = useSessionTitles(identityScopeKey)
  const createSession = useCreateSession()
  const deleteSession = useDeleteSession()
  const [visibleCount, setVisibleCount] = useState(25)
  const [filterMode, setFilterMode] = useState<
    'interactive' | 'all' | 'heartbeat'
  >('interactive')
  const [sessionToDelete, setSessionToDelete] = useState<{
    id: string
    title: string
  } | null>(null)

  const handleNewSession = useCallback(async () => {
    const result = await createSession.mutateAsync(undefined)
    setTitle(result.session_id, t('threadList.newSession'))
    void navigate({ to: '/sessions', search: { s: result.session_id } })
  }, [createSession, navigate, setTitle, t])

  const handleDeleteSession = useCallback(async () => {
    if (!sessionToDelete) return

    try {
      await deleteSession.mutateAsync(sessionToDelete.id)
      removeTitle(sessionToDelete.id)

      if (activeSessionId === sessionToDelete.id) {
        const nextSession = sessions.find(
          (session) => session.session_id !== sessionToDelete.id,
        )
        void navigate({
          to: '/sessions',
          search: { s: nextSession?.session_id },
        })
      }
      toast.success(t('threadList.deleteSuccess'))
      setSessionToDelete(null)
    } catch (error) {
      toast.error(
        t('threadList.deleteFailed', {
          error: error instanceof Error ? error.message : String(error),
        }),
      )
    }
  }, [
    activeSessionId,
    deleteSession,
    navigate,
    removeTitle,
    sessionToDelete,
    sessions,
    t,
  ])

  const { heartbeatCount, interactiveCount, entropyReductionRate } = useMemo(() => {
    let hb = 0
    for (const s of sessions) {
      if (isHeartbeatSession(s, getTitle(s.session_id))) {
        hb++
      }
    }
    const total = sessions.length
    const interactive = total - hb
    const rate = total > 0 ? Math.round((hb / total) * 100) : 0
    return { heartbeatCount: hb, interactiveCount: interactive, entropyReductionRate: rate }
  }, [sessions, getTitle])

  const filteredSessions = useMemo(() => {
    if (filterMode === 'all') return sessions
    if (filterMode === 'heartbeat') {
      return sessions.filter((session) =>
        isHeartbeatSession(session, getTitle(session.session_id)),
      )
    }
    return sessions.filter(
      (session) => !isHeartbeatSession(session, getTitle(session.session_id)),
    )
  }, [sessions, filterMode, getTitle])

  const visibleSessions = filteredSessions.slice(0, visibleCount)
  const hasMore = filteredSessions.length > visibleCount

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-border/70 bg-muted/20">
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-border/70 px-4">
        <div className="min-w-0">
          <h1 className="text-sm font-semibold text-foreground">
            {t('threadList.title')}
          </h1>
          {!isLoading ? (
            <p className="mt-0.5 font-mono text-xs text-muted-foreground">
              {filterMode === 'interactive'
                ? `${interactiveCount} / ${sessions.length}`
                : filterMode === 'heartbeat'
                  ? `${heartbeatCount} / ${sessions.length}`
                  : t('threadList.count', { count: sessions.length })}
            </p>
          ) : null}
        </div>
        <Button
          type="button"
          size="icon-sm"
          variant="outline"
          disabled={createSession.isPending}
          onClick={handleNewSession}
          aria-label={t('threadList.newSession')}
          title={t('threadList.newSession')}
        >
          {createSession.isPending ? (
            <LoaderCircleIcon className="animate-spin" />
          ) : (
            <PlusIcon />
          )}
        </Button>
      </div>

      <div className="border-b border-border/40 px-3 py-2">
        <Link
          to="/sessions"
          search={{ view: 'quarantine' }}
          className={cn(
            'flex items-center justify-between rounded-md border px-2.5 py-1.5 transition-colors font-mono text-xs',
            isQuarantineActive
              ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 font-medium shadow-2xs'
              : 'border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted/60 hover:text-foreground',
          )}
        >
          <div className="flex items-center gap-1.5">
            <ArchiveIcon className={cn('size-3.5', isQuarantineActive ? 'text-cyan-600 dark:text-cyan-400' : 'text-muted-foreground')} />
            <span>{t('quarantine.navButton')}</span>
          </div>
          <span className="rounded bg-muted/60 px-1.5 py-0.5 text-xs text-muted-foreground font-semibold">1,164</span>
        </Link>
      </div>

      {/* Anti-Entropy Mode Switcher */}
      <div className="border-b border-border/40 px-3 py-1.5 bg-muted/10">
        <div className="flex items-center justify-between gap-1">
          <div className="flex rounded-md border border-border/60 bg-muted/30 p-0.5 font-mono text-xs">
            <button
              type="button"
              onClick={() => setFilterMode('interactive')}
              className={cn(
                'flex items-center gap-1 rounded px-2 py-0.5 transition-all text-xs',
                filterMode === 'interactive'
                  ? 'bg-background text-foreground font-semibold shadow-2xs'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <span>{t('threadList.filterInteractive')}</span>
              <span className="text-xs opacity-70">({interactiveCount})</span>
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('all')}
              className={cn(
                'flex items-center gap-1 rounded px-2 py-0.5 transition-all text-xs',
                filterMode === 'all'
                  ? 'bg-background text-foreground font-semibold shadow-2xs'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <span>{t('threadList.filterAll')}</span>
              <span className="text-xs opacity-70">({sessions.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('heartbeat')}
              className={cn(
                'flex items-center gap-1 rounded px-2 py-0.5 transition-all text-xs',
                filterMode === 'heartbeat'
                  ? 'bg-background text-foreground font-semibold shadow-2xs'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <span>{t('threadList.filterHeartbeat')}</span>
              <span className="text-xs opacity-70">({heartbeatCount})</span>
            </button>
          </div>
          {entropyReductionRate > 0 && filterMode === 'interactive' && (
            <span
              title={t('threadList.entropyReductionTitle', {
                rate: `${entropyReductionRate}%`,
                count: heartbeatCount,
              })}
              className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-xs font-medium text-cyan-700 dark:text-cyan-300 shrink-0"
            >
              -{entropyReductionRate}%
            </span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="space-y-2 p-1">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 rounded-xs border border-border/40 p-2.5">
                <div className="size-4 rounded-xs bg-muted/80 animate-pulse shrink-0" />
                <div className="flex-1 space-y-1.5 min-w-0">
                  <div className="h-3.5 w-3/4 rounded-xs bg-muted/80 animate-pulse" />
                  <div className="h-2.5 w-1/2 rounded-xs bg-muted/50 animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center px-6 text-center">
            <div className="flex size-9 items-center justify-center rounded-xs bg-muted">
              <MessageSquareIcon className="size-4 text-muted-foreground" />
            </div>
            <p className="mt-3 text-sm font-medium text-foreground">
              {filterMode === 'interactive'
                ? t('threadList.emptyInteractiveTitle')
                : filterMode === 'heartbeat'
                  ? t('threadList.emptyHeartbeatTitle')
                  : t('threadList.emptyTitle')}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {filterMode === 'interactive'
                ? t('threadList.emptyInteractiveDesc')
                : filterMode === 'heartbeat'
                  ? t('threadList.emptyHeartbeatDesc')
                  : t('threadList.emptyDescription')}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {visibleSessions.map((session) => {
              const isActive = activeSessionId === session.session_id
              const title = getTitle(session.session_id)
              const isHb = isHeartbeatSession(session, title)

              return (
                <div
                  key={session.session_id}
                  className={cn(
                    'group/session relative rounded-xs transition-colors',
                    isActive
                      ? 'bg-accent text-accent-foreground shadow-2xs ring-1 ring-border/60'
                      : 'hover:bg-muted/80',
                  )}
                >
                  <Link
                    to="/sessions"
                    search={{ s: session.session_id }}
                    className="flex min-w-0 items-start gap-2.5 px-3 py-2 pr-8 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <MessageSquareIcon
                      className={cn(
                        'mt-0.5 size-3.5 shrink-0',
                        isActive ? 'text-primary' : 'text-muted-foreground',
                      )}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5 truncate text-xs font-mono font-medium">
                        <span className="truncate">{title}</span>
                        {isHb && filterMode === 'all' && (
                          <span className="rounded border border-border/60 bg-muted/40 px-1 text-xs text-muted-foreground shrink-0 font-normal">
                            {t('threadList.filterHeartbeat')}
                          </span>
                        )}
                      </span>
                      <span className="mt-0.5 block truncate font-mono text-xs text-muted-foreground/70">
                        {formatSessionTime(
                          session.mod_time,
                          i18n.resolvedLanguage,
                        )}
                      </span>
                    </span>
                  </Link>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      setSessionToDelete({
                        id: session.session_id,
                        title,
                      })
                    }}
                    disabled={deleteSession.isPending}
                    className="absolute right-1.5 top-2 flex size-5 items-center justify-center rounded-xs text-muted-foreground opacity-0 transition-[opacity,color,background-color] hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring group-hover/session:opacity-100"
                    aria-label={t('threadList.deleteSession', { title })}
                    title={t('threadList.deleteSession', { title })}
                  >
                    <Trash2Icon className="size-3" />
                  </button>
                </div>
              )
            })}

            {hasMore && (
              <div className="pt-2 text-center">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full rounded-xs h-7 text-xs font-mono"
                  onClick={() => setVisibleCount((prev) => prev + 25)}
                >
                  {i18n.language.startsWith('zh')
                    ? `加载更多会话 (${visibleSessions.length} / ${filteredSessions.length})`
                    : `Load More (${visibleSessions.length} / ${filteredSessions.length})`}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <AlertDialog
        open={Boolean(sessionToDelete)}
        onOpenChange={(open) => {
          if (!open && !deleteSession.isPending) setSessionToDelete(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('threadList.deleteConfirmTitle')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('threadList.deleteConfirmDescription', {
                title: sessionToDelete?.title,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteSession.isPending}>
              {t('threadList.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteSession.isPending}
              onClick={(event) => {
                event.preventDefault()
                void handleDeleteSession()
              }}
            >
              {deleteSession.isPending
                ? t('threadList.deleting')
                : t('threadList.confirmDelete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div className="shrink-0 border-t border-border/70 px-4 py-3 text-xs text-muted-foreground">
        {t('threadList.shortcut')}
      </div>
    </aside>
  )
}

function formatSessionTime(value: string, locale?: string): string {
  if (!value) return ''

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}
