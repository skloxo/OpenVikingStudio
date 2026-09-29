import { useState } from 'react'
import {
  Check,
  Copy,
  FileCode,
  FileDiff,
  Loader2,
  Sparkles,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { ScrollArea } from '#/components/ui/scroll-area'
import type { SnapshotCommit } from '../-lib/api'
import type { ParsedDiffLine } from './version-timeline-utils'

export interface VersionTimelineViewerProps {
  activeCommit: SnapshotCommit | null
  activeOid: string
  viewTab: 'diff' | 'source'
  onViewTabChange: (tab: 'diff' | 'source') => void
  isLoadingDiff: boolean
  diffContent: string
  parsedDiffLines: ParsedDiffLine[]
  isLoadingSource: boolean
  historicalContent: string
}

export function VersionTimelineViewer({
  activeCommit,
  activeOid,
  viewTab,
  onViewTabChange,
  isLoadingDiff,
  diffContent,
  parsedDiffLines,
  isLoadingSource,
  historicalContent,
}: VersionTimelineViewerProps) {
  const { t } = useTranslation(['resources', 'common'])
  const [copiedOid, setCopiedOid] = useState(false)

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedOid(true)
    setTimeout(() => setCopiedOid(false), 1500)
    toast.success(t('common.copied') || '已复制')
  }

  return (
    <div className="md:col-span-7 flex flex-col min-h-0 bg-background">
      {/* View Switcher & Details Bar */}
      {activeCommit ? (
        <div className="p-3 border-b border-border flex items-center justify-between shrink-0 bg-muted/15">
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-md border border-border p-0.5 bg-muted/50">
              <button
                type="button"
                onClick={() => onViewTabChange('diff')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs transition-all ${
                  viewTab === 'diff'
                    ? 'bg-background font-semibold text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <FileDiff className="size-3.5 text-cyan-400" />
                {t('versionTimeline.tabDiff')}
              </button>
              <button
                type="button"
                onClick={() => onViewTabChange('source')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs transition-all ${
                  viewTab === 'source'
                    ? 'bg-background font-semibold text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <FileCode className="size-3.5 text-cyan-400" />
                {t('versionTimeline.tabSource')}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => copyToClipboard(activeOid)}
              className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground px-2.5 py-1 rounded border border-border hover:bg-muted/50 transition-colors"
              title={activeOid}
            >
              {copiedOid ? (
                <Check className="size-3 text-cyan-400" />
              ) : (
                <Copy className="size-3" />
              )}
              <span>{activeOid.slice(0, 10)}</span>
            </button>
          </div>
        </div>
      ) : null}

      {/* Viewer Panel */}
      <div className="flex-1 min-h-0 relative">
        {!activeCommit ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            {t('versionTimeline.selectVersionPrompt')}
          </div>
        ) : viewTab === 'diff' ? (
          isLoadingDiff ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground gap-2">
              <Loader2 className="size-4 animate-spin text-cyan-400" />
              <span>{t('versionTimeline.loadingDiff')}</span>
            </div>
          ) : !diffContent || diffContent.trim() === '' ? (
            <div className="flex flex-col h-full items-center justify-center text-xs text-muted-foreground gap-2 p-8 text-center">
              <Sparkles className="size-8 text-cyan-400/70" />
              <span className="font-semibold text-sm text-foreground">
                {t('versionTimeline.noDiffTitle')}
              </span>
              <span className="text-xs text-muted-foreground max-w-sm">
                {t('versionTimeline.noDiffDesc')}
              </span>
            </div>
          ) : (
            <ScrollArea className="h-full font-mono text-xs">
              <div className="p-3 space-y-0.5 select-text">
                {parsedDiffLines.map(({ line, type, key }) => {
                  let lineStyle = 'text-foreground/85 hover:bg-muted/30'
                  if (type === 'add') {
                    lineStyle =
                      'text-cyan-400 bg-cyan-500/10 font-semibold border-l-2 border-cyan-500'
                  } else if (type === 'del') {
                    lineStyle =
                      'text-rose-400 bg-rose-500/10 font-semibold border-l-2 border-rose-500'
                  } else if (type === 'meta') {
                    lineStyle = 'text-muted-foreground font-semibold bg-muted/60'
                  }
                  return (
                    <div
                      key={key}
                      className={`px-2.5 py-0.5 rounded-sm whitespace-pre-wrap break-all ${lineStyle}`}
                    >
                      {line || ' '}
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          )
        ) : isLoadingSource ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground gap-2">
            <Loader2 className="size-4 animate-spin text-cyan-400" />
            <span>{t('versionTimeline.loadingSource')}</span>
          </div>
        ) : (
          <ScrollArea className="h-full font-mono text-xs">
            <pre className="p-4 text-foreground/95 whitespace-pre-wrap break-all select-text leading-relaxed font-mono">
              {historicalContent || t('versionTimeline.emptyContent')}
            </pre>
          </ScrollArea>
        )}
      </div>
    </div>
  )
}
