// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArchiveRestoreIcon,
  ChevronRightIcon,
  FastForwardIcon,
  HistoryIcon,
  InboxIcon,
  RefreshCwIcon,
  SearchIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { UniversalPagination } from '#/components/common/universal-pagination'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import type {
  IngestionRecordItem,
  LedgerTrack,
  ProvenanceRecordItem,
  SelectedLedgerItem,
} from '../-types/provenance-ledger'
import { ProvenanceDetailSheet } from './provenance-detail-sheet'

export function B6ProvenanceMultiLedger() {
  const queryClient = useQueryClient()
  const [activeTrack, setActiveTrack] = React.useState<LedgerTrack>('provenance')
  const [searchQuery, setSearchQuery] = React.useState('')
  const [selectedItem, setSelectedItem] = React.useState<SelectedLedgerItem | null>(null)
  const [sheetOpen, setSheetOpen] = React.useState(false)
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)

  // 1. 轨道 1: 黑匣子演变审计证据链
  const {
    data: provData,
    isLoading: provLoading,
    refetch: refetchProv,
  } = useQuery({
    queryKey: ['skills-provenance-events'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; events: ProvenanceRecordItem[] }>(
        '/api/v1/skills/ingestion/provenance?limit=100'
      )
      return res.data
    },
    refetchInterval: 15000,
  })

  // 2. 轨道 2: SQLite 准入收件箱暂存流水
  const {
    data: queueData,
    isLoading: queueLoading,
    refetch: refetchQueue,
  } = useQuery({
    queryKey: ['skills-ingestion-queue'],
    queryFn: async () => {
      const res = await ovClient.instance.get<{
        status: string
        queue_depth: {
          total: number
          pending: number
          validating: number
          staged: number
          rejected: number
          committed: number
          error: number
        }
        recent_records: IngestionRecordItem[]
      }>('/api/v1/skills/ingestion/queue?limit=100')
      return res.data
    },
    refetchInterval: 10000,
  })

  // 3. 异步批处理触发
  const processBatchMutation = useMutation({
    mutationFn: async () =>
      (await ovClient.instance.post('/api/v1/skills/ingestion/process-batch?batch_size=5', {})).data,
    onSuccess: (data: any) => {
      toast.success('已触发单批次自适应准入处理')
      queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue'] })
      queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] })
    },
    onError: (err: any) => {
      toast.error(`处理失败: ${err?.message || '未知错误'}`)
    },
  })

  const queueDepth = queueData?.queue_depth || {
    total: 0,
    pending: 0,
    validating: 0,
    staged: 0,
    rejected: 0,
    committed: 0,
    error: 0,
  }

  const provEvents = provData?.events || []
  const queueRecords = queueData?.recent_records || []

  // 过滤逻辑
  const filteredProvEvents = React.useMemo(() => {
    if (!searchQuery.trim()) return provEvents
    const q = searchQuery.toLowerCase()
    return provEvents.filter(
      (e) =>
        e.skill_name?.toLowerCase().includes(q) ||
        e.action?.toLowerCase().includes(q) ||
        e.operator?.toLowerCase().includes(q) ||
        e.receipt_id?.toLowerCase().includes(q) ||
        e.event_id?.toLowerCase().includes(q)
    )
  }, [provEvents, searchQuery])

  const filteredQueueRecords = React.useMemo(() => {
    if (!searchQuery.trim()) return queueRecords
    const q = searchQuery.toLowerCase()
    return queueRecords.filter(
      (r) =>
        r.skill_name?.toLowerCase().includes(q) ||
        r.status?.toLowerCase().includes(q) ||
        r.author?.toLowerCase().includes(q) ||
        r.receipt_id?.toLowerCase().includes(q)
    )
  }, [queueRecords, searchQuery])

  const totalItems =
    activeTrack === 'provenance' ? filteredProvEvents.length : filteredQueueRecords.length

  const paginatedProv = React.useMemo(() => {
    const start = (page - 1) * pageSize
    return filteredProvEvents.slice(start, start + pageSize)
  }, [filteredProvEvents, page, pageSize])

  const paginatedQueue = React.useMemo(() => {
    const start = (page - 1) * pageSize
    return filteredQueueRecords.slice(start, start + pageSize)
  }, [filteredQueueRecords, page, pageSize])

  const handleRowClick = (item: SelectedLedgerItem) => {
    setSelectedItem(item)
    setSheetOpen(true)
  }

  const getActionBadge = (action: string) => {
    const map: Record<string, string> = {
      INGEST: 'border-amber-300 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
      VALIDATE: 'border-cyan-300 bg-cyan-50 text-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800',
      ROUTE: 'border-sky-300 bg-sky-50 text-sky-800 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800',
      MERGE: 'border-cyan-400 bg-cyan-100/70 text-cyan-900 dark:bg-cyan-950/60 dark:text-cyan-200 dark:border-cyan-700',
      OPTIMIZE: 'border-violet-300 bg-violet-50 text-violet-800 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-800',
      ROLLBACK: 'border-rose-300 bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800',
    }
    const cls = map[action] || 'border-border bg-muted/40 text-foreground'
    return <Badge variant="outline" className={`text-xs font-mono px-1.5 py-0.5 border ${cls}`}>[{action}]</Badge>
  }

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      PENDING: 'border-amber-300 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
      VALIDATING: 'border-cyan-300 bg-cyan-50 text-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800 animate-pulse',
      STAGED: 'border-cyan-300 bg-cyan-50 text-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800',
      COMMITTED: 'border-sky-300 bg-sky-50 text-sky-800 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800',
      REJECTED: 'border-rose-300 bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800',
      ERROR: 'border-rose-300 bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800',
    }
    const cls = map[status] || 'border-border bg-muted/40 text-foreground'
    return <Badge variant="outline" className={`text-xs font-mono px-1.5 py-0.5 border ${cls}`}>{status}</Badge>
  }

  return (
    <div className="rounded-md border border-border/80 bg-card p-3.5 shadow-2xs space-y-3">
      {/* 1. 轨道切换与操作工具栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-border/60 pb-3">
        {/* 多轨 Tab */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => { setActiveTrack('provenance'); setPage(1) }}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-mono font-medium transition-all cursor-pointer ${
              activeTrack === 'provenance'
                ? 'bg-cyan-100 text-cyan-900 border border-cyan-300 dark:bg-cyan-950/60 dark:text-cyan-200 dark:border-cyan-800 font-semibold'
                : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
            }`}
          >
            <HistoryIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>📜 轨道 1: 黑匣子证据链 ({filteredProvEvents.length})</span>
          </button>
          <button
            type="button"
            onClick={() => { setActiveTrack('ingestion'); setPage(1) }}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-mono font-medium transition-all cursor-pointer ${
              activeTrack === 'ingestion'
                ? 'bg-cyan-100 text-cyan-900 border border-cyan-300 dark:bg-cyan-950/60 dark:text-cyan-200 dark:border-cyan-800 font-semibold'
                : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
            }`}
          >
            <InboxIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>📥 轨道 2: SQLite 准入流水 ({filteredQueueRecords.length})</span>
          </button>
        </div>

        {/* 搜索与批处理动作 */}
        <div className="flex items-center gap-2">
          <div className="relative w-44 sm:w-56">
            <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
              placeholder="搜索技能/ID/操作源..."
              className="text-xs font-mono h-7 pl-7 pr-2 border-border/80"
            />
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => { refetchProv(); refetchQueue() }}
            disabled={provLoading || queueLoading}
            className="text-xs h-7 font-mono px-2 border-border/80"
          >
            <RefreshCwIcon className={`size-3 mr-1 ${provLoading || queueLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            size="sm"
            variant={queueDepth.pending > 0 ? 'default' : 'outline'}
            onClick={() => processBatchMutation.mutate()}
            disabled={processBatchMutation.isPending || queueDepth.pending === 0}
            className={cn(
              'text-xs h-7 font-mono px-2.5 transition-all',
              queueDepth.pending > 0
                ? 'bg-cyan-600 hover:bg-cyan-700 text-white font-semibold shadow-xs cursor-pointer'
                : 'bg-muted/30 text-muted-foreground border-border/70 cursor-not-allowed opacity-80'
            )}
          >
            <FastForwardIcon className="size-3 mr-1" />
            {processBatchMutation.isPending
              ? '处理中...'
              : queueDepth.pending > 0
              ? `⚡ 批处理 (${Math.min(queueDepth.pending, 5)})`
              : '队列空闲'}
          </Button>
        </div>
      </div>

      {/* 2. 高密表格视窗 */}
      <div className="rounded-md border border-border/70 overflow-hidden bg-background">
        {activeTrack === 'provenance' ? (
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow className="hover:bg-transparent border-border/60">
                <TableHead className="text-xs font-mono text-muted-foreground w-28 py-2">动作 / 阶段</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground py-2">技能名称</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground py-2">演变证据摘要</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-24 py-2">快照指针</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-32 py-2">操作源</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-36 py-2">时间戳</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-16 text-right py-2">穿透</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-border/40">
              {paginatedProv.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-xs text-muted-foreground text-center py-8 font-mono">
                    暂无黑匣子演变审计证据记录
                  </TableCell>
                </TableRow>
              ) : (
                paginatedProv.map((ev) => {
                  const isError = ev.action === 'VALIDATE' && ev.details?.is_valid === false
                  return (
                    <TableRow
                      key={ev.event_id}
                      onClick={() => handleRowClick({ type: 'provenance', record: ev })}
                      className="cursor-pointer hover:bg-muted/30 text-xs font-mono transition-colors"
                    >
                      <TableCell className="py-2">{getActionBadge(ev.action)}</TableCell>
                      <TableCell className="py-2 font-semibold text-foreground">
                        <span>{ev.skill_name}</span>
                        {ev.version && <span className="text-muted-foreground font-normal ml-1">v{ev.version}</span>}
                      </TableCell>
                      <TableCell className="py-2 max-w-xs truncate text-muted-foreground">
                        {ev.details?.message || ev.details?.stage || '--'}
                      </TableCell>
                      <TableCell className="py-2">
                        {ev.snapshot_path ? (
                          <span className="flex items-center gap-1 text-cyan-700 dark:text-cyan-300 font-semibold">
                            <ArchiveRestoreIcon className="size-3" /> 可秒退
                          </span>
                        ) : (
                          <span className="text-muted-foreground/60">--</span>
                        )}
                      </TableCell>
                      <TableCell className="py-2 text-muted-foreground truncate max-w-28">
                        {ev.operator}
                      </TableCell>
                      <TableCell className="py-2 text-muted-foreground">
                        {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                      </TableCell>
                      <TableCell className="py-2 text-right">
                        <ChevronRightIcon className="size-3.5 text-muted-foreground inline" />
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        ) : (
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow className="hover:bg-transparent border-border/60">
                <TableHead className="text-xs font-mono text-muted-foreground w-28 py-2">准入状态</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground py-2">技能名称</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground py-2">状态反馈与质检报告</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-24 py-2">评分</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-32 py-2">提交者</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-36 py-2">创建时间</TableHead>
                <TableHead className="text-xs font-mono text-muted-foreground w-16 text-right py-2">穿透</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-border/40">
              {paginatedQueue.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-xs text-muted-foreground text-center py-8 font-mono">
                    暂无准入队列条目
                  </TableCell>
                </TableRow>
              ) : (
                paginatedQueue.map((rec) => (
                  <TableRow
                    key={rec.receipt_id}
                    onClick={() => handleRowClick({ type: 'ingestion', record: rec })}
                    className="cursor-pointer hover:bg-muted/30 text-xs font-mono transition-colors"
                  >
                    <TableCell className="py-2">{getStatusBadge(rec.status)}</TableCell>
                    <TableCell className="py-2 font-semibold text-foreground">{rec.skill_name}</TableCell>
                    <TableCell className="py-2 max-w-xs truncate text-muted-foreground">
                      {rec.status_message || 'Waiting in queue...'}
                    </TableCell>
                    <TableCell className="py-2 font-semibold">
                      {rec.validation_report?.opt_score !== undefined ? (
                        <span className="text-cyan-700 dark:text-cyan-300">
                          {Number(rec.validation_report.opt_score).toFixed(0)}分
                        </span>
                      ) : (
                        <span className="text-muted-foreground/60">--</span>
                      )}
                    </TableCell>
                    <TableCell className="py-2 text-muted-foreground truncate max-w-28">{rec.author}</TableCell>
                    <TableCell className="py-2 text-muted-foreground">
                      {new Date(rec.created_at * 1000).toLocaleTimeString()}
                    </TableCell>
                    <TableCell className="py-2 text-right">
                      <ChevronRightIcon className="size-3.5 text-muted-foreground inline" />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </div>

      {/* 3. 分页栏 */}
      {totalItems > pageSize && (
        <div className="pt-1">
          <UniversalPagination
            page={page}
            pageSize={pageSize}
            total={totalItems}
            onPageChange={setPage}
            onPageSizeChange={(newSize) => { setPageSize(newSize); setPage(1) }}
            pageSizeOptions={[10, 20, 50]}
            compact
          />
        </div>
      )}

      {/* 4. 详情穿透抽屉 */}
      <ProvenanceDetailSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        item={selectedItem}
      />
    </div>
  )
}
