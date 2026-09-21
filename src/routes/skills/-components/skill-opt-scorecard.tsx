import * as React from 'react'
import { ShieldCheckIcon, AlertTriangleIcon, FileTextIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { SkillOptAuditResult } from './skill-opt-types'

interface SkillOptScorecardProps {
  audit: SkillOptAuditResult | null
  isLoading?: boolean
}

export function SkillOptScorecard({ audit, isLoading }: SkillOptScorecardProps) {
  if (isLoading) {
    return (
      <Card className="p-3.5 border-border/60 bg-muted/10">
        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
          <span className="size-2 rounded-full bg-cyan-400 animate-ping" />
          正在执行四维质量门禁深度体检...
        </div>
      </Card>
    )
  }

  if (!audit) {
    return (
      <Card className="p-4 border-border/60 bg-muted/10 text-center">
        <p className="text-xs text-muted-foreground font-mono">
          👈 在左侧选择或输入技能文本，点击「执行 SkillOpt 体检」查看评测报告。
        </p>
      </Card>
    )
  }

  const gradeColor = {
    S: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
    A: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    B: 'bg-muted/40 text-foreground border-border',
    C: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
    D: 'bg-rose-500/15 text-rose-400 border-rose-500/40',
  }[audit.grade] || 'bg-muted/30 text-muted-foreground'

  return (
    <Card className="p-3.5 border-border/60 bg-card/60 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-2.5">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="size-4 text-cyan-400" />
          <span className="text-xs font-semibold tracking-tight">{audit.skill_name}</span>
          <Badge variant="outline" className={`text-xs font-mono font-bold px-1.5 py-0.5 border ${gradeColor}`}>
            Grade {audit.grade}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono">综合质量分:</span>
          <span className="text-lg font-bold font-mono tabular-nums text-cyan-400">{audit.total_score}</span>
          <span className="text-xs text-muted-foreground font-mono">/ 100</span>
        </div>
      </div>

      {/* 4 Dimension Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {audit.dimensions.map((dim) => {
          const pct = Math.round((dim.score / dim.max_score) * 100)
          const barColor = dim.status === 'good' ? 'bg-cyan-500' : dim.status === 'warning' ? 'bg-amber-500' : 'bg-rose-500'
          const textColor = dim.status === 'good' ? 'text-cyan-400' : dim.status === 'warning' ? 'text-amber-400' : 'text-rose-400'

          return (
            <div key={dim.name} className="p-2.5 rounded-md border border-border/40 bg-muted/20 flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-foreground/90 font-medium">{dim.label}</span>
                <span className={`font-bold tabular-nums ${textColor}`}>
                  {dim.score} / {dim.max_score}
                </span>
              </div>
              <div className="w-full bg-muted/40 h-1.5 rounded-full overflow-hidden">
                <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
              </div>
              <ul className="mt-0.5 text-xs font-mono text-muted-foreground space-y-0.5">
                {dim.details.slice(0, 2).map((det, i) => (
                  <li key={i} className="truncate">
                    {det}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>

      {/* Line Count & Status */}
      <div className="flex items-center justify-between text-xs font-mono px-2 py-1.5 rounded bg-muted/20 border border-border/30">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <FileTextIcon className="size-3 text-cyan-400" />
          <span>文件行数: <strong className="text-foreground tabular-nums">{audit.line_count} 行</strong></span>
        </div>
        <Badge
          variant="outline"
          className={`text-xs font-mono px-1.5 py-0.5 ${
            audit.line_count >= 100 && audit.line_count <= 300
              ? 'border-cyan-500/40 text-cyan-400 bg-cyan-500/10'
              : audit.line_count <= 400
              ? 'border-border text-muted-foreground'
              : 'border-rose-500/40 text-rose-400 bg-rose-500/10'
          }`}
        >
          {audit.line_count >= 100 && audit.line_count <= 300
            ? '🎯 黄金甜点区 (100~300行)'
            : audit.line_count <= 400
            ? '可用行数 (301~400行)'
            : audit.line_count <= 500
            ? '接近硬上限 (401~500行)'
            : '🚫 超出 500 行物理红线'}
        </Badge>
      </div>

      {/* Suggestions Checklist */}
      {audit.suggestions.length > 0 && (
        <div className="p-2.5 rounded-md border border-amber-500/30 bg-amber-500/5 flex flex-col gap-1.5">
          <div className="flex items-center gap-1.5 text-xs font-mono font-medium text-amber-400">
            <AlertTriangleIcon className="size-3.5" />
            <span>门禁诊断与改进建议 ({audit.suggestions.length})</span>
          </div>
          <ul className="text-xs font-mono text-muted-foreground space-y-1">
            {audit.suggestions.map((sug, i) => (
              <li key={i} className="flex items-start gap-1">
                <span className="text-amber-500 font-bold">•</span>
                <span>{sug}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}
