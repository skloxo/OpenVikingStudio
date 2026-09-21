import { useTranslation } from 'react-i18next'
import { Cpu, Database, Layers, Sparkles } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'

export interface KnowledgeBaseOverviewProps {
  vectorCount?: number
  collectionCount?: number
  totalAssets?: number
  isLoading?: boolean
}

export function KnowledgeBaseOverview({
  vectorCount = 0,
  collectionCount = 1,
  totalAssets = 0,
  isLoading = false,
}: KnowledgeBaseOverviewProps) {
  const { t } = useTranslation('home')

  return (
    <Card className="flex flex-col gap-4 p-4 shadow-none transition-all hover:border-primary/40 bg-card">
      {/* 卡片头部：向量引擎空间 */}
      <div className="flex items-center justify-between border-b pb-3 border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Cpu className="size-4.5" />
          </div>
          <div className="flex flex-col">
            <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2">
              {t('knowledgeBaseOverview.vectorEngineTitle')}
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {t('knowledgeBaseOverview.subtitle')}
            </span>
          </div>
        </div>
        <Badge
          variant="outline"
          className="gap-1 border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-normal px-2.5 py-1 text-xs"
        >
          <Sparkles className="size-3 text-cyan-500" />
          {t('knowledgeBaseOverview.healthyEngine')}
        </Badge>
      </div>

      {/* 向量引擎 Vector 空间核心指标栅格 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* 总向量数据量 */}
        <div className="flex flex-col rounded-lg border bg-muted/20 p-3 transition-colors hover:bg-muted/30">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.totalVectors')}
            </span>
            <Database className="size-3.5 text-cyan-500/70" />
          </div>
          <span className="font-mono text-lg font-bold text-cyan-600 dark:text-cyan-400 tabular-nums mt-1">
            {isLoading ? '...' : vectorCount.toLocaleString()}
          </span>
        </div>

        {/* 维度的集合空间 */}
        <div className="flex flex-col rounded-lg border bg-muted/20 p-3 transition-colors hover:bg-muted/30">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.activeCollections')}
            </span>
            <Layers className="size-3.5 text-blue-500/70" />
          </div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="font-mono text-lg font-bold text-foreground tabular-nums">
              {collectionCount}
            </span>
            <span className="text-xs text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.spacesUnit')}
            </span>
          </div>
        </div>

        {/* 底层计算关联资产 */}
        <div className="flex flex-col rounded-lg border bg-muted/20 p-3 transition-colors hover:bg-muted/30">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.totalAssetsLabel')}
            </span>
            <span className="text-xs text-muted-foreground font-mono">SSOT</span>
          </div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="font-mono text-lg font-bold text-foreground tabular-nums">
              {isLoading ? '...' : totalAssets.toLocaleString()}
            </span>
            <span className="text-xs text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.nodeUnit')}
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}
