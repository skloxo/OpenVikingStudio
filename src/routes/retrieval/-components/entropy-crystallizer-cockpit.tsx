import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import {
  SparklesIcon,
  ShieldCheckIcon,
  ShieldAlertIcon,
  LayersIcon,
  FileCheckIcon,
  BanIcon,
} from 'lucide-react'
import { PRESET_SCENARIOS } from '../-constants/crystallizer-presets'

interface TriGateEvaluation {
  passed: boolean
  cluster_size: number
  cluster_size_passed: boolean
  avg_similarity: number
  similarity_passed: boolean
  cooling_hours: number
  cooling_passed: boolean
  rejection_reasons: string[]
}

interface FactCrystal {
  uri: string
  axiom: string
  context_bounds: {
    version_range: string
    source_uris: string[]
    evidence_hashes: string[]
    distilled_at: number
    distiller_id: string
  }
  negative_boundary: {
    deprecated_patterns: string[]
    forbidden_keywords: string[]
  }
  status: string
  created_at: number
}

interface DistillResponse {
  crystal: FactCrystal
  superseded_uris: string[]
  net_entropy_reduced: number
  evaluation: TriGateEvaluation
}

interface CrystallizerStats {
  total_crystals: number
  total_evaluated: number
  total_blocked: number
  total_net_entropy_reduced: number
  block_rate: number
}

