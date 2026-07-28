import { useTranslation } from 'react-i18next'
import { Brain, Cpu, Database, FileText, Layers, Sparkles, Wrench } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card, CardTitle } from '#/components/ui/card'

export interface KnowledgeBaseOverviewProps {
  memoryCount?: number
  resourceCount?: number
  skillCount?: number
  vectorCount?: number
  collectionCount?: number
  isLoading?: boolean
}

export function KnowledgeBaseOverview({
  memoryCount = 0,
  resourceCount = 0,
  skillCount = 0,
  vectorCount = 0,
  collectionCount = 1,
  isLoading = false,
}: KnowledgeBaseOverviewProps) {
  const { t } = useTranslation('home')

  const totalAssets = memoryCount + resourceCount + skillCount

  return (
    <Card className="flex flex-col gap-5 p-5 shadow-none transition-all hover:border-primary/40 bg-card">
      {/* 卡片头部 */}
      <div className="flex items-center justify-between border-b pb-3.5 border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Database className="size-5" />
          </div>
          <div className="flex flex-col">
            <CardTitle className="text-base font-semibold text-foreground">
              {t('knowledgeBaseOverview.title')}
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {t('knowledgeBaseOverview.subtitle')}
            </span>
          </div>
        </div>
        <Badge
          variant="outline"
          className="gap-1 border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-normal px-2.5 py-1"
        >
          <Sparkles className="size-3 text-emerald-500" />
          {t('knowledgeBaseOverview.healthyEngine')}
        </Badge>
      </div>

      {/* 上半部分：3 大业务资产节点瓷片 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* 记忆库 Memory */}
        <div className="flex items-center gap-3 rounded-xl border bg-muted/20 p-3.5 transition-colors hover:bg-muted/30">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
            <Brain className="size-4.5" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-muted-foreground font-medium truncate">
              {t('knowledgeBaseOverview.memoryAssets')}
            </span>
            <span className="font-mono text-lg font-bold text-foreground tabular-nums">
              {isLoading ? '...' : memoryCount.toLocaleString()}
            </span>
          </div>
        </div>

        {/* 资源库 Resources */}
        <div className="flex items-center gap-3 rounded-xl border bg-muted/20 p-3.5 transition-colors hover:bg-muted/30">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <FileText className="size-4.5" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-muted-foreground font-medium truncate">
              {t('knowledgeBaseOverview.resourceAssets')}
            </span>
            <span className="font-mono text-lg font-bold text-foreground tabular-nums">
              {isLoading ? '...' : resourceCount.toLocaleString()}
            </span>
          </div>
        </div>

        {/* 技能库 Skills */}
        <div className="flex items-center gap-3 rounded-xl border bg-muted/20 p-3.5 transition-colors hover:bg-muted/30">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <Wrench className="size-4.5" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-xs text-muted-foreground font-medium truncate">
              {t('knowledgeBaseOverview.skillAssets')}
            </span>
            <span className="font-mono text-lg font-bold text-foreground tabular-nums">
              {isLoading ? '...' : skillCount.toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* 下半部分：向量引擎 Vector 空间集成栏 */}
      <div className="rounded-xl border bg-muted/30 p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground/80">
            <Cpu className="size-4 text-primary" />
            <span>{t('knowledgeBaseOverview.vectorEngineTitle')}</span>
          </div>
          <span className="text-[11px] font-mono text-muted-foreground">
            {t('knowledgeBaseOverview.totalAssetsLabel')}{' '}
            <strong className="text-foreground">{totalAssets.toLocaleString()}</strong>{' '}
            {t('knowledgeBaseOverview.nodeUnit')}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 border-t border-border/50 pt-3">
          <div className="flex flex-col">
            <span className="text-[11px] text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.totalVectors')}
            </span>
            <span className="font-mono text-base font-bold text-emerald-600 dark:text-emerald-400 tabular-nums mt-0.5">
              {isLoading ? '...' : vectorCount.toLocaleString()}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-[11px] text-muted-foreground font-medium">
              {t('knowledgeBaseOverview.activeCollections')}
            </span>
            <span className="font-mono text-base font-bold text-blue-600 dark:text-blue-400 tabular-nums mt-0.5 flex items-center gap-1.5">
              <Layers className="size-3.5" />
              {collectionCount} {t('knowledgeBaseOverview.spacesUnit')}
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}
