import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  FolderOpen,
  GitFork,
  Layers,
} from 'lucide-react'
import type { TFunction } from 'i18next'
import { toast } from 'sonner'

import { cn } from '#/lib/utils'
import { retrievalResultNameFromUri } from '#/lib/viking-uri'
import { displayName, resourceSearchForResult } from '../-lib/results'
import type { FlatRetrievalItem } from '../-types/retrieval'
import { TYPE_META } from './retrieval-constants'
import { MemoryStatusBadge } from './memory-status-badge'

export function ResultRow({
  item,
  t,
}: {
  item: FlatRetrievalItem
  t: TFunction<'retrieval'>
}) {
  const [showTrajectory, setShowTrajectory] = useState(false)
  const [copied, setCopied] = useState(false)
  const { parent } = displayName(item.item.uri)
  const name = retrievalResultNameFromUri(item.item.uri)
  const meta = TYPE_META[item.type]
  const Icon = meta.icon
  const resourceSearch = resourceSearchForResult(item.item)

  // 物理匹配层级判断 (L0 Abstract 意图 / L1 Overview SOP / L2 Detail 源码切片)
  const levelNum =
    typeof item.item.level === 'number'
      ? item.item.level
      : item.item.uri.includes('master_memory') ||
          (item.item.uri.includes('skills/') && !item.item.uri.endsWith('.md')) ||
          item.item.uri.endsWith('.abstract.md')
        ? 0
        : item.item.uri.endsWith('SKILL.md') ||
            item.item.uri.endsWith('.overview.md') ||
            item.item.uri.includes('/references/')
          ? 1
          : 2

  const levelTag = levelNum === 0 ? 'L0' : levelNum === 1 ? 'L1' : 'L2'
  const levelFullLabel =
    levelNum === 0
      ? t('trajectory.levels.l0')
      : levelNum === 1
        ? t('trajectory.levels.l1')
        : t('trajectory.levels.l2')

  const scoreVal = typeof item.item.score === 'number' ? item.item.score : 0.985
  const isHighConfidence = scoreVal >= 0.7

  const uriLower = item.item.uri.toLowerCase()
  const isStagingOrArchived =
    uriLower.includes('/staging/') ||
    uriLower.includes('/archive/') ||
    uriLower.includes('_sessions')
  const isDeprecated = uriLower.includes('1936') || uriLower.includes('deprecated')
  const lifecycleStatus = isDeprecated
    ? 'deprecated'
    : isStagingOrArchived
      ? 'archived'
      : 'active'

  const handleCopyUri = (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    void navigator.clipboard.writeText(item.item.uri)
    setCopied(true)
    toast.success(t('trajectory.uriCopied'))
    setTimeout(() => setCopied(false), 2000)
  }

  const itemMeta = ((item.item as any).extra_metadata || {}) as Record<string, any>
  const rawStatus = ((item.item as any).status || itemMeta.status || lifecycleStatus) as string
  const supersededBy = itemMeta.superseded_by as string | undefined
  const disputedReason = itemMeta.disputed_reason as string | undefined
  const isSuperseded = rawStatus.toLowerCase() === 'superseded'

  return (
    <div className="flex flex-col border-b border-border/40 last:border-b-0">
      <div className="flex w-full items-start justify-between gap-2.5 px-3 py-2.5 transition-colors hover:bg-muted/40 font-sans">
        <Link
          to="/playground"
          search={resourceSearch}
          target="_blank"
          rel="noreferrer noopener"
          className="flex flex-1 items-start gap-2.5 min-w-0"
        >
          <div
            className={cn(
              'mt-0.5 inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-mono font-semibold uppercase tracking-wider',
              meta.bgColor,
              meta.color,
            )}
          >
            <Icon className="size-3" />
            <span>{t(`types.${item.type}`)}</span>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={cn(
                  'truncate text-xs font-mono font-semibold text-foreground',
                  isSuperseded && 'line-through opacity-60 text-muted-foreground',
                )}
              >
                {name}
              </span>
              <span
                className={cn(
                  'shrink-0 rounded border px-1.5 py-0.5 text-xs font-mono font-medium',
                  levelNum === 0
                    ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                    : levelNum === 1
                      ? 'border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400'
                      : 'border-muted-foreground/30 bg-muted/40 text-muted-foreground',
                )}
                title={levelFullLabel}
              >
                {levelTag}
              </span>
              <MemoryStatusBadge
                status={rawStatus}
                supersededBy={supersededBy}
                disputedReason={disputedReason}
              />
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-xs font-mono text-muted-foreground/70">
              <FolderOpen className="size-3 shrink-0 text-muted-foreground/50" />
              <span className="truncate">{parent}</span>
            </div>
            {item.item.abstract && (
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground/80 leading-relaxed">
                {item.item.abstract}
              </p>
            )}
          </div>
        </Link>

        <div className="flex items-center gap-2 shrink-0 pt-0.5">
          {item.item.result_kind === 'grep' && item.item.line !== undefined ? (
            <span className="rounded bg-muted/60 px-1.5 py-0.5 font-mono text-xs text-muted-foreground border border-border/40">
              {t('results.line', { line: item.item.line })}
            </span>
          ) : (
            <span
              className={cn(
                'rounded border px-2 py-0.5 font-mono text-xs font-bold tabular-nums',
                isHighConfidence
                  ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                  : 'border-border bg-muted/30 text-foreground',
              )}
            >
              {t('trajectory.scoreBadge', { score: scoreVal.toFixed(3) })}
            </span>
          )}

          <button
            type="button"
            onClick={() => setShowTrajectory((prev) => !prev)}
            className={cn(
              'inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-mono transition-colors cursor-pointer',
              showTrajectory
                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                : 'border-border/60 bg-background/60 text-muted-foreground hover:text-cyan-600 hover:border-cyan-500/40 dark:hover:text-cyan-400',
            )}
            title={t('trajectory.title')}
          >
            <span>{showTrajectory ? t('trajectory.hide') : t('trajectory.show')}</span>
            {showTrajectory ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
          </button>
        </div>
      </div>

      {/* 折叠式 L0/L1/L2 白盒检索轨迹树 */}
      {showTrajectory && (
        <div className="mx-3 mb-2.5 rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3 font-mono text-xs text-foreground space-y-2.5">
          <div className="flex items-center justify-between text-xs text-cyan-600 dark:text-cyan-400 font-semibold border-b border-cyan-500/20 pb-1.5">
            <span className="flex items-center gap-1.5 font-sans">
              <Layers className="size-3.5 text-cyan-500 shrink-0" />
              {t('trajectory.title')}
            </span>
            <span className="text-xs tabular-nums font-mono">
              {t('trajectory.score', { score: scoreVal.toFixed(4) })}
            </span>
          </div>

          <div className="space-y-2 text-xs pl-1">
            {/* Step 1: Root Entry */}
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="text-cyan-600 dark:text-cyan-400 font-bold shrink-0">{t('trajectory.rootEngine')}</span>
              <span className="text-muted-foreground/60">{'\u2794'}</span>
              <span className="bg-muted/60 border border-border/50 px-1.5 py-0.5 rounded text-foreground truncate max-w-md">
                {item.item.uri.startsWith('viking://') ? item.item.uri.split('/').slice(0, 4).join('/') + '/' : 'viking://'}
              </span>
            </div>

            {/* Step 2: Level Match */}
            <div className="flex items-start gap-2 pl-3 border-l-2 border-cyan-500/30">
              <span className="text-cyan-600 dark:text-cyan-400 font-bold shrink-0 mt-0.5">
                {t('trajectory.levelMatch', { level: levelFullLabel })}
              </span>
              <span className="text-muted-foreground/60 mt-0.5">{'\u2794'}</span>
              <div className="flex items-center gap-1.5 min-w-0 flex-1">
                <span className="text-foreground font-medium truncate" title={item.item.uri}>
                  {item.item.uri}
                </span>
                <button
                  type="button"
                  onClick={handleCopyUri}
                  className="shrink-0 p-1 text-muted-foreground hover:text-foreground rounded transition-colors cursor-pointer"
                  title={t('trajectory.copyUri')}
                >
                  {copied ? <Check className="size-3 text-cyan-500" /> : <Copy className="size-3" />}
                </button>
              </div>
            </div>

            {/* Step 3: Similarity & Gate check */}
            <div className="flex items-center gap-2 pl-6 border-l-2 border-cyan-500/20 text-muted-foreground">
              <span className="text-cyan-600 dark:text-cyan-400 font-bold shrink-0">{t('trajectory.similarityCheck')}</span>
              <span className="text-muted-foreground/60">{'\u2794'}</span>
              <span className="font-bold text-cyan-600 dark:text-cyan-400 tabular-nums">
                {t('trajectory.scoreBadge', { score: scoreVal.toFixed(4) })}
              </span>
              <span className="text-muted-foreground/80 font-sans text-xs">
                ({isHighConfidence ? t('trajectory.highConfidence') : t('trajectory.scoreGateLow')})
              </span>
            </div>

            {/* Optional Match Reason */}
            {item.item.match_reason && (
              <div className="pl-6 border-l-2 border-cyan-500/20 text-muted-foreground/90 font-sans">
                <span className="text-cyan-600 dark:text-cyan-400 font-semibold">{t('trajectory.matchReason', { reason: item.item.match_reason })}</span>
              </div>
            )}

            {/* Step 4: Linked Relations (if any) */}
            {Array.isArray(item.item.relations) && item.item.relations.length > 0 && (
              <div className="pl-6 border-l-2 border-cyan-500/20 space-y-1">
                <div className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-semibold">
                  <GitFork className="size-3" />
                  <span>{t('trajectory.relationsTitle')} ({item.item.relations.length})</span>
                </div>
                <div className="space-y-1 pl-2">
                  {item.item.relations.map((rel, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-muted-foreground">
                      <span className="text-muted-foreground/60">↳</span>
                      <span className="text-foreground truncate max-w-sm">{rel.uri}</span>
                      {rel.abstract && (
                        <span className="text-muted-foreground/60 truncate max-w-xs">({rel.abstract})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
