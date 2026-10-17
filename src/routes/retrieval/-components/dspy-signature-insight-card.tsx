// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { Layers } from 'lucide-react'
import type { DSPyCompileResult } from '../-types/dspy-compiler'

interface DSPySignatureInsightCardProps {
  result: DSPyCompileResult
}

export function DSPySignatureInsightCard({ result }: DSPySignatureInsightCardProps) {
  return (
    <div className="p-3.5 bg-card border border-border/70 rounded-md space-y-2">
      <div className="flex items-center justify-between text-xs font-semibold text-foreground">
        <span className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-cyan-500" />
          强类型签名与样本洞察 ({result.signature.name})
        </span>
        <span className="text-muted-foreground font-mono text-xs">
          输入: {result.signature.input_fields.length} ｜ 输出: {result.signature.output_fields.length} ｜ Few-Shot: {result.selected_few_shot.length}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div className="bg-muted/10 border border-border/40 rounded p-2.5">
          <div className="text-muted-foreground font-mono text-xs mb-1">输入/输出类型契约:</div>
          <div className="space-y-1 font-mono text-xs">
            {result.signature.input_fields.map((f) => (
              <div key={f.name} className="flex items-center gap-1 text-foreground">
                <span className="text-cyan-500">IN</span>
                <span className="font-semibold">{f.name}</span>:
                <span className="text-muted-foreground">{f.field_type}</span>
              </div>
            ))}
            {result.signature.output_fields.map((f) => (
              <div key={f.name} className="flex items-center gap-1 text-foreground">
                <span className="text-cyan-500">OUT</span>
                <span className="font-semibold">{f.name}</span>:
                <span className="text-muted-foreground">{f.field_type}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-muted/10 border border-border/40 rounded p-2.5">
          <div className="text-muted-foreground font-mono text-xs mb-1">精选注入的 Bootstrap 样本:</div>
          {result.selected_few_shot.length > 0 ? (
            <div className="space-y-1 text-xs">
              {result.selected_few_shot.map((ex) => (
                <div key={ex.example_id} className="flex items-center justify-between">
                  <span className="font-mono text-foreground">{ex.example_id}</span>
                  <span className="text-cyan-500 font-mono">
                    得分: {ex.quality_score.toFixed(2)} ({ex.source})
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-muted-foreground text-xs">当前为 Zero-Shot 纯规约模式</div>
          )}
        </div>
      </div>
    </div>
  )
}
