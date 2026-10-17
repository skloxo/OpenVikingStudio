// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { CpuIcon, ScissorsIcon, ShieldCheckIcon, SparklesIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { TokenShiftResult, TokenShiftStats } from '../-types/tokenshift'

interface TokenShiftKpiTilesProps {
  result?: TokenShiftResult | null
  stats?: TokenShiftStats | null
}

export function TokenShiftKpiTiles({ result, stats }: TokenShiftKpiTilesProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card className="p-3.5 bg-card/60 border-border/70">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
          <span>原始 Token 预算</span>
          <CpuIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="text-xl font-mono font-semibold tabular-nums text-foreground">
          {result
            ? result.original_tokens_est
            : stats?.total_original_tokens
              ? `${stats.total_original_tokens} (累计)`
              : '--'}
          <span className="text-xs text-muted-foreground font-normal ml-1">tokens</span>
        </div>
        <div className="text-xs text-muted-foreground font-mono mt-1">
          行数: {result ? result.original_lines : '--'} 行
        </div>
      </Card>

      <Card className="p-3.5 bg-card/60 border-border/70">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
          <span>压缩后 Token</span>
          <ScissorsIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="text-xl font-mono font-semibold tabular-nums text-cyan-600 dark:text-cyan-400">
          {result
            ? result.compressed_tokens_est
            : stats?.total_compressed_tokens
              ? `${stats.total_compressed_tokens} (累计)`
              : '--'}
          <span className="text-xs text-muted-foreground font-normal ml-1">tokens</span>
        </div>
        <div className="text-xs text-muted-foreground font-mono mt-1">
          行数: {result ? result.compressed_lines : '--'} 行
        </div>
      </Card>

      <Card className="p-3.5 bg-card/60 border-border/70">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
          <span>Token 压缩节省率</span>
          <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="text-xl font-mono font-semibold tabular-nums text-foreground">
          {result
            ? `${(result.reduction_ratio * 100).toFixed(1)}%`
            : stats?.average_reduction_ratio
              ? `${(stats.average_reduction_ratio * 100).toFixed(1)}%`
              : '--%'}
        </div>
        <div className="text-xs text-muted-foreground font-mono mt-1">
          耗时: {result ? `${result.elapsed_ms}ms` : '--'}
        </div>
      </Card>

      <Card className="p-3.5 bg-card/60 border-border/70">
        <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
          <span>AST 语法树校验</span>
          <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          {result ? (
            result.syntax_validation.valid ? (
              <Badge className="bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800/40 text-xs px-2 py-0.5 font-mono">
                PASS 100% 合法
              </Badge>
            ) : (
              <Badge className="bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800/40 text-xs px-2 py-0.5 font-mono">
                FAIL 语法异常
              </Badge>
            )
          ) : (
            <span className="text-xl font-mono font-semibold text-muted-foreground">
              {stats?.syntax_pass_rate ? `${(stats.syntax_pass_rate * 100).toFixed(0)}% 通过` : '--'}
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground font-mono mt-1.5">
          解析器: {result ? result.syntax_validation.parser : '--'}
        </div>
      </Card>
    </div>
  )
}
