import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import {
  BotIcon,
  CheckCircle2Icon,
  Loader2Icon,
  MessageSquareIcon,
  PauseIcon,
  PlayIcon,
  PlusIcon,
  QrCodeIcon,
  RefreshCwIcon,
  Trash2Icon,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import { createRandomUuid } from '#/lib/browser-crypto'
import { showErrorToast } from '#/lib/error-toast'
import { cn } from '#/lib/utils'
import {
  createBotConnection,
  deleteBotConnection,
  fetchBotCapabilities,
  fetchBotConnections,
  fetchBotConversations,
  fetchCurrentFeishuOnboarding,
  startFeishuOnboarding,
  toggleBotConnection,
  updateFeishuOnboarding,
  verifyBotConnection,
  type BotConnection,
} from '../-lib/vikingbot-api'

export const Route = createFileRoute('/admin/vikingbot/')({
  component: VikingBotAdminPage,
})

function VikingBotAdminPage() {
  const { t } = useTranslation('vikingbot')
  const { connection, connectionRole, identityScopeKey, serverMode } =
    useAppConnection()
  const queryClient = useQueryClient()
  const isRoot = connectionRole === 'root' || serverMode === 'trusted'

  const connInput = {
    accountId: connection.accountId,
    adminApiKey: connection.adminApiKey,
    apiKey: connection.apiKey,
  }

  const [tab, setTab] = useState<'channels' | 'conversations'>('channels')
  const [search, setSearch] = useState('')
  const [runtimeUser, setRuntimeUser] = useState(connection.userId || 'default')
  const [appId, setAppId] = useState('')
  const [appSecret, setAppSecret] = useState('')
  const [selectedConnId, setSelectedConnId] = useState('')

  const capsQuery = useQuery({
    queryKey: ['admin-bot-capabilities', identityScopeKey],
    queryFn: () => fetchBotCapabilities(connInput),
    enabled: isRoot,
    retry: false,
  })

  const enabled = Boolean(capsQuery.data?.enabled && capsQuery.data?.can_manage)

  const connsQuery = useQuery({
    queryKey: ['admin-bot-connections', identityScopeKey, connection.accountId],
    queryFn: () => fetchBotConnections(connInput),
    enabled: isRoot && enabled,
  })

  const onboardingQuery = useQuery({
    queryKey: ['admin-bot-onboarding', identityScopeKey, connection.accountId],
    queryFn: () => fetchCurrentFeishuOnboarding(connInput),
    enabled: isRoot && enabled,
  })

  const convsQuery = useQuery({
    queryKey: ['admin-bot-convs', identityScopeKey, selectedConnId],
    queryFn: () => fetchBotConversations(connInput, selectedConnId),
    enabled: isRoot && enabled && tab === 'conversations' && Boolean(selectedConnId),
  })

  const invalidateBot = async () => {
    await queryClient.invalidateQueries({
      queryKey: ['admin-bot-connections', identityScopeKey],
    })
    await queryClient.invalidateQueries({
      queryKey: ['admin-bot-onboarding', identityScopeKey],
    })
  }

  const connectMut = useMutation({
    mutationFn: () =>
      createBotConnection(connInput, {
        type: 'feishu',
        user_id: runtimeUser.trim(),
        credentials: { app_id: appId.trim(), app_secret: appSecret.trim() },
      }),
    onSuccess: async () => {
      setAppId('')
      setAppSecret('')
      toast.success(t('state.connected'))
      await invalidateBot()
    },
    onError: (err) => showErrorToast(err),
  })

  const qrStartMut = useMutation({
    mutationFn: () =>
      startFeishuOnboarding(connInput, {
        user_id: runtimeUser.trim(),
        name: 'VikingBot',
        request_id: createRandomUuid(),
        settings: { thread_require_mention: true },
      }),
    onSuccess: invalidateBot,
    onError: (err) => showErrorToast(err),
  })

  const actionMut = useMutation({
    mutationFn: async ({
      kind,
      item,
    }: {
      kind: 'pause' | 'resume' | 'verify' | 'delete'
      item: BotConnection
    }) => {
      if (kind === 'delete') return deleteBotConnection(connInput, item)
      if (kind === 'verify') return verifyBotConnection(connInput, item)
      return toggleBotConnection(connInput, item, kind)
    },
    onSuccess: invalidateBot,
    onError: (err) => showErrorToast(err),
  })

  if (!isRoot) {
    return <p className="text-sm text-rose-500">{t('adminOnly')}</p>
  }

  if (capsQuery.isLoading) {
    return (
      <div className="flex items-center gap-2 py-8 text-xs text-muted-foreground">
        <Loader2Icon className="size-4 animate-spin text-cyan-500" />
        {t('loading')}
      </div>
    )
  }

  if (!capsQuery.data?.enabled) {
    return (
      <section className="max-w-xl space-y-3 rounded-xl border bg-card p-6">
        <h2 className="text-base font-semibold">{t('enable')}</h2>
        <p className="text-xs text-muted-foreground">{t('enableHint')}</p>
        <code className="block rounded-lg bg-muted p-3 font-mono text-xs">
          openviking-server --with-bot
        </code>
        <p className="text-xs text-muted-foreground">{t('modelHint')}</p>
        <Button size="sm" onClick={() => void capsQuery.refetch()}>
          <RefreshCwIcon />
          {t('retry')}
        </Button>
      </section>
    )
  }

  const connections = (connsQuery.data || []).filter((c) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      c.bot_name.toLowerCase().includes(q) ||
      c.identity_user.toLowerCase().includes(q)
    )
  })
  const onboarding = onboardingQuery.data

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <BotIcon className="size-5 text-cyan-500" />
            {t('managementTitle')}
          </h2>
          <p className="text-xs text-muted-foreground">{t('managementHint')}</p>
        </div>
        <div role="tablist" className="inline-flex gap-1 rounded-lg bg-muted p-1">
          {(['channels', 'conversations'] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => {
                setTab(key)
                if (key === 'conversations' && !selectedConnId && connections[0]) {
                  setSelectedConnId(connections[0].id)
                }
              }}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium',
                tab === key
                  ? 'bg-background text-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {t(key)}
            </button>
          ))}
        </div>
      </div>

      {tab === 'channels' ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
          <div className="space-y-4">
            <Input
              className="max-w-sm text-xs"
              placeholder={t('searchBots')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {!connections.length ? (
              <div className="rounded-xl border border-dashed p-8 text-center text-xs text-muted-foreground">
                {t('noConnectedBots')}
              </div>
            ) : (
              <div className="divide-y rounded-xl border bg-card">
                {connections.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 p-4"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold">
                          {item.bot_name || item.app_id}
                        </span>
                        <Badge
                          variant="outline"
                          className={
                            item.enabled
                              ? 'border-cyan-500/40 bg-cyan-500/15 text-xs text-cyan-600 dark:text-cyan-400'
                              : 'text-xs text-muted-foreground'
                          }
                        >
                          {t(
                            item.enabled
                              ? 'state.connected'
                              : 'state.paused',
                          )}
                        </Badge>
                      </div>
                      <p className="font-mono text-xs text-muted-foreground">
                        {t('runtimeUser')}: {item.identity_user} · App ID: {item.app_id}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() =>
                          actionMut.mutate({
                            kind: item.enabled ? 'pause' : 'resume',
                            item,
                          })
                        }
                      >
                        {item.enabled ? <PauseIcon /> : <PlayIcon />}
                        {t(item.enabled ? 'pause' : 'resume')}
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => actionMut.mutate({ kind: 'verify', item })}
                      >
                        <CheckCircle2Icon className="text-cyan-500" />
                        {t('verify')}
                      </Button>
                      <Button
                        size="xs"
                        variant="destructive"
                        onClick={() => {
                          if (
                            window.confirm(
                              t('deleteConfirm', { name: item.bot_name || item.app_id }),
                            )
                          ) {
                            actionMut.mutate({ kind: 'delete', item })
                          }
                        }}
                      >
                        <Trash2Icon />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4 rounded-xl border bg-card p-5">
            <h3 className="text-sm font-semibold">{t('manualTitle')}</h3>
            <p className="text-xs text-muted-foreground">{t('manualHint')}</p>
            <ol className="list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
              {(t('steps', { returnObjects: true }) as unknown as string[]).map(
                (step, i) => (
                  <li key={i}>{step}</li>
                ),
              )}
            </ol>

            <div className="space-y-3 border-t pt-3">
              <Input
                className="text-xs"
                placeholder={t('runtimeUser')}
                value={runtimeUser}
                onChange={(e) => setRuntimeUser(e.target.value)}
              />
              <Input
                className="font-mono text-xs"
                placeholder={t('appId')}
                value={appId}
                onChange={(e) => setAppId(e.target.value)}
              />
              <Input
                type="password"
                className="font-mono text-xs"
                placeholder={t('appSecret')}
                value={appSecret}
                onChange={(e) => setAppSecret(e.target.value)}
              />
              <Button
                className="w-full"
                size="sm"
                disabled={!appId.trim() || !appSecret.trim() || connectMut.isPending}
                onClick={() => connectMut.mutate()}
              >
                <PlusIcon />
                {t('connect')}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full"
                disabled={qrStartMut.isPending}
                onClick={() => qrStartMut.mutate()}
              >
                <QrCodeIcon />
                {t('startQr')}
              </Button>
            </div>

            {onboarding && (
              <div className="space-y-2 rounded-lg border bg-muted/30 p-3 text-xs">
                <p className="font-medium">
                  {t('qrActive', { state: onboarding.state })}
                </p>
                {onboarding.qr && (
                  <p className="break-all font-mono text-xs text-cyan-500">
                    {onboarding.qr}
                  </p>
                )}
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={() =>
                    void updateFeishuOnboarding(connInput, onboarding.id, 'cancel').then(
                      invalidateBot,
                    )
                  }
                >
                  {t('qrCancel')}
                </Button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-3 rounded-xl border bg-card p-5">
          {!convsQuery.data?.length ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <MessageSquareIcon className="size-4" />
              {t('noHistory')}
            </div>
          ) : (
            <ul className="divide-y">
              {convsQuery.data.map((conv) => (
                <li key={conv.conversation} className="py-3 text-xs">
                  <div className="font-medium">{conv.title || conv.group_name || conv.conversation}</div>
                  {conv.preview && (
                    <p className="mt-0.5 text-muted-foreground">{conv.preview}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
