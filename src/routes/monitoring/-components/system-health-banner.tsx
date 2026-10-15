import {
  CheckCircle2Icon,
  CircleAlertIcon,
  RefreshCwIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent } from '#/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '#/components/ui/tooltip'
import { cn } from '#/lib/utils'

export type TimeWindow = '24h' | '7d' | '30d' | 'all'

export interface SystemHealthBannerProps {
  healthy?: boolean
  healthyCount: number
  totalCount: number
  version?: string
  timeWindow: TimeWindow
  onTimeWindowChange: (window: TimeWindow) => void
  isFetching: boolean
  onRefresh: () => void
  updatedAt?: string
}

export function SystemHealthBanner({
  healthy,
  healthyCount,
  totalCount,
  version,
  timeWindow,
  onTimeWindowChange,
  isFetching,
  onRefresh,
  updatedAt,
}: SystemHealthBannerProps) {
  const { t } = useTranslation('monitoringPage')

  return (
    <div className="flex flex-col gap-3">
      {/* Top action row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
            <span className="inline-block size-2 rounded-full bg-cyan-500 animate-pulse" />
            <span className="font-semibold text-foreground">OpenViking Studio</span>
            {version && <span className="text-muted-foreground">v{version}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Time Window Switcher */}
          <div className="flex items-center rounded-lg border border-border/60 bg-muted/20 p-0.5 font-mono text-xs">
            {(['24h', '7d', '30d', 'all'] as const).map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => onTimeWindowChange(w)}
                className={cn(
                  'rounded px-2.5 py-1 text-xs font-medium transition-colors',
                  timeWindow === w
                    ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-bold shadow-none'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {w.toUpperCase()}
              </button>
            ))}
          </div>

          {updatedAt && (
            <span className="font-mono text-xs text-muted-foreground hidden sm:inline-block">
              {t('updatedAt', { time: updatedAt })}
            </span>
          )}

          <TooltipProvider delay={150}>
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isFetching}
                    onClick={onRefresh}
                    className="h-8 gap-2 px-2.5 text-xs font-normal transition-colors hover:border-cyan-500/40"
                  />
                }
              >
                <RefreshCwIcon
                  className={cn(
                    'size-3.5 text-cyan-600 dark:text-cyan-400',
                    isFetching && 'animate-spin',
                  )}
                />
                <span>{t('refresh', { defaultValue: '刷新' })}</span>
                <span className="flex items-center gap-1.5 border-l border-border/60 pl-2 font-mono text-xs text-muted-foreground">
                  <span className="size-1.5 rounded-full bg-cyan-500 animate-pulse" />
                  60s 自动
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" align="end" className="max-w-xs space-y-1.5 p-3 text-xs shadow-lg">
                <div className="flex items-center gap-1.5 font-medium text-foreground">
                  <span className="size-2 rounded-full bg-cyan-500" />
                  <span>自动刷新：已开启 (60s 惰性感应)</span>
                </div>
                <p className="text-muted-foreground leading-relaxed text-xs">
                  {t('metricsTiles.autoRefreshStatus.tooltip', {
                    defaultValue: '前端 60s 惰性视口焦点感知自动刷新状态。离开页面即 100% 挂起停止拉取，返回页面自动恢复，零无用网络开销。',
                  })}
                </p>
                <div className="flex items-center gap-1 pt-1 text-xs text-cyan-600 dark:text-cyan-400 border-t border-border/40 font-mono">
                  <span>⚡</span>
                  <span>随时点击按钮即刻手动刷新</span>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Main Health Card */}
      <Card className="gap-0 overflow-hidden py-0 border-border/60 bg-card/60">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'flex size-9 items-center justify-center rounded-lg',
                healthy
                  ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                  : 'bg-destructive/10 text-destructive',
              )}
            >
              {healthy ? (
                <CheckCircle2Icon className="size-4" />
              ) : (
                <CircleAlertIcon className="size-4" />
              )}
            </div>
            <div>
              <p className="font-semibold text-xs text-foreground tracking-tight">
                {healthy
                  ? t('summary.healthy', { defaultValue: '全系统核心组件运行稳健' })
                  : t('summary.unhealthy', { defaultValue: '系统组件存在异常待检查' })}
              </p>
              <p className="font-mono text-xs text-muted-foreground">
                {t('summary.components', {
                  healthy: healthyCount,
                  total: totalCount,
                  defaultValue: `${healthyCount} / ${totalCount} 核心组件健康就绪`,
                })}
              </p>
            </div>
          </div>

          <Badge
            variant="outline"
            className={cn(
              'gap-1.5 font-normal text-xs',
              healthy
                ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                : 'border-destructive/30 text-destructive',
            )}
          >
            <span
              className={cn(
                'size-1.5 rounded-full',
                healthy ? 'bg-cyan-500' : 'bg-destructive',
              )}
            />
            {healthy
              ? t('health.healthy', { defaultValue: '健康正常' })
              : t('health.unhealthy', { defaultValue: '存在异常' })}
          </Badge>
        </CardContent>
      </Card>
    </div>
  )
}
