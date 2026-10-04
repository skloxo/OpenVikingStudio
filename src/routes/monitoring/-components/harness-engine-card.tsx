import { useMutation, useQuery } from '@tanstack/react-query'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { CpuIcon, FlaskConicalIcon, SparklesIcon, ZapIcon } from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

export interface HarnessEngineCardProps {
  status?: string
  isHealthy?: boolean
}

interface HarnessMetricsResponse {
  compression_retention_rate?: number
  llmlingua?: {
    token_retention_rate?: number | null
    target_range?: string
    ast_gate_rate?: number | null
    avg_latency_ms?: number
    total_documents?: number
    total_tokens_saved?: number
    active_engine?: string
    is_model_loaded?: boolean
    circuit_breaker_open?: boolean
    status?: string
  }
  dspy?: {
    compilation_accuracy?: number | null
    target_threshold?: string
    ast_gate_rate?: number | null
    avg_latency_ms?: number
    total_compilations?: number
    pass_contract_count?: number
    active_engine?: string
    status?: string
  }
}

export function HarnessEngineCard({ isHealthy = true }: HarnessEngineCardProps) {
  const harnessQuery = useQuery({
    queryKey: ['harness-engine-card-metrics'],
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<HarnessMetricsResponse>(
          '/api/v1/system/harness_metrics',
        )
        return res.data
      } catch {
        return null
      }
    },
    staleTime: 30_000,
  })

  const probeMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/system/harness/probe')
      return res.data
    },
    onSuccess: () => {
      void harnessQuery.refetch()
    },
  })

  const data = harnessQuery.data
  const llm = data?.llmlingua
  const dspy = data?.dspy

  const llmRetention = llm?.token_retention_rate ?? data?.compression_retention_rate
  const llmAst = llm?.ast_gate_rate
  const llmDocs = llm?.total_documents ?? 0
  const llmLatency = llm?.avg_latency_ms ?? 0
  const llmLoaded = llm?.is_model_loaded ?? false
  const llmEngine = llm?.active_engine ?? 'microsoft/llmlingua-2'

  const dspyAst = dspy?.ast_gate_rate
  const dspyAccuracy = dspy?.compilation_accuracy
  const dspyCompiles = dspy?.total_compilations ?? 0
  const dspyLatency = dspy?.avg_latency_ms ?? 0
  const dspyEngine = dspy?.active_engine ?? 'stanford/dspy-mipo'

  const overallReady = isHealthy && (llm?.status === 'ready' || llm?.status === 'healthy')

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-cyan-500/30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <SparklesIcon className="size-4 text-cyan-500" />
            🛡️ Harness 技能自演进引擎与第三方组件监控
          </CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => probeMutation.mutate()}
            disabled={probeMutation.isPending}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono font-medium rounded-md border border-cyan-500/30 bg-cyan-500/10 text-cyan-500 hover:bg-cyan-500/20 transition-colors disabled:opacity-50"
            title="执行底层 LLMLingua-2 与 DSPy 物理采样验真"
          >
            <FlaskConicalIcon className={`size-3 text-cyan-500 ${probeMutation.isPending ? 'animate-spin' : ''}`} />
            {probeMutation.isPending ? '验真中...' : '物理验真'}
          </button>
          <Badge
            variant="outline"
            className="gap-1 font-mono text-xs border-cyan-500/40 bg-cyan-500/10 text-cyan-500"
          >
            <span className="size-1.5 rounded-full bg-cyan-500 animate-pulse" />
            {overallReady ? '组件熔融就位' : '组件检测中'}
          </Badge>
        </div>
      </div>

      <p className="text-xs text-muted-foreground font-mono">
        展示物理集成于 OpenViking 同进程内的开源顶级轮子组件（微软 LLMLingua-2 与斯坦福 DSPy）的物理门禁与指标
      </p>

      {/* 专用 4 大核心关键物理指标表头 */}
      <div className="flex flex-col gap-2">
        <div className="grid grid-cols-6 items-center px-3 py-1.5 text-xs text-muted-foreground font-medium border-b border-border/50 font-mono">
          <span className="col-span-2">开源组件/轮子名称</span>
          <span className="text-right">① Token 抽稀留存率</span>
          <span className="text-right">② AST 门禁通过率</span>
          <span className="text-right">③ DSPy 编译准确度</span>
          <span className="text-right">④ GPU 显存与延迟</span>
        </div>

        {/* 1. 微软 LLMLingua-2 物理卡片 */}
        <div className="grid grid-cols-6 items-center px-3 py-2.5 text-xs rounded-md bg-cyan-500/5 border border-cyan-500/20 font-mono">
          <div className="col-span-2 flex flex-col gap-0.5 min-w-0">
            <span className="font-sans font-medium text-foreground truncate flex items-center gap-1.5">
              <CpuIcon className="size-3.5 text-cyan-500 shrink-0" />
              LLMLingua-2 (xlm-roberta)
            </span>
            <span className="text-xs text-muted-foreground truncate">
              微软 Token 抽稀探针 · 目标区间 45%-55%
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            {llmRetention != null ? (
              <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
                {llmRetention.toFixed(1)}%
              </span>
            ) : (
              <span className="font-sans text-xs text-muted-foreground tabular-nums">待抽稀</span>
            )}
            <span className="text-xs text-muted-foreground font-sans">
              ({llmDocs > 0 ? `${llmDocs} 篇` : '0 采样'} · 45-55%)
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
              {llmAst != null ? `${llmAst.toFixed(1)}%` : '--'}
            </span>
            <span className="text-xs text-cyan-600 dark:text-cyan-400 font-sans font-semibold">
              {llmAst != null ? '(100% 结构断言)' : '--'}
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="text-muted-foreground tabular-nums">N/A</span>
            <span className="text-xs text-muted-foreground font-sans">(N/A N-Gram)</span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-foreground tabular-nums flex items-center gap-1">
              <ZapIcon className="size-3 text-cyan-500" />
              {llmDocs > 0 ? `${llmLatency.toFixed(0)}ms` : llmLoaded ? '就绪 <200ms' : '--'}
            </span>
            <span className="text-xs text-muted-foreground font-sans truncate max-w-32.5" title={llmEngine}>
              {llmEngine.includes('CUDA') ? 'CUDA FP16 · 2080Ti' : 'CPU 降级'}
            </span>
          </div>
        </div>

        {/* 2. 斯坦福 DSPy 物理卡片 */}
        <div className="grid grid-cols-6 items-center px-3 py-2.5 text-xs rounded-md bg-cyan-500/5 border border-cyan-500/20 font-mono">
          <div className="col-span-2 flex flex-col gap-0.5 min-w-0">
            <span className="font-sans font-medium text-foreground truncate flex items-center gap-1.5">
              <SparklesIcon className="size-3.5 text-cyan-500 shrink-0" />
              Stanford DSPy (MIPO Compiler)
            </span>
            <span className="text-xs text-muted-foreground truncate">
              斯坦福 SOP 编译探针 · 零假 API 规约
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="text-muted-foreground tabular-nums">N/A</span>
            <span className="text-xs text-muted-foreground font-sans">(N/A RawToken)</span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
              {dspyAst != null ? `${dspyAst.toFixed(1)}%` : '--'}
            </span>
            <span className="text-xs text-cyan-600 dark:text-cyan-400 font-sans font-semibold">
              {dspyAst != null ? '(100% 规约锁定)' : '--'}
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            {dspyAccuracy != null ? (
              <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
                {dspyAccuracy.toFixed(1)}%
              </span>
            ) : (
              <span className="font-sans text-xs text-muted-foreground tabular-nums">待编译</span>
            )}
            <span className="text-xs text-muted-foreground font-sans">
              ({dspyCompiles > 0 ? `${dspyCompiles} 次` : '0 采样'} · 门禁锁定)
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-foreground tabular-nums flex items-center gap-1">
              <ZapIcon className="size-3 text-cyan-500" />
              {dspyCompiles > 0 ? `${dspyLatency.toFixed(0)}ms` : '就绪 <10ms'}
            </span>
            <span className="text-xs text-muted-foreground font-sans truncate max-w-32.5" title={dspyEngine}>
              In-Process · 内存级
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}
