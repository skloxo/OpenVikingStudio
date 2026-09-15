import * as React from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { ovClient } from '#/lib/ov-client'
import {
  ActivityIcon,
  ArrowLeftIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
  TerminalIcon,
  WorkflowIcon,
} from 'lucide-react'

import { HarnessFsmVisualizer } from './harness-logs/-components/harness-fsm-visualizer'
import { HarnessGateDashboard } from './harness-logs/-components/harness-gate-dashboard'
import { HarnessLivePlayground } from './harness-logs/-components/harness-live-playground'
import { HarnessLessonsTable } from './harness-logs/-components/harness-lessons-table'
import type { LessonItem } from './harness-logs/-components/harness-lessons-table'
import { HarnessAgentLoopCockpit } from './harness-logs/-components/harness-agent-loop-cockpit'

export const Route = createFileRoute('/harness-logs')({
  component: HarnessLogsPage,
})

export function HarnessLogsPage() {
  const { t } = useTranslation('skillsPage')
  const [activeTab, setActiveTab] = React.useState<'fsm' | 'gates' | 'agent-loop' | 'playground' | 'lessons'>('fsm')
  const [searchQuery, setSearchQuery] = React.useState('')

  const { connection, connectionRole, isConnectionRoleLoading } = useAppConnection()
  const canQuery = !isConnectionRoleLoading && connectionRole !== 'unknown'

  const harnessStatusQuery = useQuery({
    enabled: canQuery,
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status?: string
          window?: string
          total_calls?: number
          blocked_calls?: number
          lessons_count?: number
          lessons_detail?: LessonItem[]
          fsm?: any
          gates?: any
        }>('/api/v1/system/harness_metrics')
        return res.data
      } catch (err) {
        console.warn('Failed to fetch harness metrics:', err)
        return null
      }
    },
    queryKey: ['harness-status-full-logs-page', connection.adminApiKey, connection.apiKey],
    staleTime: 15_000,
  })

  const metrics = harnessStatusQuery.data
  const lessons = metrics?.lessons_detail ?? []

  return (
    <div className="flex flex-col gap-5 p-4 sm:p-6 max-w-7xl mx-auto w-full">
      {/* Cockpit Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-4">
        <div className="flex items-center gap-3">
          <Link to="/skills">
            <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground hover:text-foreground">
              <ArrowLeftIcon className="mr-1 size-3.5" />
              返回技能中心
            </Button>
          </Link>
          <div className="h-4 w-px bg-border/60" />
          <div>
            <h1 className="text-base font-bold tracking-tight text-foreground flex items-center gap-2">
              <ShieldCheckIcon className="size-4 text-cyan-400" />
              Harness 贯彻执行与物理门禁座舱
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              Agent = Model + Harness · 12-State Deterministic FSM & Physical Verification Cockpit
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索状态 / 规则 / 教训..."
            className="h-8 w-56 rounded border border-border/60 bg-background px-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-cyan-500 font-mono"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-xs rounded text-foreground"
            disabled={harnessStatusQuery.isFetching}
            onClick={() => void harnessStatusQuery.refetch()}
          >
            <RefreshCwIcon className={harnessStatusQuery.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
            {t('refresh')}
          </Button>
        </div>
      </div>

      {/* 4 Telemetry Metrics Ribbon */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-[11px] text-muted-foreground">物理拦截次数</div>
          <div className="mt-1 font-mono text-xl font-bold text-foreground">
            {metrics?.blocked_calls ?? 0}
            <span className="ml-1 text-xs font-normal text-muted-foreground">次阻断</span>
          </div>
        </div>

        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-[11px] text-muted-foreground">FSM 转移规则</div>
          <div className="mt-1 font-mono text-xl font-bold text-foreground">
            {metrics?.fsm?.transition_rules_count ?? 26}
            <span className="ml-1 text-xs font-normal text-muted-foreground">条有向边</span>
          </div>
        </div>

        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-[11px] text-muted-foreground">物理贯彻门禁</div>
          <div className="mt-1 font-mono text-xl font-bold text-cyan-400">
            4 / 4
            <span className="ml-1 text-xs font-normal text-muted-foreground">项已激活</span>
          </div>
        </div>

        <div className="rounded-md border border-border/60 bg-card/60 p-3">
          <div className="text-[11px] text-muted-foreground">沉淀演进教训</div>
          <div className="mt-1 font-mono text-xl font-bold text-foreground">
            {metrics?.lessons_count ?? lessons.length}
            <span className="ml-1 text-xs font-normal text-muted-foreground">项 Lessons</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-1.5 border-b border-border/60 pb-1">
        {[
          { id: 'fsm', label: '12-态状态机流水线', icon: <WorkflowIcon className="size-3.5 mr-1 text-cyan-400" /> },
          { id: 'gates', label: '四大贯彻门禁看板', icon: <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-400" /> },
          { id: 'agent-loop', label: '双层循环与主动刹车', icon: <ActivityIcon className="size-3.5 mr-1 text-cyan-400" /> },
          { id: 'playground', label: '实时交互实验场', icon: <TerminalIcon className="size-3.5 mr-1 text-cyan-400" /> },
          { id: 'lessons', label: '演进教训档案', icon: <LayersIcon className="size-3.5 mr-1 text-cyan-400" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center rounded-t-md px-3 py-1.5 text-xs font-medium transition-all ${
              activeTab === tab.id
                ? 'border-b-2 border-cyan-400 bg-card text-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active Tab Views */}
      <div className="pt-1">
        {activeTab === 'fsm' && <HarnessFsmVisualizer fsm={metrics?.fsm} />}
        {activeTab === 'gates' && <HarnessGateDashboard gates={metrics?.gates} />}
        {activeTab === 'agent-loop' && <HarnessAgentLoopCockpit />}
        {activeTab === 'playground' && <HarnessLivePlayground />}
        {activeTab === 'lessons' && <HarnessLessonsTable lessons={lessons} searchQuery={searchQuery} />}
      </div>
    </div>
  )
}
