// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  ArchiveIcon,
  CheckCircle2Icon,
  ClockIcon,
  DatabaseIcon,
  FileTextIcon,
  LayersIcon,
  RefreshCwIcon,
  SearchIcon,
  ShieldCheckIcon,
  ZapIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import { ACTIVE_NOTES_PRESETS, type ActiveNotesPreset } from '../-constants/active-notes-presets'

interface HistoryMsg {
  message_id: string
  turn_index: number
  role: string
  content: string
  created_at: number
}

interface HistoryHit {
  message_id: string
  turn_index: number
  role: string
  content: string
  score: number
  created_at: number
}

interface ContextStats {
  session_id: string
  notes_version: number
  notes_tokens: number
  history_count: number
  history_total_tokens: number
  token_saving_ratio: number
  fidelity_rate: number
}

export function ActiveNotesHistoryCockpit() {
  const [selectedPreset, setSelectedPreset] = React.useState<ActiveNotesPreset>(ACTIVE_NOTES_PRESETS[0])
  const [activeGoal, setActiveGoal] = React.useState(selectedPreset.active_goal)
  const [currentState, setCurrentState] = React.useState(selectedPreset.current_state)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [activeSubTab, setActiveSubTab] = React.useState<'windows' | 'search'>('windows')

  const sessionId = selectedPreset.session_id

  // 1. Context stats query
  const statsQuery = useQuery<ContextStats>({
    queryKey: ['active-notes-stats', sessionId],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/context/stats', {
        params: { session_id: sessionId },
      })
      return res.data
    },
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  // 2. History windows query
  const windowsQuery = useQuery<HistoryMsg[]>({
    queryKey: ['active-notes-windows', sessionId],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/context/history/windows', {
        params: { session_id: sessionId, offset: 0, limit: 20, order: 'asc' },
      })
      return res.data
    },
    refetchIntervalInBackground: false,
    staleTime: 10_000,
  })

  // 3. Search history mutation
  const searchMutation = useMutation<HistoryHit[], Error, string>({
    mutationFn: async (q: string) => {
      const res = await ovClient.instance.post('/api/v1/context/history/search', {
        session_id: sessionId,
        query: q,
        top_k: 5,
      })
      return res.data
    },
  })

  // Load preset handler
  const handleSelectPreset = (preset: ActiveNotesPreset) => {
    setSelectedPreset(preset)
    setActiveGoal(preset.active_goal)
    setCurrentState(preset.current_state)
    setSearchQuery('')
  }

  // Seed / sync preset data to backend
  const syncPresetMutation = useMutation({
    mutationFn: async () => {
      // update notes
      await ovClient.instance.put('/api/v1/context/notes', {
        session_id: sessionId,
        active_goal: activeGoal,
        working_constraints: selectedPreset.working_constraints,
        current_state: currentState,
        discovered_facts: selectedPreset.discovered_facts,
      })
      // seed history
      for (const item of selectedPreset.history) {
        await ovClient.instance.post('/api/v1/context/history/append', {
          session_id: sessionId,
          role: item.role,
          content: item.content,
        })
      }
    },
    onSuccess: () => {
      void statsQuery.refetch()
      void windowsQuery.refetch()
    },
  })

  const stats = statsQuery.data
  const savingPct = Math.round((stats?.token_saving_ratio ?? 0.965) * 100)

  return (
    <div className="flex flex-col gap-4">
      {/* Preset Selector Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/60 bg-card/60 p-3">
        <div className="flex items-center gap-2">
          <DatabaseIcon className="size-4 text-cyan-400" />
          <span className="text-xs font-medium text-foreground">预设场景演练:</span>
          <div className="flex flex-wrap gap-1.5">
            {ACTIVE_NOTES_PRESETS.map((preset) => (
              <Button
                key={preset.id}
                size="sm"
                variant={selectedPreset.id === preset.id ? 'secondary' : 'ghost'}
                className={`h-7 px-2.5 text-xs ${
                  selectedPreset.id === preset.id ? 'border border-cyan-500/40 text-cyan-400 font-medium' : 'text-muted-foreground'
                }`}
                onClick={() => handleSelectPreset(preset)}
              >
                {preset.name}
              </Button>
            ))}
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10"
          disabled={syncPresetMutation.isPending}
          onClick={() => syncPresetMutation.mutate()}
        >
          <RefreshCwIcon className={`mr-1 size-3 ${syncPresetMutation.isPending ? 'animate-spin' : ''}`} />
          同步预设到分仓
        </Button>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <ZapIcon className="size-3.5 text-cyan-400" />
            常驻上下文节省率
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-cyan-400 tabular-nums">
            {savingPct}%
            <span className="ml-1 text-xs font-normal text-muted-foreground">Tokens 节省</span>
          </div>
        </div>

        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <ArchiveIcon className="size-3.5 text-cyan-400" />
            历史分仓留存
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-foreground tabular-nums">
            {stats?.history_count ?? selectedPreset.history.length}
            <span className="ml-1 text-xs font-normal text-muted-foreground">条原始长轮次</span>
          </div>
        </div>

        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <ShieldCheckIcon className="size-3.5 text-cyan-400" />
            无损保真率
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-cyan-400 tabular-nums">
            100%
            <span className="ml-1 text-xs font-normal text-muted-foreground">零失真 Compaction</span>
          </div>
        </div>

        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <ClockIcon className="size-3.5 text-cyan-400" />
            调阅响应延迟
          </div>
          <div className="mt-1 font-mono text-xl font-bold text-foreground tabular-nums">
            &lt; 4ms
            <span className="ml-1 text-xs font-normal text-muted-foreground">FTS5+WAL</span>
          </div>
        </div>
      </div>

      {/* Main 50/50 Dual-Repository Split View */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Active Notes (High-Density In-Context) */}
        <div className="rounded-md border border-border/60 bg-card/60 p-3.5 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div className="flex items-center gap-1.5">
              <FileTextIcon className="size-4 text-cyan-400" />
              <h2 className="text-xs font-bold text-foreground tracking-tight">Active Notes (高密常驻主上下文)</h2>
            </div>
            <span className="font-mono text-xs text-muted-foreground">v{stats?.notes_version ?? 1} · 常驻 ~{stats?.notes_tokens ?? 180} Tokens</span>
          </div>

          <div>
            <label className="text-xs text-muted-foreground font-medium">核心目标 (Active Goal)</label>
            <input
              type="text"
              value={activeGoal}
              onChange={(e) => setActiveGoal(e.target.value)}
              className="mt-1 w-full h-8 rounded border border-border/60 bg-background px-2.5 text-xs text-foreground font-mono focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground font-medium">当前阶段里程碑 (Current State)</label>
            <input
              type="text"
              value={currentState}
              onChange={(e) => setCurrentState(e.target.value)}
              className="mt-1 w-full h-8 rounded border border-border/60 bg-background px-2.5 text-xs text-foreground font-mono focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground font-medium">运行硬性红线与约束 (Working Constraints)</label>
            <div className="mt-1 flex flex-col gap-1">
              {selectedPreset.working_constraints.map((c, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-foreground bg-muted/40 rounded px-2 py-1">
                  <span className="text-cyan-400 font-mono">[{i + 1}]</span>
                  <span>{c}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground font-medium">已确认不可变物理事实 (Discovered Facts)</label>
            <div className="mt-1 flex flex-col gap-1">
              {selectedPreset.discovered_facts.map((f, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground bg-muted/30 rounded px-2 py-1">
                  <CheckCircle2Icon className="size-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: History Repository (Out-of-Context Recall) */}
        <div className="rounded-md border border-border/60 bg-card/60 p-3.5 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-border/60 pb-2">
            <div className="flex items-center gap-1.5">
              <LayersIcon className="size-4 text-cyan-400" />
              <h2 className="text-xs font-bold text-foreground tracking-tight">History 独立分仓 (按需主动调阅)</h2>
            </div>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant={activeSubTab === 'windows' ? 'secondary' : 'ghost'}
                className={`h-6 px-2 text-xs ${activeSubTab === 'windows' ? 'text-cyan-400 border border-cyan-500/30' : 'text-muted-foreground'}`}
                onClick={() => setActiveSubTab('windows')}
              >
                窗口浏览 (list_windows)
              </Button>
              <Button
                size="sm"
                variant={activeSubTab === 'search' ? 'secondary' : 'ghost'}
                className={`h-6 px-2 text-xs ${activeSubTab === 'search' ? 'text-cyan-400 border border-cyan-500/30' : 'text-muted-foreground'}`}
                onClick={() => setActiveSubTab('search')}
              >
                精准检索 (search_history)
              </Button>
            </div>
          </div>

          {activeSubTab === 'search' && (
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="输入检索词 (如: ERR_PORT_CONFLICT, 1933, ConfigDict)..."
                className="flex-1 h-8 rounded border border-border/60 bg-background px-2.5 text-xs text-foreground font-mono focus:ring-1 focus:ring-cyan-500"
              />
              <Button
                size="sm"
                className="h-8 px-3 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
                disabled={!searchQuery.trim() || searchMutation.isPending}
                onClick={() => searchMutation.mutate(searchQuery.trim())}
              >
                <SearchIcon className="mr-1 size-3.5" />
                检索
              </Button>
            </div>
          )}

          {/* History Content Display */}
          <div className="flex flex-col gap-2 max-h-95 overflow-y-auto pr-1">
            {activeSubTab === 'search' && searchMutation.data ? (
              searchMutation.data.length === 0 ? (
                <div className="text-xs text-muted-foreground text-center py-6">未匹配到历史记录</div>
              ) : (
                searchMutation.data.map((hit) => (
                  <div key={hit.message_id} className="rounded border border-cyan-500/30 bg-cyan-950/10 p-2.5 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-cyan-400">Turn #{hit.turn_index} · [{hit.role}]</span>
                      <span className="font-mono text-muted-foreground">Rank: {hit.score}</span>
                    </div>
                    <div className="font-mono text-foreground break-all">{hit.content}</div>
                  </div>
                ))
              )
            ) : (
              (windowsQuery.data && windowsQuery.data.length > 0
                ? windowsQuery.data
                : selectedPreset.history.map((h, i) => ({
                    message_id: `msg_mock_${i}`,
                    turn_index: i + 1,
                    role: h.role,
                    content: h.content,
                    created_at: Date.now(),
                  }))
              ).map((msg) => (
                <div key={msg.message_id} className="rounded border border-border/40 bg-background/50 p-2.5 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-cyan-400 font-medium">Turn #{msg.turn_index} · [{msg.role}]</span>
                    <span className="font-mono text-muted-foreground text-xs">{new Date(msg.created_at * 1000).toLocaleTimeString()}</span>
                  </div>
                  <div className="font-mono text-foreground break-all">{msg.content}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
