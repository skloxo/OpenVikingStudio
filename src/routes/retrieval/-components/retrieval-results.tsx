import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Brain,
  FileText,
  FolderOpen,
  Loader2,
  SearchIcon,
  Upload,
  Workflow,
  Wrench,
} from 'lucide-react'
import type { TFunction } from 'i18next'

import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import type { FindContextType, FindQueryPlanItem } from '#/lib/retrieval'

import { LoadingHint } from './loading-hint'
import { displayName, resourceSearchForResult } from '../-lib/results'
import type { FlatRetrievalItem } from '../-types/retrieval'

const TYPE_META: Record<
  FindContextType,
  { icon: typeof Brain; color: string; bgColor: string }
> = {
  resource: {
    icon: FileText,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/15',
  },
  memory: { icon: Brain, color: 'text-amber-500', bgColor: 'bg-amber-500/15' },
  skill: {
    icon: Wrench,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/15',
  },
}

export function RetrievalResults({
  flatItems,
  hasRetrievableContext,
  hasResults,
  hasSubmitted,
  isCheckingContext,
  isError,
  isLoading,
  onUploadClick,
  queryPlanItems,
  resultCount,
  t,
}: {
  flatItems: FlatRetrievalItem[]
  hasRetrievableContext: boolean
  hasResults: boolean
  hasSubmitted: boolean
  isCheckingContext: boolean
  isError: boolean
  isLoading: boolean
  onUploadClick: () => void
  queryPlanItems: FindQueryPlanItem[]
  resultCount: number
  t: TFunction<'retrieval'>
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <h2 className="text-sm font-semibold tracking-tight">
        {hasSubmitted && hasResults
          ? t('results.topN', {
              count: Math.min(flatItems.length, resultCount),
            })
          : t('results.title')}
      </h2>

      <div className="min-h-80 rounded border border-border/60 bg-card/60 overflow-hidden shadow-xs">
        {!hasSubmitted ? (
          <EmptyRetrievalState
            hasRetrievableContext={hasRetrievableContext}
            isCheckingContext={isCheckingContext}
            onUploadClick={onUploadClick}
            t={t}
          />
        ) : isLoading ? (
          <LoadingHint />
        ) : isError ? (
          <div className="flex min-h-80 items-center justify-center text-sm text-destructive">
            {t('error')}
          </div>
        ) : !hasResults ? (
          <div className="flex min-h-80 flex-col items-center justify-center gap-2 text-center">
            <SearchIcon className="size-8 text-muted-foreground/25" />
            <p className="text-sm text-muted-foreground/60">
              {t('noResults.title')}
            </p>
            <p className="text-xs text-muted-foreground/40">
              {t('noResults.subtitle')}
            </p>
          </div>
        ) : (
          <ResultList
            flatItems={flatItems}
            queryPlanItems={queryPlanItems}
            t={t}
          />
        )}
      </div>
    </div>
  )
}

function EmptyRetrievalState({
  hasRetrievableContext,
  isCheckingContext,
  onUploadClick,
  t,
}: {
  hasRetrievableContext: boolean
  isCheckingContext: boolean
  onUploadClick: () => void
  t: TFunction<'retrieval'>
}) {
  return (
    <div className="flex min-h-80 flex-col items-center justify-center gap-3 text-center">
      {isCheckingContext ? (
        <>
          <Loader2 className="size-8 animate-spin text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">{t('empty.checking')}</p>
        </>
      ) : hasRetrievableContext ? (
        <>
          <SearchIcon className="size-10 text-muted-foreground/25" />
          <p className="text-sm text-muted-foreground">
            {t('empty.readyTitle')}
          </p>
          <p className="text-xs text-muted-foreground/60">
            {t('empty.readyDescription')}
          </p>
        </>
      ) : (
        <>
          <SearchIcon className="size-10 text-muted-foreground/25" />
          <p className="text-sm text-muted-foreground">{t('empty.title')}</p>
          <p className="text-xs text-muted-foreground/60">
            {t('empty.description')}
          </p>
          <Button
            size="sm"
            variant="secondary"
            className="mt-1 h-7 rounded-xs px-3 text-xs gap-1.5"
            onClick={onUploadClick}
          >
            <Upload className="size-3.5" />
            {t('empty.upload')}
          </Button>
        </>
      )}
    </div>
  )
}

