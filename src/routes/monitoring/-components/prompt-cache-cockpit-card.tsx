import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangleIcon, CpuIcon, ZapIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'

export interface PromptCacheSummary {
  requests: number
  last_request_at?: number
  output_tokens: number
  cache: {
    first_call: {
      requests: number
      input_tokens: number
      cached_tokens: number
      cache_hit_ratio: number
    }
    continuation: {
      requests: number
      input_tokens: number
      cached_tokens: number
      cache_hit_ratio: number
    }
  }
  cache_alerts?: {
    misses?: {
      conversations: number
      streak: number
      input_tokens: number
      no_writes: boolean
      recent: Array<{
        upstream_id: string
        model?: string
        streak: number
        last_at: number
      }>
    }
    unreported: string[]
  } | null
}

export function PromptCacheCockpitCard() {
  const { data, isLoading } = useQuery<PromptCacheSummary | null>({
    queryKey: ['gateway-prompt-cache-overview'],
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          result?: PromptCacheSummary
        }>('/api/v1/gateway/overview')
        return res.data.result ?? null
      } catch {
        return null
      }
    },
    refetchInterval: 15_000,
  })

  const firstCall = data?.cache?.first_call
  const continuation = data?.cache?.continuation
  const alerts = data?.cache_alerts
  const misses = alerts?.misses

  const contRatio = continuation?.cache_hit_ratio ?? 0
  const firstRatio = firstCall?.cache_hit_ratio ?? 0
  const totalCached = (firstCall?.cached_tokens ?? 0) + (continuation?.cached_tokens ?? 0)
  const isHealthy = !misses || misses.conversations === 0

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ZapIcon className="size-4 text-cyan-500" />
          <CardTitle className="text-base font-semibold">
            Prompt Cache 态势大盘与网关吞吐 (Gateway Telemetry)
          </CardTitle>
        </div>
        <Badge
          variant="outline"
          className={cn(
            'gap-1 font-normal text-xs',
            isHealthy
              ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
              : 'border-rose-500/30 text-rose-600 dark:text-rose-400',
          )}
        >
          <span
            className={cn(
              'size-1.5 rounded-full',
              isHealthy ? 'bg-cyan-500' : 'bg-rose-500',
            )}
          />
          {isHealthy ? '缓存运转优良' : `发现 ${misses.conversations} 个长会话未命中`}
        </Badge>
      </div>

      {/* 4 维核心效能瓷片 */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">追问缓存命中率</span>
          <span className="mt-0.5 font-mono text-base font-bold text-foreground tabular-nums">
            {isLoading ? '--' : `${(contRatio * 100).toFixed(1)}%`}
          </span>
        </div>

        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">首问前缀命中率</span>
          <span className="mt-0.5 font-mono text-base font-bold text-foreground tabular-nums">
            {isLoading ? '--' : `${(firstRatio * 100).toFixed(1)}%`}
          </span>
        </div>

        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">累计节省 Token 数</span>
          <span className="mt-0.5 font-mono text-base font-bold text-foreground/90 tabular-nums">
            {isLoading ? '--' : totalCached.toLocaleString()}
          </span>
        </div>

        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">网关总处理请求数</span>
          <span className="mt-0.5 font-mono text-base font-bold text-foreground/90 tabular-nums">
            {isLoading ? '--' : (data?.requests ?? 0).toLocaleString()}
          </span>
        </div>
      </div>

      {/* 长会话持续未命中预警区 */}
      {misses && misses.conversations > 0 && (
        <div className="flex flex-col gap-2 rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-rose-600 dark:text-rose-400">
            <AlertTriangleIcon className="size-4 shrink-0" />
            <span>长上下文连续未命中告警 (Streak Miss &gt; 32k Tokens)</span>
          </div>
          <p className="text-foreground/80 leading-relaxed">
            检测到当前有 <strong className="font-mono text-rose-500">{misses.conversations}</strong> 个长对话连续{' '}
            <strong className="font-mono">{misses.streak}</strong> 次以上未命中 Prompt Cache。建议排查系统提示词前缀是否发生微小变动或中间件动态注入。
          </p>
          {misses.recent && misses.recent.length > 0 && (
            <div className="mt-1 flex flex-col gap-1">
              {misses.recent.map((m, idx) => (
                <div
                  key={`${m.upstream_id}-${idx}`}
                  className="flex items-center justify-between rounded border border-border/40 bg-background/50 px-2 py-1 font-mono text-xs"
                >
                  <span className="truncate text-foreground/90">{m.model || m.upstream_id}</span>
                  <Badge variant="outline" className="text-xs text-rose-500 border-rose-500/30">
                    连续 {m.streak} 次 Miss
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 未上报 Cache 厂商提示 */}
      {alerts?.unreported && alerts.unreported.length > 0 && (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/10 px-3 py-2 text-xs text-muted-foreground">
          <CpuIcon className="size-3.5 shrink-0 text-muted-foreground" />
          <span>
            静默厂商提示：上游提供商 <code className="font-mono text-foreground/80">{alerts.unreported.join(', ')}</code> 近期未报告任何缓存命中，可能未开启 Prompt Cache 或中转未回传 details。
          </span>
        </div>
      )}
    </Card>
  )
}
