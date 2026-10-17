import * as React from 'react'
import { HelpCircleIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { DormantEndpointItem } from '../-types/audit'

interface FrequencyDormantTableProps {
  items: DormantEndpointItem[]
}

export function FrequencyDormantTable({ items }: FrequencyDormantTableProps) {
  const { t } = useTranslation('requestLogs')

  return (
    <Card className="overflow-hidden border-border/70 bg-card/40">
      <div className="border-b border-border/60 bg-muted/20 px-3.5 py-2.5 text-xs text-muted-foreground flex items-center gap-1.5">
        <HelpCircleIcon className="size-3.5 shrink-0" />
        <span>{t('frequency.dormantTips')}</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border/60 bg-muted/20 text-muted-foreground">
            <tr>
              <th className="px-3 py-2.5 font-medium">#</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.route')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.methods')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.category')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.calls')}</th>
              <th className="px-3 py-2.5 font-medium">{t('frequency.table.recommendation')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-xs text-muted-foreground">
                  {t('frequency.dormantZeroAlert')}
                </td>
              </tr>
            ) : (
              items.map((dep, idx) => (
                <tr key={dep.route} className="hover:bg-muted/30">
                  <td className="px-3 py-2.5 font-mono text-muted-foreground">
                    {idx + 1}
                  </td>
                  <td className="px-3 py-2.5 font-mono font-medium text-foreground">
                    {dep.route}
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {dep.methods.map((m) => (
                        <Badge key={m} variant="outline" className="border-border/60 font-mono text-xs">
                          {m}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground">
                    {dep.category}
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge variant="secondary" className="font-mono text-xs text-muted-foreground">
                      0 calls
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground">
                    {dep.recommendation}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
