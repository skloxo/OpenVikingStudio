// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ClockIcon,
  DatabaseIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ZapIcon,
  FileTextIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import { VALET_INGESTION_PRESETS, type ValetPreset } from '../-constants/valet-presets'

interface ValetTicketItem {
  ticket_id: string
  uri: string
  source: string
  caller: string
  status: 'accepted' | 'parking' | 'parked' | 'rejected'
  created_at: number
  processed_at?: number
  detail?: string
}

interface ValetStatsData {
  total_handovers: number
  avg_handover_ms: number
  queue_depth: number
  dedup_ratio: number
  merged_count: number
  rejected_count: number
  persisted_count: number
}

export function ValetIngestionCockpit() {
  const queryClient = useQueryClient()
  const [selectedPreset, setSelectedPreset] = React.useState<ValetPreset>(VALET_INGESTION_PRESETS[0])
  const [inputUri, setInputUri] = React.useState(selectedPreset.uri)
  const [inputContent, setInputContent] = React.useState(selectedPreset.content)
  const [activeTicket, setActiveTicket] = React.useState<ValetTicketItem | null>(null)
  const [lastHandoverLatency, setLastHandoverLatency] = React.useState<number | null>(null)

  // 1. Telemetry Stats Query
  const statsQuery = useQuery<ValetStatsData>({
    queryKey: ['valet-stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/valet/stats')
      return res.data
    },
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
    staleTime: 4_000,
  })

  // 2. Tickets List Query
  const ticketsQuery = useQuery<ValetTicketItem[]>({
    queryKey: ['valet-tickets'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/valet/tickets', {
        params: { limit: 20 },
      })
      return res.data
    },
    refetchInterval: 3_000,
    refetchIntervalInBackground: false,
    staleTime: 2_000,
  })

  // 3. Handover Mutation
  const handoverMutation = useMutation<ValetTicketItem, Error, { uri: string; content: string; source: string; caller: string }>({
    mutationFn: async (payload) => {
      const t0 = performance.now()
      const res = await ovClient.instance.post('/api/v1/valet/handover', payload)
      const lat = performance.now() - t0
      setLastHandoverLatency(lat)
      return res.data
    },
    onSuccess: (data) => {
      setActiveTicket(data)
      queryClient.invalidateQueries({ queryKey: ['valet-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['valet-stats'] })
    },
  })

  // 4. Batch Handover Mutation
  const batchMutation = useMutation<ValetTicketItem[], Error, Array<{ uri: string; content: string }>>({
    mutationFn: async (items) => {
      const t0 = performance.now()
      const res = await ovClient.instance.post('/api/v1/valet/batch', { items })
      const lat = performance.now() - t0
      setLastHandoverLatency(lat)
      return res.data
    },
    onSuccess: (data) => {
      if (data.length > 0) setActiveTicket(data[0])
      queryClient.invalidateQueries({ queryKey: ['valet-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['valet-stats'] })
    },
  })

  const handleSelectPreset = (preset: ValetPreset) => {
    setSelectedPreset(preset)
    setInputUri(preset.uri)
    setInputContent(preset.content)
  }

  const handleDispatchHandover = () => {
    if (selectedPreset.isBatch && selectedPreset.batchItems) {
      batchMutation.mutate(selectedPreset.batchItems)
    } else {
      handoverMutation.mutate({
        uri: inputUri,
        content: inputContent,
        source: selectedPreset.source,
        caller: selectedPreset.caller,
      })
    }
  }

  const stats = statsQuery.data ?? {
    total_handovers: 0,
    avg_handover_ms: 0,
    queue_depth: 0,
    dedup_ratio: 0,
    merged_count: 0,
    rejected_count: 0,
    persisted_count: 0,
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 4 大核心 KPI 瓦片卡片 (座舱级高密性冷淡设计) */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-lg border border-border/60 bg-card p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">前门交接平均时延</span>
            <ClockIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono text-cyan-600 dark:text-cyan-400 tabular-nums">
              {stats.avg_handover_ms > 0 ? stats.avg_handover_ms.toFixed(2) : '< 5.00'}
            </span>
            <span className="text-xs text-muted-foreground font-mono">ms (目标 &lt; 10ms)</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            末次前门网络: {lastHandoverLatency ? `${lastHandoverLatency.toFixed(1)}ms` : '--'}
          </div>
        </div>

        <div className="rounded-lg border border-border/60 bg-card p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">累计泊车请求</span>
            <DatabaseIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono text-foreground tabular-nums">
              {stats.total_handovers}
            </span>
            <span className="text-xs text-muted-foreground font-mono">次 (HTTP 202)</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            已落盘晶体: {stats.persisted_count} 篇
          </div>
        </div>

        <div className="rounded-lg border border-border/60 bg-card p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">反熵去重准入率</span>
            <ShieldAlertIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono text-cyan-600 dark:text-cyan-400 tabular-nums">
              {stats.dedup_ratio.toFixed(1)}%
            </span>
            <span className="text-xs text-muted-foreground font-mono">去噪合流</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            静默合并: {stats.merged_count} | 拦截: {stats.rejected_count}
          </div>
        </div>

        <div className="rounded-lg border border-border/60 bg-card p-3 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">待入库异步队列水深</span>
            <LayersIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono text-foreground tabular-nums">
              {stats.queue_depth}
            </span>
            <span className="text-xs text-muted-foreground font-mono">条等待中</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground font-mono">
            状态: {stats.queue_depth === 0 ? '空闲自愈' : '并发消化中'}
          </div>
        </div>
      </div>

      {/* 预设选择器栏 */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/60 bg-card p-2.5">
        <span className="text-xs font-semibold text-muted-foreground mr-1">场景预设:</span>
        {VALET_INGESTION_PRESETS.map((preset) => (
          <Button
            key={preset.id}
            size="sm"
            variant={selectedPreset.id === preset.id ? 'default' : 'outline'}
            onClick={() => handleSelectPreset(preset)}
            className="text-xs h-7 cursor-pointer"
          >
            {preset.name}
          </Button>
        ))}
      </div>

      {/* 双栏工作台 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* 左栏 (7/12): 泊车交接控制台 */}
        <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-card p-4 lg:col-span-7">
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div className="flex items-center gap-2">
              <ZapIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
              <h3 className="text-xs font-bold text-foreground">前门交接与物理泊车 (Handover 202)</h3>
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              来源: {selectedPreset.source} | 调度方: {selectedPreset.caller}
            </span>
          </div>

          <p className="text-xs text-muted-foreground">{selectedPreset.description}</p>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-foreground">目标资源 URI</label>
            <input
              type="text"
              value={inputUri}
              onChange={(e) => setInputUri(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-foreground">
              {selectedPreset.isBatch ? '批处理多段投递内容' : '单篇知识内容 Markdown'}
            </label>
            <textarea
              rows={8}
              value={inputContent}
              onChange={(e) => setInputContent(e.target.value)}
              className="w-full resize-none rounded-md border border-input bg-background p-2.5 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="text-xs text-muted-foreground font-mono">
              协议模式: <span className="font-bold text-cyan-600 dark:text-cyan-400">HTTP 202 Accepted 异步票据</span>
            </div>
            <Button
              size="sm"
              disabled={handoverMutation.isPending || batchMutation.isPending}
              onClick={handleDispatchHandover}
              className="text-xs h-8 cursor-pointer"
            >
              <ZapIcon className="size-3.5 mr-1.5 text-cyan-400" />
              {handoverMutation.isPending || batchMutation.isPending ? '物理泊车交接中...' : '⚡ 极速交接 (Handover)'}
            </Button>
          </div>
        </div>

        {/* 右栏 (5/12): 票据流水与状态监视 */}
        <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-card p-4 lg:col-span-5">
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div className="flex items-center gap-2">
              <FileTextIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
              <h3 className="text-xs font-bold text-foreground">泊车票据流水 (Valet Tickets)</h3>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => ticketsQuery.refetch()}
              className="h-6 px-2 text-xs cursor-pointer"
            >
              <RefreshCwIcon className={`size-3 mr-1 ${ticketsQuery.isFetching ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>

          {/* 活跃选定票据卡片 */}
          {activeTicket && (
            <div className="rounded-md border border-cyan-500/40 bg-cyan-500/5 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-cyan-600 dark:text-cyan-400">
                  {activeTicket.ticket_id}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded font-mono font-semibold ${
                  activeTicket.status === 'parked' ? 'bg-cyan-500/20 text-cyan-400' :
                  activeTicket.status === 'rejected' ? 'bg-rose-500/20 text-rose-400' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {activeTicket.status}
                </span>
              </div>
              <div className="mt-1 text-xs text-foreground font-mono truncate">{activeTicket.uri}</div>
              {activeTicket.detail && (
                <div className="mt-1 text-xs text-muted-foreground font-mono">{activeTicket.detail}</div>
              )}
            </div>
          )}

          {/* 票据列表 */}
          <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
            {ticketsQuery.data && ticketsQuery.data.length > 0 ? (
              ticketsQuery.data.map((t) => (
                <div
                  key={t.ticket_id}
                  onClick={() => setActiveTicket(t)}
                  className={`flex flex-col gap-1 rounded-md border p-2 text-xs transition-colors cursor-pointer ${
                    activeTicket?.ticket_id === t.ticket_id
                      ? 'border-cyan-500 bg-muted/50'
                      : 'border-border/40 hover:bg-muted/30'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-muted-foreground truncate max-w-44">
                      {t.ticket_id}
                    </span>
                    <span className={`px-1.5 py-0.2 text-xs rounded font-mono ${
                      t.status === 'parked' ? 'text-cyan-400' :
                      t.status === 'rejected' ? 'text-rose-400' :
                      'text-amber-400'
                    }`}>
                      {t.status}
                    </span>
                  </div>
                  <div className="font-mono text-foreground truncate">{t.uri}</div>
                </div>
              ))
            ) : (
              <div className="flex h-32 items-center justify-center text-xs text-muted-foreground font-mono">
                暂无泊车票据流水，请点击左侧极速交接
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
