import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'

export interface HttpStatusItem {
  codeGroup: string
  labelKey: string
  count: number
  color: string
}

export interface HttpStatusChartProps {
  total: number
  successRate: number
  statusCounts?: {
    code2xx?: number
    code3xx?: number
    code4xx?: number
    code5xx?: number
  }
  isHealthy?: boolean
}

export function HttpStatusChart({
  total = 0,
  successRate = 1.0,
  statusCounts = { code2xx: 0, code3xx: 0, code4xx: 0, code5xx: 0 },
  isHealthy = true,
}: HttpStatusChartProps) {
  const { t } = useTranslation('monitoringPage')

  // 避免样本为 0 时的除零计算
  const count2xx = statusCounts.code2xx ?? Math.round(total * successRate)
  const count4xx = statusCounts.code4xx ?? Math.round(total * (1 - successRate) * 0.7)
  const count5xx = statusCounts.code5xx ?? Math.round(total * (1 - successRate) * 0.3)
  const count3xx = statusCounts.code3xx ?? 0

  const chartData: HttpStatusItem[] = [
    { codeGroup: '2xx', labelKey: 'httpStatusCard.code2xx', count: count2xx, color: '#10b981' },
    { codeGroup: '3xx', labelKey: 'httpStatusCard.code3xx', count: count3xx, color: '#3b82f6' },
    { codeGroup: '4xx', labelKey: 'httpStatusCard.code4xx', count: count4xx, color: '#f59e0b' },
    { codeGroup: '5xx', labelKey: 'httpStatusCard.code5xx', count: count5xx, color: '#f43f5e' },
  ].filter((item) => item.count > 0 || total === 0)

  const formattedSuccessRate = (successRate * 100).toFixed(1)

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('httpStatusCard.title')}</CardTitle>
        <Badge
          variant="outline"
          className={cn(
            'gap-1 font-normal',
            isHealthy
              ? 'border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
              : 'border-destructive/30 text-destructive',
          )}
        >
          <span
            className={cn(
              'size-1.5 rounded-full',
              isHealthy ? 'bg-emerald-500' : 'bg-destructive',
            )}
          />
          {isHealthy ? t('httpStatusCard.healthy') : t('httpStatusCard.unhealthy')}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        {/* 左侧：2 个核心概览指标 */}
        <div className="flex flex-col gap-3">
          <div className="flex flex-col justify-center rounded-lg border bg-emerald-500/10 border-emerald-500/20 px-3.5 py-2.5">
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              {t('httpStatusCard.successRate')}
            </span>
            <span className="font-mono text-xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums mt-0.5">
              {formattedSuccessRate}%
            </span>
          </div>

          <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3.5 py-2.5">
            <span className="text-xs text-muted-foreground font-medium">
              {t('httpStatusCard.totalRequests')}
            </span>
            <span className="font-mono text-xl font-bold text-foreground tabular-nums mt-0.5">
              {total.toLocaleString()}
            </span>
          </div>
        </div>

        {/* 中间：Recharts 环形饼图 (Donut Chart) */}
        <div className="h-44 w-full flex items-center justify-center">
          {total === 0 ? (
            <div className="text-xs text-muted-foreground">{t('httpStatusCard.noData')}</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={65}
                  paddingAngle={3}
                  dataKey="count"
                  nameKey="codeGroup"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as HttpStatusItem
                      const percent = total > 0 ? ((data.count / total) * 100).toFixed(1) : '0'
                      return (
                        <div className="rounded-lg border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md font-mono">
                          <p className="font-bold flex items-center gap-1.5">
                            <span className="size-2 rounded-full" style={{ backgroundColor: data.color }} />
                            {data.codeGroup}: {data.count.toLocaleString()} ({percent}%)
                          </p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* 右侧：图例说明列 */}
        <div className="flex flex-col gap-2">
          {chartData.map((item) => {
            const percent = total > 0 ? ((item.count / total) * 100).toFixed(1) : '0'
            return (
              <div
                key={item.codeGroup}
                className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-muted/20 text-xs font-mono"
              >
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                  <span className="font-sans font-medium text-foreground">{t(item.labelKey)}</span>
                </div>
                <span className="font-bold text-foreground tabular-nums">
                  {item.count.toLocaleString()} <span className="text-[10px] text-muted-foreground font-normal">({percent}%)</span>
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}
