import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import {
  ArrowUpRightIcon,
  BrainCircuitIcon,
  FileTextIcon,
  LoaderCircleIcon,
  MessageSquareTextIcon,
  RefreshCwIcon,
  SearchIcon,
  XIcon,
} from 'lucide-react'
import * as React from 'react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { Input } from '#/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { useAppConnection } from '#/hooks/use-app-connection'
import { isOvClientError } from '#/lib/ov-client'

import {
  EmptyHelpChecklist,
  HighlightedText,
} from './-components/experience-list-helpers'
import { ExperienceOverviewBar } from './-components/experience-overview-bar'
import { ExperiencePagination } from './-components/experience-pagination'
import { ExperiencePreviewSheet } from './-components/experience-preview-sheet'
import { ExperienceSetupGuide } from './-components/experience-setup-guide'
import { fetchExperiences, searchExperiences } from './-lib/api'
import {
  buildExperiencesUri,
  formatTimestamp,
  isExperienceUpdatedSinceLastSeen,
  markExperiencesSeen,
} from './-lib/experience'
import type { ExperienceFileItem } from './-lib/types'

export const Route = createFileRoute('/agent-experience/')({
  component: AgentExperienceRoute,
})

function getErrorMessage(error: unknown): string {
  if (isOvClientError(error) || error instanceof Error) {
    return error.message
  }
  return String(error)
}

