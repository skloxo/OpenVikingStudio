import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'

export interface ModelUsageRow {
  model: string
  provider: string
  calls: number
  promptTokens: number
  completionTokens: number
  totalTokens: number
  lastUpdated: string
}

export interface ModelGroup {
  groupName: string
  rows: ModelUsageRow[]
}

function parseModelsStatus(status: string): ModelGroup[] {
  const blocks = parseObserverStatus(status)
  const groups: ModelGroup[] = []

  let currentGroupName = ''

  for (const block of blocks) {
    if (block.kind === 'text') {
      const text = block.value.trim()
      if (text.endsWith(':')) {
        currentGroupName = text.slice(0, -1).trim()
      }
    } else {
      const headers = block.headers
      const col = {
        model: headers.findIndex((h) => /^model$/i.test(h.trim()) || /model/i.test(h)),
        provider: headers.findIndex((h) => /provider/i.test(h)),
        calls: headers.findIndex((h) => /calls/i.test(h)),
        prompt: headers.findIndex((h) => /prompt/i.test(h)),
        completion: headers.findIndex((h) => /completion/i.test(h)),
        total: headers.findIndex((h) => /total/i.test(h)),
        lastUpdated: headers.findIndex((h) => /updated/i.test(h)),
      }

      const rows: ModelUsageRow[] = block.rows.map((row) => ({
        model: col.model >= 0 ? (row[col.model] ?? '') : row[0] ?? '',
        provider: col.provider >= 0 ? (row[col.provider] ?? 'openai') : 'openai',
        calls: col.calls >= 0 ? (parseInt(row[col.calls]?.replace(/,/g, '') ?? '0', 10) || 0) : 0,
        promptTokens: col.prompt >= 0 ? (parseInt(row[col.prompt]?.replace(/,/g, '') ?? '0', 10) || 0) : 0,
        completionTokens: col.completion >= 0 ? (parseInt(row[col.completion]?.replace(/,/g, '') ?? '0', 10) || 0) : 0,
        totalTokens: col.total >= 0 ? (parseInt(row[col.total]?.replace(/,/g, '') ?? '0', 10) || 0) : 0,
        lastUpdated: col.lastUpdated >= 0 ? (row[col.lastUpdated] ?? '') : '',
      }))

      if (rows.length > 0) {
        groups.push({
          groupName: currentGroupName || 'Models',
          rows,
        })
      }
    }
  }

  return groups
}

export interface ModelMonitoringCardProps {
  /** Observer system 返回的 models 组件 status 原始文本 */
  status?: string
  isHealthy?: boolean
}

