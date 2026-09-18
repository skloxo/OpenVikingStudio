import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { EndpointFrequencyItem } from '../-types/audit'


interface FrequencyHotTableProps {
  items: EndpointFrequencyItem[]
  isLoading: boolean
}

export function FrequencyHotTable({ items, isLoading }: FrequencyHotTableProps) {
  const { t } = useTranslation('requestLogs')

  return (
    <Card className="overflow-hidden border-border/70 bg-card/40">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border/60 bg-muted/20 text-muted-foreground">
            <tr>
              <th className="px-3 py-2.5 font-medium">#</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.route')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.method')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.category')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.calls')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.share')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.avgDuration')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.errorRate')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.lastCalled')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {isLoading ? (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-xs text-muted-foreground">
                  {t('loading')}
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-xs text-muted-foreground">
                  {t('empty.title')}
                </td>
              </tr>
            ) : (
              items.map((ep, idx) => {
                const isHighError = ep.error_rate > 0.05
                return (
                  <tr key={`${ep.route}-${ep.method}`} className="hover:bg-muted/30">
                    <td className="px-3 py-2.5 font-mono text-muted-foreground">
                      {idx + 1}
                    </td>
                    <td className="max-w-70 truncate px-3 py-2.5 font-mono font-medium" title={ep.route}>
                      {ep.route}
                    </td>

                    <td className="px-3 py-2.5">
                      <Badge variant="outline" className="border-border/60 font-mono text-xs">
                        {ep.method}
                      </Badge>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      {ep.category}
                    </td>
                    <td className="px-3 py-2.5 font-mono font-medium tabular-nums">
                      {ep.call_count.toLocaleString()}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted/60">
                          <div
                            className="h-full rounded-full bg-cyan-500"
                            style={{ width: `${Math.min(ep.share_percent, 100)}%` }}
                          />
                        </div>
                        <span className="font-mono tabular-nums text-muted-foreground">
                          {ep.share_percent.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-muted-foreground">
                      {`${ep.avg_duration_ms} ms`}
                    </td>

                    <td className="px-3 py-2.5">
                      <span
                        className={`font-mono tabular-nums ${
                          isHighError ? 'text-rose-400 font-medium' : 'text-muted-foreground'
                        }`}
                      >
                        {(ep.error_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-muted-foreground">
                      {ep.last_called_at ? ep.last_called_at.replace('T', ' ').slice(0, 19) : '--'}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
