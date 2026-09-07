import { CpuIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import type { ParsedModelItem } from '../../-lib/settings-types'

function ModelTile({
  item,
  title,
  showTokens = true,
}: {
  item: ParsedModelItem | undefined
  title: string
  showTokens?: boolean
}) {
  const { t } = useTranslation('settings')
  return (
    <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          {title}
        </span>
        <Badge
          variant="outline"
          className={cn(
            'px-1.5 py-0 text-[11px]',
            item
              ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-500'
              : 'border-border text-muted-foreground',
          )}
        >
          {item ? 'Ready' : '--'}
        </Badge>
      </div>
      <div
        className="font-mono text-xs font-semibold text-foreground truncate"
        title={item?.model || '--'}
      >
        {item?.model || '--'}
      </div>
      <div className="text-[11px] text-muted-foreground">
        {t('hub.models.provider')}:{' '}
        <span className="font-mono text-foreground">
          {item?.provider || '--'}
        </span>
      </div>
      <div className="text-[11px] text-muted-foreground/80 font-mono tabular-nums truncate">
        {item
          ? showTokens
            ? `${t('hub.models.calls')}: ${Number(item.calls).toLocaleString()} · ${t('hub.models.tokens')}: ${Number(item.totalTokens).toLocaleString()}`
            : `${t('hub.models.calls')}: ${Number(item.calls).toLocaleString()}`
          : t('hub.models.noActiveModel')}
      </div>
    </div>
  )
}

interface ModelsPanoramaCardProps {
  activeVlm?: ParsedModelItem
  activeEmbedding?: ParsedModelItem
  activeRerank?: ParsedModelItem
  activeCompressor?: ParsedModelItem
}

export function ModelsPanoramaCard({
  activeVlm,
  activeEmbedding,
  activeRerank,
  activeCompressor,
}: ModelsPanoramaCardProps) {
  const { t } = useTranslation('settings')

  return (
    <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
      <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
            <CpuIcon className="size-4" />
          </div>
          <div>
            <CardTitle className="text-sm font-semibold">
              {t('hub.models.title')}
            </CardTitle>
            <p className="text-[11px] text-muted-foreground">
              {t('hub.models.description')}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
        <ModelTile title={t('hub.models.vlm')} item={activeVlm} />
        <ModelTile title={t('hub.models.embedding')} item={activeEmbedding} />
        <ModelTile title={t('hub.models.rerank')} item={activeRerank} />
        <ModelTile
          title={t('hub.models.compressor')}
          item={activeCompressor}
          showTokens={false}
        />
      </CardContent>
    </Card>
  )
}
