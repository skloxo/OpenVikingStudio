// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArchiveRestoreIcon,
  ClockIcon,
  FastForwardIcon,
  HistoryIcon,
  InboxIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'

interface IngestionRecord {
  receipt_id: string
  skill_name: string
  raw_content: string
  author: string
  status: 'PENDING' | 'VALIDATING' | 'STAGED' | 'REJECTED' | 'COMMITTED' | 'ERROR'
  status_message: string
  validation_report?: {
    is_valid: boolean
    line_count: number
    latency_ms: number
    routing?: { action: string; target_package: string; top1_score: number; margin: number }
  }
  created_at: number
  updated_at: number
}

interface ProvenanceEvent {
  event_id: string
  timestamp: number
  action: 'INGEST' | 'VALIDATE' | 'ROUTE' | 'MERGE' | 'ROLLBACK'
  skill_name: string
  version: string
  receipt_id: string
  operator: string
  details: Record<string, any>
  snapshot_path?: string
}

export function SkillIngestionCockpit() {
  const queryClient = useQueryClient()
  const [selectedRecord, setSelectedRecord] = React.useState<IngestionRecord | null>(null)

  const { data: queueData, isLoading: queueLoading, refetch: refetchQueue } = useQuery({
    queryKey: ['skills-ingestion-queue'],
    queryFn: async () => (await ovClient.instance.get<{ status: string; queue_depth: any; recent_records: IngestionRecord[] }>('/api/v1/skills/ingestion/queue?limit=25')).data,
    refetchInterval: 10000,
  })

  const { data: provData, isLoading: provLoading, refetch: refetchProv } = useQuery({
    queryKey: ['skills-provenance-events'],
    queryFn: async () => (await ovClient.instance.get<{ status: string; events: ProvenanceEvent[] }>('/api/v1/skills/ingestion/provenance?limit=20')).data,
    refetchInterval: 15000,
  })

  const processBatchMutation = useMutation({
    mutationFn: async () => await ovClient.instance.post('/api/v1/skills/ingestion/process-batch?batch_size=5', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue'] })
      queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] })
    },
  })

  const rollbackMutation = useMutation({
    mutationFn: async ({ snapshotPath, targetPath }: { snapshotPath: string; targetPath: string }) =>
      await ovClient.instance.post('/api/v1/skills/ingestion/rollback', { snapshot_path: snapshotPath, target_file_path: targetPath }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] }),
  })

  const queueDepth = queueData?.queue_depth || { total: 0, pending: 0, validating: 0, staged: 0, rejected: 0, committed: 0, error: 0 }

  const getStatusBadge = (status: string) => {
    const map: Record<string, { cls: string; label: string }> = {
      PENDING: { cls: 'text-amber-400 border-amber-500/30', label: 'PENDING' },
      VALIDATING: { cls: 'text-cyan-400 border-cyan-500/30 animate-pulse', label: 'VALIDATING' },
      STAGED: { cls: 'text-cyan-300 border-cyan-500/30', label: 'STAGED' },
      REJECTED: { cls: 'text-rose-400 border-rose-500/30', label: 'REJECTED' },
      COMMITTED: { cls: 'text-blue-400 border-blue-500/30', label: 'COMMITTED' },
    }
    const item = map[status] || { cls: 'text-muted-foreground', label: status }
    return <Badge variant="outline" className={`text-xs font-mono ${item.cls}`}>{item.label}</Badge>
  }

  return (
    <div className="space-y-4">
      {/* 1. Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/20 border border-border/60 rounded-md p-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <InboxIcon className="size-4 text-cyan-400" />
            技能准入治理与黑匣子证据链座舱
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            确定性静态门禁 (YAML v2.0 / ≤500行 / AST 拦截) + SQLite 暂存并发控制 + 动态 KNN 路由 + 黑匣子回溯
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => { refetchQueue(); refetchProv() }} disabled={queueLoading || provLoading} className="text-xs h-8 font-mono">
            <RefreshCwIcon className={`size-3.5 mr-1.5 ${queueLoading || provLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button size="sm" onClick={() => processBatchMutation.mutate()} disabled={processBatchMutation.isPending || queueDepth.pending === 0} className="text-xs h-8 font-mono bg-cyan-600 hover:bg-cyan-500 text-white">
            <FastForwardIcon className="size-3.5 mr-1.5" />
            {processBatchMutation.isPending ? '处理中...' : '⚡ 执行单批处理 (5条)'}
          </Button>
        </div>
      </div>

      {/* 2. Top Metric Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="p-3 bg-card/60 border-border/60">
          <div className="text-xs text-muted-foreground flex items-center justify-between">
            <span>待校验积压</span>
            <ClockIcon className="size-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-foreground mt-1">{queueDepth.pending}</div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">validating: {queueDepth.validating}</div>
        </Card>

        <Card className="p-3 bg-card/60 border-border/60">
          <div className="text-xs text-muted-foreground flex items-center justify-between">
            <span>已通过准入 (Staged)</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-cyan-400 mt-1">{queueDepth.staged}</div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">ready for package routing</div>
        </Card>

        <Card className="p-3 bg-card/60 border-border/60">
          <div className="text-xs text-muted-foreground flex items-center justify-between">
            <span>门禁阻断违规</span>
            <ShieldAlertIcon className="size-3.5 text-rose-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-rose-400 mt-1">{queueDepth.rejected}</div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">AST / schema violations</div>
        </Card>

        <Card className="p-3 bg-card/60 border-border/60">
          <div className="text-xs text-muted-foreground flex items-center justify-between">
            <span>证据链事件总数</span>
            <HistoryIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-foreground mt-1">{provData?.events?.length || 0}</div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">auditability: 100%</div>
        </Card>
      </div>

      {/* 3. Main Split Panels: Ingestion Queue vs Provenance Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Ingestion Queue */}
        <Card className="p-3.5 bg-card/60 border-border/60 flex flex-col">
          <div className="flex items-center justify-between pb-2 border-b border-border/40">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <InboxIcon className="size-3.5 text-cyan-400" />
              暂存收件箱队列 ({queueData?.recent_records?.length || 0})
            </span>
            <span className="text-xs font-mono text-muted-foreground">SQLite WAL</span>
          </div>

          <div className="space-y-2 mt-3 overflow-y-auto max-h-96 pr-1">
            {!queueData?.recent_records || queueData.recent_records.length === 0 ? (
              <div className="text-xs text-muted-foreground text-center py-8">暂存队列空闲，暂无待准入技能</div>
            ) : (
              queueData.recent_records.map((record: IngestionRecord) => (
                <div
                  key={record.receipt_id}
                  onClick={() => setSelectedRecord(record)}
                  className={`p-2.5 rounded-md border text-xs cursor-pointer transition-colors ${
                    selectedRecord?.receipt_id === record.receipt_id ? 'border-cyan-500 bg-cyan-950/20' : 'border-border/40 bg-muted/10 hover:border-border'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-medium text-foreground truncate">{record.skill_name}</span>
                    {getStatusBadge(record.status)}
                  </div>
                  <div className="text-muted-foreground mt-1 line-clamp-1 font-mono">{record.status_message || 'Waiting in inbox...'}</div>
                  {record.validation_report?.routing && (
                    <div className="mt-1 text-cyan-400/90 font-mono text-xs flex items-center gap-2">
                      <span>pkg: {record.validation_report.routing.target_package}</span>
                      <span>action: {record.validation_report.routing.action}</span>
                      <span>score: {(record.validation_report.routing.top1_score * 100).toFixed(0)}%</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-muted-foreground mt-1 font-mono text-xs">
                    <span>{record.receipt_id}</span>
                    <span>{new Date(record.created_at * 1000).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Right: Blackbox Provenance Audit Timeline */}
        <Card className="p-3.5 bg-card/60 border-border/60 flex flex-col">
          <div className="flex items-center justify-between pb-2 border-b border-border/40">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <HistoryIcon className="size-3.5 text-cyan-400" />
              黑匣子演变审计证据链 (PROVENANCE.jsonl)
            </span>
            <span className="text-xs font-mono text-muted-foreground">Non-destructive</span>
          </div>

          <div className="space-y-2 mt-3 overflow-y-auto max-h-96 pr-1">
            {!provData?.events || provData.events.length === 0 ? (
              <div className="text-xs text-muted-foreground text-center py-8">暂无演变事件留痕记录</div>
            ) : (
              provData.events.map((ev: ProvenanceEvent) => (
                <div key={ev.event_id} className="p-2.5 rounded-md border border-border/40 bg-muted/10 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-mono">
                      <span className="text-cyan-400 font-bold">[{ev.action}]</span>
                      <span className="text-foreground">{ev.skill_name}</span>
                      <span className="text-muted-foreground">v{ev.version}</span>
                    </div>
                    {ev.snapshot_path && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          rollbackMutation.mutate({
                            snapshotPath: ev.snapshot_path!,
                            targetPath: `~/.openviking/data/viking/default/skills/${ev.skill_name}/SKILL.md`,
                          })
                        }
                        disabled={rollbackMutation.isPending}
                        className="text-xs h-6 px-2 font-mono text-cyan-400 border-cyan-500/40 hover:bg-cyan-950/30"
                      >
                        <ArchiveRestoreIcon className="size-3 mr-1" />
                        秒级回退
                      </Button>
                    )}
                  </div>
                  <div className="text-muted-foreground mt-1 font-mono text-xs truncate">
                    op: {ev.operator} | id: {ev.event_id}
                  </div>
                  <div className="text-muted-foreground mt-0.5 font-mono text-xs">
                    {new Date(ev.timestamp * 1000).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
