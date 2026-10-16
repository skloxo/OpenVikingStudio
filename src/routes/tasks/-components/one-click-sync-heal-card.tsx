import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { ZapIcon, RotateCwIcon, Trash2Icon, CheckCircle2Icon, AlertTriangleIcon, RefreshCwIcon } from 'lucide-react'
import { Card } from '#/components/ui/card'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
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
import { ovClient } from '#/lib/ov-client'

export interface SyncMetricsData {
  sync_rate_pct: number
  total_files: number
  indexed_count: number
  pending_count: number
  failed_count: number
  fast_path_count?: number
  dlq_pending_count: number
  dlq_total_count: number
}

interface OneClickSyncHealCardProps {
  onHealed?: () => void
}

export function OneClickSyncHealCard({ onHealed }: OneClickSyncHealCardProps) {
  const { t } = useTranslation('tasksPage')
  const [metrics, setMetrics] = React.useState<SyncMetricsData | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [busyAction, setBusyAction] = React.useState<string | null>(null)
  const [confirmClearOpen, setConfirmClearOpen] = React.useState(false)
  const [feedback, setFeedback] = React.useState<{ text: string; type: 'info' | 'warn' | 'success' } | null>(null)

  const fetchMetrics = React.useCallback(async () => {
    try {
      setLoading(true)
      const res = await ovClient.instance.get<{ status: string } & SyncMetricsData>('/api/v1/queue/sync-metrics')
      if (res.data.status === 'success') setMetrics(res.data)
    } catch (err) {
      console.error('[OneClickSyncHealCard] Failed to fetch sync metrics:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { void fetchMetrics() }, [fetchMetrics])

  const runOp = async (name: string, apiCall: () => Promise<void>) => {
    try {
      setBusyAction(name)
      await apiCall()
      await fetchMetrics()
      onHealed?.()
    } catch (err) {
      setFeedback({ type: 'warn', text: `${name} err: ${String(err)}` })
    } finally {
      setBusyAction(null)
    }
  }

  const handleSyncHeal = () => runOp('sync-heal', async () => {
    const res = await ovClient.instance.post<{ status: string; candidate_count: number; healed_count: number }>('/api/v1/queue/sync-heal')
    const { candidate_count = 0, healed_count = 0 } = res.data || {}
    setFeedback({ type: 'success', text: t('syncHeal.healResult', { candidates: candidate_count, healed: healed_count }) })
  })

  const handleRetryFailed = () => runOp('retry-failed', async () => {
    const res = await ovClient.instance.post<{ status: string; result?: { retried_count?: number } }>('/api/v1/queue/retry_failed', {})
    const count = res.data.result?.retried_count ?? 0
    setFeedback({ type: 'success', text: t('syncHeal.retryResult', { count }) })
  })

  const handleClearDlq = () => runOp('clear-dlq', async () => {
    const res = await ovClient.instance.post<{ status: string; result?: { cleared_count?: number } }>('/api/v1/queue/clear_dlq', {})
    const count = res.data.result?.cleared_count ?? 0
    setFeedback({ type: 'info', text: t('syncHeal.clearResult', { count }) })
  })

  const syncRate = metrics?.sync_rate_pct ?? 100.0
  const dlqCount = metrics?.dlq_pending_count ?? 0
  const failedCount = metrics?.failed_count ?? 0
  const pendingCount = metrics?.pending_count ?? 0
  const hasIssues = dlqCount > 0 || failedCount > 0 || syncRate < 99.0

  return (
    <Card className="flex flex-col gap-3 p-3.5 shadow-none border border-border/60 transition-colors hover:border-primary/40">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-wide text-foreground">{t('syncHeal.title')}</span>
          <Badge
            variant="outline"
            className={`h-5 px-1.5 text-xs font-mono tabular-nums rounded-md ${
              hasIssues ? 'border-amber-400/40 text-amber-400 bg-amber-400/5' : 'border-cyan-500/40 text-cyan-500 bg-cyan-500/5'
            }`}
          >
            {hasIssues ? t('syncHeal.statusWarning') : t('syncHeal.statusHealthy')}
          </Badge>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            disabled={Boolean(busyAction) || loading}
            onClick={() => { void fetchMetrics() }}
            className="h-6 px-2 text-xs font-mono"
            title={t('syncHeal.btnRefresh')}
          >
            <RefreshCwIcon className={`size-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>

          <Button
            size="sm"
            variant="outline"
            disabled={Boolean(busyAction)}
            onClick={() => { void handleSyncHeal() }}
            className="h-6 px-2 text-xs font-mono text-cyan-500 border-cyan-500/30 hover:bg-cyan-500/10"
          >
            <ZapIcon className={`mr-1 size-3 ${busyAction === 'sync-heal' ? 'animate-spin' : ''}`} />
            {busyAction === 'sync-heal' ? t('syncHeal.healing') : t('syncHeal.btnSyncHeal')}
          </Button>

          <Button
            size="sm"
            variant="outline"
            disabled={Boolean(busyAction)}
            onClick={() => { void handleRetryFailed() }}
            className="h-6 px-2 text-xs font-mono text-amber-400 border-amber-400/30 hover:bg-amber-400/10"
          >
            <RotateCwIcon className={`mr-1 size-3 ${busyAction === 'retry-failed' ? 'animate-spin' : ''}`} />
            {busyAction === 'retry-failed' ? t('syncHeal.retrying') : t('syncHeal.btnRetryFailed')}
          </Button>

          <Button
            size="sm"
            variant="outline"
            disabled={Boolean(busyAction) || dlqCount === 0}
            onClick={() => setConfirmClearOpen(true)}
            className="h-6 px-2 text-xs font-mono text-rose-500 border-rose-500/30 hover:bg-rose-500/10"
          >
            <Trash2Icon className="mr-1 size-3" />
            {busyAction === 'clear-dlq' ? t('syncHeal.clearing') : t('syncHeal.btnClearDlq')}
          </Button>

          <AlertDialog open={confirmClearOpen} onOpenChange={setConfirmClearOpen}>
            <AlertDialogContent className="max-w-md">
              <AlertDialogHeader>
                <AlertDialogTitle className="text-sm font-semibold">{t('syncHeal.confirmClearTitle')}</AlertDialogTitle>
                <AlertDialogDescription className="text-xs text-muted-foreground">{t('syncHeal.confirmClearDesc')}</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="h-7 text-xs">{t('syncHeal.cancel')}</AlertDialogCancel>
                <AlertDialogAction
                  className="h-7 text-xs bg-rose-600 hover:bg-rose-700 text-white"
                  onClick={() => {
                    setConfirmClearOpen(false)
                    void handleClearDlq()
                  }}
                >
                  {t('syncHeal.confirmClearBtn')}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('syncHeal.syncRate')}</span>
          <span className={`font-mono text-base font-bold tabular-nums ${syncRate >= 99.0 ? 'text-cyan-500' : syncRate >= 90.0 ? 'text-amber-400' : 'text-rose-500'}`}>
            {syncRate.toFixed(1)}%
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {metrics?.indexed_count ?? 0} / {metrics?.total_files ?? 0} {t('syncHeal.pieces')}
          </span>
        </div>

        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('syncHeal.dlqPending')}</span>
          <span className={`font-mono text-base font-bold tabular-nums ${dlqCount > 0 ? 'text-rose-500' : 'text-foreground'}`}>{dlqCount}</span>
          <span className="text-xs text-muted-foreground">{dlqCount > 0 ? t('syncHeal.dlqNeedRetry') : t('syncHeal.dlqZeroLoss')}</span>
        </div>

        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('syncHeal.pendingSync')}</span>
          <span className="font-mono text-base font-bold tabular-nums text-foreground">{pendingCount}</span>
          <span className="text-xs text-muted-foreground">{t('syncHeal.streaming')}</span>
        </div>

        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('syncHeal.failedFiles')}</span>
          <span className={`font-mono text-base font-bold tabular-nums ${failedCount > 0 ? 'text-amber-400' : 'text-foreground'}`}>{failedCount}</span>
          <span className="text-xs text-muted-foreground">{t('syncHeal.canAutoHeal')}</span>
        </div>
      </div>

      {feedback && (
        <div className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-mono border ${
          feedback.type === 'success' ? 'border-cyan-500/30 bg-cyan-500/5 text-cyan-400' : feedback.type === 'warn' ? 'border-amber-400/30 bg-amber-400/5 text-amber-400' : 'border-border/60 bg-muted/20 text-muted-foreground'
        }`}>
          {feedback.type === 'success' ? <CheckCircle2Icon className="size-3.5 shrink-0" /> : <AlertTriangleIcon className="size-3.5 shrink-0" />}
          <span>{feedback.text}</span>
        </div>
      )}
    </Card>
  )
}
