// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { Binary, CheckCircle2, Database, ShieldCheck, Zap } from 'lucide-react'
import type { DSPyCompileResult, DSPyCompilerStats } from '../-types/dspy-compiler'

interface DSPyKpiTilesProps {
  result?: DSPyCompileResult | null
  stats?: DSPyCompilerStats | null
}

export function DSPyKpiTiles({ result, stats }: DSPyKpiTilesProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div className="p-3.5 bg-card border border-border/70 rounded-md">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
          <span>ORIGINAL TOKENS</span>
          <Database className="w-3.5 h-3.5 text-muted-foreground" />
        </div>
        <div className="text-xl font-bold font-mono text-foreground mt-1 tabular-nums">
          {result ? result.original_token_count : '--'}
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">原始松散提示词估算</div>
      </div>

      <div className="p-3.5 bg-card border border-border/70 rounded-md">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
          <span>COMPILED TOKENS</span>
          <Zap className="w-3.5 h-3.5 text-cyan-500" />
        </div>
        <div className="text-xl font-bold font-mono text-cyan-500 mt-1 tabular-nums">
          {result ? result.compiled_token_count : '--'}
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {result ? `Token 比率: ${(result.compression_ratio * 100).toFixed(1)}%` : '强类型规约合成'}
        </div>
      </div>

      <div className="p-3.5 bg-card border border-border/70 rounded-md">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
          <span>CONTRACT STATUS</span>
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-500" />
        </div>
        <div className="text-xl font-bold font-mono mt-1 flex items-center gap-1.5">
          {result ? (
            <span className="text-cyan-500 flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" /> {result.contract_status}
            </span>
          ) : (
            <span className="text-muted-foreground">READY</span>
          )}
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {result?.anti_hallucination_injected ? '零幻觉护栏已激活' : 'Schema 强类型门禁'}
        </div>
      </div>

      <div className="p-3.5 bg-card border border-border/70 rounded-md">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
          <span>LATENCY & CALLS</span>
          <Binary className="w-3.5 h-3.5 text-cyan-500" />
        </div>
        <div className="text-xl font-bold font-mono text-foreground mt-1 tabular-nums">
          {result ? `${result.elapsed_ms}ms` : stats ? `${stats.average_latency_ms}ms` : '--'}
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          累计编译: {stats ? stats.total_compilations : 0} 次
        </div>
      </div>
    </div>
  )
}
