/* eslint-disable i18next/no-literal-string */
import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import {
  ActivityIcon,
  ShieldCheckIcon,
  RefreshCwIcon,
  ZapIcon,
  ClockIcon,
  SparklesIcon,
  AlertTriangleIcon,
} from 'lucide-react'

interface MemoryPurityReport {
  snr_ratio: number
  conflict_rate: number
  freshness_retained: number
  purity_score: number
  total_memories: number
  canonical_count: number
  active_count: number
  superseded_count: number
  disputed_count: number
  unconsolidated_fragments: number
  master_cards_count: number
  evaluated_at: number
  watchdog_status: {
    window?: string
    unconsolidated_threshold_met?: boolean
    unconsolidated_count?: number
    next_rem_window?: string
  }
}

interface WatchdogEnforceResult {
  triggered: boolean
  reason: string
  current_hour_utc?: number
  is_rem_window?: boolean
  unconsolidated_fragments?: number
  hours_since_last_dream?: number
  purity_score?: number
  snr_ratio?: number
  dream_cycle?: any
  error?: string
}

export function MemoryPurityGaugeCard() {
  const queryClient = useQueryClient()
  const [enforceFeedback, setEnforceFeedback] = React.useState<string | null>(null)

  // 1. Fetch Holistic Purity Report
  const { data: purity, isLoading, refetch } = useQuery<MemoryPurityReport>({
    queryKey: ['memory-purity-report'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result: MemoryPurityReport }>(
        '/api/v1/memory/purity/report'
      )
      return res.data.result
    },
    staleTime: 15_000,
    refetchIntervalInBackground: false,
  })

  // 2. Trigger Watchdog Enforcement
  const enforceMutation = useMutation({
    mutationFn: async (force: boolean) => {
      const res = await ovClient.instance.post<{ status: string; result: WatchdogEnforceResult }>(
        '/api/v1/memory/watchdog/enforce',
        { dry_run: false, force }
      )
      return res.data.result
    },
    onSuccess: (data) => {
      if (data.triggered) {
        setEnforceFeedback(`守护动作已触发: ${data.reason} (提纯结晶完成)`)
      } else {
        setEnforceFeedback('守护巡检通过: 碎片未达高水位且不在夜间REM窗口，无需额外做梦')
      }
      queryClient.invalidateQueries({ queryKey: ['memory-purity-report'] })
      queryClient.invalidateQueries({ queryKey: ['dream-stats'] })
      queryClient.invalidateQueries({ queryKey: ['memory-governance-stream'] })
    },
    onError: (err: any) => {
      setEnforceFeedback(`守护巡检异常: ${err?.message || '未知错误'}`)
    },
  })

  const score = purity?.purity_score ?? 0
  const scoreColor =
    score >= 85
      ? 'text-cyan-400'
      : score >= 60
        ? 'text-amber-400'
        : 'text-rose-500'

  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900/80 p-3.5 text-xs text-neutral-200">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-3">
        <div className="flex items-center gap-2">
          <ActivityIcon className="size-4 text-cyan-400" />
          <span className="font-semibold text-neutral-100">
            体外大脑记忆纯度度量衡与全自动做梦守护 (Memory Purity & Dream Watchdog)
          </span>
          <span className="rounded border border-neutral-800 bg-neutral-800/60 px-1.5 py-0.5 text-xs text-neutral-400">
            Layer 5 收官
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => enforceMutation.mutate(false)}
            disabled={enforceMutation.isPending}
            className="flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-950/30 px-2.5 py-1 text-xs text-cyan-300 transition-colors hover:bg-cyan-900/40 disabled:opacity-50"
          >
            <ShieldCheckIcon className="size-3.5" />
            <span>{enforceMutation.isPending ? '评估中...' : '守护巡检'}</span>
          </button>
          <button
            onClick={() => enforceMutation.mutate(true)}
            disabled={enforceMutation.isPending}
            className="flex items-center gap-1.5 rounded-md border border-amber-500/40 bg-amber-950/30 px-2.5 py-1 text-xs text-amber-300 transition-colors hover:bg-amber-900/40 disabled:opacity-50"
          >
            <SparklesIcon className="size-3.5" />
            <span>强制做梦提纯</span>
          </button>
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="rounded p-1 text-neutral-400 transition-colors hover:text-neutral-200 disabled:opacity-50"
            title="刷新指标"
          >
            <RefreshCwIcon className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Grid: Health Score & 3 Metric Tiles */}
      <div className="mt-3.5 grid grid-cols-1 gap-3 sm:grid-cols-4">
        {/* Purity Health Score Tile */}
        <div className="flex flex-col items-center justify-center rounded border border-neutral-800 bg-neutral-950/50 p-3">
          <span className="text-xs text-neutral-400">记忆纯度综合得分</span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className={`font-mono text-3xl font-bold ${scoreColor}`}>
              {purity ? purity.purity_score : '--'}
            </span>
            <span className="text-xs text-neutral-500">/ 100</span>
          </div>
          <span className="mt-1 text-xs text-neutral-400">
            {score >= 85 ? '极高信噪比 · 稳健' : score >= 60 ? '中等信噪比 · 可提纯' : '存在碎片退化风险'}
          </span>
        </div>

        {/* SNR Tile */}
        <div className="rounded border border-neutral-800 bg-neutral-950/50 p-3">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>信噪比指数 (SNR)</span>
            <span className="font-mono text-cyan-400 font-semibold">40% 权重</span>
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-neutral-100">
            {purity ? `${purity.snr_ratio.toFixed(2)}x` : '--'}
          </div>
          <p className="mt-1 text-xs text-neutral-400">
            权威主事实 ({purity?.canonical_count ?? 0} 篇 + {purity?.master_cards_count ?? 0} 卡) vs 散落碎片与已废弃
          </p>
        </div>

        {/* Conflict Rate Tile */}
        <div className="rounded border border-neutral-800 bg-neutral-950/50 p-3">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>未消解认知冲突率</span>
            <span className="font-mono text-cyan-400 font-semibold">35% 权重</span>
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-neutral-100">
            {purity ? `${(purity.conflict_rate * 100).toFixed(1)}%` : '--'}
          </div>
          <p className="mt-1 text-xs text-neutral-400">
            争议条目: {purity?.disputed_count ?? 0} / 总记忆: {purity?.total_memories ?? 0} (目标趋近 0%)
          </p>
        </div>

        {/* Freshness Retained Tile */}
        <div className="rounded border border-neutral-800 bg-neutral-950/50 p-3">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>90天时效新鲜留存率</span>
            <span className="font-mono text-cyan-400 font-semibold">25% 权重</span>
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-neutral-100">
            {purity ? `${(purity.freshness_retained * 100).toFixed(1)}%` : '--'}
          </div>
          <p className="mt-1 text-xs text-neutral-400">
            近期命中或已校验活跃条目比例 (高频对抗时效衰减)
          </p>
        </div>
      </div>

      {/* Watchdog Status & Feedback Banner */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded border border-neutral-800/80 bg-neutral-950/40 p-2.5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <ZapIcon className="size-3.5 text-cyan-400" />
            <span className="text-neutral-400">未提纯碎片:</span>
            <span className="font-mono font-medium text-neutral-200">
              {purity?.unconsolidated_fragments ?? 0}
            </span>
            <span className="text-xs text-neutral-500">/ 100 触发阈值</span>
          </div>
          <div className="flex items-center gap-1.5 border-l border-neutral-800 pl-3">
            <ClockIcon className="size-3.5 text-neutral-400" />
            <span className="text-neutral-400">夜间 REM 窗口:</span>
            <span className="font-mono text-neutral-300">
              {purity?.watchdog_status?.next_rem_window || '02:00 ~ 06:00 UTC'}
            </span>
          </div>
        </div>

        {enforceFeedback && (
          <div className="flex items-center gap-1.5 text-xs text-cyan-300 font-mono">
            <span>{enforceFeedback}</span>
          </div>
        )}
      </div>
    </div>
  )
}
