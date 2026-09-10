import { useMemo, useState } from 'react'
import { BrainCircuitIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { useSessionMemoryDiffs } from '#/lib/sessions/use-sessions'
import type { SessionMeta } from '@ov-server/api/v1/sessions'
import { ImpactCounts, ImpactSummaryCards } from './impact-summary-cards'
import { MemoryDiffItem } from './memory-diff-item'
import type {
  UniversalMemoryDiff,
  UniversalMemoryDiffOperation,
} from './types'
import { summarizeDiffs, summarizeOperations } from './types'

const ALL_MEMORY_TYPES = 'all'

export interface UnifiedMemoryImpactDrawerProps {
  /** 受控模式：外部传入的完整 Diff 列表 */
  diffs?: UniversalMemoryDiff[]
  /** 受控模式：外部直接传入扁平原子操作列表（自动包装为单一 Diff） */
  operations?: UniversalMemoryDiffOperation[]
  /** 异步查询模式：传入会话元数据，在抽屉打开时按需触发请求 */
  session?: SessionMeta
  /** 外部控制抽屉开关 */
  open?: boolean
  onOpenChange?: (open: boolean) => void
  /** 自定义触发器按钮节点，未传入受控 open 时有效 */
  trigger?: React.ReactNode
  /** 自定义标题与描述文案 */
  title?: string
  description?: string
}

export function UnifiedMemoryImpactDrawer({
  diffs: controlledDiffs,
  operations: flatOperations,
  session,
  open: externalOpen,
  onOpenChange: setExternalOpen,
  trigger,
  title: customTitle,
  description: customDescription,
}: UnifiedMemoryImpactDrawerProps) {
  const { i18n, t } = useTranslation('sessions')
  const [internalOpen, setInternalOpen] = useState(false)
  const isControlled = externalOpen !== undefined
  const isOpen = isControlled ? externalOpen : internalOpen
  const handleOpenChange = (nextOpen: boolean) => {
    if (isControlled) {
      setExternalOpen?.(nextOpen)
    } else {
      setInternalOpen(nextOpen)
    }
  }

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

  const titleText = customTitle || t('impact.title', '记忆增量影响')
  const descriptionText =
    customDescription ||
    t('impact.description', {
      changes: totalChanges,
      commits: resolvedDiffs.length,
      defaultValue: `共 ${totalChanges} 项变更，涉及 ${resolvedDiffs.length} 次演进`,
    })

  return (
    <>
      {trigger ? (
        <span onClick={() => handleOpenChange(true)} className="inline-flex">
          {trigger}
        </span>
      ) : null}

      <Sheet open={isOpen} onOpenChange={handleOpenChange}>
        <SheetContent className="gap-0 data-[side=right]:sm:max-w-3xl">
          <SheetHeader className="border-b px-6 py-4">
            <div className="flex items-center gap-3 pr-10">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
                <BrainCircuitIcon className="size-4.5" />
              </div>
              <div className="min-w-0">
                <SheetTitle className="text-base font-semibold text-foreground">
                  {titleText}
                </SheetTitle>
                <SheetDescription className="text-xs text-muted-foreground">
                  {descriptionText}
                </SheetDescription>
              </div>
            </div>
          </SheetHeader>

          {isLoading ? (
            <div className="flex min-h-48 items-center justify-center text-xs text-muted-foreground">
              {t('impact.loading', '正在加载记忆变更快照...')}
            </div>
          ) : isError ? (
            <div className="flex min-h-48 flex-col items-center justify-center gap-3 px-6 text-center">
              <p className="text-xs text-destructive">
                {t('impact.loadFailed', '加载记忆变更失败')}
              </p>
              <Button
                onClick={() => void diffsQuery.refetch()}
                size="xs"
                variant="outline"
              >
                {t('impact.retry', '重试')}
              </Button>
            </div>
          ) : totalChanges === 0 ? (
            <div className="flex min-h-48 items-center justify-center px-6 text-center text-xs text-muted-foreground">
              {t('impact.empty', '本次未产生记忆增量变更')}
            </div>
          ) : (
            <>
              <ImpactSummaryCards
                summary={totals}
                labels={{
                  add: t('impact.kinds.add', '新增写入'),
                  update: t('impact.kinds.update', '特例演化'),
                  delete: t('impact.kinds.delete', '失效清理'),
                }}
              />

              {memoryTypes.length > 1 ? (
                <div
                  aria-label={t('impact.filterByType', '按记忆类型筛选')}
                  className="flex gap-1 overflow-x-auto border-b bg-background px-6 py-2"
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
                      className="text-[11px] h-6 px-2"
                    >
                      {type === ALL_MEMORY_TYPES
                        ? t('impact.allTypes', '全部类型')
                        : type}
                    </Button>
                  ))}
                </div>
              ) : null}

              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
                <div className="space-y-5">
                  {visibleDiffs.map((diff) => (
                    <section key={diff.archiveId} className="space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-2">
                          <code className="font-mono text-xs font-medium text-foreground">
                            {diff.archiveId}
                          </code>
                          <ImpactCounts totals={diff.summary} />
                        </div>
                        {diff.extractedAt ? (
                          <time className="shrink-0 text-[11px] text-muted-foreground">
                            {formatDate(diff.extractedAt, i18n.resolvedLanguage)}
                          </time>
                        ) : null}
                      </div>

                      <div className="overflow-hidden rounded-lg border bg-background">
                        {diff.operations.map((op, idx) => (
                          <MemoryDiffItem
                            key={`${op.kind}-${op.uri}-${idx}`}
                            operation={op}
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
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  )
}

function formatDate(value: string, language?: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}
