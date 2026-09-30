// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  GitCommitIcon,
  GitBranchIcon,
  ShieldCheckIcon,
  ClockIcon,
  SearchIcon,
  ArrowRightIcon,
  RefreshCwIcon,
  LayersIcon,
} from 'lucide-react'
import { ovClient } from '#/lib/ov-client'

interface ConflictStats {
  total_nodes: number
  active_nodes: number
  disputed_nodes: number
  superseded_nodes: number
  total_resolutions: number
  purity_ratio: number
}

interface ConflictEvent {
  old_uri: string
  new_uri: string
  old_status: string
  new_status: string
  reason: string
  timestamp: number
}

interface LineageDagChain {
  root_uri: string
  current_active_ssot: string
  superseded_path: string[]
  full_chain: string[]
  is_superseded: boolean
  predecessor: string | null
}

export function MemoryLineageDAGCard() {
  const queryClient = useQueryClient()
  const [traceInput, setTraceInput] = React.useState('')
  const [activeTraceUri, setActiveTraceUri] = React.useState<string | null>(null)

  // 1. Conflict & Lifecycle Stats Query
  const statsQuery = useQuery<ConflictStats>({
    queryKey: ['memory-conflicts-stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/memory/conflicts/stats')
      return res.data?.result ?? res.data
    },
    refetchInterval: 8_000,
    refetchIntervalInBackground: false,
    staleTime: 5_000,
  })

  // 2. Conflict Resolution History Query
  const historyQuery = useQuery<ConflictEvent[]>({
    queryKey: ['memory-conflicts-history'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/memory/conflicts/history?limit=10')
      return res.data?.result ?? res.data ?? []
    },
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
    staleTime: 5_000,
  })

  // 3. Lineage DAG Trace Query
  const traceQuery = useQuery<LineageDagChain>({
    queryKey: ['memory-lineage-dag', activeTraceUri],
    queryFn: async () => {
      if (!activeTraceUri) return null as any
      const res = await ovClient.instance.get(`/api/v1/memory/lineage/dag?uri=${encodeURIComponent(activeTraceUri)}`)
      return res.data?.result ?? res.data
    },
    enabled: Boolean(activeTraceUri),
  })

  const stats = statsQuery.data
  const history = historyQuery.data ?? []

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border/60 bg-card p-3.5 shadow-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <GitBranchIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
          <h3 className="text-xs font-semibold text-foreground">
            记忆版本演进与认知冲突消解流水线 (Superseding Lineage DAG)
          </h3>
          <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 font-mono text-xs text-cyan-600 dark:text-cyan-400">
            Layer 2 抗熵增闭环
          </span>
        </div>
        <button
          type="button"
          onClick={() => {
            queryClient.invalidateQueries({ queryKey: ['memory-conflicts-stats'] })
            queryClient.invalidateQueries({ queryKey: ['memory-conflicts-history'] })
          }}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <RefreshCwIcon className="size-3" />
          <span>刷新</span>
        </button>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="flex flex-col gap-1 rounded-md border border-border/40 bg-muted/20 p-2.5">
          <span className="text-xs text-muted-foreground">活跃 SSOT 节点</span>
          <div className="font-mono text-base font-bold tabular-nums text-cyan-600 dark:text-cyan-400">
            {stats?.active_nodes ?? '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">权威条目</span>
          </div>
        </div>

        <div className="flex flex-col gap-1 rounded-md border border-border/40 bg-muted/20 p-2.5">
          <span className="text-xs text-muted-foreground">已沉底替代节点 (Superseded)</span>
          <div className="font-mono text-base font-bold tabular-nums text-foreground">
            {stats?.superseded_nodes ?? '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">条目已降权</span>
          </div>
        </div>

        <div className="flex flex-col gap-1 rounded-md border border-border/40 bg-muted/20 p-2.5">
          <span className="text-xs text-muted-foreground">冲突闭环消解量</span>
          <div className="font-mono text-base font-bold tabular-nums text-foreground">
            {stats?.total_resolutions ?? '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">次血缘建链</span>
          </div>
        </div>

        <div className="flex flex-col gap-1 rounded-md border border-border/40 bg-muted/20 p-2.5">
          <span className="text-xs text-muted-foreground">记忆纯度指数 (Purity Ratio)</span>
          <div className="font-mono text-base font-bold tabular-nums text-cyan-600 dark:text-cyan-400">
            {stats?.purity_ratio != null ? `${(stats.purity_ratio * 100).toFixed(1)}%` : '--'}
            <span className="ml-1 text-xs font-normal text-muted-foreground">信噪比保真</span>
          </div>
        </div>
      </div>

      {/* DAG Tracer Search */}
      <div className="flex flex-col gap-2 rounded-md border border-border/40 bg-muted/10 p-2.5">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
            <input
              type="text"
              value={traceInput}
              onChange={(e) => setTraceInput(e.target.value)}
              placeholder="输入记忆 URI (如 viking://resources/master_memory/...) 追踪血缘演化 DAG 链路..."
              className="w-full rounded border border-border/50 bg-background py-1.5 pl-8 pr-3 text-xs font-mono text-foreground placeholder:text-muted-foreground focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <button
            type="button"
            onClick={() => setActiveTraceUri(traceInput.trim())}
            disabled={!traceInput.trim()}
            className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-700 disabled:opacity-50 transition-colors"
          >
            追踪 DAG
          </button>
        </div>

        {/* Trace Result */}
        {traceQuery.data && (
          <div className="flex flex-col gap-1.5 rounded border border-cyan-500/30 bg-cyan-500/5 p-2 text-xs font-mono">
            <div className="flex items-center gap-2 text-foreground font-semibold">
              <span>当前权威 SSOT:</span>
              <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-cyan-600 dark:text-cyan-400">
                {traceQuery.data.current_active_ssot}
              </span>
              {traceQuery.data.is_superseded && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-muted-foreground">已废弃替代</span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-muted-foreground pt-1">
              <span>演进链条 ({traceQuery.data.full_chain.length} 阶):</span>
              {traceQuery.data.full_chain.map((uri, idx) => (
                <React.Fragment key={uri}>
                  <span className={idx === traceQuery.data.full_chain.length - 1 ? 'text-cyan-600 dark:text-cyan-400 font-bold' : ''}>
                    {uri.split('/').pop()}
                  </span>
                  {idx < traceQuery.data.full_chain.length - 1 && <ArrowRightIcon className="size-3 text-muted-foreground" />}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Recent Conflict Resolutions List */}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-muted-foreground">
          最近认知冲突消解与版本更替流水 (最近 {history.length} 条)
        </span>
        <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
          {history.length > 0 ? (
            history.map((ev, i) => (
              <div
                key={`${ev.old_uri}-${ev.new_uri}-${i}`}
                className="flex items-center justify-between gap-2 rounded border border-border/30 bg-muted/10 p-2 text-xs font-mono hover:bg-muted/20 transition-colors"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="text-muted-foreground line-through truncate max-w-44" title={ev.old_uri}>
                    {ev.old_uri.split('/').pop()}
                  </span>
                  <ArrowRightIcon className="size-3 text-cyan-600 dark:text-cyan-400 shrink-0" />
                  <span className="text-cyan-600 dark:text-cyan-400 font-semibold truncate max-w-44" title={ev.new_uri}>
                    {ev.new_uri.split('/').pop()}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0 text-muted-foreground text-xs font-sans">
                  <span className="truncate max-w-48 text-muted-foreground" title={ev.reason}>
                    {ev.reason}
                  </span>
                  <span className="font-mono tabular-nums text-xs">
                    {new Date(ev.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="py-4 text-center text-xs text-muted-foreground">
              暂无冲突消解事件。系统在前门准入或手动调用时会自动登记新旧版本更替链条。
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
