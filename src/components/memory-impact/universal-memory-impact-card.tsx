import * as React from 'react'
import { BrainCircuitIcon, ChevronDownIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '#/lib/utils'
import { ImpactCounts } from './impact-summary-cards'
import { UnifiedMemoryImpactView } from './memory-impact-view'
import type { UnifiedMemoryImpactViewProps } from './memory-impact-view'
import {
  summarizeDiffs,
  summarizeOperations,
} from './types'

export interface UniversalMemoryImpactCardProps extends UnifiedMemoryImpactViewProps {
  /** 自定义卡片标题，缺省为“记忆影响审计快照” */
  title?: string
  /** 是否允许折叠，默认为 true */
  collapsible?: boolean
  /** 默认展开状态，默认为 true */
  defaultExpanded?: boolean
  /** 卡片额外外层样式 */
  containerClassName?: string
}

/**
 * 真正原子化的通用记忆影响卡片 (Atomic Drop-in Component)
 *
 * 第一性原理架构设计：
 * 1. 自包含全套视觉骨架（统一图标 + 统一标题 + 统一增量胶囊徽章 + 统一折叠展开交互）；
 * 2. 任何地方直接使用，零胶水代码，彻底杜绝 ABCD 与 ABCDEF 散落不一致；
 * 3. 内部无缝对齐三态卡片、多分类 Tab、文件 Diff 与全文查看器，单点演进全局受益。
 */
export function UniversalMemoryImpactCard({
  diffs,
  operations,
  session,
  isOpen = true,
  title,
  collapsible = true,
  defaultExpanded = true,
  className,
  containerClassName,
  showSummaryCards = true,
  emptyText,
}: UniversalMemoryImpactCardProps) {
  const { t } = useTranslation('sessions')
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)

  // 统一解析增量胶囊计数
  const totals = React.useMemo(() => {
    if (diffs && diffs.length > 0) {
      return summarizeDiffs(diffs)
    }
    if (operations && operations.length > 0) {
      return summarizeOperations(operations)
    }
    return { adds: 0, updates: 0, deletes: 0 }
  }, [diffs, operations])

  const resolvedTitle = title || t('impact.title', '记忆影响审计快照')

  return (
    <div
      className={cn(
        'rounded-xl border border-primary/25 bg-primary/5 p-3.5 space-y-2.5 transition-all min-w-0 w-full overflow-hidden',
        containerClassName,
      )}
    >
      <div className="flex items-center justify-between pb-2 border-b border-border/40 min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <BrainCircuitIcon className="size-4 text-primary shrink-0" />
          <span className="text-xs font-semibold text-foreground truncate">
            {resolvedTitle}
          </span>
          <ImpactCounts totals={totals} className="shrink-0" />
        </div>

        {collapsible && (
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer select-none shrink-0"
          >
            <span>
              {isExpanded
                ? t('impact.collapseShort', '收起')
                : t('impact.expandFull', '展开')}
            </span>
            <ChevronDownIcon
              className={cn(
                'size-3.5 transition-transform duration-200',
                isExpanded && 'rotate-180',
              )}
            />
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="pt-0.5 min-w-0 w-full">
          <UnifiedMemoryImpactView
            diffs={diffs}
            operations={operations}
            session={session}
            isOpen={isOpen}
            showSummaryCards={showSummaryCards}
            emptyText={emptyText}
            className={cn('p-0 space-y-3 min-w-0', className)}
          />
        </div>
      )}
    </div>
  )
}

export const UniversalMemoryImpact = UniversalMemoryImpactCard
