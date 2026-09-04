import * as React from 'react'
import {
  ActivityIcon,
  CpuIcon,
  DatabaseIcon,
  GaugeIcon,
  HelpCircleIcon,
  LayersIcon,
  ZapIcon,
  SparklesIcon,
  ShieldCheckIcon,
  TimerIcon,
  FileTextIcon,
  RefreshCwIcon,
  HardDriveIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '#/components/ui/tooltip'
import { cn } from '#/lib/utils'
import type { DeepObserverMetrics } from '../-types'

interface DeepMetricsGridProps {
  metrics: DeepObserverMetrics
  isLoading?: boolean
}

interface MetricTileConfig {
  id: string
  titleKey: string
  icon: React.ElementType
  value: string
  unit?: string
  subText?: string
  badgeText?: string
  badgeVariant?: 'positive' | 'negative' | 'neutral'
  tooltipKey: string
  isMissing?: boolean
  category: 'physics' | 'engine'
}

export function DeepMetricsGrid({ metrics, isLoading }: DeepMetricsGridProps) {
  const { t } = useTranslation('monitoringPage')

  const tileConfigs: MetricTileConfig[] = React.useMemo(() => {
    return [
      // === Section 1: Physics & Retrieval Metrics (Tile 1~8) ===
      {
        id: 'http-success-rate',
        titleKey: 'metricsTiles.httpSuccessRate.title',
        icon: ShieldCheckIcon,
        value: metrics.httpSuccessRate !== null ? `${metrics.httpSuccessRate.toFixed(2)}` : '--',
        unit: '%',
        subText: t('metricsTiles.httpSuccessRate.subText', { defaultValue: '99.9% 目标 SLA' }),
        badgeText: t('metricsTiles.httpSuccessRate.badgeText', { defaultValue: 'SLA 达标' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.httpSuccessRate.tooltip',
        category: 'physics',
      },
      {
        id: 'vector-count',
        titleKey: 'metricsTiles.vectorCount.title',
        icon: DatabaseIcon,
        value: metrics.vectorCount !== null ? metrics.vectorCount.toLocaleString() : '--',
        unit: '条',
        subText: t('metricsTiles.vectorCount.subText', { defaultValue: 'VikingDB 挂载 context 集合' }),
        badgeText: t('metricsTiles.vectorCount.badgeText', { defaultValue: '全量就位' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.vectorCount.tooltip',
        category: 'physics',
      },
      {
        id: 'vector-hit-rate',
        titleKey: 'metricsTiles.vectorHitRate.title',
        icon: ZapIcon,
        value: metrics.vectorHitRate !== null ? `${metrics.vectorHitRate.toFixed(1)}` : '--',
        unit: '%',
        subText: metrics.vectorHitRate !== null ? t('metricsTiles.vectorHitRate.activeSubText', { defaultValue: '语义向量召回命中率' }) : t('metricsTiles.vectorHitRate.pendingSubText', { defaultValue: '服务启动后暂无检索请求' }),
        badgeText: metrics.vectorHitRate !== null ? t('metricsTiles.vectorHitRate.badgeText', { defaultValue: '高命中' }) : t('common.pending', { defaultValue: '等待请求' }),
        badgeVariant: metrics.vectorHitRate !== null ? 'positive' : 'neutral',
        tooltipKey: 'metricsTiles.vectorHitRate.tooltip',
        category: 'physics',
      },
      {
        id: 'gpu-vram-usage',
        titleKey: 'metricsTiles.gpuVramUsage.title',
        icon: CpuIcon,
        value: metrics.gpuVramUsage ? `${metrics.gpuVramUsage.usedGb} / ${metrics.gpuVramUsage.totalGb}` : '--',
        unit: 'GB',
        subText: metrics.gpuVramUsage ? t('metricsTiles.gpuVramUsage.activeSubText', { defaultValue: '本地 GPU 显存监控' }) : t('metricsTiles.gpuVramUsage.pendingSubText', { defaultValue: '无本地 GPU 或运行于 CPU' }),
        badgeText: metrics.gpuVramUsage ? t('metricsTiles.gpuVramUsage.badgeText', { defaultValue: '轻载健康' }) : t('metricsTiles.gpuVramUsage.cpuBadge', { defaultValue: 'CPU 模式' }),
        badgeVariant: metrics.gpuVramUsage ? 'positive' : 'neutral',
        tooltipKey: 'metricsTiles.gpuVramUsage.tooltip',
        category: 'physics',
      },
      {
        id: 'top1-accuracy',
        titleKey: 'metricsTiles.top1Accuracy.title',
        icon: SparklesIcon,
        value: metrics.top1Accuracy !== null ? `${metrics.top1Accuracy.toFixed(1)}` : '--',
        unit: '%',
        subText: metrics.top1Accuracy !== null ? t('metricsTiles.top1Accuracy.activeSubText', { defaultValue: 'Rerank 重排全量成功' }) : t('metricsTiles.top1Accuracy.pendingSubText', { defaultValue: '服务启动后暂无重排记录' }),
        badgeText: metrics.top1Accuracy !== null ? t('metricsTiles.top1Accuracy.badgeText', { defaultValue: '精排就绪' }) : t('common.pending', { defaultValue: '等待请求' }),
        badgeVariant: metrics.top1Accuracy !== null ? 'positive' : 'neutral',
        tooltipKey: 'metricsTiles.top1Accuracy.tooltip',
        category: 'physics',
      },
      {
        id: 'avg-cosine-score',
        titleKey: 'metricsTiles.avgCosineScore.title',
        icon: GaugeIcon,
        value: metrics.avgCosineScore !== null ? metrics.avgCosineScore.toFixed(4) : '--',
        subText: metrics.avgCosineScore !== null ? t('metricsTiles.avgCosineScore.activeSubText', { defaultValue: '高维向量空间余弦相似度均值' }) : t('metricsTiles.avgCosineScore.pendingSubText', { defaultValue: '等待向量相似度查询' }),
        badgeText: metrics.avgCosineScore !== null ? t('metricsTiles.avgCosineScore.badgeText', { defaultValue: '基准正常' }) : t('common.noData', { defaultValue: '暂无数据' }),
        badgeVariant: metrics.avgCosineScore !== null ? 'positive' : 'neutral',
        tooltipKey: 'metricsTiles.avgCosineScore.tooltip',
        category: 'physics',
      },
      {
        id: 'embedding-latency',
        titleKey: 'metricsTiles.embeddingLatency.title',
        icon: TimerIcon,
        value: metrics.embeddingLatencyMs !== null ? `${metrics.embeddingLatencyMs.toFixed(1)}` : '--',
        unit: 'ms',
        subText: metrics.embeddingLatencyMs !== null ? t('metricsTiles.embeddingLatency.activeSubText', { defaultValue: '平均向量检索耗时' }) : t('metricsTiles.embeddingLatency.pendingSubText', { defaultValue: '等待向量检索请求' }),
        badgeText: metrics.embeddingLatencyMs !== null ? t('metricsTiles.embeddingLatency.badgeText', { defaultValue: '极速' }) : t('common.ready', { defaultValue: '就绪' }),
        badgeVariant: metrics.embeddingLatencyMs !== null ? 'positive' : 'neutral',
        tooltipKey: 'metricsTiles.embeddingLatency.tooltip',
        category: 'physics',
      },
      {
        id: 'max-latency',
        titleKey: 'metricsTiles.maxLatency.title',
        icon: ActivityIcon,
        value: metrics.maxLatencyMs !== null ? `${metrics.maxLatencyMs.toFixed(0)}` : '--',
        unit: 'ms',
        subText: metrics.maxLatencyMs !== null ? t('metricsTiles.maxLatency.activeSubText', { defaultValue: '单次最长请求延迟 Peak' }) : t('metricsTiles.maxLatency.pendingSubText', { defaultValue: '等待 API 请求极值' }),
        badgeText: metrics.maxLatencyMs !== null ? t('metricsTiles.maxLatency.badgeText', { defaultValue: 'P99 峰值' }) : t('common.ready', { defaultValue: '就绪' }),
        badgeVariant: metrics.maxLatencyMs && metrics.maxLatencyMs > 5000 ? 'neutral' : (metrics.maxLatencyMs !== null ? 'positive' : 'neutral'),
        tooltipKey: 'metricsTiles.maxLatency.tooltip',
        category: 'physics',
      },

      // === Section 2: Engine State & Memory Slimming (Tile 9~16) ===
      {
        id: 'total-audit-logs',
        titleKey: 'metricsTiles.totalAuditLogs.title',
        icon: FileTextIcon,
        value: metrics.totalAuditLogs !== null ? metrics.totalAuditLogs.toLocaleString() : '--',
        unit: '条',
        subText: t('metricsTiles.totalAuditLogs.subText', { defaultValue: 'Console Audit 全量记录' }),
        badgeText: t('metricsTiles.totalAuditLogs.badgeText', { defaultValue: '全量追溯' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.totalAuditLogs.tooltip',
        category: 'engine',
      },
      {
        id: 'auto-refresh-status',
        titleKey: 'metricsTiles.autoRefreshStatus.title',
        icon: RefreshCwIcon,
        value: metrics.autoRefreshEnabled ? '开启' : '关闭',
        subText: t('metricsTiles.autoRefreshStatus.subText', { defaultValue: '60s 视口感知懒拉取' }),
        badgeText: t('metricsTiles.autoRefreshStatus.badgeText', { defaultValue: '惰性感应' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.autoRefreshStatus.tooltip',
        category: 'engine',
      },
      {
        id: 'fs-io-ops',
        titleKey: 'metricsTiles.fsIoOps.title',
        icon: HardDriveIcon,
        value: metrics.fsStats ? (metrics.fsStats.totalOps > 1000000 ? `${(metrics.fsStats.totalOps / 1000000).toFixed(2)}M` : metrics.fsStats.totalOps.toLocaleString()) : '--',
        unit: '次',
        subText: t('metricsTiles.fsIoOps.subText', { defaultValue: metrics.fsStats ? `平均 IO 延迟 ${metrics.fsStats.avgMs.toFixed(3)}ms (localfs)` : 'FileSystem 读写 IO 操作' }),
        badgeText: t('metricsTiles.fsIoOps.badgeText', { defaultValue: '读写极速' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.fsIoOps.tooltip',
        category: 'engine',
      },
      {
        id: 'token-total',
        titleKey: 'metricsTiles.tokenTotal.title',
        icon: LayersIcon,
        value: metrics.tokenStats ? metrics.tokenStats.today.toLocaleString() : '--',
        unit: 'Tokens',
        subText: t('metricsTiles.tokenTotal.subText', { defaultValue: '今日 Embedding 输入 Token' }),
        badgeText: t('metricsTiles.tokenTotal.badgeText', { defaultValue: '精约高效' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.tokenTotal.tooltip',
        category: 'engine',
      },
      {
        id: 'memory-slimming-rate',
        titleKey: 'metricsTiles.memorySlimmingRate.title',
        icon: SparklesIcon,
        value: metrics.memorySlimmingRate !== null ? `${metrics.memorySlimmingRate}` : '--',
        unit: '%',
        subText: t('metricsTiles.memorySlimmingRate.subText', { defaultValue: '原始文件 ➔ 记忆 Token 压缩率' }),
        badgeText: t('metricsTiles.memorySlimmingRate.badgeText', { defaultValue: '高效瘦身' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.memorySlimmingRate.tooltip',
        category: 'engine',
      },
      {
        id: 'vectorization-rate',
        titleKey: 'metricsTiles.vectorizationRate.title',
        icon: ZapIcon,
        value: metrics.vectorizationRate !== null ? metrics.vectorizationRate.toLocaleString() : '--',
        unit: 'Vec/s',
        subText: t('metricsTiles.vectorizationRate.subText', { defaultValue: 'OpenViking EMB 吞吐效率' }),
        badgeText: t('metricsTiles.vectorizationRate.badgeText', { defaultValue: '高吞吐' }),
        badgeVariant: 'positive',
        tooltipKey: 'metricsTiles.vectorizationRate.tooltip',
        category: 'engine',
      },
    ]
  }, [metrics, t])

  return (
    <TooltipProvider>
      <div className="flex w-full flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold tracking-tight text-foreground/90">
              {t('metricsTiles.sectionTitle', { defaultValue: '内核深层观测指标' })}
            </h2>
            <Badge variant="outline" className="font-mono text-[11px] font-normal border-border/60">
              {t('metricsTiles.liveBadge', { defaultValue: `${tileConfigs.length} 项指标实时监测` })}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-4">
          {tileConfigs.map((tile) => {
            const IconComponent = tile.icon
            return (
              <div
                key={tile.id}
                className={cn(
                  'group relative flex flex-col justify-between rounded-md border border-border/60 bg-card p-3.5 shadow-none transition-colors hover:border-cyan-500/40 hover:bg-card/80',
                  isLoading && 'opacity-70 animate-pulse',
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <IconComponent className="size-4 text-muted-foreground transition-colors group-hover:text-cyan-400" />
                    <span className="text-xs font-medium text-muted-foreground group-hover:text-foreground">
                      {t(tile.titleKey, { defaultValue: tile.id })}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    {tile.badgeText ? (
                      <Badge
                        variant="outline"
                        className={cn(
                          'px-1.5 py-0 text-[11px] font-normal border-0',
                          tile.badgeVariant === 'positive' && 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
                          tile.badgeVariant === 'negative' && 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
                          tile.badgeVariant === 'neutral' && 'bg-muted/40 text-muted-foreground',
                        )}
                      >
                        {tile.badgeText}
                      </Badge>
                    ) : null}

                    <Tooltip>
                      <TooltipTrigger
                        aria-label={t(tile.titleKey, { defaultValue: tile.id })}
                        className="text-muted-foreground/60 hover:text-muted-foreground focus:outline-none"
                      >
                        <HelpCircleIcon className="size-3.5" />
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs text-xs">
                        {t(tile.tooltipKey, { defaultValue: tile.subText || tile.id })}
                      </TooltipContent>
                    </Tooltip>
                  </div>
                </div>

                <div className="mt-3 flex items-baseline gap-1.5">
                  <span className="font-mono text-xl font-bold tracking-tight tabular-nums text-foreground">
                    {tile.value}
                  </span>
                  {tile.unit ? (
                    <span className="font-mono text-xs text-muted-foreground">
                      {tile.unit}
                    </span>
                  ) : null}
                </div>

                {tile.subText ? (
                  <p className="mt-1 line-clamp-1 text-[11px] text-muted-foreground/80 font-mono tabular-nums">
                    {tile.subText}
                  </p>
                ) : null}
              </div>
            )
          })}
        </div>
      </div>
    </TooltipProvider>
  )
}
