import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { useSessionMemoryDiffs } from '#/lib/sessions/use-sessions'
import type { SessionMeta } from '@ov-server/api/v1/sessions'
import { cn } from '#/lib/utils'
import { ImpactCounts, ImpactSummaryCards } from './impact-summary-cards'
import { MemoryDiffItem } from './memory-diff-item'
import type {
  UniversalMemoryDiff,
  UniversalMemoryDiffOperation,
} from './types'
import { summarizeDiffs, summarizeOperations } from './types'

const ALL_MEMORY_TYPES = 'all'

export interface UnifiedMemoryImpactViewProps {
  /** 受控模式：外部传入的完整 Diff 列表 */
  diffs?: UniversalMemoryDiff[]
  /** 受控模式：外部直接传入扁平原子操作列表（自动包装为单一 Diff） */
  operations?: UniversalMemoryDiffOperation[]
  /** 异步查询模式：传入会话元数据，按需触发请求 */
  session?: SessionMeta
  /** 是否处于可见/打开状态（控制异步查询） */
  isOpen?: boolean
  /** 自定义容器样式 */
  className?: string
  /** 是否展示顶部 3 列汇总卡片（内嵌在窄卡片中时可按需隐藏） */
  showSummaryCards?: boolean
  /** 空状态提示文本 */
  emptyText?: string
}

/**
 * 通用记忆影响纯视图组件 (Headless / Embeddable View)
 * 彻底切除与 `<Sheet>` 抽屉外壳的硬绑定，既可直接嵌入页面、抽屉卡片内部，也可放置在弹窗中。
 */
export function UnifiedMemoryImpactView({
  diffs: controlledDiffs,
  operations: flatOperations,
  session,
  isOpen = true,
  className,
  showSummaryCards = true,
  emptyText,
}: UnifiedMemoryImpactViewProps) {
  const { i18n, t } = useTranslation('sessions')
  const [memoryType, setMemoryType] = useState(ALL_MEMORY_TYPES)

  // 如果传了 session 则启动异步查询
  const diffsQuery = useSessionMemoryDiffs(session, isOpen)

  // 统一解析标准化 diffs 列表
  const resolvedDiffs: UniversalMemoryDiff[] = useMemo(() => {
    if (controlledDiffs) return controlledDiffs
    if (flatOperations) {
      return [
        {
          archiveId: 'current',
          summary: summarizeOperations(flatOperations),
          operations: flatOperations,
        },
      ]
    }
    if (diffsQuery.data) {
      return diffsQuery.data.map((d) => ({
        archiveId: d.archiveId,
        extractedAt: d.extractedAt,
        summary: d.summary,
        operations: d.operations,
      }))
    }
    return []
  }, [controlledDiffs, flatOperations, diffsQuery.data])

  const totals = useMemo(() => summarizeDiffs(resolvedDiffs), [resolvedDiffs])
  const totalChanges = totals.adds + totals.updates + totals.deletes

  // 提取所有涉及的 memoryType
  const memoryTypes = useMemo(() => {
    return Array.from(
      new Set(
        resolvedDiffs.flatMap((diff) =>
          diff.operations.map((op) => op.memoryType),
        ),
      ),
    ).sort()
  }, [resolvedDiffs])

  const activeMemoryType = memoryTypes.includes(memoryType)
    ? memoryType
    : ALL_MEMORY_TYPES

  const visibleDiffs = useMemo(() => {
    return resolvedDiffs.flatMap((diff) => {
      const ops =
        activeMemoryType === ALL_MEMORY_TYPES
          ? diff.operations
          : diff.operations.filter((op) => op.memoryType === activeMemoryType)
      return ops.length > 0
        ? [
            {
              ...diff,
              operations: ops,
              summary: summarizeOperations(ops),
            },
          ]
        : []
    })
  }, [activeMemoryType, resolvedDiffs])

  const isLoading = Boolean(session && diffsQuery.isLoading)
  const isError = Boolean(session && diffsQuery.isError)

  if (isLoading) {
    return (
      <div className="flex min-h-28 items-center justify-center text-xs text-muted-foreground">
        {t('impact.loading', '正在加载记忆变更快照...')}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex min-h-28 flex-col items-center justify-center gap-2 p-4 text-center">
        <p className="text-xs text-rose-600 dark:text-rose-400">
          {t('impact.loadFailed', '加载记忆变更失败')}
        </p>
        <Button
          onClick={() => void diffsQuery.refetch()}
          size="xs"
          variant="outline"
          className="h-6 text-[11px]"
        >
          {t('impact.retry', '重试')}
        </Button>
      </div>
    )
  }

  if (totalChanges === 0) {
    return (
      <div className="flex min-h-24 items-center justify-center p-4 text-center text-xs text-muted-foreground">
        {emptyText || t('impact.empty', '本次未产生记忆增量变更')}
      </div>
    )
  }

  const getMemoryTypeLabel = (type: string) => {
    if (type === ALL_MEMORY_TYPES) {
      return t('impact.allTypes', '全部')
    }
    return t(`impact.types.${type}`, { defaultValue: type })
  }

  return (
    <div className={cn('flex flex-col gap-3 min-w-0 w-full', className)}>
      {showSummaryCards && (
        <ImpactSummaryCards
          summary={totals}
          labels={{
            add: t('impact.kinds.add', '新增写入'),
            update: t('impact.kinds.update', '特例演化'),
            delete: t('impact.kinds.delete', '失效清理'),
          }}
        />
      )}

      {memoryTypes.length > 0 && (
        <div
          aria-label={t('impact.filterByType', '按记忆分类筛选')}
          className="flex gap-1 overflow-x-auto border-b border-border/40 pb-1.5 min-w-0"
          role="tablist"
        >
          {[ALL_MEMORY_TYPES, ...memoryTypes].map((type) => (
            <Button
              aria-selected={activeMemoryType === type}
              key={type}
              onClick={() => setMemoryType(type)}
              role="tab"
              size="xs"
              variant={activeMemoryType === type ? 'secondary' : 'ghost'}
              className="text-[11px] h-6 px-2 shrink-0"
            >
              {getMemoryTypeLabel(type)}
            </Button>
          ))}
        </div>
      )}

      <div className="space-y-4">
        {visibleDiffs.map((diff) => (
          <section key={diff.archiveId} className="space-y-2">
            <div className="flex items-center justify-between gap-2 px-1">
              <div className="flex min-w-0 items-center gap-2">
                <code className="font-mono text-xs font-medium text-foreground">
                  {diff.archiveId}
                </code>
                <ImpactCounts totals={diff.summary} />
              </div>
              {diff.extractedAt ? (
                <time className="shrink-0 text-[11px] text-muted-foreground font-mono">
                  {formatDate(diff.extractedAt, i18n.resolvedLanguage)}
                </time>
              ) : null}
            </div>

            <div className="overflow-hidden rounded-lg border border-border/60 bg-background/80 shadow-2xs min-w-0 w-full">
              {diff.operations.map((op, idx) => (
                <MemoryDiffItem
                  key={`${op.kind}-${op.uri}-${idx}`}
                  operation={op}
                  defaultOpen={diff.operations.length <= 5}
                  labels={{
                    before: t('impact.before', '变更前'),
                    after: t('impact.after', '变更后'),
                    addedContent: t('impact.addedContent', '新增内容'),
                    deletedContent: t('impact.deletedContent', '删除内容'),
                    emptyContent: t('impact.emptyContent', '(无内容)'),
                  }}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

export const UnifiedMemoryImpactPanel = UnifiedMemoryImpactView

function formatDate(value: string, language?: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}
