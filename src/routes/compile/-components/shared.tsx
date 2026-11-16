import { AlertCircleIcon, ArrowLeftIcon, LoaderCircleIcon } from 'lucide-react'
import { Link, useLocation, useRouter } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { errorText } from '../-lib/api'
import { compileErrorKey } from '../-lib/errors'
import { compileListReturn } from '../-lib/navigation'

export function CompileShell({
  children,
  title,
  actions,
  back = true,
}: {
  children: ReactNode
  title: string
  actions?: ReactNode
  back?: boolean
}) {
  const { t } = useTranslation('compile')
  const location = useLocation()
  const router = useRouter()
  const { identityScopeKey } = useAppConnection()
  const returnTo = compileListReturn(
    location.state.compileListOrigin,
    identityScopeKey,
    location.state.__TSR_index ?? 0,
  )
  return (
    <main className="mx-auto flex w-full max-w-6xl min-w-0 flex-col gap-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          {back && (
            <Link
              to="/compile"
              search={returnTo.search}
              onClick={(event) => {
                if (
                  returnTo.restoreHistory &&
                  event.button === 0 &&
                  !event.metaKey &&
                  !event.ctrlKey &&
                  !event.shiftKey &&
                  !event.altKey
                ) {
                  event.preventDefault()
                  router.history.back()
                }
              }}
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeftIcon className="size-4" />
              {t('back')}
            </Link>
          )}
          <h1 className="text-2xl font-semibold tracking-tight [overflow-wrap:anywhere]">
            {title}
          </h1>
          {!back && (
            <p className="text-sm text-muted-foreground">{t('description')}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">{actions}</div>
      </header>
      {children}
    </main>
  )
}

export function CompileError({
  error,
  retry,
}: {
  error: unknown
  retry?: () => void
}) {
  const { t } = useTranslation('compile')
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-rose-500/30 bg-rose-500/5 p-4 text-sm text-rose-700 dark:text-rose-300"
    >
      <AlertCircleIcon className="size-4 shrink-0 text-rose-500" />
      <div className="min-w-0 flex-1 break-words">
        <p>{t(compileErrorKey(error) as never)}</p>
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-muted-foreground">
            {t('errors.details')}
          </summary>
          <p className="mt-1 whitespace-pre-wrap text-xs">{errorText(error)}</p>
        </details>
      </div>
      {retry && (
        <Button variant="outline" size="sm" onClick={retry}>
          {t('retry')}
        </Button>
      )}
    </div>
  )
}

export function CompileLoading() {
  const { t } = useTranslation('compile')
  return (
    <div
      role="status"
      className="flex items-center gap-2 py-8 text-sm text-muted-foreground"
    >
      <LoaderCircleIcon className="size-4 animate-spin text-cyan-500" />
      {t('loading')}
    </div>
  )
}

export function CompileStatus({ status }: { status?: string }) {
  const { t } = useTranslation('compile')
  const known = [
    'pending',
    'running',
    'cancelling',
    'completed',
    'failed',
    'cancelled',
  ].includes(status || '')
    ? status!
    : 'unknown'

  const tone =
    known === 'completed'
      ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
      : known === 'failed'
        ? 'border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400'
        : known === 'running' || known === 'cancelling'
          ? 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
          : ''

  return (
    <Badge
      variant={known === 'failed' ? 'destructive' : 'secondary'}
      className={tone}
    >
      {t(`statuses.${known}` as never)}
    </Badge>
  )
}
