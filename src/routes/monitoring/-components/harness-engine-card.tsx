import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { CpuIcon, SparklesIcon } from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

export interface HarnessEngineCardProps {
  status?: string
  isHealthy?: boolean
}

export function HarnessEngineCard({ isHealthy = true }: HarnessEngineCardProps) {
  const harnessQuery = useQuery({
    queryKey: ['harness-engine-card-metrics'],
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          compression_retention_rate?: number
          llmlingua?: {
            token_retention_rate?: number
            target_range?: string
            ast_gate_rate?: number
            status?: string
          }
          dspy?: {
            compilation_accuracy?: number
            target_threshold?: string
            ast_gate_rate?: number
            status?: string
          }
        }>('/api/v1/system/harness_metrics')
        return res.data
      } catch {
        return null
      }
    },
    staleTime: 30_000,
  })

  const data = harnessQuery.data
  const llmRetention = data?.llmlingua?.token_retention_rate ?? data?.compression_retention_rate
  const llmAst = data?.llmlingua?.ast_gate_rate
  const dspyAst = data?.dspy?.ast_gate_rate
  const dspyAccuracy = data?.dspy?.compilation_accuracy

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-cyan-500/30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <SparklesIcon className="size-4 text-cyan-500" />
            🛡️ Harness 技能自演进引擎与第三方组件监控
          </CardTitle>
        </div>
        <Badge
          variant="outline"
          className="gap-1 font-mono text-[11px] border-cyan-500/40 bg-cyan-500/10 text-cyan-500"
        >
          <span className="size-1.5 rounded-full bg-cyan-500 animate-pulse" />
          {isHealthy ? '组件熔融就位' : '组件降级'}
        </Badge>
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
            <span className="text-[11px] text-muted-foreground truncate">
              微软 Token 抽稀探针 · 目标区间 45%-55%
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
              {llmRetention !== undefined ? `${llmRetention}%` : '--'}
            </span>
            <span className="text-[11px] text-muted-foreground font-sans">(安全 45-55%)</span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
              {llmAst !== undefined ? `${llmAst}%` : '--'}
            </span>
            <span className="text-[11px] text-cyan-600 dark:text-cyan-400 font-sans font-semibold">
              {llmAst !== undefined ? '(100% 锁定)' : '--'}
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="text-muted-foreground tabular-nums">N/A</span>
            <span className="text-[11px] text-muted-foreground font-sans">(N/A N-Gram)</span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-muted-foreground tabular-nums">--</span>
            <span className="text-[11px] text-muted-foreground font-sans">(&lt;500MB / &lt;10ms)</span>
          </div>
        </div>

        {/* 2. 斯坦福 DSPy 物理卡片 */}
        <div className="grid grid-cols-6 items-center px-3 py-2.5 text-xs rounded-md bg-cyan-500/5 border border-cyan-500/20 font-mono">
          <div className="col-span-2 flex flex-col gap-0.5 min-w-0">
            <span className="font-sans font-medium text-foreground truncate flex items-center gap-1.5">
              <SparklesIcon className="size-3.5 text-cyan-500 shrink-0" />
              Stanford DSPy (MIPO Compiler)
            </span>
            <span className="text-[11px] text-muted-foreground truncate">
              斯坦福 SOP 编译探针 · 零假 API 规约
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="text-muted-foreground tabular-nums">N/A</span>
            <span className="text-[11px] text-muted-foreground font-sans">(N/A RawToken)</span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
              {dspyAst !== undefined ? `${dspyAst}%` : '--'}
            </span>
            <span className="text-[11px] text-cyan-600 dark:text-cyan-400 font-sans font-semibold">
              {dspyAst !== undefined ? '(100% 锁定)' : '--'}
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums">
              {dspyAccuracy !== undefined ? `${dspyAccuracy}%` : '--'}
            </span>
            <span className="text-[11px] text-cyan-600 dark:text-cyan-400 font-sans font-semibold">
              {dspyAccuracy !== undefined ? '(安全 >95%)' : '--'}
            </span>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="font-semibold text-muted-foreground tabular-nums">--</span>
            <span className="text-[11px] text-muted-foreground font-sans">(&lt;500MB / &lt;10ms)</span>
          </div>
        </div>
      </div>
    </Card>
  )
}