export function AgentExperienceRoute() {
  const { t, i18n } = useTranslation('agentExperiencePage')
  const { connection, identityScopeKey } = useAppConnection()
  const [keyword, setKeyword] = React.useState('')
  const [searchKeyword, setSearchKeyword] = React.useState('')
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)
  const [previewExperience, setPreviewExperience] =
    React.useState<ExperienceFileItem | null>(null)

  const experiencesUri = buildExperiencesUri(connection.userId)
  React.useEffect(() => {
    const timeout = window.setTimeout(() => {
      setSearchKeyword(keyword.trim())
      setPage(1)
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [keyword])

  const experiencesQuery = useQuery({
    queryFn: ({ signal }) =>
      searchKeyword
        ? searchExperiences({ experiencesUri, keyword: searchKeyword, signal })
        : fetchExperiences({ experiencesUri, page, pageSize, signal }),
    queryKey: [
      'agent-experience-list',
      identityScopeKey,
      experiencesUri,
      page,
      pageSize,
      searchKeyword,
    ],
    staleTime: 30_000,
  })

  const pageItems = experiencesQuery.data?.items ?? []
  const hasMore = experiencesQuery.data?.hasMore ?? false
  const experiences = pageItems

  const [updatedUris, setUpdatedUris] = React.useState<ReadonlySet<string>>(
    () => new Set(),
  )
  const markedRef = React.useRef<string | null>(null)
  React.useEffect(() => {
    if (!experiencesQuery.isSuccess || experiences.length === 0) return
    const fingerprint = `${experiencesUri}:${experiences
      .map((item) => item.uri)
      .join('|')}`
    if (markedRef.current === fingerprint) return
    markedRef.current = fingerprint

    setUpdatedUris(
      new Set(
        experiences
          .filter((experience) =>
            isExperienceUpdatedSinceLastSeen(
              experience.uri,
              experience.modTime,
            ),
          )
          .map((experience) => experience.uri),
      ),
    )
    markExperiencesSeen(experiences)
  }, [experiences, experiencesQuery.isSuccess, experiencesUri])

  const connectionUnavailable =
    isOvClientError(experiencesQuery.error) &&
    experiencesQuery.error.code === 'NETWORK_ERROR'

  return (
    <div className="flex w-full min-w-0 flex-col gap-5 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid gap-1.5">
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight">
              {t('title')}
            </h1>
          </div>
          <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={experiencesQuery.isFetching}
            onClick={() => void experiencesQuery.refetch()}
          >
            <RefreshCwIcon
              className={
                experiencesQuery.isFetching ? 'animate-spin' : undefined
              }
            />
            {t('refresh')}
          </Button>
        </div>
      </header>

      <ExperienceOverviewBar />

      <ExperienceSetupGuide />

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 px-4 py-3">
        <div className="relative w-full sm:max-w-md">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label={t('searchPlaceholder')}
            autoComplete="off"
            className="h-9 bg-transparent pr-9 pl-8 shadow-none dark:bg-transparent"
            name="agent-experience-search"
            placeholder={t('searchPlaceholder')}
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          {keyword ? (
            <button
              type="button"
              aria-label={t('searchClear')}
              className="absolute top-1/2 right-2 flex size-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              onClick={() => setKeyword('')}
            >
              <XIcon className="size-3.5" />
            </button>
          ) : null}
        </div>
        {experiencesQuery.isSuccess && (
          <span className="text-xs tabular-nums text-muted-foreground">
            {t(searchKeyword ? 'searchCount' : 'pageCount', {
              count: experiences.length,
            })}
          </span>
        )}
      </div>

      {experiencesQuery.isLoading ? (
        <Card className="min-h-56 items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin" />
            {t('loading')}
          </div>
        </Card>
      ) : experiencesQuery.isError ? (
        <Card className="min-h-56 items-center justify-center px-6 text-center">
          <div className="grid gap-1">
            <p className="font-medium">{t('loadFailed')}</p>
            <p className="max-w-xl text-sm text-muted-foreground">
              {connectionUnavailable
                ? t('networkError')
                : getErrorMessage(experiencesQuery.error)}
            </p>
            {connectionUnavailable ? (
              <Button
                render={<Link to="/settings" />}
                nativeButton={false}
                variant="outline"
                size="sm"
                className="mx-auto mt-2"
              >
                {t('connectionSettings')}
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mx-auto mt-2"
                disabled={experiencesQuery.isFetching}
                onClick={() => void experiencesQuery.refetch()}
              >
                <RefreshCwIcon
                  className={
                    experiencesQuery.isFetching ? 'animate-spin' : undefined
                  }
                />
                {t('refresh')}
              </Button>
            )}
          </div>
        </Card>
      ) : pageItems.length === 0 && page === 1 && !hasMore && !searchKeyword ? (
        <Card className="min-h-56 items-center justify-center px-6 py-8 text-center">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <BrainCircuitIcon className="size-5" />
          </div>
          <div className="grid max-w-md gap-1">
            <p className="font-medium">{t('empty')}</p>
            <p className="text-sm text-muted-foreground">
              {t('emptyDescription')}
            </p>
            <Button
              render={<Link to="/sessions" />}
              nativeButton={false}
              variant="outline"
              size="sm"
              className="mx-auto mt-3"
            >
              <MessageSquareTextIcon />
              {t('emptyAction')}
            </Button>
          </div>
          <div className="pt-4">
            <EmptyHelpChecklist />
          </div>
        </Card>
      ) : (
        <Card
          size="sm"
          className="rounded-xl bg-background shadow-none ring-border/70 data-[size=sm]:gap-0 data-[size=sm]:py-0"
        >
          {experiences.length === 0 ? (
            <div className="grid min-h-40 place-items-center px-6 py-8 text-center">
              <div className="grid max-w-md gap-1">
                <p className="font-medium">{t('searchNoResults')}</p>
                <p className="text-sm text-muted-foreground">
                  {t('searchNoResultsDescription')}
                </p>
              </div>
            </div>
          ) : (
            <Table className="table-fixed">
              <TableHeader>
                <TableRow className="bg-muted/15 hover:bg-muted/15">
                  <TableHead className="h-10 pl-4 text-xs font-normal text-muted-foreground">
                    {t('columnFile')}
                  </TableHead>
                  <TableHead className="hidden h-10 w-28 sm:table-cell text-xs font-normal text-muted-foreground">
                    {t('columnSource')}
                  </TableHead>
                  <TableHead className="hidden h-10 w-24 md:table-cell text-xs font-normal text-muted-foreground">
                    {t('columnApplied')}
                  </TableHead>
                  {!searchKeyword && (
                    <TableHead className="hidden h-10 w-44 lg:table-cell text-xs font-normal text-muted-foreground">
                      {t('columnUpdated')}
                    </TableHead>
                  )}
                  <TableHead className="h-10 w-28 pr-4 text-right text-xs font-normal text-muted-foreground">
                    {t('columnActions')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {experiences.map((experience) => {
                  const updated = formatTimestamp(
                    experience.modTime,
                    i18n.language,
                  )
                  const isUpdated = updatedUris.has(experience.uri)

                  return (
                    <TableRow
                      key={experience.uri}
                      className="group cursor-pointer border-border/50 transition-colors hover:bg-muted/30"
                      onClick={() => setPreviewExperience(experience)}
                    >
                      <TableCell className="min-w-0 py-3.5 pl-4">
                        <div className="flex min-w-0 items-center gap-3">
                          <span className="flex size-5 shrink-0 items-center justify-center text-muted-foreground/60 transition-colors group-hover:text-foreground">
                            <FileTextIcon className="size-4" />
                          </span>
                          <div className="grid min-w-0 gap-1">
                            <div className="flex min-w-0 items-center gap-1.5">
                              <button
                                type="button"
                                title={experience.uri}
                                className="min-w-0 truncate text-left text-sm font-medium underline-offset-4 hover:text-primary hover:underline focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  setPreviewExperience(experience)
                                }}
                              >
                                <HighlightedText
                                  keyword={searchKeyword}
                                  text={experience.name}
                                />
                              </button>
                              {isUpdated ? (
                                <Badge
                                  variant="secondary"
                                  className="shrink-0 bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 text-xs"
                                >
                                  {t('updatedBadge')}
                                </Badge>
                              ) : null}
                            </div>
                            {searchKeyword &&
                            !experience.name
                              .toLocaleLowerCase()
                              .includes(searchKeyword.toLocaleLowerCase()) ? (
                              <span
                                className="truncate font-mono text-xs text-muted-foreground"
                                title={experience.uri}
                              >
                                <HighlightedText
                                  keyword={searchKeyword}
                                  text={experience.uri}
                                />
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="hidden sm:table-cell">
                        <Badge
                          variant="outline"
                          className={
                            experience.source === 'evolution_lesson'
                              ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 text-xs'
                              : 'text-xs text-muted-foreground'
                          }
                        >
                          {experience.source === 'evolution_lesson'
                            ? t('sourceBadge.evolutionLesson')
                            : t('sourceBadge.experience')}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-xs tabular-nums text-muted-foreground">
                        {experience.trajectoryCount !== undefined
                          ? t('appliedCount', {
                              count: experience.trajectoryCount,
                            })
                          : '-'}
                      </TableCell>
                      {!searchKeyword && (
                        <TableCell className="hidden lg:table-cell text-xs tabular-nums text-muted-foreground">
                          {updated ?? '-'}
                        </TableCell>
                      )}
                      <TableCell
                        className="pr-4 text-right"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <Button
                          render={
                            <Link
                              params={{ experienceUri: experience.uri }}
                              to="/agent-experience/$experienceUri"
                            />
                          }
                          nativeButton={false}
                          size="xs"
                          variant="ghost"
                          className="gap-1 text-muted-foreground hover:text-foreground"
                          aria-label={t('openDetail', {
                            name: experience.name,
                          })}
                        >
                          {t('viewAnalysis')}
                          <ArrowUpRightIcon className="size-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
          {!searchKeyword && (
            <ExperiencePagination
              page={page}
              hasMore={hasMore}
              disabled={experiencesQuery.isFetching}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={(nextPageSize) => {
                setPageSize(nextPageSize)
                setPage(1)
              }}
            />
          )}
        </Card>
      )}

      <ExperiencePreviewSheet
        experience={previewExperience}
        language={i18n.language}
        onClose={() => setPreviewExperience(null)}
      />
    </div>
  )
}
