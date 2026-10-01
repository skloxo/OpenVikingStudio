import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import {
  SparklesIcon,
  FlameIcon,
  ClockIcon,
  ShieldCheckIcon,
  LayersIcon,
  TrendingUpIcon,
  RefreshCwIcon,
  CheckCircle2Icon,
} from 'lucide-react'
import { TemporalDecaySimulator } from './temporal-decay-simulator'

interface DreamStats {
  total_dreams: number
  fragments_consolidated: number
  master_cards_created: number
  net_entropy_reduced: number
  last_dream_timestamp: number
  last_dream_id: string | null
  purity_ratio: number
}

interface DreamRunResult {
  status: string
  dream_id: string
  snapshot_commit: string | null
  theme: string
  fragments_scanned: number
  fragments_consolidated: number
  master_cards_created: number
  master_card_uris: string[]
  net_entropy_reduced: number
  duration_ms: number
}

export function TemporalDecayDreamCard() {
  const queryClient = useQueryClient()
  const [dreamTheme, setDreamTheme] = React.useState<string>('systemd_service')
  const [lastDreamResult, setLastDreamResult] = React.useState<DreamRunResult | null>(null)

  // 1. Fetch Dream Telemetry
  const { data: dreamStats, isLoading: statsLoading, refetch: refetchStats } = useQuery<DreamStats>({
    queryKey: ['dream-stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result: DreamStats }>(
        '/api/v1/memory/dream/stats'
      )
      return res.data.result
    },
    staleTime: 15_000,
    refetchIntervalInBackground: false,
  })

  // 2. Trigger Offline Dream Run
  const dreamMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post<{ status: string; result: DreamRunResult }>(
        '/api/v1/memory/dream/run',
        {
          theme: dreamTheme.trim() || undefined,
          min_cluster_size: 2,
          dry_run: false,
        }
      )
      return res.data.result
    },
    onSuccess: (data) => {
      setLastDreamResult(data)
      queryClient.invalidateQueries({ queryKey: ['dream-stats'] })
      queryClient.invalidateQueries({ queryKey: ['conflict-stats'] })
      queryClient.invalidateQueries({ queryKey: ['conflict-history'] })
    },
  })

  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900/80 p-3.5 text-xs text-neutral-200">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex size-6 items-center justify-center rounded-md bg-neutral-800 text-cyan-400">
            <SparklesIcon className="size-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-neutral-100">
              时效动力学衰减与离线做梦蒸馏座舱 (Temporal Decay & Offline Dream)
            </h3>
            <p className="font-mono text-xs text-neutral-400">
              Score_eff = Score_sem × e^(-λ·Δt) × (1 + β·ln(1 + N_hits))
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="rounded-md border border-neutral-700 bg-neutral-800/80 px-2 py-0.5 font-mono text-xs text-neutral-300">
            Layer 3 & 4 治理中枢
          </span>
          <button
            onClick={() => refetchStats()}
            className="flex items-center gap-1 rounded-md border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-300 transition-colors hover:bg-neutral-700 hover:text-neutral-100"
          >
            <RefreshCwIcon className={`size-3 ${statsLoading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* Top Telemetry Metric Tiles */}
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-md border border-neutral-800 bg-neutral-950/60 p-2.5">
          <div className="flex items-center gap-1.5 text-neutral-400">
            <ClockIcon className="size-3 text-cyan-400" />
            <span>做梦蒸馏轮次</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-mono text-base font-bold text-neutral-100 tabular-nums">
              {dreamStats?.total_dreams ?? 0}
            </span>
            <span className="font-mono text-xs text-neutral-500">次运行</span>
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-neutral-950/60 p-2.5">
          <div className="flex items-center gap-1.5 text-neutral-400">
            <LayersIcon className="size-3 text-neutral-400" />
            <span>碎片固化收拢</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-mono text-base font-bold text-neutral-100 tabular-nums">
              {dreamStats?.fragments_consolidated ?? 0}
            </span>
            <span className="font-mono text-xs text-neutral-500">条碎片</span>
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-neutral-950/60 p-2.5">
          <div className="flex items-center gap-1.5 text-neutral-400">
            <ShieldCheckIcon className="size-3 text-cyan-400" />
            <span>主知识卡片 (SSOT)</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-mono text-base font-bold text-cyan-400 tabular-nums">
              {dreamStats?.master_cards_created ?? 0}
            </span>
            <span className="font-mono text-xs text-neutral-500">张晶体</span>
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-neutral-950/60 p-2.5">
          <div className="flex items-center gap-1.5 text-neutral-400">
            <TrendingUpIcon className="size-3 text-cyan-400" />
            <span>净信息熵削减量</span>
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-mono text-base font-bold text-cyan-400 tabular-nums">
              {dreamStats?.net_entropy_reduced ?? 0}
            </span>
            <span className="font-mono text-xs text-neutral-500">单位冗余</span>
          </div>
        </div>
      </div>

      {/* Simulator Section (Seam Split) */}
      <TemporalDecaySimulator />

      {/* Offline Dream Actions & Execution Box */}
      <div className="mt-3.5 rounded-md border border-neutral-800 bg-neutral-950/50 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <FlameIcon className="size-3.5 text-cyan-400" />
            <span className="text-xs font-semibold text-neutral-200">
              离线做梦蒸馏流水线 (ov_dream Knowledge Consolidation)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="指定主题 (留空则全量聚类)"
              value={dreamTheme}
              onChange={(e) => setDreamTheme(e.target.value)}
              className="w-48 rounded-md border border-neutral-700 bg-neutral-900 px-2 py-1 font-mono text-xs text-neutral-200 outline-none focus:border-cyan-500"
            />
            <button
              onClick={() => dreamMutation.mutate()}
              disabled={dreamMutation.isPending}
              className="flex items-center gap-1.5 rounded-md border border-cyan-700 bg-cyan-950/60 px-3 py-1 font-semibold text-cyan-300 transition-colors hover:bg-cyan-900/60 disabled:opacity-50"
            >
              <SparklesIcon className={`size-3 ${dreamMutation.isPending ? 'animate-spin' : ''}`} />
              {dreamMutation.isPending ? '正在做梦蒸馏中...' : '启动离线做梦蒸馏'}
            </button>
          </div>
        </div>

        {/* Dream Execution Result */}
        {lastDreamResult && (
          <div className="mt-2.5 rounded-md border border-neutral-800 bg-neutral-900/90 p-2.5 font-mono text-xs">
            <div className="flex items-center gap-2 text-cyan-400">
              <CheckCircle2Icon className="size-3.5" />
              <span className="font-semibold">做梦固化完成: {lastDreamResult.dream_id}</span>
              <span className="text-neutral-500">耗时 {lastDreamResult.duration_ms}ms</span>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-4 text-neutral-300">
              <span>扫描碎片: {lastDreamResult.fragments_scanned} 条</span>
              <span>固化废弃: {lastDreamResult.fragments_consolidated} 条</span>
              <span>新铸主卡片: {lastDreamResult.master_cards_created} 张</span>
              <span className="text-cyan-400">净熵削减: {lastDreamResult.net_entropy_reduced} 单位</span>
            </div>
            {lastDreamResult.master_card_uris.length > 0 && (
              <div className="mt-1.5 text-neutral-400">
                主卡片 URI:{' '}
                {lastDreamResult.master_card_uris.map((uri) => (
                  <span key={uri} className="ml-1 text-cyan-300">
                    {uri}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
