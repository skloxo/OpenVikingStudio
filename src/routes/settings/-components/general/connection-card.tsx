import * as React from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  CircleAlertIcon,
  CircleDashedIcon,
  CircleHelpIcon,
  ExternalLinkIcon,
  KeyRoundIcon,
  RotateCcwIcon,
  ShieldCheckIcon,
  TriangleAlertIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Alert, AlertDescription, AlertTitle } from '#/components/ui/alert'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldLabel,
} from '#/components/ui/field'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import type { ConnectionDraft } from '#/hooks/use-app-connection'
import { probeStudioConnection } from '#/lib/admin'
import type { CapabilityProbeResult } from '#/lib/admin'
import { DEFAULT_ACCOUNT_ID, DEFAULT_USER_ID } from '#/lib/admin-options'
import { PLAIN_INPUT_PROPS } from '#/lib/form-input'
import { cn } from '#/lib/utils'

function getCapabilityIcon(result: CapabilityProbeResult | undefined) {
  if (!result) return <CircleDashedIcon className="size-4" />
  if (result.state === 'ok') return <ShieldCheckIcon className="size-4" />
  if (result.state === 'error') return <CircleAlertIcon className="size-4" />
  return <CircleDashedIcon className="size-4" />
}

function CapabilityStatus({
  isLoading,
  label,
  result,
}: {
  isLoading: boolean
  label: string
  result: CapabilityProbeResult | undefined
}) {
  const { t } = useTranslation('settings')
  const state = isLoading ? 'checking' : result?.state || 'skipped'

  return (
    <div
      className={cn(
        'flex min-w-0 items-start gap-2 rounded-md border bg-background/70 px-3 py-2 text-sm',
        state === 'ok' && 'border-cyan-500/35 text-cyan-500',
        state === 'error' && 'border-destructive/35 text-destructive',
      )}
    >
      <div className={cn('mt-0.5', isLoading && 'animate-spin')}>
        {getCapabilityIcon(result)}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-medium text-xs">{label}</span>
          <span className="text-[11px] text-muted-foreground">
            {t(`health.state.${state}`)}
          </span>
        </div>
        {result?.detail ? (
          <p className="mt-1 truncate text-[11px] text-muted-foreground">
            {result.detail}
          </p>
        ) : null}
      </div>
    </div>
  )
}

function UserApiKeyInput({
  accountId,
  id,
  onChange,
  placeholder,
  userId,
  value,
}: {
  accountId: string
  id: string
  onChange: (value: string) => void
  placeholder: string
  userId: string
  value: string
}) {
  const hasIdentity = Boolean(accountId.trim() && userId.trim())
  const identity = hasIdentity ? `${accountId}/${userId}` : '未选择身份'

  return (
    <div className="flex h-9 w-full min-w-0 items-center gap-2 rounded-md border border-input bg-transparent bg-clip-padding px-2.5 shadow-xs transition-[color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30">
      <span className="shrink-0 rounded-sm bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
        [{identity}]
      </span>
      <input
        id={id}
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="h-full min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
        {...PLAIN_INPUT_PROPS}
      />
    </div>
  )
}

interface ConnectionCardProps {
  onRecheckAll: () => void
  isRechecking?: boolean
}

