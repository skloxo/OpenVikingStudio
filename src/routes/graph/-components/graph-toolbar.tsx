import { RotateCcwIcon, SearchIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { cn } from '#/lib/utils'

export type GraphFilterCategory = 'all' | 'peers' | 'sessions' | 'skills'
export type GraphMode = '2d' | '3d'

interface GraphToolbarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  activeFilter: GraphFilterCategory
  onFilterChange: (filter: GraphFilterCategory) => void
  mode: GraphMode
  onModeChange: (mode: GraphMode) => void
  onResetZoom: () => void
}

export function GraphToolbar({
  searchQuery,
  onSearchChange,
  activeFilter,
  onFilterChange,
  mode,
  onModeChange,
  onResetZoom,
}: GraphToolbarProps) {
  const { t } = useTranslation('monitoringPage')

  const filterOptions: { id: GraphFilterCategory; labelKey: string; defaultLabel: string; colorClass: string }[] = [
    {
      id: 'all',
      labelKey: 'graphPage.filterAll',
      defaultLabel: '全盘中枢',
      colorClass: 'bg-muted/60 text-foreground',
    },
    {
      id: 'peers',
      labelKey: 'graphPage.filterPeers',
      defaultLabel: 'Peers 看护节点',
      colorClass: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
    },
    {
      id: 'sessions',
      labelKey: 'graphPage.filterSessions',
      defaultLabel: 'Sessions 轨迹节点',
      colorClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
    },
    {
      id: 'skills',
      labelKey: 'graphPage.filterSkills',
      defaultLabel: 'Skills 技能节点',
      colorClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
    },
  ]

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/80 bg-card/85 p-3 shadow-lg backdrop-blur-md transition-colors duration-200">
      {/* Search Input */}
      <div className="flex items-center gap-3">
        <div className="relative w-64 md:w-80">
          <SearchIcon className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground/60" />
          <Input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t('graphPage.searchPlaceholder', {
              defaultValue: '搜索 URI 节点名称 (如: viking://resources)...',
            })}
            className="h-8 pl-8 font-mono text-xs shadow-none border-border/60 bg-background/50 focus-visible:ring-cyan-500/30"
          />
        </div>
      </div>

      {/* Mode Switch, Category Filter Pills & Zoom Reset */}
      <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
        {/* 2D / 3D Mode Switcher */}
        <div className="flex items-center gap-1 rounded-md bg-muted/40 p-1 border border-border/50">
          <button
            type="button"
            onClick={() => onModeChange('2d')}
            className={cn(
              'rounded px-2.5 py-1 text-[11px] font-bold transition-all focus:outline-none',
              mode === '2d'
                ? 'bg-cyan-500 text-white shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
            )}
          >
            🎨 2D 平面 (推荐)
          </button>
          <button
            type="button"
            onClick={() => onModeChange('3d')}
            className={cn(
              'rounded px-2.5 py-1 text-[11px] font-bold transition-all focus:outline-none',
              mode === '3d'
                ? 'bg-amber-500 text-white shadow-xs'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
            )}
          >
            🌌 3D 星空
          </button>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-1 rounded-md bg-muted/30 p-1 border border-border/40">
          {filterOptions.map((opt) => {
            const isActive = activeFilter === opt.id
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => onFilterChange(opt.id)}
                className={cn(
                  'rounded px-2 py-1 text-[11px] font-medium transition-colors focus:outline-none',
                  isActive
                    ? `${opt.colorClass} shadow-none border`
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
                )}
              >
                {t(opt.labelKey, { defaultValue: opt.defaultLabel })}
              </button>
            )
          })}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={onResetZoom}
          className="h-8 gap-1.5 px-2.5 text-xs font-mono border-border/60 hover:bg-muted/50 shadow-none"
        >
          <RotateCcwIcon className="size-3" />
          <span>{t('graphPage.zoomReset', { defaultValue: '重置缩放' })}</span>
        </Button>
      </div>
    </div>
  )
}
