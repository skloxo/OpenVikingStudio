import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'

interface ParsedVikingDbRow {
  collection: string
  vectorCount: number
  indexCount: number
  status: string
}

function parseVikingDbStatus(status: string): ParsedVikingDbRow[] {
  const blocks = parseObserverStatus(status)
  const tableBlock = blocks.find((b) => b.kind === 'table')
  if (!tableBlock) return []

  const headers = tableBlock.headers

  // 精准匹配列名，避免 Index Count 中的 count 被误判为 Vector Count
  const col = {
    collection: headers.findIndex((h) => /^collection$/i.test(h.trim()) || /collection/i.test(h)),
    vectorCount: headers.findIndex((h) => /vector\s*count|vectors/i.test(h.trim())),
    indexCount: headers.findIndex((h) => /index\s*count|indexes/i.test(h.trim())),
    status: headers.findIndex((h) => /^status$/i.test(h.trim()) || /status/i.test(h)),
  }

  return tableBlock.rows.map((row) => ({
    collection: col.collection >= 0 ? (row[col.collection] ?? 'default') : row[0] ?? 'default',
    vectorCount: col.vectorCount >= 0 ? parseInt(row[col.vectorCount]?.replace(/,/g, '') ?? '0', 10) || 0 : 0,
    indexCount: col.indexCount >= 0 ? parseInt(row[col.indexCount]?.replace(/,/g, '') ?? '0', 10) || 0 : 0,
    status: col.status >= 0 ? (row[col.status] ?? 'OK') : 'OK',
  }))
}

export interface VikingDbCardProps {
  /** Observer system 返回的 vikingdb 组件 status 文本 */
  status: string
  isHealthy: boolean
}

export function VikingDbCard({ status, isHealthy }: VikingDbCardProps) {
  const { t } = useTranslation('monitoringPage')
  const rows = React.useMemo(() => parseVikingDbStatus(status), [status])

  const getCollectionDisplayName = (name: string): string => {
    const lower = name.toLowerCase()
    if (lower === 'total') return t('vikingdb.total')
    if (lower === 'context') return t('vikingdb.context')
    return name
  }

  // 区分普通数据行与 TOTAL 合计行
  const normalRows = rows.filter((r) => r.collection.toUpperCase() !== 'TOTAL')
  const totalRow = rows.find((r) => r.collection.toUpperCase() === 'TOTAL')

  const totalVectors = totalRow
    ? totalRow.vectorCount
    : normalRows.reduce((sum, r) => sum + r.vectorCount, 0)
  const totalIndexes = totalRow
    ? totalRow.indexCount
    : normalRows.reduce((sum, r) => sum + r.indexCount, 0)
  const collectionCount = normalRows.length

  // 当仅有 1 个集合时，隐藏冗余的 TOTAL 行与重复列，避免三层数字叠加重复
  const isSingleCollection = collectionCount <= 1
  const displayRows = isSingleCollection ? normalRows : rows

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('vikingdb.title')}</CardTitle>
        {!isHealthy && (
          <Badge
            variant="outline"
            className="gap-1 font-normal border-destructive/30 text-destructive"
          >
            <span className="size-1.5 rounded-full bg-destructive" />
            {t('vikingdb.unhealthy')}
          </Badge>
        )}
      </div>

      {/* 顶部 3 个关键汇总指标瓷片 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-[11px] text-muted-foreground font-medium">{t('vikingdb.activeCollections')}</span>
          <span className="font-mono text-base font-bold text-foreground tabular-nums mt-0.5">
            {collectionCount}
          </span>
        </div>
        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-[11px] font-medium text-muted-foreground">{t('vikingdb.totalVectors')}</span>
          <span className="font-mono text-base font-bold text-foreground/90 tabular-nums mt-0.5">
            {totalVectors.toLocaleString()}
          </span>
        </div>
        <div className="flex flex-col justify-center rounded-lg border bg-muted/20 px-3 py-2">
          <span className="text-[11px] text-muted-foreground font-medium">{t('vikingdb.searchIndexes')}</span>
          <span className="font-mono text-base font-bold text-foreground tabular-nums mt-0.5">
            {totalIndexes}
          </span>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="rounded-lg border bg-muted/20 p-3 text-center text-xs text-muted-foreground">
          {status ? (
            <span className="font-mono text-xs text-foreground/80">{status}</span>
          ) : (
            t('vikingdb.noData')
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="grid grid-cols-4 px-3 py-1 text-xs text-muted-foreground font-medium border-b border-border/50">
            <span>{t('vikingdb.collection')}</span>
            <span className="text-right">{t('vikingdb.vectorCount')}</span>
            <span className="text-right">{t('vikingdb.indexCount')}</span>
            <span className="text-right">{t('vikingdb.status')}</span>
          </div>
          {displayRows.map((row, i) => {
            const isTotalRow = row.collection.toUpperCase() === 'TOTAL'
            return (
              <div
                key={row.collection + i}
                className={cn(
                  'grid grid-cols-4 items-center px-3 py-2 text-xs rounded-md font-mono transition-colors',
                  isTotalRow
                    ? 'bg-muted/60 font-bold border border-border/80 text-foreground mt-1'
                    : 'bg-muted/20 hover:bg-muted/40 text-foreground/90',
                )}
              >
                <span className="font-sans font-medium truncate">
                  {getCollectionDisplayName(row.collection)}
                </span>
                <span
                  className={cn(
                    'text-right font-bold tabular-nums',
                    row.vectorCount > 0 ? 'text-foreground/90' : 'text-muted-foreground/60',
                  )}
                >
                  {row.vectorCount.toLocaleString()}
                </span>
                <span className="text-right text-muted-foreground tabular-nums">
                  {row.indexCount}
                </span>
                <span className="text-right">
                  <span
                    className={cn(
                      'inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold',
                      /ok|normal|healthy/i.test(row.status)
                        ? 'bg-muted/20 text-foreground/90'
                        : 'bg-destructive/10 text-destructive',
                    )}
                  >
                    {row.status}
                  </span>
                </span>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
