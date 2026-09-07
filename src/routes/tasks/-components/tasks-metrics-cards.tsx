import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { Card } from '#/components/ui/card'
import { QueueStatusCard } from '#/routes/monitoring/-components/queue-status-card'
import type { ParsedQueueRow } from '#/routes/monitoring/-components/queue-status-card'

export interface TaskKpiData {
  total: number
  completed: number
  running: number
  pending: number
  failed: number
  successRate: number
  avgDurationSec: number
  topType: string
  topCount: number
  typeRows: any[]
}

interface TasksMetricsCardsProps {
  kpiData: TaskKpiData
  queueObserverRows: ParsedQueueRow[]
  isQueueLoading: boolean
}

export function TasksMetricsCards({
  kpiData,
  queueObserverRows,
  isQueueLoading,
}: TasksMetricsCardsProps) {
  const { t } = useTranslation('tasksPage')

  return (
    <div className="flex flex-col gap-3.5">
      {/* 4 大 Task 核心运行 KPI 观察行 */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.successRate')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.successRate.toFixed(1)}%
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.scopeNote', { total: kpiData.total, failed: kpiData.failed })}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.avgDuration')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.avgDurationSec < 1
                ? `${(kpiData.avgDurationSec * 1000).toFixed(0)}ms`
                : `${kpiData.avgDurationSec.toFixed(1)}s`}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.avgNote')}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.totalTasks')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {t('pipeline.kpi.tasksCount', { count: kpiData.total })}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.completedNote', { completed: kpiData.completed })}
          </p>
        </Card>

        <Card className="flex flex-col gap-1 p-3 shadow-none transition-colors hover:border-primary/40">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium">
              {t('pipeline.kpi.activePending')}
            </span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-xl font-bold tabular-nums text-foreground">
              {kpiData.running} / {kpiData.pending}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {t('pipeline.kpi.activeNote')}
          </p>
        </Card>
      </div>

      {/* 业务任务状态 (8 种任务) 与 执行引擎状态 (7 大引擎) 50/50 并排观测行 */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
        {/* 左侧 (50% 宽度 - 优先看上层任务): 业务任务状态 (8 种任务) */}
        <div>
          <QueueStatusCard
            title={t('pipeline.taskQueueStatus')}
            customRows={kpiData.typeRows}
            isHealthy={kpiData.failed === 0}
            isTaskCard={true}
          />
        </div>

        {/* 右侧 (50% 宽度 - 拆分出的下层工序): 执行引擎状态 (7 大引擎) */}
        <div>
          <QueueStatusCard
            title={t('pipeline.processQueueStatus')}
            customRows={queueObserverRows}
            isLoading={isQueueLoading && queueObserverRows.length === 0}
            isHealthy={kpiData.failed === 0}
          />
        </div>
      </div>
    </div>
  )
}
