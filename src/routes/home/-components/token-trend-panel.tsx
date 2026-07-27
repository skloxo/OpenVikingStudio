import { lazy, Suspense } from 'react'

import { Skeleton } from '#/components/ui/skeleton'

import { TOKEN_SERIES_DAYS } from '../-constants/dashboard'
import type { ConsoleSeries, HomeT, TokenSeriesItem } from '../-types/dashboard'
import { getLastDaysRange, isDisabledPayload } from '../-lib/format'
import { normalizeTokenSeries } from '../-lib/normalize'
import { EmptyState, Panel, SectionHeading } from './panel'

const TokenTrendChart = lazy(() =>
  import('./token-trend-chart').then((module) => ({
    default: module.TokenTrendChart,
  })),
)

export function TokenTrendPanel({
  data,
  disabled: disabledProp,
  disabledMessage,
  isError,
  isLoading,
  t,
}: {
  data: ConsoleSeries<TokenSeriesItem> | undefined
  disabled?: boolean
  disabledMessage?: string
  isError: boolean
  isLoading: boolean
  t: HomeT
}) {
  const items = normalizeTokenSeries(data?.items)
  const disabled = Boolean(disabledProp) || isDisabledPayload(data)
  const rangeLabel =
    data?.start_date && data.end_date
      ? `${data.start_date} - ${data.end_date}`
      : `${getLastDaysRange(TOKEN_SERIES_DAYS).startDate} - ${getLastDaysRange(TOKEN_SERIES_DAYS).endDate}`

  return (
    <Panel>
      <SectionHeading
        action={
          <span className="rounded-sm border border-[oklch(0.68_0.12_232/0.2)] bg-background/70 px-2.5 py-0.5 text-xs tabular-nums text-muted-foreground shadow-2xs dark:bg-white/6">
            {rangeLabel}
          </span>
        }
        description={t('tokenTrend.description')}
        title={t('tokenTrend.title')}
      />

      {isLoading ? (
        <Skeleton className="h-60 w-full" />
      ) : isError ? (
        <EmptyState>{t('requestFailed')}</EmptyState>
      ) : disabled ? (
        <EmptyState>{disabledMessage ?? t('usageDisabled')}</EmptyState>
      ) : items.length === 0 ? (
        <EmptyState>{t('tokenTrend.empty')}</EmptyState>
      ) : (
        <Suspense fallback={<Skeleton className="h-60 w-full" />}>
          <TokenTrendChart items={items} t={t} />
        </Suspense>
      )}
    </Panel>
  )
}
