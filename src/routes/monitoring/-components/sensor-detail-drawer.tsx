/* eslint-disable i18next/no-literal-string */
// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import {
  ActivityIcon,
  SlidersIcon,
  UserCheckIcon,
  ClockIcon,
  TerminalIcon,
  CopyIcon,
  CheckIcon,
  LayersIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { ovClient } from '#/lib/ov-client'

export interface SensorSessionDetail {
  session_id: string
  token_snr: number
  p5_precision: number
  human_intervention_flag: boolean
  effective_tokens: number
  total_tokens: number
  overhead_tokens: number
  top5_hits: number
  interventions_count: number
  timestamp: number
  snr_formula?: string
  p5_formula?: string
  snr_status?: string
  p5_status?: string
  intervention_status?: string
}

interface SensorDetailDrawerProps {
  session: SensorSessionDetail | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SensorDetailDrawer({
  session,
  open,
  onOpenChange,
}: SensorDetailDrawerProps) {
  const [copied, setCopied] = React.useState(false)
  const [detail, setDetail] = React.useState<SensorSessionDetail | null>(null)

  React.useEffect(() => {
    if (!open || !session) {
      setDetail(null)
      return
    }
    setDetail(session)
    ovClient.instance
      .get<{ status: string; data: SensorSessionDetail }>(
        `/api/v1/metrics/agent-sensors/sessions/${encodeURIComponent(session.session_id)}`,
      )
      .then((res) => {
        if (res.data.status === 'success') {
          setDetail(res.data.data)
        }
      })
      .catch(() => {})
  }, [open, session])

  if (!session) return null

  const d = detail || session
  const formattedDate = d.timestamp
    ? new Date(d.timestamp * 1000).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '--'

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(d, null, 2))
    setCopied(true)
    toast.success('会话探针物理原始 JSON 已复制')
    setTimeout(() => setCopied(false), 2000)
  }

  const snrPct = Math.round(d.token_snr * 100)
  const p5Pct = Math.round(d.p5_precision * 100)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md md:max-w-lg overflow-y-auto bg-background/95 backdrop-blur-md border-l border-border/60 p-5 space-y-4 text-xs text-muted-foreground"
      >
        <SheetHeader className="space-y-1 pb-3 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1 rounded bg-cyan-500/10 text-cyan-500">
                <TerminalIcon className="size-4" />
              </div>
              <SheetTitle className="text-xs font-bold tracking-tight text-foreground font-mono">
                {d.session_id}
              </SheetTitle>
            </div>
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-2 py-1 rounded border border-border/50 bg-secondary/50 hover:bg-secondary text-[12px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              {copied ? <CheckIcon className="size-3 text-cyan-500" /> : <CopyIcon className="size-3" />}
              <span>{copied ? '已复制' : '复制 JSON'}</span>
            </button>
          </div>
          <SheetDescription className="text-[12px] text-muted-foreground flex items-center gap-1.5">
            <ClockIcon className="size-3" />
            <span>采样落盘时间: {formattedDate}</span>
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-3">
          <h4 className="text-[12px] font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
            <LayersIcon className="size-3.5 text-cyan-500" />
            三维效能物理白盒拆解 (Whitebox Deconstruction)
          </h4>

          {/* 1. Token SNR Card */}
          <div className="rounded-md border border-border/40 bg-card/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
                <ActivityIcon className="size-3.5 text-cyan-500" />
                Token SNR 有效载荷信噪比
              </span>
              <span className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${d.token_snr >= 0.65 ? 'bg-cyan-500/10 text-cyan-500' : 'bg-muted text-muted-foreground'}`}>
                {d.token_snr >= 0.65 ? 'OPTIMAL' : 'DEGRADED'}
              </span>
            </div>
            <div className="flex items-baseline justify-between font-mono">
              <span className="text-lg font-bold text-foreground">{snrPct}%</span>
              <span className="text-[12px] text-muted-foreground">基线要求 ≥ 65%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-muted/40 overflow-hidden">
              <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${Math.min(100, Math.max(0, snrPct))}%` }} />
            </div>
            <div className="rounded bg-background/80 p-2.5 space-y-1 font-mono text-[12px] border border-border/30">
              <div className="flex justify-between">
                <span className="text-muted-foreground">计算公式:</span>
                <span className="text-cyan-500 font-semibold">
                  {d.snr_formula || `${d.effective_tokens.toLocaleString()} / ${d.total_tokens.toLocaleString()} = ${snrPct}%`}
                </span>
              </div>
              <div className="flex justify-between text-muted-foreground">
                <span>有效代码与指令:</span>
                <span className="text-foreground">{d.effective_tokens.toLocaleString()} tokens</span>
              </div>
              <div className="flex justify-between text-muted-foreground">
                <span>系统上下文冗余:</span>
                <span className="text-foreground">{d.overhead_tokens.toLocaleString()} tokens</span>
              </div>
            </div>
          </div>

          {/* 2. P@5 Precision Card */}
          <div className="rounded-md border border-border/40 bg-card/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
                <SlidersIcon className="size-3.5 text-cyan-500" />
                P@5 知识召回采纳精度
              </span>
              <span className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${d.p5_precision >= 0.8 ? 'bg-cyan-500/10 text-cyan-500' : 'bg-muted text-muted-foreground'}`}>
                {d.p5_precision >= 0.8 ? 'TARGET REACHED' : 'SUBOPTIMAL'}
              </span>
            </div>
            <div className="flex items-baseline justify-between font-mono">
              <span className="text-lg font-bold text-foreground">{p5Pct}%</span>
              <span className="text-[12px] text-muted-foreground">基线要求 ≥ 80%</span>
            </div>
            <div className="grid grid-cols-5 gap-1 pt-0.5">
              {[1, 2, 3, 4, 5].map((idx) => (
                <div
                  key={idx}
                  className={`h-2 rounded-xs transition-all ${idx <= d.top5_hits ? 'bg-cyan-500/80' : 'bg-muted/40'}`}
                  title={`Context Hit ${idx}: ${idx <= d.top5_hits ? '采纳' : '未引用'}`}
                />
              ))}
            </div>
            <div className="rounded bg-background/80 p-2.5 space-y-1 font-mono text-[12px] border border-border/30">
              <div className="flex justify-between">
                <span className="text-muted-foreground">采纳断言:</span>
                <span className="text-cyan-500 font-semibold">{d.p5_formula || `${d.top5_hits} / 5 = ${p5Pct}%`}</span>
              </div>
              <div className="flex justify-between text-muted-foreground">
                <span>Top-5 上下文引用数:</span>
                <span className="text-foreground">{d.top5_hits} / 5 个切片</span>
              </div>
            </div>
          </div>

          {/* 3. Human Intervention Card */}
          <div className="rounded-md border border-border/40 bg-card/50 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
                <UserCheckIcon className="size-3.5 text-cyan-500" />
                人工纠偏介入度量
              </span>
              <span className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${d.human_intervention_flag ? 'bg-rose-500/10 text-rose-500' : 'bg-cyan-500/10 text-cyan-500'}`}>
                {d.human_intervention_flag ? 'INTERRUPTED' : 'AUTONOMOUS'}
              </span>
            </div>
            <div className="flex items-baseline justify-between font-mono">
              <span className="text-lg font-bold text-foreground">{d.interventions_count} 次纠偏</span>
              <span className="text-[12px] text-muted-foreground">红线要求 ≤ 15% 会话</span>
            </div>
            <div className="text-[12px] text-muted-foreground leading-relaxed">
              {d.human_intervention_flag
                ? '检测到人类输入了修正或重试指令（如“不对/重做/报错/修改”），已记入纠偏事件。'
                : '会话全流程由智能体自主闭环交付，零人工转向与打断。'}
            </div>
          </div>
        </div>

        {/* Raw JSON Trace */}
        <pre className="rounded-md border border-border/30 bg-muted/20 p-2.5 font-mono text-[12px] overflow-x-auto leading-relaxed text-foreground/80 max-h-36">
          {JSON.stringify(d, null, 2)}
        </pre>
      </SheetContent>
    </Sheet>
  )
}
