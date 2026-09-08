import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { ShieldCheckIcon, HardDriveIcon } from 'lucide-react'

import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'

interface GatekeeperStats {
  add: number
  update: number
  delete: number
  noop: number
  total_probes: number
  saved_bytes: number
}

interface GatekeeperApiResponse {
  status: string
  result: {
    stats: GatekeeperStats
    history?: unknown[]
  }
}

export function GatekeeperMetricsCard() {
  const { t } = useTranslation('tasksPage')

  const { data } = useQuery<GatekeeperApiResponse>({
    queryKey: ['entropy-gatekeeper-stats'],
    queryFn: async () => {
      const resp = await ovClient.instance.get('/api/v1/system/entropy/gatekeeper')
      return resp.data
    },
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  })

  const stats = data?.result.stats || {
    add: 0,
    update: 0,
    delete: 0,
    noop: 0,
    total_probes: 0,
    saved_bytes: 0,
  }

  const dedupRate = stats.total_probes > 0
    ? ((stats.noop / stats.total_probes) * 100).toFixed(1)
    : '0.0'

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${bytes} B`
  }

  return (
    <Card className="flex flex-col gap-3 p-3.5 shadow-none border-border/70">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2.5">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="size-4 text-primary shrink-0" />
          <span className="text-sm font-semibold tracking-tight text-foreground">
            {t('gatekeeper.title')}
          </span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            — {t('gatekeeper.subtitle')}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1 text-muted-foreground">
            <HardDriveIcon className="size-3.5" />
            <span className="text-[11px]">{t('gatekeeper.savedDiskIo')}:</span>
            <span className="font-mono font-semibold text-foreground">
              {formatBytes(stats.saved_bytes)}
            </span>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <span className="text-[11px]">{t('gatekeeper.dedupRate')}:</span>
            <span className="font-mono font-semibold text-primary">
              {dedupRate}%
            </span>
          </div>
        </div>
      </div>

      {/* 4 维变异状态统计胶囊 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="flex flex-col rounded-md border border-border/50 bg-muted/20 px-2.5 py-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            {t('gatekeeper.add')}
          </span>
          <span className="mt-0.5 font-mono text-base font-bold tabular-nums text-foreground">
            {stats.add}
          </span>
        </div>

        <div className="flex flex-col rounded-md border border-amber-500/20 bg-amber-500/5 px-2.5 py-2">
          <span className="text-[11px] font-medium text-amber-700 dark:text-amber-400">
            {t('gatekeeper.update')}
          </span>
          <span className="mt-0.5 font-mono text-base font-bold tabular-nums text-amber-600 dark:text-amber-400">
            {stats.update}
          </span>
        </div>

        <div className="flex flex-col rounded-md border border-rose-500/20 bg-rose-500/5 px-2.5 py-2">
          <span className="text-[11px] font-medium text-rose-700 dark:text-rose-400">
            {t('gatekeeper.delete')}
          </span>
          <span className="mt-0.5 font-mono text-base font-bold tabular-nums text-rose-600 dark:text-rose-400">
            {stats.delete}
          </span>
        </div>

        <div className="flex flex-col rounded-md border border-border/50 bg-muted/20 px-2.5 py-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            {t('gatekeeper.noop')}
          </span>
          <span className="mt-0.5 font-mono text-base font-bold tabular-nums text-foreground">
            {stats.noop}
          </span>
        </div>
      </div>
    </Card>
  )
}
