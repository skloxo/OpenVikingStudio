// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  ClockIcon,
  FastForwardIcon,
  FileCode2Icon,
  InboxIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'

export interface IngestionItem {
  receipt_id: string
  skill_name: string
  raw_content: string
  author: string
  status: 'PENDING' | 'VALIDATING' | 'STAGED' | 'REJECTED' | 'COMMITTED' | 'ERROR'
  status_message: string
  validation_report?: {
    is_valid?: boolean
    line_count?: number
    latency_ms?: number
    opt_score?: number
    routing?: { action: string; target_package: string; top1_score: number; margin: number }
    diagnostics?: string[]
    recommendations?: string[]
    source_path?: string
    ante_gate?: { decision: string; target: string; affinity_score: number }
  }
  created_at: number
  updated_at: number
}

interface ActiveIngestionViewProps {
  onSelectSkillDetail?: (skillName: string) => void
}

export function ActiveIngestionView({ onSelectSkillDetail }: ActiveIngestionViewProps) {
  const queryClient = useQueryClient()
  const [selectedItem, setSelectedItem] = React.useState<IngestionItem | null>(null)
  const [statusFilter, setStatusFilter] = React.useState<string>('ALL')

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['skills-ingestion-queue'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{
        status: string
        queue_depth: { total: number; pending: number; validating: number; staged: number; rejected: number; committed: number; error: number }
        recent_records: IngestionItem[]
      }>('/api/v1/skills/ingestion/queue?limit=50')
      return res.data
    },
    refetchInterval: 10000,
  })

  const processMutation = useMutation({
    mutationFn: async () => {
      return (await ovClient.instance.post('/api/v1/skills/ingestion/process-batch?batch_size=10', {})).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue'] })
      queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] })
      queryClient.invalidateQueries({ queryKey: ['skills'] })
    },
  })

  const records = data?.recent_records || []
  const depth = data?.queue_depth || { total: 0, pending: 0, validating: 0, staged: 0, rejected: 0, committed: 0, error: 0 }

  const filteredRecords = React.useMemo(() => {
    if (statusFilter === 'ALL') return records
    return records.filter((r) => r.status === statusFilter)
  }, [records, statusFilter])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return (
          <Badge variant="outline" className="text-xs font-mono font-medium border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            ⏳ 排队待质检
          </Badge>
        )
      case 'VALIDATING':
        return (
          <Badge variant="outline" className="text-xs font-mono font-medium border-cyan-400 bg-cyan-50 text-cyan-800 dark:border-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-300 animate-pulse">
            ⚡ 质检评估中
          </Badge>
        )
      case 'STAGED':
        return (
          <Badge variant="outline" className="text-xs font-mono font-medium border-cyan-300 bg-cyan-100/60 text-cyan-800 dark:border-cyan-600 dark:bg-cyan-950/50 dark:text-cyan-200">
            📦 已暂存待熔炼
          </Badge>
        )
      case 'COMMITTED':
        return (
          <Badge variant="outline" className="text-xs font-mono font-medium border-cyan-500 bg-cyan-500/10 text-cyan-700 dark:border-cyan-500 dark:text-cyan-300">
            ✅ 已结晶入库
          </Badge>
        )
      case 'REJECTED':
        return (
          <Badge variant="outline" className="text-xs font-mono font-medium border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300">
            🛑 门禁拦截打回
          </Badge>
        )
      default:
        return (
          <Badge variant="outline" className="text-xs font-mono text-muted-foreground border-border bg-muted/30">
            {status}
          </Badge>
        )
    }
  }

  return (
    <div className="flex flex-col gap-3 font-sans">
      {/* 顶部流水线态势指示器 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-card p-3 shadow-2xs">
        <div className="flex items-center gap-2">
          <InboxIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
          <h2 className="text-xs font-semibold font-mono text-foreground">
            📥 散装技能自动化准入流水线 · 待入库展示态势
          </h2>
          <Badge variant="outline" className="text-xs font-mono border-border bg-muted/40 text-muted-foreground">
            总记录: {depth.total}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-7 text-xs font-mono gap-1 text-foreground border-border hover:bg-muted/40 cursor-pointer"
          >
            <RefreshCwIcon className={cn('size-3', isFetching && 'animate-spin')} />
            刷新队列
          </Button>
          <Button
            size="sm"
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending || (depth.pending === 0 && depth.validating === 0 && depth.staged === 0)}
            className="h-7 text-xs font-mono gap-1.5 bg-cyan-600 hover:bg-cyan-700 text-white dark:bg-cyan-500 dark:hover:bg-cyan-600 dark:text-black font-semibold cursor-pointer"
          >
            <FastForwardIcon className="size-3.5" />
            {processMutation.isPending ? '正在批量处理...' : '一键推进流水线批处理'}
          </Button>
        </div>
      </div>

      {/* 状态统计分桶过滤栏 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <Card
          className={cn(
            'p-2.5 cursor-pointer transition-all border shadow-2xs',
            statusFilter === 'ALL' ? 'border-cyan-500 bg-cyan-500/5' : 'border-border/70 bg-card hover:bg-muted/30'
          )}
          onClick={() => setStatusFilter('ALL')}
        >
          <div className="text-xs text-muted-foreground font-mono">全部流水线记录</div>
          <div className="text-lg font-bold font-mono text-foreground mt-0.5">{depth.total}</div>
        </Card>
        <Card
          className={cn(
            'p-2.5 cursor-pointer transition-all border shadow-2xs',
            statusFilter === 'PENDING' ? 'border-amber-500 bg-amber-500/5' : 'border-border/70 bg-card hover:bg-muted/30'
          )}
          onClick={() => setStatusFilter('PENDING')}
        >
          <div className="text-xs text-amber-700 dark:text-amber-400 font-mono">⏳ 排队待检</div>
          <div className="text-lg font-bold font-mono text-amber-800 dark:text-amber-300 mt-0.5">{depth.pending}</div>
        </Card>
        <Card
          className={cn(
            'p-2.5 cursor-pointer transition-all border shadow-2xs',
            statusFilter === 'VALIDATING' ? 'border-cyan-500 bg-cyan-500/5' : 'border-border/70 bg-card hover:bg-muted/30'
          )}
          onClick={() => setStatusFilter('VALIDATING')}
        >
          <div className="text-xs text-cyan-700 dark:text-cyan-400 font-mono">⚡ 质检评估中</div>
          <div className="text-lg font-bold font-mono text-cyan-800 dark:text-cyan-300 mt-0.5">{depth.validating}</div>
        </Card>
        <Card
          className={cn(
            'p-2.5 cursor-pointer transition-all border shadow-2xs',
            statusFilter === 'STAGED' ? 'border-cyan-500 bg-cyan-500/5' : 'border-border/70 bg-card hover:bg-muted/30'
          )}
          onClick={() => setStatusFilter('STAGED')}
        >
          <div className="text-xs text-cyan-600 dark:text-cyan-300 font-mono">📦 暂存待熔炼</div>
          <div className="text-lg font-bold font-mono text-cyan-700 dark:text-cyan-200 mt-0.5">{depth.staged}</div>
        </Card>
        <Card
          className={cn(
            'p-2.5 cursor-pointer transition-all border shadow-2xs',
            statusFilter === 'REJECTED' ? 'border-rose-500 bg-rose-500/5' : 'border-border/70 bg-card hover:bg-muted/30'
          )}
          onClick={() => setStatusFilter('REJECTED')}
        >
          <div className="text-xs text-rose-700 dark:text-rose-400 font-mono">🛑 门禁打回</div>
          <div className="text-lg font-bold font-mono text-rose-800 dark:text-rose-300 mt-0.5">{depth.rejected}</div>
        </Card>
        <Card
          className={cn(
            'p-2.5 cursor-pointer transition-all border shadow-2xs',
            statusFilter === 'COMMITTED' ? 'border-cyan-500 bg-cyan-500/5' : 'border-border/70 bg-card hover:bg-muted/30'
          )}
          onClick={() => setStatusFilter('COMMITTED')}
        >
          <div className="text-xs text-cyan-700 dark:text-cyan-300 font-mono">✅ 已结晶入库</div>
          <div className="text-lg font-bold font-mono text-cyan-800 dark:text-cyan-200 mt-0.5">{depth.committed}</div>
        </Card>
      </div>

      {/* 散装技能流水线记录列表 */}
      {filteredRecords.length === 0 ? (
        <Card className="p-8 text-center border-dashed border-border/80 bg-muted/10">
          <p className="text-xs text-muted-foreground font-mono">
            {isLoading ? '正在获取流水线数据...' : '当前视图暂无待处理记录'}
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {filteredRecords.map((item) => {
            const report = item.validation_report
            const anteGate = report?.ante_gate
            const isExpanded = selectedItem?.receipt_id === item.receipt_id

            return (
              <Card
                key={item.receipt_id}
                className={cn(
                  'p-3 transition-all border shadow-2xs flex flex-col gap-2',
                  isExpanded ? 'border-cyan-500/80 bg-muted/20' : 'border-border/70 bg-card hover:border-border'
                )}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs font-mono text-foreground">{item.skill_name}</span>
                    {getStatusBadge(item.status)}
                    {report?.opt_score !== undefined && (
                      <Badge variant="outline" className={cn(
                        'text-xs font-mono font-medium',
                        report.opt_score >= 70 ? 'border-cyan-300 text-cyan-800 bg-cyan-50 dark:border-cyan-800 dark:text-cyan-300' : 'border-rose-300 text-rose-800 bg-rose-50 dark:border-rose-800 dark:text-rose-300'
                      )}>
                        评分: {report.opt_score.toFixed(1)}/100
                      </Badge>
                    )}
                    {anteGate?.target && (
                      <Badge variant="outline" className="text-xs font-mono border-border bg-muted/40 text-muted-foreground">
                        🎯 归宿: {anteGate.target}
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground font-mono">
                      {new Date(item.created_at * 1000).toLocaleTimeString()}
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSelectedItem(isExpanded ? null : item)}
                      className="h-6 text-xs font-mono text-cyan-700 hover:text-cyan-800 dark:text-cyan-300 dark:hover:text-cyan-200 cursor-pointer px-1.5"
                    >
                      {isExpanded ? '收起详情 ▴' : '查看工序 ▾'}
                    </Button>
                  </div>
                </div>

                <div className="text-xs text-muted-foreground font-mono line-clamp-1">
                  {item.status_message || '等待自主闭环处理...'}
                </div>

                {isExpanded && (
                  <div className="mt-2 pt-2 border-t border-border/60 flex flex-col gap-2.5 text-xs font-mono">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-muted/30 p-2 rounded">
                      <div>
                        <span className="text-muted-foreground">来源路径: </span>
                        <span className="text-foreground break-all">{report?.source_path || '未知'}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">工单凭证 (Receipt): </span>
                        <span className="text-foreground">{item.receipt_id}</span>
                      </div>
                    </div>

                    {report?.diagnostics && report.diagnostics.length > 0 && (
                      <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-200">
                        <div className="font-semibold mb-1 flex items-center gap-1">
                          <AlertTriangleIcon className="size-3.5 text-amber-600 dark:text-amber-400" />
                          质检诊断分析:
                        </div>
                        <ul className="list-disc list-inside space-y-0.5">
                          {report.diagnostics.map((d, idx) => (
                            <li key={idx}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {report?.recommendations && report.recommendations.length > 0 && (
                      <div className="p-2 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-900 dark:text-cyan-200">
                        <div className="font-semibold mb-1 flex items-center gap-1">
                          <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                          自动化修复建议 (AutoRemediator 将自动补齐):
                        </div>
                        <ul className="list-disc list-inside space-y-0.5">
                          {report.recommendations.map((r, idx) => (
                            <li key={idx}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
