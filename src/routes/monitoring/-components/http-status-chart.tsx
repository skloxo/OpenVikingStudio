import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'

export interface ExactStatusCodeItem {
  code: number
  count: number
  color: string
  label: string
}

export interface HttpStatusChartProps {
  total: number
  successRate: number
  codeMap?: Record<number, number>
  isHealthy?: boolean
}

// 为常用具体状态码分配语义颜色与含义标签
function getStatusCodeInfo(code: number): { color: string; label: string } {
  switch (code) {
    case 200:
      return { color: '#10b981', label: 'HTTP 200 (成功)' }
    case 201:
      return { color: '#34d399', label: 'HTTP 201 (已创建)' }
    case 204:
      return { color: '#6ee7b7', label: 'HTTP 204 (无内容)' }
    case 304:
      return { color: '#3b82f6', label: 'HTTP 304 (缓存未修改)' }
    case 400:
      return { color: '#f59e0b', label: 'HTTP 400 (请求参数错误)' }
    case 401:
      return { color: '#fbbf24', label: 'HTTP 401 (未授权)' }
    case 403:
      return { color: '#d97706', label: 'HTTP 403 (拒绝访问)' }
    case 404:
      return { color: '#f97316', label: 'HTTP 404 (资源未找到)' }
    case 500:
      return { color: '#f43f5e', label: 'HTTP 500 (服务器内部错误)' }
    case 502:
      return { color: '#e11d48', label: 'HTTP 502 (网关错误)' }
    case 503:
      return { color: '#be123c', label: 'HTTP 503 (服务不可用)' }
    default:
      if (code >= 200 && code < 300) return { color: '#10b981', label: `HTTP ${code} (成功)` }
      if (code >= 300 && code < 400) return { color: '#3b82f6', label: `HTTP ${code} (重定向)` }
      if (code >= 400 && code < 500) return { color: '#f59e0b', label: `HTTP ${code} (客户端错误)` }
      return { color: '#f43f5e', label: `HTTP ${code} (服务端错误)` }
  }
}

export function HttpStatusChart({
  total = 0,
  successRate = 1.0,
  codeMap = {},
  isHealthy = true,
}: HttpStatusChartProps) {
  const { t } = useTranslation('monitoringPage')

  // 将全量 total 扩展映射到对应的 status code 分布
  const chartData: ExactStatusCodeItem[] = React.useMemo(() => {
    const entries = Object.entries(codeMap)
    if (entries.length === 0) {
      if (total > 0) {
        const successCount = Math.round(total * successRate)
        const errorCount = total - successCount
        const result: ExactStatusCodeItem[] = [
          { code: 200, count: successCount, ...getStatusCodeInfo(200) },
        ]
        if (errorCount > 0) {
          result.push({ code: 500, count: errorCount, ...getStatusCodeInfo(500) })
        }
        return result
      }
      return []
    }

    const mapSum = entries.reduce((acc, [, val]) => acc + (Number(val) || 0), 0)
    const factor = total > 0 && mapSum > 0 ? total / mapSum : 1

    return entries
      .map(([codeStr, count]) => {
        const code = parseInt(codeStr, 10)
        const info = getStatusCodeInfo(code)
        const rawCount = Number(count) || 0
        const scaledCount = Math.round(rawCount * factor)
        return {
          code,
          count: scaledCount,
          color: info.color,
          label: info.label,
        }
      })
      .filter((item) => item.count > 0)
      .sort((a, b) => b.count - a.count)
  }, [codeMap, total, successRate])

  const sampleTotal = chartData.reduce((sum, item) => sum + item.count, 0)
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

      {chartData.length === 0 ? (
        <div className="rounded-lg border bg-muted/20 p-6 text-center text-xs text-muted-foreground">
          {t('httpStatusCard.noData')}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          {/* 左侧：概览指标 */}
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
              <span className="text-xs text-muted-foreground font-medium truncate" title={t('httpStatusCard.totalRequests')}>
                {t('httpStatusCard.totalRequests')}
              </span>
              <span className="font-mono text-xl font-bold text-foreground tabular-nums mt-0.5">
                {total.toLocaleString()}
              </span>
            </div>
          </div>

          {/* 中间：Recharts 环形饼图 */}
          <div className="h-44 w-full flex items-center justify-center">
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
                  nameKey="label"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as ExactStatusCodeItem
                      const percent = sampleTotal > 0 ? ((data.count / sampleTotal) * 100).toFixed(1) : '100'
                      return (
                        <div className="rounded-lg border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md font-mono">
                          <p className="font-bold flex items-center gap-1.5">
                            <span className="size-2 rounded-full" style={{ backgroundColor: data.color }} />
                            {data.label}: {data.count.toLocaleString()} ({percent}%)
                          </p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 右侧：全量状态码图例 */}
          <div className="flex flex-col gap-2">
            {chartData.map((item) => {
              const percent = sampleTotal > 0 ? ((item.count / sampleTotal) * 100).toFixed(1) : '100'
              return (
                <div
                  key={item.code}
                  className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-muted/20 text-xs font-mono"
                >
                  <div className="flex items-center gap-2">
                    <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="font-sans font-medium text-foreground">{item.label}</span>
                  </div>
                  <span className="font-bold text-foreground tabular-nums">
                    {item.count.toLocaleString()} <span className="text-[10px] text-muted-foreground font-normal">({percent}%)</span>
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </Card>
  )
}
