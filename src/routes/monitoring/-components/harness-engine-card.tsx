import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { CpuIcon, SparklesIcon } from 'lucide-react'

export interface HarnessEngineCardProps {
  status?: string
  isHealthy?: boolean
}

export function HarnessEngineCard({ isHealthy = true }: HarnessEngineCardProps) {
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

      {/* 专用表头 */}
      <div className="flex flex-col gap-2">
        <div className="grid grid-cols-6 items-center px-3 py-1.5 text-xs text-muted-foreground font-medium border-b border-border/50 font-mono">
          <span className="col-span-2">开源组件/轮子名称</span>
          <span>服务归属层</span>
          <span className="text-right">核心调优指标</span>
          <span className="text-right">物理门禁标准</span>
          <span className="text-right">探针状态</span>
        </div>

        {/* 1. 微软 LLMLingua-2 物理卡片 */}
        <div className="grid grid-cols-6 items-center px-3 py-2 text-xs rounded-md bg-cyan-500/5 border border-cyan-500/20 font-mono">
          <div className="col-span-2 flex flex-col gap-0.5 min-w-0">
            <span className="font-sans font-medium text-foreground truncate flex items-center gap-1.5">
              <CpuIcon className="size-3.5 text-cyan-500 shrink-0" />
              LLMLingua-2 (xlm-roberta)
            </span>
            <span className="text-[10px] text-muted-foreground truncate">
              微软 Token 抽稀与 AST 物理门禁
            </span>
          </div>
          <span className="text-cyan-600 dark:text-cyan-400 text-[11px] font-sans font-bold">
            harness.engine
          </span>
          <span className="text-right text-muted-foreground tabular-nums text-[11px]">
            rate=0.50 / threshold=0.35
          </span>
          <span className="text-right text-cyan-600 dark:text-cyan-400 font-bold tabular-nums">
            AST 语法锁定
          </span>
          <span className="text-right text-muted-foreground font-bold tabular-nums">
            --
          </span>
        </div>

        {/* 2. 斯坦福 DSPy 物理卡片 */}
        <div className="grid grid-cols-6 items-center px-3 py-2 text-xs rounded-md bg-cyan-500/5 border border-cyan-500/20 font-mono">
          <div className="col-span-2 flex flex-col gap-0.5 min-w-0">
            <span className="font-sans font-medium text-foreground truncate flex items-center gap-1.5">
              <SparklesIcon className="size-3.5 text-cyan-500 shrink-0" />
              Stanford DSPy (MIPO Compiler)
            </span>
            <span className="text-[10px] text-muted-foreground truncate">
              斯坦福 SOP 编译与自动消歧
            </span>
          </div>
          <span className="text-cyan-600 dark:text-cyan-400 text-[11px] font-sans font-bold">
            harness.engine
          </span>
          <span className="text-right text-muted-foreground tabular-nums text-[11px]">
            FewShot N=3 / Precision
          </span>
          <span className="text-right text-cyan-600 dark:text-cyan-400 font-bold tabular-nums">
            零假 API 锁定
          </span>
          <span className="text-right text-muted-foreground font-bold tabular-nums">
            --
          </span>
        </div>
      </div>
    </Card>
  )
}
