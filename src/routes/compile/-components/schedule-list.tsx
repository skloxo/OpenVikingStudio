import { useInfiniteQuery } from '@tanstack/react-query'
import { ClockIcon, RefreshCwIcon } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { fetchCompileConfigs, type CompileConfigSummary } from '../-lib/api'
import { CompileSelect } from './compile-select'
import { CompileScheduleTarget } from './schedule-target'
import { CompileError, CompileLoading } from './shared'

type Filter = 'all' | 'active' | 'disabled'

export function CompileScheduleList() {
  const { t } = useTranslation('compile')
  const { identityScopeKey } = useAppConnection()
  const [filter, setFilter] = useState<Filter>('all')

  const query = useInfiniteQuery({
    queryKey: ['compile-configs', identityScopeKey],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) => fetchCompileConfigs(pageParam, signal),
    getNextPageParam: (page) => page.next_cursor || undefined,
  })

  const targets = [
    ...new Map<string, CompileConfigSummary>(
      query.data?.pages
        .flatMap((page) => page.targets)
        .map((target) => [target.to, target]),
    ).values(),
  ]
  const visible = targets.filter((target) =>
    filter === 'all'
      ? true
      : filter === 'active'
        ? target.auto_update
        : !target.auto_update,
  )

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {t('schedule.listDescription')}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <CompileSelect
            label={t('schedule.filter')}
            className="min-w-36"
            value={filter}
            onValueChange={(value) => setFilter(value as Filter)}
            options={[
              { value: 'all', label: t('schedule.allTargets') },
              { value: 'active', label: t('schedule.active') },
              { value: 'disabled', label: t('schedule.disabled') },
            ]}
          />
          <Button
            variant="outline"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            <RefreshCwIcon />
            {t('refresh')}
          </Button>
        </div>
      </div>

      {query.isLoading ? (
        <CompileLoading />
      ) : query.isError ? (
        <CompileError error={query.error} retry={() => void query.refetch()} />
      ) : null}

      {!query.isLoading && !query.isError && !visible.length && (
        <div className="grid justify-items-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <ClockIcon className="size-8 text-muted-foreground" />
          <h2 className="font-medium">
            {t(
              filter === 'all'
                ? 'schedule.empty'
                : query.hasNextPage
                  ? 'schedule.emptyLoaded'
                  : 'schedule.emptyFiltered',
            )}
          </h2>
        </div>
      )}

      {!!visible.length && (
        <ul className="overflow-hidden rounded-xl border">
          {visible.map((target) => (
            <CompileScheduleTarget key={target.to} target={target} />
          ))}
        </ul>
      )}

      {query.hasNextPage && (
        <Button
          variant="outline"
          className="self-center"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {t(query.isFetchingNextPage ? 'loading' : 'more')}
        </Button>
      )}
    </div>
  )
}
