import type { ComponentType, ReactNode } from 'react'
import { ArrowDownIcon, ArrowUpIcon, MinusIcon } from 'lucide-react'
import { Card } from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { cn } from '#/lib/utils'

export type MetricTileStatus = 'neutral' | 'positive' | 'warning' | 'negative'

export interface MetricTileProps {
  title: ReactNode
  value: ReactNode
  subValue?: ReactNode
  description?: ReactNode
  icon?: ComponentType<{ className?: string }>
  status?: MetricTileStatus
  trend?: {
    direction: 'up' | 'down' | 'neutral'
    text: string
    positiveIsGood?: boolean
  }
  badge?: ReactNode
  loading?: boolean
  compact?: boolean
  className?: string
  onClick?: () => void
}

const statusColorMap: Record<MetricTileStatus, string> = {
  neutral: 'text-foreground',
  positive: 'text-cyan-500 dark:text-cyan-400',
  warning: 'text-amber-500 dark:text-amber-400',
  negative: 'text-rose-500 dark:text-rose-400',
}

const iconStatusColorMap: Record<MetricTileStatus, string> = {
  neutral: 'text-muted-foreground',
  positive: 'text-cyan-500/80',
  warning: 'text-amber-500/80',
  negative: 'text-rose-500/80',
}

export function MetricTile({
  title,
  value,
  subValue,
  description,
  icon: Icon,
  status = 'neutral',
  trend,
  badge,
  loading = false,
  compact = false,
  className,
  onClick,
}: MetricTileProps) {
  if (loading) {
    return (
      <Card
        className={cn(
          'flex flex-col justify-between border-border/50 bg-card/50',
          compact ? 'p-2.5' : 'p-3.5',
          className,
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="size-4 rounded-full" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-3.5 w-10" />
        </div>
        {description && <Skeleton className="mt-2 h-3 w-32" />}
      </Card>
    )
  }

  const isInteractive = typeof onClick === 'function'

  return (
    <Card
      className={cn(
        'group flex flex-col justify-between border-border/60 bg-card/60 transition-all select-none',
        compact ? 'p-2.5' : 'p-3.5',
        isInteractive && 'cursor-pointer hover:border-cyan-500/40 hover:bg-card/90 active:scale-[0.99]',
        className,
      )}
      onClick={onClick}
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
    >
      {/* 顶部标题与图标/Badge 栏 */}
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs font-medium text-muted-foreground">
          {title}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {badge}
          {Icon && (
            <Icon className={cn('size-3.5', iconStatusColorMap[status])} />
          )}
        </div>
      </div>

      {/* 核心数值展示（等宽数字、语义色彩） */}
      <div className="mt-2 flex items-baseline gap-1.5 overflow-hidden">
        <span
          className={cn(
            'truncate text-lg font-semibold tracking-tight font-mono tabular-nums',
            statusColorMap[status],
          )}
        >
          {value}
        </span>
        {subValue && (
          <span className="text-xs text-muted-foreground font-mono truncate">
            {subValue}
          </span>
        )}
      </div>

      {/* 底部辅助说明或趋势指标 */}
      {(description || trend) && (
        <div className="mt-2 flex items-center justify-between gap-2 text-xs text-muted-foreground">
          {description && <span className="truncate">{description}</span>}
          {trend && (
            <span
              className={cn(
                'inline-flex items-center gap-0.5 text-xs font-mono font-medium shrink-0',
                trend.direction === 'neutral'
                  ? 'text-muted-foreground'
                  : (trend.direction === 'up' && (trend.positiveIsGood ?? true)) ||
                      (trend.direction === 'down' && !(trend.positiveIsGood ?? true))
                    ? 'text-cyan-500 dark:text-cyan-400'
                    : 'text-rose-500 dark:text-rose-400',
              )}
            >
              {trend.direction === 'up' && <ArrowUpIcon className="size-3" />}
              {trend.direction === 'down' && <ArrowDownIcon className="size-3" />}
              {trend.direction === 'neutral' && <MinusIcon className="size-3" />}
              {trend.text}
            </span>
          )}
        </div>
      )}
    </Card>
  )
}
