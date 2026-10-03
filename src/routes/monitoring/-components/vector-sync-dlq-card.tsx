import * as React from 'react'
import { Card, CardTitle } from '#/components/ui/card'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'

interface SyncMetricsData {
  sync_rate_pct: number
  total_files: number
  indexed_count: number
  pending_count: number
  failed_count: number
  dlq_pending_count: number
  dlq_total_count: number
}

interface DeadLetterItem {
  id: number
  queue_name: string
  uri?: string
  error_type: string
  error_message: string
  retry_count: number
  created_at: number
}

export function VectorSyncDlqCard() {
  const [metrics, setMetrics] = React.useState<SyncMetricsData | null>(null)
  const [deadLetters, setDeadLetters] = React.useState<DeadLetterItem[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [isHealing, setIsHealing] = React.useState(false)

  const fetchData = React.useCallback(async () => {
    try {
      setIsLoading(true)
      const res = await ovClient.instance.get<{ status: string } & SyncMetricsData>(
        '/api/v1/queue/sync-metrics'
      )
      if (res.data?.status === 'success') {
        setMetrics(res.data)
      }
      const dlqRes = await ovClient.instance.get<{ status: string; items: DeadLetterItem[] }>(
        '/api/v1/queue/dlq?limit=5&resolved=0'
      )
      if (dlqRes.data?.status === 'success') {
        setDeadLetters(dlqRes.data.items || [])
      }
    } catch (err) {
      console.error('[VectorSyncDlqCard] Failed to fetch sync metrics:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => {
    fetchData()
    const timer = setInterval(fetchData, 15000)
    return () => clearInterval(timer)
  }, [fetchData])

  const handleTriggerHeal = async () => {
    try {
      setIsHealing(true)
      await ovClient.instance.post('/api/v1/queue/sync-heal')
      await fetchData()
    } catch (err) {
      console.error('[VectorSyncDlqCard] Heal failed:', err)
    } finally {
      setIsHealing(false)
    }
  }

  const syncRate = metrics?.sync_rate_pct ?? 100.0
  const dlqCount = metrics?.dlq_pending_count ?? 0
  const failedCount = metrics?.failed_count ?? 0

  return (
    <Card className="flex flex-col gap-2.5 p-3 shadow-none border transition-colors hover:border-primary/40">
      <div className="flex items-center justify-between border-b pb-2 border-border/60">
        <div className="flex items-center gap-2">
          <CardTitle className="text-xs font-semibold tracking-wide">
            向量索引同步与死信队列 (Vector Sync & DLQ)
          </CardTitle>
          <Badge
            variant="outline"
            className="h-5 px-1.5 text-xs font-mono tabular-nums rounded-md border-border/60"
          >
            {dlqCount === 0 ? 'DLQ 清空' : `死信待审: ${dlqCount}`}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            disabled={isHealing || isLoading}
            onClick={handleTriggerHeal}
            className="h-6 px-2 text-xs font-mono"
          >
            {isHealing ? '自愈中...' : '自愈巡检'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {/* 指标 1: 同步健康率 */}
        <div className="flex flex-col gap-0.5 rounded-md border bg-muted/20 p-2">
          <span className="text-xs text-muted-foreground">向量同步率</span>
          <span
            className={`font-mono text-base font-bold tabular-nums ${
              syncRate >= 99.0
                ? 'text-cyan-500'
                : syncRate >= 90.0
                ? 'text-amber-400'
                : 'text-rose-500'
            }`}
          >
            {syncRate.toFixed(1)}%
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {metrics?.indexed_count ?? 0} / {metrics?.total_files ?? 0} 篇
          </span>
        </div>

        {/* 指标 2: 死信积压数 */}
        <div className="flex flex-col gap-0.5 rounded-md border bg-muted/20 p-2">
          <span className="text-xs text-muted-foreground">DLQ 积压死信</span>
          <span
            className={`font-mono text-base font-bold tabular-nums ${
              dlqCount > 0 ? 'text-rose-500' : 'text-foreground'
            }`}
          >
            {dlqCount}
          </span>
          <span className="text-xs text-muted-foreground">
            {dlqCount > 0 ? '需介入重试' : '零静默丢弃'}
          </span>
        </div>

        {/* 指标 3: 待处理队列 */}
        <div className="flex flex-col gap-0.5 rounded-md border bg-muted/20 p-2">
          <span className="text-xs text-muted-foreground">队列待向量化</span>
          <span className="font-mono text-base font-bold tabular-nums text-foreground">
            {metrics?.pending_count ?? 0}
          </span>
          <span className="text-xs text-muted-foreground">实时流转中</span>
        </div>

        {/* 指标 4: 索引失败数 */}
        <div className="flex flex-col gap-0.5 rounded-md border bg-muted/20 p-2">
          <span className="text-xs text-muted-foreground">失败失联数</span>
          <span
            className={`font-mono text-base font-bold tabular-nums ${
              failedCount > 0 ? 'text-amber-400' : 'text-foreground'
            }`}
          >
            {failedCount}
          </span>
          <span className="text-xs text-muted-foreground">可自动自愈</span>
        </div>
      </div>

      {deadLetters.length > 0 && (
        <div className="flex flex-col gap-1 border-t pt-2 border-border/40">
          <span className="text-xs font-medium text-rose-500">
            最近未决死信 (Top {deadLetters.length}):
          </span>
          <div className="flex flex-col gap-1 max-h-24 overflow-y-auto">
            {deadLetters.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between text-xs font-mono bg-muted/30 px-2 py-1 rounded"
              >
                <span className="truncate max-w-[200px] text-foreground">
                  {item.uri || `msg-${item.id}`}
                </span>
                <span className="text-amber-400">{item.error_type}</span>
                <span className="text-muted-foreground truncate max-w-[150px]">
                  {item.error_message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