export function ModelMonitoringCard({ status, isHealthy }: ModelMonitoringCardProps) {
  const { t } = useTranslation('monitoringPage')

  // 若父组件传入的 status 为空，自主向 /api/v1/observer/models 兜底发起查询，彻底杜绝无数据与异常状态漂移
  const fallbackQuery = useQuery({
    enabled: !status,
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          result?: {
            name: string
            is_healthy: boolean
            status: string
          }
        }>('/api/v1/observer/models')
        return res.data.result ?? null
      } catch {
        return null
      }
    },
    queryKey: ['observer-models-fallback'],
    staleTime: 15_000,
  })

  const rawStatus = status || fallbackQuery.data?.status || ''
  const healthy = (status ? isHealthy : fallbackQuery.data?.is_healthy) ?? true

  const groups = React.useMemo(() => {
    return parseModelsStatus(rawStatus)
  }, [rawStatus])

  // 统计汇总瓷片数据：活跃模型数严格统计 activeRows (各领域当前配置的活跃模型，计4)
  const allRows = groups.flatMap((g) => g.rows)
  const activeRows = allRows.filter(
    (r) => r.provider !== 'historical' && !r.model.includes('历史') && !r.model.includes('Historical')
  )
  const activeModelsCount = activeRows.length
  const totalCalls = allRows.reduce((sum, r) => sum + r.calls, 0)
  const totalTokens = allRows.reduce((sum, r) => sum + r.totalTokens, 0)

  const getGroupTitle = (name: string): string => {
    const lower = name.toLowerCase()
    if (lower.includes('vlm')) return t('modelsCard.vlmGroup')
    if (lower.includes('embedding')) return t('modelsCard.embeddingGroup')
    if (lower.includes('rerank')) return t('modelsCard.rerankGroup')
    if (lower.includes('encoder') || lower.includes('compress') || lower.includes('lingua')) return t('modelsCard.compressorGroup')
    return name
  }

  const fmtTime = (iso: string): string => {
    if (!iso || iso === '--') return '--'
    try {
      const d = new Date(iso)
      if (isNaN(d.getTime())) return iso
      const now = new Date()
      const sameDay =
        d.getFullYear() === now.getFullYear() &&
        d.getMonth() === now.getMonth() &&
        d.getDate() === now.getDate()
      return sameDay
        ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : d.toLocaleDateString([], { month: '2-digit', day: '2-digit' }) +
            ' ' +
            d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return iso
    }
  }

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('modelsCard.title')}</CardTitle>
        <Badge
          variant="outline"
          className={cn(
            'gap-1 font-normal',
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
          {healthy ? t('modelsCard.healthy') : t('modelsCard.unhealthy')}
        </Badge>
      </div>

      {/* 顶部 3 个关键统计汇总瓷片 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs text-muted-foreground font-medium">{t('modelsCard.activeModels')}</span>
          <span className="font-mono text-base font-bold text-foreground tabular-nums mt-0.5">
            {activeModelsCount}
          </span>
        </div>

        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">{t('modelsCard.totalCalls')}</span>
          <span className="font-mono text-base font-bold text-foreground tabular-nums mt-0.5">
            {totalCalls.toLocaleString()}
          </span>
        </div>

        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">{t('modelsCard.totalTokensTile')}</span>
          <span className="font-mono text-base font-bold text-foreground/90 tabular-nums mt-0.5">
            {totalTokens.toLocaleString()}
          </span>
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="rounded-lg border bg-muted/20 p-3 text-center text-xs text-muted-foreground">
          {status ? (
            <span className="font-mono text-xs text-foreground/80">{status}</span>
          ) : (
            t('modelsCard.noData')
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* 单头统一表头 — 8 列 */}
          <div className="grid grid-cols-8 items-center px-3 py-1 text-xs text-muted-foreground font-medium border-b border-border/50">
            <span className="col-span-2">{t('modelsCard.modelName')}</span>
            <span>{t('modelsCard.provider')}</span>
            <span className="text-right">{t('modelsCard.calls')}</span>
            <span className="text-right">{t('modelsCard.promptTokens')}</span>
            <span className="text-right">{t('modelsCard.completionTokens')}</span>
            <span className="text-right">{t('modelsCard.totalTokens')}</span>
            <span className="text-right">{t('modelsCard.lastUpdated')}</span>
          </div>

          {/* 各分类模型列表（VLM, Embedding, Rerank, Compressor），内部包含 1 行活跃配置 + 1 行历史下线模型汇总 */}
          {groups.map((group, idx) => (
            <div key={group.groupName + idx} className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-foreground/80 flex items-center gap-1.5 pt-1">
                <span className="size-1.5 rounded-full bg-primary/60" />
                {getGroupTitle(group.groupName)}
              </span>

              {group.rows.map((row, rIdx) => {
                const isHistorical =
                  row.provider === 'historical' ||
                  row.model.includes('历史') ||
                  row.model.includes('Historical')

                if (isHistorical) {
                  return (
                    <div
                      key={row.model + rIdx}
                      className="grid grid-cols-8 items-center px-3 py-1.5 text-xs rounded-md border border-dashed border-border/60 bg-muted/10 hover:bg-muted/20 font-mono transition-colors"
                    >
                      <div className="col-span-2 flex items-center gap-1.5 truncate">
                        <span className="size-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
                        <span className="font-sans text-xs text-muted-foreground truncate">
                          {row.model}
                        </span>
                      </div>
                      <div className="flex items-center">
                        <Badge
                          variant="outline"
                          className="text-[12px] font-normal border-muted-foreground/30 text-muted-foreground py-0 px-1.5"
                        >
                          {t('modelsCard.archivedBadge', '已下线归档')}
                        </Badge>
                      </div>
                      <span className="text-right text-muted-foreground tabular-nums">
                        {row.calls.toLocaleString()}
                      </span>
                      <span className="text-right text-muted-foreground/80 tabular-nums">
                        {row.promptTokens.toLocaleString()}
                      </span>
                      <span className="text-right text-muted-foreground/60 tabular-nums">
                        {row.completionTokens > 0 ? row.completionTokens.toLocaleString() : '--'}
                      </span>
                      <span className="text-right font-medium text-muted-foreground tabular-nums">
                        {row.totalTokens.toLocaleString()}
                      </span>
                      <span className="text-right text-muted-foreground/60 tabular-nums font-sans">
                        {fmtTime(row.lastUpdated)}
                      </span>
                    </div>
                  )
                }

                return (
                  <div
                    key={row.model + rIdx}
                    className="grid grid-cols-8 items-center px-3 py-2 text-xs rounded-md bg-muted/20 hover:bg-muted/40 font-mono transition-colors"
                  >
                    <span className="col-span-2 font-sans font-medium text-foreground truncate">
                      {row.model}
                    </span>
                    <span className="text-muted-foreground capitalize text-xs font-sans">
                      {row.provider}
                    </span>
                    <span className="text-right font-bold text-foreground tabular-nums">
                      {row.calls.toLocaleString()}
                    </span>
                    <span className="text-right text-muted-foreground tabular-nums">
                      {row.promptTokens.toLocaleString()}
                    </span>
                    <span className="text-right text-muted-foreground/70 tabular-nums">
                      {row.completionTokens > 0 ? row.completionTokens.toLocaleString() : '--'}
                    </span>
                    <span className="text-right font-bold text-foreground tabular-nums">
                      {row.totalTokens.toLocaleString()}
                    </span>
                    <span className="text-right text-muted-foreground tabular-nums font-sans text-[12px]">
                      {fmtTime(row.lastUpdated)}
                    </span>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
