import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { ovClient } from '#/lib/ov-client'
import {
  ActivityIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  WorkflowIcon,
  FileCodeIcon,
  DnaIcon,
} from 'lucide-react'

import { HarnessFsmVisualizer } from '#/routes/harness-logs/-components/harness-fsm-visualizer'
import { HarnessGateDashboard } from '#/routes/harness-logs/-components/harness-gate-dashboard'
import { HarnessAgentLoopCockpit } from '#/routes/harness-logs/-components/harness-agent-loop-cockpit'
import { HarnessFailureWhitelistRadar } from '#/routes/harness-logs/-components/harness-failure-whitelist-radar'
import { HarnessHITLOffloadCenter } from '#/routes/harness-logs/-components/harness-hitl-offload-center'

export function HarnessGuardrailsCockpit() {
  const { t } = useTranslation('skillsPage')
  const [activeSubTab, setActiveSubTab] = React.useState<'gates' | 'fsm' | 'agent-loop' | 'failure-radar' | 'hitl-offload'>('gates')
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
          fsm?: any
          gates?: any
        }>('/api/v1/system/harness_metrics')
        return res.data
      } catch (err) {
        console.warn('Failed to fetch harness metrics:', err)
        return null
      }
    },
    queryKey: ['harness-guardrails-in-logs', connection.adminApiKey, connection.apiKey],
    staleTime: 15_000,
  })

  const metrics = harnessStatusQuery.data
  const activeGatesCount = metrics?.gates
    ? Object.values(metrics.gates).filter((g: any) => g.status === 'active').length
    : 5
  const totalGatesCount = metrics?.gates ? Object.keys(metrics.gates).length : 5

  return (
    <div className="flex flex-col gap-4">
      {/* KPI Overview Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-md border border-border/70 bg-card p-3 shadow-xs">
          <div className="text-xs text-muted-foreground">物理贯彻门禁</div>
          <div className="mt-1 font-mono text-xl font-bold text-cyan-700 dark:text-cyan-400">
            {activeGatesCount} / {totalGatesCount}
            <span className="ml-1 text-xs font-normal text-muted-foreground">项已激活</span>
          </div>
        </div>

        <div className="rounded-md border border-border/70 bg-card p-3 shadow-xs">
          <div className="text-xs text-muted-foreground">确定性状态机</div>
          <div className="mt-1 font-mono text-xl font-bold text-cyan-700 dark:text-cyan-400">
            {metrics?.fsm?.states?.length ?? 12}
            <span className="ml-1 text-xs font-normal text-muted-foreground">态 Deterministic</span>
          </div>
        </div>

        <div className="rounded-md border border-border/70 bg-card p-3 shadow-xs">
          <div className="text-xs text-muted-foreground">FSM 转移规则</div>
          <div className="mt-1 font-mono text-xl font-bold text-foreground">
            {metrics?.fsm?.transition_rules_count ?? 26}
            <span className="ml-1 text-xs font-normal text-muted-foreground">条有向边</span>
          </div>
        </div>

        <div className="rounded-md border border-border/70 bg-card p-3 shadow-xs flex flex-col justify-between">
          <div className="text-xs text-muted-foreground">演进与自愈中心联动</div>
          <div className="mt-1">
            <Link to="/evolution" search={{ tab: 'lessons' }}>
              <Button size="sm" variant="outline" className="h-7 w-full text-xs font-mono text-cyan-800 dark:text-cyan-400 border-cyan-300 dark:border-cyan-800/40 bg-cyan-50 dark:bg-cyan-950/20 hover:bg-cyan-100 dark:hover:bg-cyan-950/40 cursor-pointer">
                <DnaIcon className="mr-1 size-3" />
                查看演进教训与自愈 ➔
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Sub Tabs Navigation */}
      <div className="flex items-center justify-between border-b border-border/60 pb-1">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {[
            { id: 'gates', label: '五大物理门禁看板', icon: <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
            { id: 'fsm', label: '12-态状态机执行流', icon: <WorkflowIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
            { id: 'agent-loop', label: '双层循环与主动刹车', icon: <ActivityIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
            { id: 'failure-radar', label: '失败画像与白名单雷达', icon: <ShieldAlertIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
            { id: 'hitl-offload', label: '读Offload与HITL', icon: <FileCodeIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" /> },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveSubTab(tab.id as any)}
              className={`flex items-center rounded-t-md px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                activeSubTab === tab.id
                  ? 'border-b-2 border-cyan-600 dark:border-cyan-400 bg-card text-foreground font-semibold'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-7 text-xs rounded text-foreground"
          disabled={harnessStatusQuery.isFetching}
          onClick={() => void harnessStatusQuery.refetch()}
        >
          <RefreshCwIcon className={harnessStatusQuery.isFetching ? 'size-3 animate-spin mr-1' : 'size-3 mr-1'} />
          {t('refresh')}
        </Button>
      </div>

      {/* Active SubTab Views */}
      <div className="pt-1">
        {activeSubTab === 'gates' && <HarnessGateDashboard gates={metrics?.gates} />}
        {activeSubTab === 'fsm' && <HarnessFsmVisualizer fsm={metrics?.fsm} />}
        {activeSubTab === 'agent-loop' && <HarnessAgentLoopCockpit />}
        {activeSubTab === 'failure-radar' && <HarnessFailureWhitelistRadar />}
        {activeSubTab === 'hitl-offload' && <HarnessHITLOffloadCenter />}
      </div>
    </div>
  )
}
