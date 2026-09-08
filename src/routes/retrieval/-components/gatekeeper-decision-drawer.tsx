import { useTranslation } from 'react-i18next'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '#/components/ui/sheet'
import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'

export interface GatekeeperDecisionRecord {
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

  if (!decision) return null

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'noop':
        return (
          <Badge variant="outline" className="border-border/60 bg-muted/30 text-muted-foreground text-[11px] font-mono font-medium">
            {t('gatekeeper.noop')}
          </Badge>
        )
      case 'update':
        return (
          <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[11px] font-mono font-medium">
            {t('gatekeeper.update')}
          </Badge>
        )
      case 'delete':
        return (
          <Badge variant="outline" className="border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[11px] font-mono font-medium">
            {t('gatekeeper.delete')}
          </Badge>
        )
      default:
        return (
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary text-[11px] font-mono font-medium">
            {t('gatekeeper.add')}
          </Badge>
        )
    }
  }

  const formatBytes = (bytes?: number) => {
    if (!bytes) return '0 B'
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${bytes} B`
  }

  const formatTime = (ts?: number) => {
    if (!ts) return '--'
    const d = new Date(ts * 1000)
    return d.toLocaleTimeString()
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex w-full flex-col gap-4 overflow-y-auto sm:max-w-lg">
        <SheetHeader className="gap-1 border-b pb-3">
          <div className="flex items-center justify-between gap-2">
            <SheetTitle className="text-base font-semibold">
              {t('gatekeeper.drawerTitle')}
            </SheetTitle>
            {getActionBadge(decision.action)}
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            {t('gatekeeper.subtitle')}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-3.5 text-xs">
          {/* Similarity score block */}
          <div className="flex flex-col rounded-lg border bg-muted/20 p-3">
            <span className="text-[11px] font-medium text-muted-foreground">
              {t('gatekeeper.similarity')}
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className={cn(
                'font-mono text-2xl font-bold tabular-nums',
                decision.similarity >= 0.97 ? 'text-primary' :
                decision.similarity >= 0.92 ? 'text-amber-500' : 'text-foreground'
              )}>
                {decision.similarity.toFixed(4)}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">
                {decision.similarity >= 0.97
                  ? t('gatekeeper.simBandHigh')
                  : decision.similarity >= 0.92
                    ? t('gatekeeper.simBandMed')
                    : t('gatekeeper.simBandLow')}
              </span>
            </div>
          </div>

          {/* Decision reason */}
          <div className="flex flex-col rounded-lg border border-border/60 bg-background p-3">
            <span className="text-[11px] font-medium text-muted-foreground">
              {t('gatekeeper.decisionReason')}
            </span>
            <p className="mt-1.5 font-mono text-xs leading-relaxed text-foreground">
              {decision.reason}
            </p>
          </div>

          {/* Target URI */}
          {decision.uri && (
            <div className="flex flex-col rounded-lg border bg-muted/20 p-3">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t('gatekeeper.inputUri')}
              </span>
              <span className="mt-1 break-all font-mono text-[11px] text-foreground">
                {decision.uri}
              </span>
            </div>
          )}

          {/* Matched URI */}
          {decision.matched_uri && (
            <div className="flex flex-col rounded-lg border bg-muted/20 p-3">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t('gatekeeper.matchedUri')}
              </span>
              <span className="mt-1 break-all font-mono text-[11px] text-foreground">
                {decision.matched_uri}
              </span>
            </div>
          )}

          {/* Matched snippet */}
          {decision.matched_text_snippet && (
            <div className="flex flex-col rounded-lg border bg-muted/20 p-3">
              <span className="text-[11px] font-medium text-muted-foreground">
                {t('gatekeeper.viewSnippet')}
              </span>
              <p className="mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] text-muted-foreground">
                {decision.matched_text_snippet}
              </p>
            </div>
          )}

          {/* Metadata footer */}
          <div className="grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
            <div>
              <span>{t('gatekeeper.savedBytes')}: </span>
              <span className="font-mono font-medium text-foreground">{formatBytes(decision.saved_bytes)}</span>
            </div>
            <div className="text-right">
              <span>{t('gatekeeper.timestamp')}: </span>
              <span className="font-mono font-medium text-foreground">{formatTime(decision.timestamp)}</span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
