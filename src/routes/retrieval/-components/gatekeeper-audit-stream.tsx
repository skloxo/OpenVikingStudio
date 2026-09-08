import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { ActivityIcon, FileSearchIcon } from 'lucide-react'

import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import { GatekeeperDecisionDrawer } from './gatekeeper-decision-drawer'
import type { GatekeeperDecisionRecord } from './gatekeeper-decision-drawer'

interface GatekeeperApiResponse {
  status: string
  result: {
    stats: unknown
    history: GatekeeperDecisionRecord[]
  }
}

export function GatekeeperAuditStream() {
  const { t } = useTranslation('tasksPage')
  const [selectedDecision, setSelectedDecision] = React.useState<GatekeeperDecisionRecord | null>(null)

  const { data, isLoading } = useQuery<GatekeeperApiResponse>({
    queryKey: ['entropy-gatekeeper-stats'],
    queryFn: async () => {
      const resp = await ovClient.instance.get('/api/v1/system/entropy/gatekeeper')
      return resp.data
    },
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  })

  const history = data?.result.history || []

  const formatTime = (timestamp?: number) => {
    if (!timestamp) return '--:--:--'
    const date = new Date(timestamp > 1e11 ? timestamp : timestamp * 1000)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  }

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'noop':
        return (
          <Badge variant="outline" className="border-border/60 bg-muted/40 text-muted-foreground text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.noop')}
          </Badge>
        )
      case 'update':
        return (
          <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.update')}
          </Badge>
        )
      case 'delete':
        return (
          <Badge variant="outline" className="border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.delete')}
          </Badge>
        )
      default:
        return (
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.add')}
          </Badge>
        )
    }
  }

  return (
    <>
      <Card className="flex flex-col gap-2.5 p-3.5 shadow-none border-border/70">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2.5">
          <div className="flex items-center gap-2">
            <ActivityIcon className="size-4 text-primary shrink-0" />
            <span className="text-sm font-semibold tracking-tight text-foreground">
              {t('gatekeeper.streamTitle')}
            </span>
            <span className="hidden text-xs text-muted-foreground sm:inline">
              — {t('gatekeeper.streamSubtitle')}
            </span>
          </div>
          <div className="flex items-center gap-2.5 text-xs text-muted-foreground">
            <span className="inline-block size-1.5 rounded-full bg-primary animate-pulse" />
            <span className="font-mono text-[11px]">
              {history.length > 0 ? `${history.length} 条记录` : t('gatekeeper.emptyDecisions')}
            </span>
          </div>
        </div>

        {/* 流水列表区域 */}
        {isLoading ? (
          <div className="py-8 text-center text-xs text-muted-foreground">
            {t('loading')}
          </div>
        ) : history.length === 0 ? (
          <div className="py-6 text-center text-[11px] text-muted-foreground rounded-md border border-dashed border-border/50">
            {t('gatekeeper.emptyDecisions')}
          </div>
        ) : (
          <div className="flex flex-col overflow-hidden rounded-md border border-border/50 bg-background">
            {/* 表头 */}
            <div className="flex items-center gap-3 border-b border-border/50 bg-muted/20 px-3 py-1.5 text-[11px] font-medium text-muted-foreground">
              <span className="w-16 shrink-0">{t('gatekeeper.colTime')}</span>
              <span className="w-20 shrink-0">{t('gatekeeper.colAction')}</span>
              <span className="w-52 shrink-0">{t('gatekeeper.colTarget')}</span>
              <span className="w-16 shrink-0">{t('gatekeeper.colSim')}</span>
              <span className="min-w-0 flex-1">{t('gatekeeper.colReason')}</span>
              <span className="w-12 shrink-0 text-right">{t('gatekeeper.colInspect')}</span>
            </div>

            {/* 数据体 */}
            <div className="flex flex-col divide-y divide-border/40 max-h-85 overflow-y-auto">
              {history.slice().reverse().map((rec, idx) => {
                const targetUri = rec.uri || rec.matched_uri || '--'
                return (
                  <div
                    key={`${rec.timestamp || idx}-${idx}`}
                    onClick={() => setSelectedDecision(rec)}
                    className="flex items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-muted/40 cursor-pointer"
                  >
                    {/* 时间戳 */}
                    <span className="w-16 shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
                      {formatTime(rec.timestamp)}
                    </span>

                    {/* 裁决动作 */}
                    <div className="w-20 shrink-0">
                      {getActionBadge(rec.action)}
                    </div>

                    {/* 目标 URI */}
                    <span
                      className="w-52 shrink-0 truncate font-mono text-[11px] text-foreground/90"
                      title={targetUri}
                    >
                      {targetUri}
                    </span>

                    {/* 相似度 */}
                    <span
                      className={cn(
                        'w-16 shrink-0 font-mono text-[11px] tabular-nums font-semibold',
                        rec.similarity >= 0.95
                          ? 'text-primary'
                          : rec.similarity >= 0.9
                            ? 'text-amber-500 dark:text-amber-400'
                            : 'text-muted-foreground'
                      )}
                    >
                      {rec.similarity > 0 ? (rec.similarity * 100).toFixed(1) + '%' : '--'}
                    </span>

                    {/* 裁决依据 (直接阅读) */}
                    <span
                      className="min-w-0 flex-1 truncate text-[11px] text-muted-foreground"
                      title={rec.reason}
                    >
                      {rec.reason || '--'}
                    </span>

                    {/* 溯源按钮 */}
                    <div className="w-12 shrink-0 text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedDecision(rec)
                        }}
                        className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
                      >
                        <FileSearchIcon className="size-3" />
                        <span className="sr-only sm:not-sr-only sm:inline-block sm:ml-1 text-[11px]">
                          {t('gatekeeper.colInspect')}
                        </span>
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </Card>

      <GatekeeperDecisionDrawer
        open={Boolean(selectedDecision)}
        onOpenChange={(open) => {
          if (!open) setSelectedDecision(null)
        }}
        decision={selectedDecision}
      />
    </>
  )
}
