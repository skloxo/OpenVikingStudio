import { useCallback, useEffect } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { CompassIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { useCreateSession } from '#/lib/sessions/use-sessions'
import { useSessionTitles } from '#/lib/sessions/use-session-titles'
import { QuarantineDashboard } from './-components/quarantine-dashboard'
import { Thread } from './-components/thread'
import { ThreadList } from './-components/thread-list'

const COMMAND_KEY_LABEL = '⌘'
const NEW_SESSION_KEY_LABEL = 'N'

export const Route = createFileRoute('/sessions/')({
  component: SessionsPage,
  validateSearch: (search: Record<string, unknown>): { s?: string; search?: string; id?: string; view?: string } => ({
    s: (search.s as string) || (search.search as string) || (search.id as string) || undefined,
    view: (search.view as string) || undefined,
  }),
})

function SessionsPage() {
  const { t } = useTranslation('sessions')
  const { s: activeSessionId, view } = Route.useSearch()
  const isQuarantineView = view === 'quarantine'
  const { identityScopeKey } = useAppConnection()
  const navigate = useNavigate()
  const createSession = useCreateSession()
  const { setTitle } = useSessionTitles(identityScopeKey)

  const handleNewSession = useCallback(async () => {
    const result = await createSession.mutateAsync(undefined)
    setTitle(result.session_id, t('threadList.newSession'))
    void navigate({ to: '/sessions', search: { s: result.session_id } })
  }, [createSession, navigate, setTitle, t])

  // Cmd+N to create new session
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return
      if (e.key === 'n') {
        e.preventDefault()
        handleNewSession()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [handleNewSession])

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100svh-3rem)] min-w-0 overflow-hidden md:-mx-6">
      <ThreadList
        activeSessionId={activeSessionId}
        isQuarantineActive={isQuarantineView}
      />
      <section className="min-w-0 flex-1 bg-background">
        {isQuarantineView ? (
          <QuarantineDashboard
            onBackToActive={() =>
              void navigate({ to: '/sessions', search: { s: activeSessionId } })
            }
          />
        ) : activeSessionId ? (
          <Thread sessionId={activeSessionId} />
        ) : (
          <SessionsEmpty
            onOpenQuarantine={() =>
              void navigate({ to: '/sessions', search: { view: 'quarantine' } })
            }
          />
        )}
      </section>
    </div>
  )
}

function SessionsEmpty({ onOpenQuarantine }: { onOpenQuarantine?: () => void }) {
  const { t } = useTranslation('sessions')

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-muted">
        <CompassIcon className="size-7 text-muted-foreground" />
      </div>
      <div className="text-center">
        <h3 className="text-sm font-medium text-foreground">
          {t('empty.title')}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {t('empty.description')}
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">
          {COMMAND_KEY_LABEL}
        </kbd>
        <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">
          {NEW_SESSION_KEY_LABEL}
        </kbd>
        <span>{t('threadList.newSession')}</span>
      </div>
      {onOpenQuarantine && (
        <Button
          size="sm"
          variant="outline"
          onClick={onOpenQuarantine}
          className="mt-2 h-7 border-amber-500/30 text-xs font-mono text-amber-400 hover:bg-amber-500/10"
        >
          {t('quarantine.emptyViewBtn')}
        </Button>
      )}
    </div>
  )
}
