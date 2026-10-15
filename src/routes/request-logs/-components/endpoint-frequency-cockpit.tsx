import * as React from 'react'
import {
  ActivityIcon,
  FlameIcon,
  MoonIcon,
  LayersIcon,
  RefreshCwIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { Card, CardContent } from '#/components/ui/card'
import type {
  EndpointFrequencyResult,
  EndpointFrequencyWindow,
} from '../-types/audit'
import { FrequencyDormantTable } from './frequency-dormant-table'
import { FrequencyHotTable } from './frequency-hot-table'

interface EndpointFrequencyCockpitProps {
  data?: EndpointFrequencyResult
  isLoading: boolean
  isFetching: boolean
  window: EndpointFrequencyWindow
  onWindowChange: (window: EndpointFrequencyWindow) => void
  onRefresh: () => void
}

const WINDOW_OPTIONS: EndpointFrequencyWindow[] = ['all', '24h', '7d', '30d']

export function EndpointFrequencyCockpit({
  data,
  isLoading,
  isFetching,
  window,
  onWindowChange,
  onRefresh,
}: EndpointFrequencyCockpitProps) {
  const { t } = useTranslation('requestLogs')
  const [activeTab, setActiveTab] = React.useState<'hot' | 'dormant' | 'category'>('hot')

  const totalCalls = data?.total_calls ?? 0
  const activeCount = data?.active_endpoints_count ?? 0
  const dormantCount = data?.dormant_endpoints_count ?? 0
  const activeRate = data?.active_rate ? (data.active_rate * 100).toFixed(1) : '0.0'

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Header Controls */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold tracking-tight">
            {t('frequency.title')}
          </h2>
          <p className="text-xs text-muted-foreground">
            {t('frequency.subtitle')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md border border-border/80 bg-muted/20 p-0.5">
            {WINDOW_OPTIONS.map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => onWindowChange(w)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  window === w
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t(`frequency.window.${w}`)}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isFetching}
            className="h-8 gap-1.5 px-2.5 text-xs"
          >
            <RefreshCwIcon className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            <span>{t('refresh')}</span>
          </Button>
        </div>
      </div>

      {/* 4 KPI Cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card className="bg-card/60">
          <CardContent className="flex items-center justify-between p-3.5">
            <div>
              <p className="text-xs text-muted-foreground">{t('metrics.total')}</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                {isLoading ? '--' : totalCalls.toLocaleString()}
              </p>
            </div>
            <div className="flex size-8 items-center justify-center rounded-md border border-cyan-500/20 bg-cyan-500/10 text-cyan-500">
              <ActivityIcon className="size-4" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/60">
          <CardContent className="flex items-center justify-between p-3.5">
            <div>
              <p className="text-xs text-muted-foreground">{t('frequency.kpi.activeEndpoints')}</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-cyan-500">
                {isLoading ? '--' : activeCount}
              </p>
            </div>
            <div className="flex size-8 items-center justify-center rounded-md border border-cyan-500/20 bg-cyan-500/10 text-cyan-500">
              <FlameIcon className="size-4" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/60">
          <CardContent className="flex items-center justify-between p-3.5">
            <div>
              <p className="text-xs text-muted-foreground">{t('frequency.kpi.dormantEndpoints')}</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-muted-foreground">
                {isLoading ? '--' : dormantCount}
              </p>
            </div>
            <div className="flex size-8 items-center justify-center rounded-md border border-border/80 bg-muted/30 text-muted-foreground">
              <MoonIcon className="size-4" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/60">
          <CardContent className="flex items-center justify-between p-3.5">
            <div>
              <p className="text-xs text-muted-foreground">{t('frequency.kpi.activeRate')}</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                {isLoading ? '--' : `${activeRate}%`}
              </p>
            </div>
            <div className="flex size-8 items-center justify-center rounded-md border border-border/80 bg-muted/30 text-muted-foreground">
              <LayersIcon className="size-4" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-border/60">
        <button
          type="button"
          onClick={() => setActiveTab('hot')}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
            activeTab === 'hot'
              ? 'border-cyan-500 text-cyan-500'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <FlameIcon className="size-3.5" />
          <span>{t('frequency.tabs.hot')} ({data?.top_hot_endpoints.length ?? 0})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('dormant')}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
            activeTab === 'dormant'
              ? 'border-cyan-500 text-cyan-500'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <MoonIcon className="size-3.5" />
          <span>{t('frequency.tabs.dormant')} ({data?.dormant_endpoints.length ?? 0})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('category')}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
            activeTab === 'category'
              ? 'border-cyan-500 text-cyan-500'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <LayersIcon className="size-3.5" />
          <span>{t('frequency.tabs.category')}</span>
        </button>
      </div>

      {/* Tab 1: Hot Endpoints */}
      {activeTab === 'hot' && (
        <FrequencyHotTable
          items={data?.top_hot_endpoints ?? []}
          isLoading={isLoading}
        />
      )}

      {/* Tab 2: Dormant Endpoints */}
      {activeTab === 'dormant' && (
        <FrequencyDormantTable items={data?.dormant_endpoints ?? []} />
      )}

      {/* Tab 3: Category Breakdown */}
      {activeTab === 'category' && (
        <div className="grid gap-3 md:grid-cols-2">
          {data?.category_breakdown.map((cat) => (
            <Card key={cat.category} className="border-border/70 bg-card/40">
              <CardContent className="p-3.5">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-xs">{cat.category}</span>
                  <span className="font-mono text-xs font-semibold tabular-nums text-cyan-500">
                    {cat.call_count.toLocaleString()} calls
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted/60">
                    <div
                      className="h-full rounded-full bg-cyan-500"
                      style={{ width: `${Math.min(cat.share_percent, 100)}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs tabular-nums text-muted-foreground">
                    {cat.share_percent.toFixed(1)}%
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
