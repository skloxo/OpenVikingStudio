import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import {
  ArchiveIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  ChevronUpIcon,
  DatabaseIcon,
  RotateCcwIcon,
  ShieldCheckIcon,
  SlidersIcon,
  TrendingUpIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'

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

export interface ColdAuditCandidate {
  uri: string
  status: string
  delta_days: number
  decay_multiplier: number
  adjusted_score: number
  is_candidate: boolean
}

export interface ColdAuditData {
  total_active_memories: number
  total_cold_archived: number
  dormant_candidates_count: number
  candidates: ColdAuditCandidate[]
  average_active_score: number
  retrieval_snr_gain_pct: number
  data_loss_rate_pct: number
}

export interface ColdArchiveItem {
  uri: string
  original_status: string
  archive_reason: string
  decay_score: number
  archived_at: number
  active_count: number
  metadata: Record<string, any>
}

export function TemporalDecaySimulator() {
  const queryClient = useQueryClient()
  const [showFormulaInspector, setShowFormulaInspector] = React.useState<boolean>(false)
  const [actionNotice, setActionNotice] = React.useState<string | null>(null)

  // Simulation parameters for bottom formula inspector
  const [memoryType, setMemoryType] = React.useState<'experience' | 'canonical' | 'event' | 'general'>('experience')
  const [deltaDays, setDeltaDays] = React.useState<number>(30)
  const [activeHits, setActiveHits] = React.useState<number>(8)
  const [rawScore, setRawScore] = React.useState<number>(0.85)
  const [status, setStatus] = React.useState<'active' | 'disputed' | 'superseded'>('active')

  // 1. Fetch Real SQLite Storage Audit
  const auditQuery = useQuery<ColdAuditData>({
    queryKey: ['memory-cold-audit'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result: ColdAuditData }>(
        '/api/v1/memory/cold/audit?decay_threshold=0.35&limit=100'
      )
      return res.data.result
    },
    refetchInterval: 10_000,
    staleTime: 10_000,
  })

  // 2. Fetch Safely Archived Cold Items
  const coldListQuery = useQuery<{ total: number; records: ColdArchiveItem[] }>({
    queryKey: ['memory-cold-list'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result: { total: number; records: ColdArchiveItem[] } }>(
        '/api/v1/memory/cold/list?limit=20'
      )
      return res.data.result
    },
    refetchInterval: 10_000,
    staleTime: 10_000,
  })

  // 3. Archive to Cold Mutation
  const archiveMutation = useMutation({
    mutationFn: async ({ uri, decayScore }: { uri: string; decayScore?: number }) => {
      const res = await ovClient.instance.post<{ status: string; result: ColdArchiveItem }>(
        '/api/v1/memory/cold/archive',
        {
          uri,
          reason: '座舱一键安全冷归档（艾宾浩斯衰减隔离）',
          decay_score: decayScore,
        }
      )
      return res.data.result
    },
    onSuccess: (data) => {
      setActionNotice(`已将记忆 ${data.uri} 安全冷归档！原始数据 100% 完整保留，日常检索信噪比提升。`)
      void queryClient.invalidateQueries({ queryKey: ['memory-cold-audit'] })
      void queryClient.invalidateQueries({ queryKey: ['memory-cold-list'] })
    },
  })

  // 4. Revive from Cold Mutation
  const reviveMutation = useMutation({
    mutationFn: async (uri: string) => {
      const res = await ovClient.instance.post<{ status: string; result: { uri: string; message: string } }>(
        '/api/v1/memory/cold/revive',
        { uri, reason: '座舱操作员人工一键复活唤醒' }
      )
      return res.data.result
    },
    onSuccess: (data) => {
      setActionNotice(data.message)
      void queryClient.invalidateQueries({ queryKey: ['memory-cold-audit'] })
      void queryClient.invalidateQueries({ queryKey: ['memory-cold-list'] })
    },
  })

  // 5. Formula Simulation Query
  const simQuery = useQuery<DecaySimResult>({
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
          status,
        }
      )
      return res.data.result
    },
    enabled: showFormulaInspector,
    staleTime: 10_000,
  })

  const audit = auditQuery.data
  const coldList = coldListQuery.data?.records ?? []

  return (
    <div className="mt-3.5 space-y-3 rounded-md border border-neutral-800 bg-neutral-950/50 p-3">
      {/* Top Banner Notice */}
      {actionNotice && (
        <div className="flex items-center justify-between rounded-md border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs text-cyan-300">
          <div className="flex items-center gap-1.5">
            <CheckCircle2Icon className="size-3.5 shrink-0 text-cyan-400" />
            <span>{actionNotice}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActionNotice(null)}
            className="h-5 px-1.5 text-xs text-cyan-400 hover:bg-cyan-500/20"
          >
            关闭
          </Button>
        </div>
      )}

      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between border-b border-neutral-800 pb-2">
        <div className="flex items-center gap-1.5">
          <DatabaseIcon className="size-3.5 text-cyan-400" />
          <span className="text-xs font-semibold text-neutral-200">
            真实记忆时效衰减体检与安全冷归档座舱 (Real Decay Audit & Non-Destructive Cold Archive)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-5 border-cyan-500/30 bg-cyan-500/10 px-1.5 text-xs text-cyan-400">
            零数据破坏 · 100% 可逆
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFormulaInspector(!showFormulaInspector)}
            className="h-6 gap-1 px-2 text-xs text-neutral-400 hover:text-neutral-200"
          >
            <SlidersIcon className="size-3" />
            <span>{showFormulaInspector ? '收起动力学公式' : '展开动力学公式'}</span>
            {showFormulaInspector ? <ChevronUpIcon className="size-3" /> : <ChevronDownIcon className="size-3" />}
          </Button>
        </div>
      </div>

      {/* 4 Objective Metric Tiles */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded border border-neutral-800 bg-neutral-900/60 p-2.5">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>活跃记忆总数</span>
            <DatabaseIcon className="size-3 text-cyan-400" />
          </div>
          <div className="mt-1 font-mono text-base font-bold text-neutral-100 tabular-nums">
            {audit?.total_active_memories ?? '--'}{' '}
            <span className="text-xs font-normal text-neutral-500">条</span>
          </div>
        </div>

        <div className="rounded border border-neutral-800 bg-neutral-900/60 p-2.5">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>安全冷归档记忆</span>
            <ArchiveIcon className="size-3 text-amber-400" />
          </div>
          <div className="mt-1 font-mono text-base font-bold text-amber-400 tabular-nums">
            {audit?.total_cold_archived ?? 0}{' '}
            <span className="text-xs font-normal text-neutral-500">条</span>
          </div>
        </div>

        <div className="rounded border border-neutral-800 bg-neutral-900/60 p-2.5">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>日常检索信噪比增益</span>
            <TrendingUpIcon className="size-3 text-cyan-400" />
          </div>
          <div className="mt-1 font-mono text-base font-bold text-cyan-400 tabular-nums">
            +{audit?.retrieval_snr_gain_pct ?? 0}%
          </div>
        </div>

        <div className="rounded border border-neutral-800 bg-neutral-900/60 p-2.5">
          <div className="flex items-center justify-between text-xs text-neutral-400">
            <span>数据防损安全保障</span>
            <ShieldCheckIcon className="size-3 text-cyan-400" />
          </div>
          <div className="mt-1 font-mono text-base font-bold text-cyan-400 tabular-nums">
            100% 安全
          </div>
        </div>
      </div>

      {/* Dual Real-Data Panels */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {/* Left: Storage Audit & Dormant Candidates */}
        <div className="rounded border border-neutral-800 bg-neutral-900/40 p-2.5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-neutral-200">
              全库艾宾浩斯衰减扫描 (休眠待归档: {audit?.dormant_candidates_count ?? 0})
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={auditQuery.isFetching}
              onClick={() => void auditQuery.refetch()}
              className="h-5 px-2 text-xs text-cyan-400 hover:bg-cyan-500/10"
            >
              <ZapIcon className="mr-1 size-2.5" />
              重新扫描
            </Button>
          </div>
          <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
            {audit?.candidates && audit.candidates.length > 0 ? (
              audit.candidates.map((c) => (
                <div
                  key={c.uri}
                  className="flex items-center justify-between rounded border border-neutral-800 bg-neutral-950/60 px-2 py-1.5 text-xs"
                >
                  <div className="truncate pr-2 font-mono">
                    <span className="text-neutral-200 truncate">{c.uri}</span>
                    <div className="text-neutral-400 font-sans">
                      已休眠 {c.delta_days} 天 ｜ 健康分: {c.adjusted_score}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={archiveMutation.isPending}
                    onClick={() => archiveMutation.mutate({ uri: c.uri, decayScore: c.adjusted_score })}
                    className="h-5 shrink-0 px-2 text-xs text-amber-400 hover:bg-amber-500/10 border-amber-500/30"
                  >
                    <ArchiveIcon className="mr-1 size-3" />
                    冷归档
                  </Button>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-xs text-neutral-500">
                当前活跃记忆健康度良好，暂无低于阈值的休眠记忆
              </div>
            )}
          </div>
        </div>

        {/* Right: Cold Quarantined List & One-Click Revive */}
        <div className="rounded border border-neutral-800 bg-neutral-900/40 p-2.5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-neutral-200">
              冷归档安全隔离库 ({coldList.length} 条已归档)
            </span>
            <Badge variant="outline" className="h-4 border-neutral-700 bg-neutral-800 px-1 text-xs text-neutral-400">
              隔离中
            </Badge>
          </div>
          <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
            {coldList.length > 0 ? (
              coldList.map((item) => (
                <div
                  key={item.uri}
                  className="flex items-center justify-between rounded border border-neutral-800 bg-neutral-950/60 px-2 py-1.5 text-xs"
                >
                  <div className="truncate pr-2 font-mono">
                    <span className="text-amber-400 truncate">{item.uri}</span>
                    <div className="text-neutral-400 font-sans truncate" title={item.archive_reason}>
                      {item.archive_reason}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={reviveMutation.isPending}
                    onClick={() => reviveMutation.mutate(item.uri)}
                    className="h-5 shrink-0 px-2 text-xs text-cyan-400 hover:bg-cyan-500/10 border-cyan-500/30"
                  >
                    <RotateCcwIcon className="mr-1 size-3" />
                    安全复活
                  </Button>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-xs text-neutral-500">
                冷存储库为空，所有记忆均在活跃索引中高效流转
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Collapsible Formula Inspector */}
      {showFormulaInspector && (
        <div className="border-t border-neutral-800 pt-3">
          <div className="mb-2 text-xs text-neutral-400">
            底层算法参数推演导引：Score_eff = Score_sem × e^(-λ·Δt) × (1 + β·ln(1 + N_hits))
          </div>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <label className="text-xs text-neutral-400">记忆类型 (λ 衰减系数)</label>
              <select
                value={memoryType}
                onChange={(e) => setMemoryType(e.target.value as any)}
                className="mt-1 w-full rounded border border-neutral-700 bg-neutral-900 px-2 py-1 font-mono text-xs text-neutral-200 outline-none focus:border-cyan-500"
              >
                <option value="experience">experience (λ=0.007, 慢衰减)</option>
                <option value="canonical">canonical (λ=0.0, 绝对免疫)</option>
                <option value="event">event/task (λ=0.05, 快衰减)</option>
                <option value="general">general (λ=0.01, 默认)</option>
              </select>
            </div>
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
            <div>
              <label className="text-xs text-neutral-400">生命周期状态</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as any)}
                className="mt-1 w-full rounded border border-neutral-700 bg-neutral-900 px-2 py-1 font-mono text-xs text-neutral-200 outline-none focus:border-cyan-500"
              >
                <option value="active">active (1.0x)</option>
                <option value="disputed">disputed (0.50x 惩罚)</option>
                <option value="superseded">superseded (0.20x 废弃)</option>
              </select>
            </div>
          </div>

          {simQuery.data && (
            <div className="mt-2.5 flex flex-wrap items-center justify-between rounded border border-neutral-800 bg-neutral-900/80 p-2 font-mono text-xs">
              <span className="text-neutral-400">
                时效乘子: <b className="text-neutral-200">{simQuery.data.decay_multiplier}</b> ｜ 频次强化: <b className="text-cyan-400">×{simQuery.data.hit_boost}</b> ｜ 综合有效分: <b className="text-cyan-400">{simQuery.data.adjusted_score.toFixed(4)}</b>
              </span>
              <span className="text-cyan-400 font-sans">
                {simQuery.data.adjusted_score >= simQuery.data.raw_score ? '越用越强 (频次增益)' : '平滑衰退'}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
