import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { CopyIcon, CheckIcon, ShieldCheckIcon, FileTextIcon, HardDriveIcon, ClockIcon, BrainCircuitIcon } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '#/components/ui/sheet'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import { formatBytes } from '#/lib/formatters'
import {
  UnifiedMemoryImpactDrawer,
} from '#/components/memory-impact'
import type { UniversalMemoryDiffOperation } from '#/components/memory-impact'

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
  const [impactOpen, setImpactOpen] = React.useState(false)

  const impactOperations = React.useMemo<UniversalMemoryDiffOperation[]>(() => {
    if (!decision) return []
    const isUpdate = decision.action === 'update'
    const targetUri = decision.uri || decision.matched_uri || 'viking://unknown'
    return [
      {
        kind: isUpdate ? 'update' : 'add',
        uri: targetUri,
        memoryType: 'knowledge',
        before: isUpdate ? (decision.matched_text_snippet || undefined) : undefined,
        after: decision.reason || undefined,
        description: decision.reason,
        meta: {
          decisionId: decision.id,
          similarity: decision.similarity,
          action: decision.action,
        },
      },
    ]
  }, [decision])

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
      <SheetContent className="flex w-full flex-col gap-4 overflow-y-auto sm:max-w-lg">
        {/* Header: 留出 pr-10 彻底杜绝与右上角关闭按钮重叠 */}
        <SheetHeader className="gap-2 border-b border-border/50 pb-3 pr-10 text-left">
          <div className="flex flex-wrap items-center gap-2">
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
          <SheetDescription className="text-xs text-muted-foreground">
            {t('gatekeeper.subtitle')}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-3 text-xs">
          {/* 确切余弦相似度 */}
          <div className="flex flex-col rounded-md border border-border/60 bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t('gatekeeper.similarity')}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">
                {decision.similarity >= 0.97
                  ? t('gatekeeper.simBandHigh')
                  : decision.similarity >= 0.92
                    ? t('gatekeeper.simBandMed')
                    : t('gatekeeper.simBandLow')}
              </span>
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span
                className={cn(
                  'font-mono text-2xl font-bold tabular-nums',
                  decision.similarity >= 0.95
                    ? 'text-primary'
                    : decision.similarity >= 0.9
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-foreground'
                )}
              >
                {decision.similarity.toFixed(4)}
              </span>
              <span className="text-[11px] text-muted-foreground font-mono">
                ({(decision.similarity * 100).toFixed(1)}%)
              </span>
            </div>
          </div>

          {/* 裁决依据自解释 */}
          <div className="flex flex-col rounded-md border border-border/60 bg-background p-3">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-foreground">
              <ShieldCheckIcon className="size-3.5 text-primary" />
              <span>{t('gatekeeper.decisionReason')}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-foreground/90 whitespace-pre-wrap">
              {decision.reason}
            </p>
          </div>

          {/* 写入目标 URI */}
          {decision.uri && (
            <div className="flex flex-col rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center justify-between">
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
              <span className="mt-1.5 break-all font-mono text-[11px] text-foreground">
                {decision.uri}
              </span>
            </div>
          )}

          {/* 命中已有参考事实 */}
          {decision.matched_uri && (
            <div className="flex flex-col rounded-md border border-border/60 bg-muted/20 p-3">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t('gatekeeper.matchedUri')}
              </span>
              <span className="mt-1.5 break-all font-mono text-[11px] text-primary/90">
                {decision.matched_uri}
              </span>
            </div>
          )}

          {/* 命中参考摘要对比 */}
          {decision.matched_text_snippet && (
            <div className="flex flex-col rounded-md border border-border/60 bg-muted/20 p-3">
              <div className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
                <FileTextIcon className="size-3.5" />
                <span>{t('gatekeeper.viewSnippet')}</span>
              </div>
              <p className="mt-1.5 max-h-36 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted-foreground rounded bg-background/60 p-2 border border-border/40">
                {decision.matched_text_snippet}
              </p>
            </div>
          )}

          {/* 知识落盘影响与增量快照联动 */}
          {decision.action !== 'noop' && decision.action !== 'delete' && (
            <div className="flex items-center justify-between rounded-md border border-primary/25 bg-primary/5 p-2.5">
              <div className="flex items-center gap-2">
                <BrainCircuitIcon className="size-4 text-primary shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[11px] font-medium text-foreground">
                    {t('gatekeeper.viewMemoryImpact')}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {decision.action === 'update'
                      ? t('gatekeeper.updateImpactHint')
                      : t('gatekeeper.addImpactHint')}
                  </span>
                </div>
              </div>
              <Button
                type="button"
                size="xs"
                variant="outline"
                onClick={() => setImpactOpen(true)}
                className="h-6.5 text-[11px] font-medium border-primary/30 hover:bg-primary/10 hover:text-primary gap-1 shrink-0"
              >
                <span>{t('gatekeeper.auditDiff')}</span>
              </Button>
            </div>
          )}

          {/* 底部元数据栏 */}
          <div className="grid grid-cols-2 gap-2 rounded-md border border-border/40 bg-muted/10 p-2.5 text-[11px] text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <HardDriveIcon className="size-3.5" />
              <span>{t('gatekeeper.savedBytes')}:</span>
              <span className="font-mono font-semibold text-foreground">
                {formatBytes(decision.saved_bytes)}
              </span>
            </div>
            <div className="flex items-center justify-end gap-1.5">
              <ClockIcon className="size-3.5" />
              <span className="font-mono">{formatTime(decision.timestamp)}</span>
            </div>
          </div>
        </div>
      </SheetContent>

      {/* 嵌套呼出公共通用记忆增量抽屉 */}
      <UnifiedMemoryImpactDrawer
        open={impactOpen}
        onOpenChange={setImpactOpen}
        operations={impactOperations}
        title={
          decision.action === 'update'
            ? t('gatekeeper.impactTitleUpdate')
            : t('gatekeeper.impactTitleAdd')
        }
        description={decision.reason}
      />
    </Sheet>
  )
}
