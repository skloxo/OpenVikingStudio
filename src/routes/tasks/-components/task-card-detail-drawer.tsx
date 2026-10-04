// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { AlertCircleIcon, CheckCircle2Icon, CopyIcon, TagIcon, UserIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { ovClient } from '#/lib/ov-client'

export interface TaskCardRecord {
  card_id: string
  fingerprint: string
  title: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  module: string
  symptom: string
  initiator: string
  affected_agents: string[]
  occurrence_count: number
  root_cause_hypothesis?: string
  reproduce_steps?: string
  suggested_action?: string
  status: 'pending' | 'resolved'
  created_at: number
  last_seen_at: number
  resolved_at?: number
  resolution_metadata?: {
    resolution_tag: string
    commit_hash?: string
    summary?: string
  }
}

interface TaskCardDetailDrawerProps {
  card: TaskCardRecord | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onResolvedSuccess?: () => void
}

export function TaskCardDetailDrawer({
  card,
  open,
  onOpenChange,
  onResolvedSuccess,
}: TaskCardDetailDrawerProps) {
  const [tagInput, setTagInput] = React.useState('v1.7.3')
  const [summaryInput, setSummaryInput] = React.useState('')
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  if (!card) return null

  const isPending = card.status === 'pending'

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tagInput.trim()) {
      toast.error('请输入解决版本 Tag (例如 v1.7.3)')
      return
    }
    setIsSubmitting(true)
    try {
      await ovClient.instance.post(`/api/v1/task-cards/${card.card_id}/resolve`, {
        resolution_tag: tagInput.trim(),
        summary: summaryInput.trim(),
      })
      toast.success(`工单 ${card.card_id} 已成功归档至 ${tagInput.trim()}`)
      onOpenChange(false)
      onResolvedSuccess?.()
    } catch (err: any) {
      toast.error(`归档失败: ${err?.response?.data?.detail || err?.message || '未知错误'}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const copyToClipboard = (text: string, label: string) => {
    void navigator.clipboard.writeText(text)
    toast.success(`${label}已复制到剪贴板`)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col gap-4 overflow-y-auto sm:max-w-xl p-4 text-xs">
        <SheetHeader className="gap-1 border-b border-border/60 pb-3">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={
                card.priority === 'P0'
                  ? 'border-rose-500/40 bg-rose-500/10 text-rose-400 font-semibold'
                  : card.priority === 'P1'
                  ? 'border-amber-400/40 bg-amber-400/10 text-amber-400 font-semibold'
                  : 'border-border/60 bg-muted/30 text-muted-foreground'
              }
            >
              {card.priority}
            </Badge>
            <Badge
              variant="outline"
              className={
                isPending
                  ? 'border-amber-400/30 bg-amber-400/10 text-amber-400'
                  : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400'
              }
            >
              {isPending ? '待处理 (Pending)' : '已归档 (Resolved)'}
            </Badge>
            <span className="font-mono text-muted-foreground tabular-nums ml-auto">
              发生 {card.occurrence_count} 次
            </span>
          </div>
          <SheetTitle className="text-base font-semibold leading-snug tracking-tight text-foreground">
            {card.title}
          </SheetTitle>
          <SheetDescription className="font-mono text-xs text-muted-foreground flex items-center justify-between">
            <span>{card.card_id}</span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => copyToClipboard(card.card_id, '工单 ID ')}
            >
              <CopyIcon className="size-3" />
            </Button>
          </SheetDescription>
        </SheetHeader>

        {/* 核心元数据条目 */}
        <div className="grid grid-cols-2 gap-2 rounded-md bg-muted/20 p-2.5 border border-border/40">
          <div>
            <span className="text-muted-foreground">受影响模块: </span>
            <code className="text-foreground font-mono">{card.module}</code>
          </div>
          <div>
            <span className="text-muted-foreground">首发智能体: </span>
            <span className="text-foreground font-mono">{card.initiator}</span>
          </div>
          <div className="col-span-2 flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-muted-foreground">受波及智能体:</span>
            {card.affected_agents.map((agent) => (
              <Badge key={agent} variant="secondary" className="font-mono text-[12px] py-0 px-1.5">
                <UserIcon className="size-3 mr-1 opacity-70" />
                {agent}
              </Badge>
            ))}
          </div>
        </div>

        {/* 现象与日志 */}
        <div className="flex flex-col gap-1.5">
          <span className="font-semibold text-foreground flex items-center gap-1">
            <AlertCircleIcon className="size-3.5 text-rose-400" />
            物理现象与脱水堆栈:
          </span>
          <pre className="rounded-md bg-muted/40 p-2.5 font-mono text-[12px] leading-relaxed text-foreground whitespace-pre-wrap break-all border border-border/40 max-h-48 overflow-y-auto">
            {card.symptom}
          </pre>
        </div>

        {/* 根因推测与复现 */}
        {card.root_cause_hypothesis && (
          <div className="flex flex-col gap-1">
            <span className="font-medium text-muted-foreground">💡 根因推测:</span>
            <p className="rounded-md bg-muted/20 p-2 text-foreground text-[12px]">
              {card.root_cause_hypothesis}
            </p>
          </div>
        )}

        {card.reproduce_steps && (
          <div className="flex flex-col gap-1">
            <span className="font-medium text-muted-foreground">🧪 复现路径与上下文:</span>
            <pre className="rounded-md bg-muted/20 p-2 font-mono text-[12px] text-foreground whitespace-pre-wrap">
              {card.reproduce_steps}
            </pre>
          </div>
        )}

        {/* 解决归档信息或归档操作 */}
        {!isPending && card.resolution_metadata ? (
          <div className="rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-cyan-400 font-semibold">
              <CheckCircle2Icon className="size-4" />
              <span>已闭环解决</span>
              <Badge variant="outline" className="border-cyan-500/40 text-cyan-400 ml-auto font-mono">
                {card.resolution_metadata.resolution_tag}
              </Badge>
            </div>
            {card.resolution_metadata.summary && (
              <p className="text-muted-foreground text-[12px]">
                {card.resolution_metadata.summary}
              </p>
            )}
            {card.resolution_metadata.commit_hash && (
              <div className="font-mono text-muted-foreground text-[12px]">
                Commit: <code>{card.resolution_metadata.commit_hash}</code>
              </div>
            )}
          </div>
        ) : (
          <form onSubmit={handleResolve} className="rounded-md border border-border/60 bg-muted/10 p-3 flex flex-col gap-2.5 mt-auto">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <TagIcon className="size-3.5 text-cyan-400" />
              人工 / Master Agent 快速闭环归档:
            </span>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="交付版本 Tag (例如 v1.7.3)"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                className="h-8 rounded-md border border-border/60 bg-background px-2.5 text-xs text-foreground placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="解决说明或 Commit Hash (可选)"
                value={summaryInput}
                onChange={(e) => setSummaryInput(e.target.value)}
                className="h-8 rounded-md border border-border/60 bg-background px-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="w-full bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/40"
            >
              标记为已解决并归档
            </Button>
          </form>
        )}
      </SheetContent>
    </Sheet>
  )
}
