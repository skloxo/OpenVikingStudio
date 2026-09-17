import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDownIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
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
  status: string
  isHealthy: boolean
}

export function ModelMonitoringCard({ status, isHealthy }: ModelMonitoringCardProps) {
  const { t } = useTranslation('monitoringPage')
  const [showArchived, setShowArchived] = React.useState(false)

  const groups = React.useMemo(() => {
    return parseModelsStatus(status)
  }, [status])

  const activeGroups = React.useMemo(() => {
    return groups.filter((g) => !g.groupName.toLowerCase().includes('archive'))
  }, [groups])

  const archivedGroup = React.useMemo(() => {
    return groups.find((g) => g.groupName.toLowerCase().includes('archive'))
  }, [groups])

  // 统计汇总瓷片数据：活跃模型数严格统计 activeGroups 中的行数 (4)
  const activeRows = activeGroups.flatMap((g) => g.rows)
  const activeModelsCount = activeRows.length
  const allRows = groups.flatMap((g) => g.rows)
  const totalCalls = allRows.reduce((sum, r) => sum + r.calls, 0)
  const totalTokens = allRows.reduce((sum, r) => sum + r.totalTokens, 0)

  const getGroupTitle = (name: string): string => {
    const lower = name.toLowerCase()
    if (lower.includes('vlm')) return t('modelsCard.vlmGroup')
    if (lower.includes('embedding')) return t('modelsCard.embeddingGroup')
    if (lower.includes('rerank')) return t('modelsCard.rerankGroup')
    if (lower.includes('encoder') || lower.includes('compress') || lower.includes('lingua')) return t('modelsCard.compressorGroup')
    if (lower.includes('archive')) return t('modelsCard.archivedGroup')
    return name
  }

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('modelsCard.title')}</CardTitle>
        {!isHealthy && (
          <Badge
            variant="outline"
            className="gap-1 font-normal border-destructive/30 text-destructive"
          >
            <span className="size-1.5 rounded-full bg-destructive" />
            {t('modelsCard.unhealthy')}
          </Badge>
        )}
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

      {activeGroups.length === 0 && !archivedGroup ? (
        <div className="rounded-lg border bg-muted/20 p-3 text-center text-xs text-muted-foreground">
          {status ? (
            <span className="font-mono text-xs text-foreground/80">{status}</span>
          ) : (
            t('modelsCard.noData')
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* 单头统一表头（避免每个分类重复打印表头） */}
          <div className="grid grid-cols-6 items-center px-3 py-1 text-xs text-muted-foreground font-medium border-b border-border/50">
            <span className="col-span-2">{t('modelsCard.modelName')}</span>
            <span>{t('modelsCard.provider')}</span>
            <span className="text-right">{t('modelsCard.calls')}</span>
            <span className="text-right">{t('modelsCard.promptTokens')}</span>
            <span className="text-right">{t('modelsCard.totalTokens')}</span>
          </div>

          {/* 活跃模型列表（VLM, Embedding, Rerank, Compressor） */}
          {activeGroups.map((group, idx) => (
            <div key={group.groupName + idx} className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-foreground/80 flex items-center gap-1.5 pt-1">
                <span className="size-1.5 rounded-full bg-primary/60" />
                {getGroupTitle(group.groupName)}
              </span>

              {group.rows.map((row, rIdx) => (
                <div
                  key={row.model + rIdx}
                  className="grid grid-cols-6 items-center px-3 py-2 text-xs rounded-md bg-muted/20 hover:bg-muted/40 font-mono transition-colors"
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
                  <span className="text-right font-bold text-foreground tabular-nums">
                    {row.totalTokens.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          ))}

          {/* 历史已下线模型概括合计卡片 (折叠展开) */}
          {archivedGroup && archivedGroup.rows.length > 0 && (
            <div className="flex flex-col gap-2 pt-3 border-t border-border/50">
              <button
                type="button"
                onClick={() => setShowArchived((prev) => !prev)}
                className="flex items-center justify-between px-3 py-2 text-xs rounded-md bg-muted/15 hover:bg-muted/30 transition-colors text-muted-foreground hover:text-foreground text-left"
              >
                <div className="flex items-center gap-2">
                  <span className="size-1.5 rounded-full bg-muted-foreground/40" />
                  <span className="font-sans font-medium text-xs text-foreground/80">
                    {t('modelsCard.archivedGroup')} ({archivedGroup.rows.length})
                  </span>
                </div>
                <div className="flex items-center gap-4 font-mono text-xs">
                  <span>
                    {t('modelsCard.archivedCalls')}:{' '}
                    <strong className="text-foreground">
                      {archivedGroup.rows.reduce((s, r) => s + r.calls, 0).toLocaleString()}
                    </strong>
                  </span>
                  <span>
                    {t('modelsCard.archivedTokens')}:{' '}
                    <strong className="text-foreground">
                      {archivedGroup.rows.reduce((s, r) => s + r.totalTokens, 0).toLocaleString()}
                    </strong>
                  </span>
                  <ChevronDownIcon
                    className={cn(
                      'size-3.5 transition-transform duration-200 text-muted-foreground',
                      showArchived && 'rotate-180 text-foreground'
                    )}
                  />
                </div>
              </button>

              {showArchived && (
                <div className="flex flex-col gap-1 pl-1">
                  {archivedGroup.rows.map((row, rIdx) => (
                    <div
                      key={row.model + rIdx}
                      className="grid grid-cols-6 items-center px-3 py-1.5 text-xs rounded-md bg-muted/10 hover:bg-muted/20 font-mono text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <span className="col-span-2 font-sans truncate">
                        {row.model}
                      </span>
                      <span className="capitalize text-xs font-sans text-muted-foreground/80">
                        {row.provider}
                      </span>
                      <span className="text-right tabular-nums">
                        {row.calls.toLocaleString()}
                      </span>
                      <span className="text-right tabular-nums">
                        {row.promptTokens.toLocaleString()}
                      </span>
                      <span className="text-right font-medium text-foreground/80 tabular-nums">
                        {row.totalTokens.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