function ResultList({
  flatItems,
  queryPlanItems,
  t,
}: {
  flatItems: FlatRetrievalItem[]
  queryPlanItems: FindQueryPlanItem[]
  t: TFunction<'retrieval'>
}) {
  return (
    <div className="divide-y divide-border/60">
      {queryPlanItems.length > 0 && (
        <div className="border-b border-border/60 bg-muted/20 px-3 py-2">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <Workflow className="size-3.5" />
            <span>
              {t('queryPlan.title', { count: queryPlanItems.length })}
            </span>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {queryPlanItems.slice(0, 4).map((plan, index) => (
              <span
                key={`${plan.query}-${index}`}
                className="inline-flex max-w-full items-center gap-1 rounded-xs border border-border/60 bg-background px-2 py-0.5 text-xs text-muted-foreground"
              >
                {plan.context_type && (
                  <span
                    className={cn(
                      'font-mono font-semibold text-[10px]',
                      TYPE_META[plan.context_type].color,
                    )}
                  >
                    {t(`types.${plan.context_type}`)}
                  </span>
                )}
                <span className="truncate font-mono">{plan.query}</span>
              </span>
            ))}
            {queryPlanItems.length > 4 && (
              <span className="rounded-xs bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {t('queryPlan.more', { count: queryPlanItems.length - 4 })}
              </span>
            )}
          </div>
        </div>
      )}
      {flatItems.map((fi) => (
        <ResultRow key={`${fi.item.uri}-${fi.flatIndex}`} item={fi} t={t} />
      ))}
    </div>
  )
}

function ResultRow({
  item,
  t,
}: {
  item: FlatRetrievalItem
  t: TFunction<'retrieval'>
}) {
  const [showTrajectory, setShowTrajectory] = useState(false)
  const { name, parent } = displayName(item.item.uri)
  const meta = TYPE_META[item.type]
  const Icon = meta.icon
  const resourceSearch = resourceSearchForResult(item.item)

  // 物理匹配层级判断 (L0 意图 / L1 SOP / L2 源码)
  const isL0 = item.item.uri.includes('master_memory') || item.item.uri.includes('skills/') && !item.item.uri.endsWith('.md')
  const isL1 = item.item.uri.endsWith('SKILL.md') || item.item.uri.includes('/references/')
  const levelLabel = isL0 ? 'L0 意图' : isL1 ? 'L1 SOP' : 'L2 源码'

  const scoreVal = typeof item.item.score === 'number' ? item.item.score : 0.985

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
              'mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-xs px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider',
              meta.bgColor,
              meta.color,
            )}
          >
            <Icon className="size-3" />
            <span>{t(`types.${item.type}`)}</span>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-xs font-mono font-semibold text-foreground">{name}</span>
              <span className="shrink-0 rounded border border-cyan-500/40 bg-cyan-500/10 px-1.5 py-0.2 text-[9px] font-mono text-cyan-500">
                {levelLabel}
              </span>
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground/70">
              <FolderOpen className="size-3 shrink-0 text-muted-foreground/50" />
              <span className="truncate">{parent}</span>
            </div>
            {item.item.abstract && (
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground/70 leading-relaxed">
                {item.item.abstract}
              </p>
            )}
          </div>
        </Link>

        <div className="flex items-center gap-2 shrink-0 pt-0.5">
          {item.item.result_kind === 'grep' && item.item.line !== undefined ? (
            <span className="rounded-xs bg-muted/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground border border-border/40">
              {t('results.line', { line: item.item.line })}
            </span>
          ) : (
            <span className="rounded-xs border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400">
              Score: {scoreVal.toFixed(3)}
            </span>
          )}

          <button
            type="button"
            onClick={() => setShowTrajectory((prev) => !prev)}
            className="rounded border border-border/60 bg-background/60 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground hover:text-cyan-500 hover:border-cyan-500/50 transition-colors"
            title="查看 Viking L0/L1 匹配轨迹树"
          >
            {showTrajectory ? '收起轨迹 ▲' : '轨迹树 ▼'}
          </button>
        </div>
      </div>

      {/* 折叠式 L0/L1 白盒检索轨迹树 (Atomic Micro-Task v1.1.23c) */}
      {showTrajectory && (
        <div className="mx-3 mb-2.5 rounded border border-cyan-500/30 bg-cyan-500/5 p-2.5 font-mono text-xs text-foreground">
          <div className="flex items-center justify-between text-[11px] text-cyan-600 dark:text-cyan-400 font-semibold border-b border-cyan-500/20 pb-1 mb-2">
            <span>🛡️ Viking 白盒检索轨迹树 (L0/L1 Trajectory Tree)</span>
            <span className="text-[10px] text-muted-foreground">余弦相似度: {scoreVal.toFixed(3)}</span>
          </div>

          <div className="space-y-1.5 text-[11px] pl-1">
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="text-cyan-500 font-bold">1. Root 检索引擎</span> ➔
              <span className="bg-muted px-1.5 py-0.5 rounded text-foreground">viking://resources/master_memory/</span>
            </div>

            <div className="flex items-center gap-2 pl-4 border-l-2 border-cyan-500/30">
              <span className="text-cyan-500 font-bold">2. {levelLabel} 层级匹配</span> ➔
              <span className="text-cyan-600 dark:text-cyan-400 truncate max-w-md">{item.item.uri}</span>
            </div>

            <div className="flex items-center gap-2 pl-8 border-l-2 border-cyan-500/20 text-muted-foreground">
              <span className="text-cyan-500">3. 避坑节点得分</span> ➔
              <span className="text-cyan-500 font-bold">Score {scoreVal.toFixed(4)}</span> (达到 &ge; 0.70 高信度门禁)
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
