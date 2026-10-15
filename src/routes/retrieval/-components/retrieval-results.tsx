import {
  Loader2,
  SearchIcon,
  Upload,
  Workflow,
} from 'lucide-react'
import type { TFunction } from 'i18next'

import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import type { FindQueryPlanItem } from '#/lib/retrieval'

import { LoadingHint } from './loading-hint'
import type { FlatRetrievalItem } from '../-types/retrieval'
import { TYPE_META } from './retrieval-constants'
import { ResultRow } from './retrieval-result-row'

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

      <div className="min-h-80 rounded-lg border border-border/60 bg-card/60 overflow-hidden shadow-xs">
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
            className="mt-1 h-7 rounded px-3 text-xs gap-1.5"
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
                className="inline-flex max-w-full items-center gap-1 rounded border border-border/60 bg-background px-2 py-0.5 text-xs text-muted-foreground"
              >
                {plan.context_type && (
                  <span
                    className={cn(
                      'font-mono font-semibold text-xs',
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
              <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
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

