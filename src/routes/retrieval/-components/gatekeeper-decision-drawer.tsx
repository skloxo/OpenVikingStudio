import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  CopyIcon,
  CheckIcon,
  ShieldCheckIcon,
  FileTextIcon,
  HardDriveIcon,
  ClockIcon,
} from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '#/components/ui/sheet'
import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'
import { formatBytes } from '#/lib/formatters'
import {
  deriveMemoryType,
  UniversalMemoryImpact,
} from '#/components/memory-impact'
import type { UniversalMemoryDiff, UniversalMemoryDiffOperation } from '#/components/memory-impact'
import { fetchFileContent } from '#/routes/resources/-lib/api'

export interface GatekeeperDecisionRecord {
  id?: string
  action: 'noop' | 'update' | 'delete' | 'add'
  similarity: number
  matched_uri?: string | null
  matched_text_snippet?: string | null
  reason: string
  saved_bytes?: number
  timestamp?: number
  uri?: string
}

interface GatekeeperDecisionDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  decision: GatekeeperDecisionRecord | null
}

export function GatekeeperDecisionDrawer({
  open,
  onOpenChange,
  decision,
}: GatekeeperDecisionDrawerProps) {
  const { t } = useTranslation('tasksPage')
  const [copiedId, setCopiedId] = React.useState(false)
  const [copiedUri, setCopiedUri] = React.useState(false)
  const [fileContent, setFileContent] = React.useState<string | null>(null)
  const [loadingContent, setLoadingContent] = React.useState(false)

  React.useEffect(() => {
    if (!open || !decision) {
      setFileContent(null)
      return
    }
    const targetUri = decision.uri || decision.matched_uri
    if (!targetUri || !targetUri.startsWith('viking://')) {
      setFileContent(null)
      return
    }

    let isMounted = true
    setLoadingContent(true)

    fetchFileContent(targetUri)
      .then((res) => {
        if (isMounted) {
          setFileContent(res.content || '')
        }
      })
      .catch((err) => {
        console.warn('Failed to fetch file content for impact drawer:', err)
        if (isMounted) {
          setFileContent(null)
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoadingContent(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [open, decision?.uri, decision?.matched_uri, decision?.id])

  const impactDiffs = React.useMemo<UniversalMemoryDiff[]>(() => {
    if (!decision) return []
    const isUpdate = decision.action === 'update'
    const targetUri = decision.uri || decision.matched_uri || 'viking://unknown'
    const memType = deriveMemoryType(targetUri)

    const operations: UniversalMemoryDiffOperation[] = []

    // 1. 主落盘目标知识操作
    operations.push({
      kind: isUpdate ? 'update' : 'add',
      uri: targetUri,
      memoryType: memType,
      before: isUpdate ? (decision.matched_text_snippet || undefined) : undefined,
      after: fileContent || decision.matched_text_snippet || decision.reason,
      description: decision.reason,
      meta: {
        decisionId: decision.id,
        similarity: decision.similarity,
        action: decision.action,
      },
    })

    // 2. 若属于特例演化且存在不同的命中文档，一并登记命中文档原件
    if (isUpdate && decision.matched_uri && decision.matched_uri !== targetUri) {
      operations.push({
        kind: 'update',
        uri: decision.matched_uri,
        memoryType: deriveMemoryType(decision.matched_uri),
        before: decision.matched_text_snippet || undefined,
        after: decision.matched_text_snippet || undefined,
        description: `命中历史沉淀原件 (余弦相似度: ${(decision.similarity * 100).toFixed(1)}%)`,
        meta: {
          matched: true,
          similarity: decision.similarity,
        },
      })
    }

    const archiveLabel = decision.id
      ? `decision_${decision.id.slice(0, 8)}`
      : 'gatekeeper_record'

    const extractedAt = decision.timestamp
      ? new Date(decision.timestamp > 1e11 ? decision.timestamp : decision.timestamp * 1000).toISOString()
      : undefined

    const adds = operations.filter((o) => o.kind === 'add').length
    const updates = operations.filter((o) => o.kind === 'update').length
    const deletes = operations.filter((o) => o.kind === 'delete').length

    return [
      {
        archiveId: archiveLabel,
        extractedAt,
        summary: {
          adds,
          updates,
          deletes,
        },
        operations,
      },
    ]
  }, [decision, fileContent, loadingContent])

  if (!decision) return null

  const handleCopy = (text: string, type: 'id' | 'uri') => {
    void navigator.clipboard.writeText(text)
    if (type === 'id') {
      setCopiedId(true)
      setTimeout(() => setCopiedId(false), 2000)
    } else {
      setCopiedUri(true)
      setTimeout(() => setCopiedUri(false), 2000)
    }
  }

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'noop':
        return (
          <Badge variant="outline" className="border-border/60 bg-muted/40 text-muted-foreground text-[11px] font-mono font-medium px-2 py-0.5">
            {t('gatekeeper.noop')}
          </Badge>
        )
      case 'update':
        return (
          <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[11px] font-mono font-medium px-2 py-0.5">
            {t('gatekeeper.update')}
          </Badge>
        )
      case 'delete':
        return (
          <Badge variant="outline" className="border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[11px] font-mono font-medium px-2 py-0.5">
            {t('gatekeeper.delete')}
          </Badge>
        )
      default:
        return (
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary text-[11px] font-mono font-medium px-2 py-0.5">
            {t('gatekeeper.add')}
          </Badge>
        )
    }
  }

  const formatTime = (ts?: number) => {
    if (!ts) return '--'
    const d = new Date(ts > 1e11 ? ts : ts * 1000)
    return d.toLocaleString([], {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="gap-0 data-[side=right]:sm:max-w-3xl flex flex-col">
        {/* Header: 768px 宽度下宽敞的 Header，右侧提供元数据与关闭按钮 */}
        <SheetHeader className="border-b px-6 py-4 shrink-0">
          <div className="flex items-center justify-between gap-3 pr-8">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
                <ShieldCheckIcon className="size-4.5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <SheetTitle className="text-base font-semibold text-foreground">
                    {t('gatekeeper.drawerTitle')}
                  </SheetTitle>
                  {getActionBadge(decision.action)}
                  {decision.id && (
                    <button
                      type="button"
                      onClick={() => handleCopy(decision.id!, 'id')}
                      className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground bg-muted/40 hover:bg-muted/70 rounded px-1.5 py-0.5 border border-border/50 transition-colors cursor-pointer"
                      title={t('gatekeeper.copySuccess')}
                    >
                      <span>#{decision.id}</span>
                      {copiedId ? (
                        <CheckIcon className="size-3 text-primary" />
                      ) : (
                        <CopyIcon className="size-3 opacity-70" />
                      )}
                    </button>
                  )}
                </div>
                <SheetDescription className="text-xs text-muted-foreground mt-0.5">
                  {t('gatekeeper.subtitle')}
                </SheetDescription>
              </div>
            </div>

            {/* 右侧微胶囊元数据 */}
            <div className="hidden sm:flex items-center gap-2 shrink-0 text-[11px] text-muted-foreground font-mono">
              <span className="flex items-center gap-1 bg-muted/40 px-2 py-0.5 rounded border border-border/40">
                <HardDriveIcon className="size-3 text-primary/80" />
                <span>{formatBytes(decision.saved_bytes)}</span>
              </span>
              <span className="flex items-center gap-1 bg-muted/40 px-2 py-0.5 rounded border border-border/40">
                <ClockIcon className="size-3 opacity-70" />
                <span>{formatTime(decision.timestamp)}</span>
              </span>
            </div>
          </div>
        </SheetHeader>

        {/* 抽屉可滚动正文：两栏 50/50 仪表盘网格 + 全宽记忆影响审计 */}
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5 space-y-4 text-xs">
          {/* 顶层 50/50 对等双栏卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {/* 左栏：确切余弦相似度与判定依据 */}
            <div className="flex flex-col gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-medium text-muted-foreground">
                    {t('gatekeeper.similarity')}
                  </span>
                  <Badge variant="outline" className="font-mono text-[11px] px-1.5 py-0 border-border/60">
                    {decision.similarity >= 0.97
                      ? t('gatekeeper.simBandHigh')
                      : decision.similarity >= 0.92
                        ? t('gatekeeper.simBandMed')
                        : t('gatekeeper.simBandLow')}
                  </Badge>
                </div>
                <span className="font-mono text-xs text-muted-foreground">
                  {(decision.similarity * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span
                  className={cn(
                    'font-mono text-2xl font-bold tabular-nums',
                    decision.similarity >= 0.95
                      ? 'text-primary'
                      : decision.similarity >= 0.9
                        ? 'text-amber-600 dark:text-amber-400'
                        : 'text-foreground',
                  )}
                >
                  {decision.similarity.toFixed(4)}
                </span>
              </div>
              <div className="pt-2 border-t border-border/40">
                <span className="text-[11px] font-medium text-muted-foreground block mb-1">
                  {t('gatekeeper.decisionReason')}
                </span>
                <p className="text-xs leading-relaxed text-foreground/90 whitespace-pre-wrap">
                  {decision.reason}
                </p>
              </div>
            </div>

            {/* 右栏：写入目标与命中已有事实 */}
            <div className="flex flex-col gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3.5 justify-between">
              <div className="space-y-2.5">
                {decision.uri && (
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-medium text-muted-foreground">
                        {t('gatekeeper.inputUri')}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopy(decision.uri!, 'uri')}
                        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground cursor-pointer"
                      >
                        {copiedUri ? <CheckIcon className="size-3 text-primary" /> : <CopyIcon className="size-3" />}
                        <span>{copiedUri ? t('gatekeeper.copySuccessUri') : t('gatekeeper.copyUri')}</span>
                      </button>
                    </div>
                    <code className="block break-all font-mono text-xs text-foreground bg-background/60 p-1.5 rounded border border-border/40">
                      {decision.uri}
                    </code>
                  </div>
                )}

                {decision.matched_uri && (
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-medium text-muted-foreground">
                        {t('gatekeeper.matchedUri')}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopy(decision.matched_uri!, 'uri')}
                        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground cursor-pointer"
                        title={t('gatekeeper.copyUri')}
                      >
                        <CopyIcon className="size-3" />
                      </button>
                    </div>
                    <code className="block break-all font-mono text-xs text-primary/90 bg-background/60 p-1.5 rounded border border-border/40">
                      {decision.matched_uri}
                    </code>
                  </div>
                )}
              </div>

              {decision.matched_text_snippet && (
                <div className="pt-2 border-t border-border/40">
                  <div className="flex items-center gap-1.5 mb-1">
                    <FileTextIcon className="size-3.5 text-muted-foreground" />
                    <span className="text-[11px] font-medium text-muted-foreground">
                      {t('gatekeeper.viewSnippet')}
                    </span>
                  </div>
                  <p className="max-h-24 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted-foreground rounded bg-background/80 p-2 border border-border/40">
                    {decision.matched_text_snippet}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* 知识落盘影响增量快照 (原子化通用组件，与任务中心、会话中心 100% 结构一致) */}
          {decision.action !== 'noop' && decision.action !== 'delete' && (
            <UniversalMemoryImpact
              diffs={impactDiffs}
              title={decision.action === 'update'
                ? t('gatekeeper.impactTitleUpdate', { defaultValue: '知识演进记忆影响' })
                : t('gatekeeper.impactTitleAdd', { defaultValue: '新增知识落盘影响快照' })}
            />
          )}

          {/* 移动端兜底元数据栏 */}
          <div className="flex sm:hidden items-center justify-between rounded-md border border-border/40 bg-muted/10 p-2.5 text-[11px] text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <HardDriveIcon className="size-3.5" />
              <span>{t('gatekeeper.savedBytes')}:</span>
              <span className="font-mono font-semibold text-foreground">
                {formatBytes(decision.saved_bytes)}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <ClockIcon className="size-3.5" />
              <span className="font-mono">{formatTime(decision.timestamp)}</span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
