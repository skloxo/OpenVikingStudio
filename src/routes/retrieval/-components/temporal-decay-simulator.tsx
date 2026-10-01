import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import { SlidersIcon } from 'lucide-react'

export interface DecaySimResult {
  uri: string
  is_immune: boolean
  status: string
  delta_days: number
  raw_score: number
  decay_factor: number
  adjusted_score: number
  penalty_reason: string | null
  active_count: number
  memory_type: string
  hit_boost: number
  decay_multiplier: number
  lambda_val: number
}

export function TemporalDecaySimulator() {
  const [memoryType, setMemoryType] = React.useState<'experience' | 'canonical' | 'event' | 'general'>('experience')
  const [deltaDays, setDeltaDays] = React.useState<number>(30)
  const [activeHits, setActiveHits] = React.useState<number>(8)
  const [rawScore, setRawScore] = React.useState<number>(0.85)
  const [status, setStatus] = React.useState<'active' | 'disputed' | 'superseded'>('active')

  const { data: simData, isFetching: simLoading } = useQuery<DecaySimResult>({
    queryKey: ['decay-simulate', memoryType, deltaDays, activeHits, rawScore, status],
    queryFn: async () => {
      const res = await ovClient.instance.post<{ status: string; result: DecaySimResult }>(
        '/api/v1/memory/decay/simulate',
        {
          uri: `viking://resources/${memoryType}/demo_sample.md`,
          raw_score: rawScore,
          delta_days: deltaDays,
          active_count: activeHits,
          memory_type: memoryType,
          status: status,
        }
      )
      return res.data.result
    },
    staleTime: 10_000,
    refetchIntervalInBackground: false,
  })

  const scoreGain = React.useMemo(() => {
    if (!simData) return 0
    return Math.round(((simData.adjusted_score - simData.raw_score) / (simData.raw_score || 1)) * 100)
  }, [simData])

  return (
    <div className="mt-3.5 rounded-md border border-neutral-800 bg-neutral-950/50 p-3">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
        <div className="flex items-center gap-1.5">
          <SlidersIcon className="size-3.5 text-cyan-400" />
          <span className="text-xs font-semibold text-neutral-200">
            时效动力学与频次强化实时仿真台 (Interactive Decay Simulator)
          </span>
        </div>
        {simLoading && <span className="font-mono text-xs text-neutral-500">计算中...</span>}
      </div>

      <div className="mt-2.5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {/* Memory Type */}
        <div>
          <label className="text-xs text-neutral-400">记忆类型 (λ 衰减系数)</label>
          <select
            value={memoryType}
            onChange={(e) => setMemoryType(e.target.value as any)}
            className="mt-1 w-full rounded-md border border-neutral-700 bg-neutral-900 px-2 py-1 font-mono text-xs text-neutral-200 outline-none focus:border-cyan-500"
          >
            <option value="experience">experience (λ=0.007, 慢衰减)</option>
            <option value="canonical">canonical (λ=0.0, 绝对免疫)</option>
            <option value="event">event/task (λ=0.05, 快衰减)</option>
            <option value="general">general (λ=0.01, 默认)</option>
          </select>
        </div>

        {/* Delta Days */}
        <div>
          <div className="flex justify-between text-xs text-neutral-400">
            <span>时间跨度 Δt</span>
            <span className="font-mono text-neutral-200 tabular-nums">{deltaDays} 天</span>
          </div>
          <input
            type="range"
            min="0"
            max="180"
            value={deltaDays}
            onChange={(e) => setDeltaDays(Number(e.target.value))}
            className="mt-1.5 w-full accent-cyan-500"
          />
        </div>

        {/* Active Hits */}
        <div>
          <div className="flex justify-between text-xs text-neutral-400">
            <span>采纳频次 N_hits</span>
            <span className="font-mono text-cyan-400 tabular-nums">{activeHits} 次</span>
          </div>
          <input
            type="range"
            min="0"
            max="50"
            value={activeHits}
            onChange={(e) => setActiveHits(Number(e.target.value))}
            className="mt-1.5 w-full accent-cyan-500"
          />
        </div>

        {/* Raw Score */}
        <div>
          <div className="flex justify-between text-xs text-neutral-400">
            <span>语义基准分</span>
            <span className="font-mono text-neutral-200 tabular-nums">{rawScore.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.30"
            max="1.0"
            step="0.05"
            value={rawScore}
            onChange={(e) => setRawScore(Number(e.target.value))}
            className="mt-1.5 w-full accent-cyan-500"
          />
        </div>

        {/* Status */}
        <div>
          <label className="text-xs text-neutral-400">生命周期状态</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as any)}
            className="mt-1 w-full rounded-md border border-neutral-700 bg-neutral-900 px-2 py-1 font-mono text-xs text-neutral-200 outline-none focus:border-cyan-500"
          >
            <option value="active">active (1.0x)</option>
            <option value="disputed">disputed (0.50x 惩罚)</option>
            <option value="superseded">superseded (0.20x 废弃)</option>
          </select>
        </div>
      </div>

      {/* Live Calculation Output Card */}
      {simData && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-neutral-800 bg-neutral-900/90 p-2.5 font-mono">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <div>
              <span className="text-neutral-500">时效乘子 e^(-λΔt): </span>
              <span className="font-bold text-neutral-200 tabular-nums">{simData.decay_multiplier}</span>
            </div>
            <div>
              <span className="text-neutral-500">频次强化 (1+β·ln(1+N)): </span>
              <span className="font-bold text-cyan-400 tabular-nums">×{simData.hit_boost}</span>
            </div>
            <div>
              <span className="text-neutral-500">综合因子: </span>
              <span className="font-bold text-neutral-100 tabular-nums">{simData.decay_factor}</span>
            </div>
            <div>
              <span className="text-neutral-500">最终有效得分: </span>
              <span className="text-sm font-bold text-cyan-400 tabular-nums">
                {simData.adjusted_score.toFixed(4)}
              </span>
              <span className="ml-1 text-xs text-neutral-500">
                (原分 {simData.raw_score.toFixed(2)})
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
                scoreGain >= 0
                  ? 'border border-cyan-800 bg-cyan-950/70 text-cyan-400'
                  : 'border border-amber-800 bg-amber-950/70 text-amber-400'
              }`}
            >
              {scoreGain >= 0 ? `+${scoreGain}% (越用越强)` : `${scoreGain}% (平滑衰退)`}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