export function ConnectionCard({
  onRecheckAll,
  isRechecking = false,
}: ConnectionCardProps) {
  const { i18n, t } = useTranslation('settings')
  const isZh = i18n.resolvedLanguage?.startsWith('zh')

  const { connection, saveConnection, serverMode } = useAppConnection()
  const [draft, setDraft] = React.useState<ConnectionDraft>(connection)
  const pendingDraftRef = React.useRef<ConnectionDraft | null>(null)
  const saveTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveConnectionRef = React.useRef(saveConnection)

  React.useEffect(() => {
    saveConnectionRef.current = saveConnection
  }, [saveConnection])

  React.useEffect(() => {
    if (!pendingDraftRef.current) {
      setDraft(connection)
    }
  }, [connection])

  React.useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      if (pendingDraftRef.current) {
        saveConnectionRef.current(pendingDraftRef.current)
      }
    }
  }, [])

  function updateDraft(next: Partial<ConnectionDraft>): void {
    const updated = { ...draft, ...next }
    setDraft(updated)
    pendingDraftRef.current = updated
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      saveTimerRef.current = null
      const pending = pendingDraftRef.current
      pendingDraftRef.current = null
      if (pending) saveConnectionRef.current(pending)
    }, 350)
  }

  const probeQuery = useQuery({
    enabled: Boolean(draft.baseUrl) && serverMode !== 'checking',
    placeholderData: keepPreviousData,
    queryFn: () =>
      probeStudioConnection({
        accountId: draft.accountId || DEFAULT_ACCOUNT_ID,
        adminApiKey: draft.adminApiKey,
        apiKey: draft.apiKey,
        baseUrl: draft.baseUrl,
        serverMode,
        userId: draft.userId || DEFAULT_USER_ID,
      }),
    queryKey: [
      'studio-connection-probe',
      draft.baseUrl,
      draft.adminApiKey,
      draft.apiKey,
      draft.accountId,
      draft.userId,
      serverMode,
    ],
    retry: false,
    staleTime: 5_000,
  })

  const isDevMode = serverMode === 'dev'
  const isUnsupportedAuthMode = serverMode === 'oidc' || serverMode === 'ldap'
  const rootApiKey = connection.adminApiKey.trim()
  const hasControlCredential = Boolean(draft.adminApiKey.trim())
  const hasDataCredential = Boolean(draft.apiKey.trim())
  const adminProbe = probeQuery.data?.admin
  const dataProbe = probeQuery.data?.data
  const hasAdminAccess = !isDevMode && adminProbe?.state === 'ok'
  const authenticationGuideUrl = isZh
    ? 'https://docs.openviking.ai/zh/guides/04-authentication'
    : 'https://docs.openviking.ai/en/guides/04-authentication'

  const trustedCredentialRequired =
    serverMode === 'trusted' &&
    !probeQuery.isFetching &&
    !hasControlCredential &&
    (adminProbe?.state === 'error' || dataProbe?.state === 'error')

  const keyGuide =
    serverMode === 'trusted'
      ? trustedCredentialRequired
        ? {
            primary: t('connection.keyGuide.trusted.primary'),
            secondary: t('connection.keyGuide.trusted.secondary'),
            title: t('connection.keyGuide.trusted.title'),
          }
        : null
      : !hasControlCredential && !hasDataCredential
        ? {
            primary: t('connection.keyGuide.empty.primary'),
            secondary: t('connection.keyGuide.empty.secondary'),
            title: t('connection.keyGuide.empty.title'),
          }
        : !hasControlCredential
          ? {
              primary: t('connection.keyGuide.control.primary'),
              secondary: t('connection.keyGuide.control.secondary'),
              title: t('connection.keyGuide.control.title'),
            }
          : !hasDataCredential
            ? {
                primary: t('connection.keyGuide.data.primary'),
                secondary: t('connection.keyGuide.data.secondary'),
                title: t('connection.keyGuide.data.title'),
              }
            : null

  return (
    <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
      <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
              <KeyRoundIcon className="size-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold">
                {t('connection.title')}
              </CardTitle>
              <p className="text-[11px] text-muted-foreground">
                {t('connectionPage.description')}
              </p>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={probeQuery.isFetching || isRechecking}
            onClick={() => {
              void probeQuery.refetch()
              onRecheckAll()
              toast.info(t('connection.rechecking'))
            }}
            className="h-7 rounded px-2.5 text-xs gap-1.5 cursor-pointer font-sans"
          >
            <RotateCcwIcon
              className={cn(
                'size-3',
                (probeQuery.isFetching || isRechecking) &&
                  'animate-spin text-cyan-500',
              )}
            />
            <span>{t('connection.recheck')}</span>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 px-5 py-4">
        <Field>
          <FieldLabel htmlFor="settings-base-url" className="text-xs">
            {t('fields.baseUrl')}
          </FieldLabel>
          <FieldContent>
            <Input
              id="settings-base-url"
              value={draft.baseUrl}
              onChange={(event) => updateDraft({ baseUrl: event.target.value })}
              placeholder={t('placeholders.baseUrl')}
              inputMode="url"
              className="h-8 text-xs font-mono"
              {...PLAIN_INPUT_PROPS}
            />
          </FieldContent>
        </Field>

        {isDevMode ? (
          <p className="rounded-md border border-dashed bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            {t('connection.devMode')}
          </p>
        ) : isUnsupportedAuthMode ? (
          <Alert variant="destructive" className="border-destructive/50">
            <TriangleAlertIcon className="size-4" />
            <AlertTitle className="text-xs">
              {t('connection.unsupportedAuthMode.title')}
            </AlertTitle>
            <AlertDescription className="grid gap-1.5 text-xs">
              <p>{t('connection.unsupportedAuthMode.primary', { mode: serverMode })}</p>
              <p>{t('connection.unsupportedAuthMode.description', { mode: serverMode, ov: 'ov' })}</p>
              <a
                href={authenticationGuideUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex w-fit items-center gap-1 font-medium text-foreground underline underline-offset-2"
              >
                {t('connection.keyGuide.learnMore')}
                <ExternalLinkIcon className="size-3.5" />
              </a>
            </AlertDescription>
          </Alert>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="settings-root-api-key" className="text-xs">
                  {t('fields.rootApiKey')}
                </FieldLabel>
                <FieldContent>
                  <Input
                    id="settings-root-api-key"
                    type="password"
                    value={draft.adminApiKey}
                    onChange={(event) => updateDraft({ adminApiKey: event.target.value })}
                    placeholder={t('placeholders.adminApiKey')}
                    className="h-8 text-xs font-mono"
                    {...PLAIN_INPUT_PROPS}
                  />
                  <FieldDescription className="text-[11px]">
                    {t('connection.rootHint')}
                  </FieldDescription>
                </FieldContent>
              </Field>
              <Field>
                <FieldLabel htmlFor="settings-user-api-key" className="text-xs">
                  {t('fields.userApiKey')}
                </FieldLabel>
                <FieldContent>
                  <UserApiKeyInput
                    accountId={draft.accountId}
                    id="settings-user-api-key"
                    userId={draft.userId}
                    value={draft.apiKey}
                    onChange={(apiKey) => updateDraft({ apiKey })}
                    placeholder={t('placeholders.userApiKey')}
                  />
                  <FieldDescription className="text-[11px]">
                    {t('connection.userHint')}
                  </FieldDescription>
                </FieldContent>
              </Field>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <CapabilityStatus
                isLoading={probeQuery.isFetching}
                label={t('health.admin')}
                result={adminProbe}
              />
              <CapabilityStatus
                isLoading={probeQuery.isFetching}
                label={t('health.data')}
                result={dataProbe}
              />
            </div>

            {(serverMode === 'api_key' || serverMode === 'trusted') && keyGuide ? (
              <Alert className="border-cyan-500/25 bg-cyan-500/4">
                <CircleHelpIcon className="text-cyan-500 size-4" />
                <AlertTitle className="text-xs">{keyGuide.title}</AlertTitle>
                <AlertDescription className="grid gap-1 text-xs text-pretty [&_p:not(:last-child)]:mb-0">
                  <p>{keyGuide.primary}</p>
                  <p className="text-muted-foreground">{keyGuide.secondary}</p>
                  <a
                    href={authenticationGuideUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex w-fit items-center gap-1 font-medium text-foreground text-xs"
                  >
                    {t('connection.keyGuide.learnMore')}
                    <ExternalLinkIcon className="size-3" />
                  </a>
                </AlertDescription>
              </Alert>
            ) : null}

            {!hasAdminAccess && rootApiKey && adminProbe?.state === 'error' ? (
              <p className="text-xs text-destructive">
                {t('connection.adminError', { message: adminProbe.detail || '' })}
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  )
}
