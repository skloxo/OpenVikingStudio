import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  CopyIcon,
  CheckIcon,
  FileTextIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'
import type { GatekeeperDecisionRecord } from './gatekeeper-decision-drawer'

interface GatekeeperDecisionOverviewProps {
  decision: GatekeeperDecisionRecord
  copiedUri: boolean
  onCopy: (text: string, type: 'id' | 'uri') => void
}

export function GatekeeperDecisionOverview({
  decision,
  copiedUri,
  onCopy,
}: GatekeeperDecisionOverviewProps) {
  const { t } = useTranslation('tasksPage')

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
      {/* 左栏：确切余弦相似度与判定依据 */}
      <div className="flex flex-col gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              {t('gatekeeper.similarity')}
            </span>
            <Badge variant="outline" className="font-mono text-xs px-1.5 py-0 border-border/60">
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
          <span className="text-xs font-medium text-muted-foreground block mb-1">
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
                <span className="text-xs font-medium text-muted-foreground">
                  {t('gatekeeper.inputUri')}
                </span>
                <button
                  type="button"
                  onClick={() => onCopy(decision.uri!, 'uri')}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
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
                <span className="text-xs font-medium text-muted-foreground">
                  {t('gatekeeper.matchedUri')}
                </span>
                <button
                  type="button"
                  onClick={() => onCopy(decision.matched_uri!, 'uri')}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
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
              <span className="text-xs font-medium text-muted-foreground">
                {t('gatekeeper.viewSnippet')}
              </span>
            </div>
            <p className="max-h-24 overflow-y-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted-foreground rounded bg-background/80 p-2 border border-border/40">
              {decision.matched_text_snippet}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