export function EntropyCrystallizerCockpit() {
  const queryClient = useQueryClient()
  const [selectedScenarioId, setSelectedScenarioId] = React.useState('port_lessons_passed')
  const [evalResult, setEvalResult] = React.useState<TriGateEvaluation | null>(null)
  const [distillResult, setDistillResult] = React.useState<DistillResponse | null>(null)

  const activeScenario = React.useMemo(
    () => PRESET_SCENARIOS.find((s) => s.id === selectedScenarioId) ?? PRESET_SCENARIOS[0],
    [selectedScenarioId]
  )

  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['crystallizer-stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result: CrystallizerStats }>(
        '/api/v1/memory/crystallize/stats'
      )
      return res.data.result
    },
    staleTime: 15_000,
    refetchIntervalInBackground: false,
  })

  const { data: crystalsData, refetch: refetchCrystals } = useQuery({
    queryKey: ['crystallizer-crystals'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result: FactCrystal[] }>(
        '/api/v1/memory/crystallize/crystals'
      )
      return res.data.result
    },
    staleTime: 15_000,
    refetchIntervalInBackground: false,
  })

  const evalMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post<{ status: string; result: TriGateEvaluation }>(
        '/api/v1/memory/crystallize/evaluate',
        { fragments: activeScenario.fragments }
      )
      return res.data.result
    },
    onSuccess: (data) => {
      setEvalResult(data)
      setDistillResult(null)
      void refetchStats()
    },
  })

  const distillMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post<{ status: string; result: DistillResponse }>(
        '/api/v1/memory/crystallize/distill',
        {
          fragments: activeScenario.fragments,
          axiom: activeScenario.axiom,
          version_range: activeScenario.version_range,
          deprecated_patterns: activeScenario.deprecated_patterns,
          forbidden_keywords: activeScenario.forbidden_keywords,
        }
      )
      return res.data.result
    },
    onSuccess: (data) => {
      setDistillResult(data)
      setEvalResult(data.evaluation)
      void queryClient.invalidateQueries({ queryKey: ['crystallizer-stats'] })
      void queryClient.invalidateQueries({ queryKey: ['crystallizer-crystals'] })
      void refetchStats()
      void refetchCrystals()
    },
  })

  return (
    <div className="flex flex-col gap-4">
      {/* 4 大核心 KPI 瓦片 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="flex flex-col gap-1 rounded-md border border-border/60 bg-card p-3 shadow-none">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>已熔炼不可变事实</span>
            <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground">
            {statsData?.total_crystals ?? '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">晶体</span>
          </div>
          <div className="text-xs text-muted-foreground">SSOT 权威事实结晶节点</div>
        </div>

        <div className="flex flex-col gap-1 rounded-md border border-border/60 bg-card p-3 shadow-none">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>存量物理净减熵</span>
            <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-cyan-600 dark:text-cyan-400">
            {statsData?.total_net_entropy_reduced != null ? `+${statsData.total_net_entropy_reduced}` : '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">节点净减</span>
          </div>
          <div className="text-xs text-muted-foreground">碎片挂载 superseded 沉底</div>
        </div>

        <div className="flex flex-col gap-1 rounded-md border border-border/60 bg-card p-3 shadow-none">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>三门硬门禁拦截率</span>
            <ShieldAlertIcon className="size-3.5 text-amber-500" />
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground">
            {statsData?.block_rate != null ? `${(statsData.block_rate * 100).toFixed(0)}%` : '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">
              ({statsData?.total_blocked ?? 0}/{statsData?.total_evaluated ?? 0})
            </span>
          </div>
          <div className="text-xs text-muted-foreground">严防早熟与泛化假结晶</div>
        </div>

        <div className="flex flex-col gap-1 rounded-md border border-border/60 bg-card p-3 shadow-none">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>三门并联硬准则</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="font-mono text-xs font-semibold text-foreground pt-1">
            条数 ≥5 · 相似 &gt;0.75 · 冷却 ≥24h
          </div>
          <div className="text-xs text-muted-foreground">不可跨越的物理防御护栏</div>
        </div>
      </div>

      {/* 交互试验台与三门状态面板 */}
      <div className="rounded-md border border-border/60 bg-card p-3.5 flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2">
          <div>
            <h2 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              三门并联硬门禁验证与熔炼演练试验台
            </h2>
            <p className="text-xs text-muted-foreground">
              并联验证聚类统计显著性、语义余弦收敛度与时间冷却期，杜绝假减熵
            </p>
          </div>

          <div className="flex items-center gap-1.5">
            {PRESET_SCENARIOS.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  setSelectedScenarioId(s.id)
                  setEvalResult(null)
                  setDistillResult(null)
                }}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                  selectedScenarioId === s.id
                    ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-semibold border border-cyan-500/30'
                    : 'bg-muted/40 text-muted-foreground hover:text-foreground hover:bg-muted/60'
                }`}
              >
                {s.name}
              </button>
            ))}
          </div>
        </div>

        {/* 场景详情与候选碎片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="flex flex-col gap-2 rounded border border-border/40 bg-muted/20 p-2.5">
            <span className="text-xs font-semibold text-foreground">候选碎片集群 ({activeScenario.fragments.length}条)</span>
            <div className="flex flex-col gap-1.5 max-h-36 overflow-y-auto pr-1">
              {activeScenario.fragments.map((f) => (
                <div key={f.uri} className="rounded bg-background/80 p-1.5 border border-border/40 text-xs">
                  <div className="font-mono text-muted-foreground truncate">{f.uri.split('/').pop()}</div>
                  <div className="text-foreground truncate">{f.content}</div>
                </div>
              ))}
            </div>
          </div>

          {/* 三门状态指示条 */}
          <div className="flex flex-col gap-2 rounded border border-border/40 bg-muted/20 p-2.5">
            <span className="text-xs font-semibold text-foreground">三门并联门禁状态 (Tri-Gate)</span>
            <div className="flex flex-col gap-2 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Gate 1: 条数 (≥ 5条)</span>
                <span className={`font-mono px-1.5 py-0.5 rounded text-xs ${
                  evalResult ? (evalResult.cluster_size_passed ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400' : 'bg-amber-500/15 text-amber-500') : 'text-muted-foreground'
                }`}>
                  {evalResult ? `${evalResult.cluster_size}条 (${evalResult.cluster_size_passed ? '通过' : '拦截'})` : '待评估'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Gate 2: 相似度 (&gt; 0.75)</span>
                <span className={`font-mono px-1.5 py-0.5 rounded text-xs ${
                  evalResult ? (evalResult.similarity_passed ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400' : 'bg-amber-500/15 text-amber-500') : 'text-muted-foreground'
                }`}>
                  {evalResult ? `${evalResult.avg_similarity.toFixed(2)} (${evalResult.similarity_passed ? '通过' : '拦截'})` : '待评估'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Gate 3: 冷却期 (≥ 24h)</span>
                <span className={`font-mono px-1.5 py-0.5 rounded text-xs ${
                  evalResult ? (evalResult.cooling_passed ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400' : 'bg-amber-500/15 text-amber-500') : 'text-muted-foreground'
                }`}>
                  {evalResult ? `${evalResult.cooling_hours.toFixed(0)}h (${evalResult.cooling_passed ? '通过' : '拦截'})` : '待评估'}
                </span>
              </div>
            </div>

            <div className="mt-auto flex items-center gap-2 pt-2 border-t border-border/30">
              <button
                type="button"
                disabled={evalMutation.isPending}
                onClick={() => evalMutation.mutate()}
                className="flex-1 rounded bg-muted/60 px-2 py-1 text-xs font-medium text-foreground hover:bg-muted cursor-pointer transition-colors"
              >
                {evalMutation.isPending ? '评估中...' : '测试三门'}
              </button>
              <button
                type="button"
                disabled={distillMutation.isPending}
                onClick={() => distillMutation.mutate()}
                className="flex-1 rounded bg-cyan-600 dark:bg-cyan-500 px-2 py-1 text-xs font-medium text-white hover:bg-cyan-700 cursor-pointer transition-colors"
              >
                {distillMutation.isPending ? '熔炼中...' : '熔铸事实晶体'}
              </button>
            </div>
          </div>

          {/* 评估与熔炼输出面板 */}
          <div className="flex flex-col gap-2 rounded border border-border/40 bg-muted/20 p-2.5">
            <span className="text-xs font-semibold text-foreground">结晶结果与净减熵</span>
            {evalResult && !evalResult.passed && (
              <div className="flex flex-col gap-1.5 rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs">
                <span className="font-semibold text-amber-500 flex items-center gap-1">
                  <ShieldAlertIcon className="size-3.5" /> 三门门禁严格拦截
                </span>
                <ul className="list-disc pl-4 text-muted-foreground space-y-0.5">
                  {evalResult.rejection_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {distillResult && (
              <div className="flex flex-col gap-1.5 rounded border border-cyan-500/30 bg-cyan-500/10 p-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
                    <SparklesIcon className="size-3.5" /> 晶体熔炼成功
                  </span>
                  <span className="font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400">
                    +{distillResult.net_entropy_reduced} 节点物理净减
                  </span>
                </div>
                <div className="text-xs text-foreground font-semibold">L0 公理: {distillResult.crystal.axiom}</div>
                <div className="text-xs text-muted-foreground">
                  L1 版本: {distillResult.crystal.context_bounds.version_range} · 原 {distillResult.superseded_uris.length} 条碎片全部标记 superseded
                </div>
                {distillResult.crystal.negative_boundary.deprecated_patterns.length > 0 && (
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    <BanIcon className="size-3 text-muted-foreground" /> L2 排斥: {distillResult.crystal.negative_boundary.deprecated_patterns.join(', ')}
                  </div>
                )}
              </div>
            )}

            {!evalResult && !distillResult && (
              <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                点击「测试三门」或「熔铸事实晶体」运行实操演练
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 已熔炼事实晶体知识库 (SSOT Fact Crystals) */}
      <div className="rounded-md border border-border/60 bg-card p-3.5 flex flex-col gap-2.5">
        <div className="flex items-center justify-between border-b border-border/50 pb-2">
          <div>
            <h2 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <FileCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              不可变事实晶体库 (SSOT Fact Crystals)
            </h2>
            <p className="text-xs text-muted-foreground">
              高纯度 L0 公理、L1 版本与证据链、L2 负向排斥哨兵的三层晶体集合
            </p>
          </div>
          <span className="text-xs font-mono text-muted-foreground">
            总计 {crystalsData?.length ?? 0} 个有效晶体
          </span>
        </div>

        <div className="flex flex-col gap-2">
          {crystalsData && crystalsData.length > 0 ? (
            crystalsData.map((c) => (
              <div key={c.uri} className="rounded border border-border/40 bg-muted/10 p-3 flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <SparklesIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
                    {c.axiom}
                  </span>
                  <span className="rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 px-1.5 py-0.5 text-xs font-mono">
                    {c.context_bounds.version_range}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground font-mono">
                  <span>URI: {c.uri}</span>
                  <span>来源碎片: {c.context_bounds.source_uris.length}条</span>
                  <span>熔炼者: {c.context_bounds.distiller_id}</span>
                </div>

                {c.negative_boundary.deprecated_patterns.length > 0 && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground pt-1 border-t border-border/30">
                    <BanIcon className="size-3 text-amber-500" />
                    <span>L2 负向排斥哨兵: {c.negative_boundary.deprecated_patterns.join(' | ')}</span>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="py-6 text-center text-xs text-muted-foreground">
              暂无已熔炼事实晶体。在上方试验台点击「熔铸事实晶体」即可完成首次不可变事实提纯。
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
