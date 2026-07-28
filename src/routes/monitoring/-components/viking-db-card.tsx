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
  const col = {
    collection: headers.findIndex((h) =>
      /collection|name|table/i.test(h),
    ),
    vectorCount: headers.findIndex((h) =>
      /vector|count|size|documents/i.test(h),
    ),
    indexCount: headers.findIndex((h) =>
      /index|indexes/i.test(h),
    ),
    status: headers.findIndex((h) =>
      /status|state|health/i.test(h),
    ),
  }

  return tableBlock.rows.map((row) => ({
    collection: col.collection >= 0 ? (row[col.collection] ?? 'default') : row[0] ?? 'default',
    vectorCount: col.vectorCount >= 0 ? parseInt(row[col.vectorCount] ?? '0', 10) || 0 : 0,
    indexCount: col.indexCount >= 0 ? parseInt(row[col.indexCount] ?? '0', 10) || 0 : 0,
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

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between">
        <CardTitle className="text-base font-semibold">{t('vikingdb.title')}</CardTitle>
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
          {isHealthy ? t('vikingdb.healthy') : t('vikingdb.unhealthy')}
        </Badge>
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
        <div className="flex flex-col gap-2">
          <div className="grid grid-cols-4 px-2 py-1 text-xs text-muted-foreground font-medium border-b border-border/50">
            <span>{t('vikingdb.collection')}</span>
            <span className="text-right">{t('vikingdb.vectorCount')}</span>
            <span className="text-right">{t('vikingdb.indexCount')}</span>
            <span className="text-right">{t('vikingdb.status')}</span>
          </div>
          {rows.map((row, i) => (
            <div
              key={row.collection + i}
              className="grid grid-cols-4 items-center px-2 py-1.5 text-xs rounded-md bg-muted/20 hover:bg-muted/40 font-mono"
            >
              <span className="font-sans font-medium text-foreground truncate">
                {getCollectionDisplayName(row.collection)}
              </span>
              <span className="text-right text-emerald-600 dark:text-emerald-400 font-bold tabular-nums">
                {row.vectorCount.toLocaleString()}
              </span>
              <span className="text-right text-muted-foreground tabular-nums">
                {row.indexCount}
              </span>
              <span className="text-right">
                <span
                  className={cn(
                    'inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold',
                    /ok|normal|healthy/i.test(row.status)
                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                      : 'bg-destructive/10 text-destructive',
                  )}
                >
                  {row.status}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
