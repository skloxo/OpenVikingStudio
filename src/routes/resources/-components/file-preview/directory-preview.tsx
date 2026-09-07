import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslation } from 'react-i18next'

import { parseOkfSidecarMarkdown } from '#/lib/okf-markdown'
import { normalizeDirUri, normalizeReadContent } from '../../-lib/normalize'
import { fetchDirectorySidecarContent } from '../../-lib/api'
import type { VikingFsEntry } from '../../-types/viking-fm'
import { OkfMetadataPanel } from '../okf-metadata-panel'
import {
  DirectoryMarkdownLink,
  markdownComponents,
  transformDirectoryMarkdownUrl,
} from './markdown-renderer'

export type DirectoryLevelId = 'abstract' | 'overview'

export const DIRECTORY_LEVEL_META: Array<{
  id: DirectoryLevelId
  label: string
  name: string
  title: string
}> = [
  {
    id: 'abstract',
    label: 'Abstract',
    name: 'L0',
    title: 'Short semantic abstract',
  },
  {
    id: 'overview',
    label: 'Overview',
    name: 'L1',
    title: 'Directory overview',
  },
]

export function cleanSummaryContent(value: unknown): string {
  if (value === undefined || value === null) return ''
  const normalized = normalizeReadContent(value)
  const text = typeof normalized === 'string' ? normalized.trim() : ''
  if (!text) return ''
  if (
    /\[directory (overview|abstract) is not (generated|ready)\]/i.test(text)
  ) {
    return ''
  }
  return text
}

export function directoryLevelPreview(
  directoryUri: string,
  level: DirectoryLevelId,
  ...values: unknown[]
) {
  const rawContent =
    values.map(cleanSummaryContent).find((content) => content.length > 0) ?? ''
  const document = rawContent
    ? parseOkfSidecarMarkdown(
        `${normalizeDirUri(directoryUri)}.${level}.md`,
        rawContent,
      )
    : null

  return {
    content: document?.body ?? rawContent,
    document,
  }
}

export function useDirectoryPreview(file: VikingFsEntry | null) {
  const enabled = Boolean(file?.isDir)
  const abstractQuery = useQuery({
    enabled,
    queryKey: ['viking-directory-sidecar', file?.uri, 'abstract'],
    queryFn: () => fetchDirectorySidecarContent(file!.uri, 'abstract'),
    staleTime: 30_000,
  })
  const overviewQuery = useQuery({
    enabled,
    queryKey: ['viking-directory-sidecar', file?.uri, 'overview'],
    queryFn: () => fetchDirectorySidecarContent(file!.uri, 'overview'),
    staleTime: 30_000,
  })

  return useMemo(() => {
    const directoryUri = file?.uri ?? ''
    return {
      isLoading: abstractQuery.isLoading || overviewQuery.isLoading,
      levels: [
        {
          ...DIRECTORY_LEVEL_META[0],
          ...directoryLevelPreview(
            directoryUri,
            'abstract',
            abstractQuery.data,
            file?.abstract,
          ),
          error: abstractQuery.error,
        },
        {
          ...DIRECTORY_LEVEL_META[1],
          ...directoryLevelPreview(
            directoryUri,
            'overview',
            overviewQuery.data,
            file?.overview,
          ),
          error: overviewQuery.error,
        },
      ],
    }
  }, [
    abstractQuery.data,
    abstractQuery.error,
    abstractQuery.isLoading,
    file?.abstract,
    file?.overview,
    overviewQuery.data,
    overviewQuery.error,
    overviewQuery.isLoading,
  ])
}

interface DirectoryPreviewViewProps {
  file: VikingFsEntry
  onNavigate?: (uri: string) => void
}

export function DirectoryPreviewView({
  file,
  onNavigate,
}: DirectoryPreviewViewProps) {
  const { t } = useTranslation('resources')
  const directoryPreview = useDirectoryPreview(file)
  const [activeDirectoryLevels, setActiveDirectoryLevels] = useState<
    Set<DirectoryLevelId>
  >(new Set(['abstract', 'overview']))

  const availableDirectoryLevels = directoryPreview.levels.filter(
    (level) => level.document !== null || level.content.trim(),
  )
  const visibleDirectoryLevels = availableDirectoryLevels.filter((level) =>
    activeDirectoryLevels.has(level.id),
  )

  return (
    <div className="grid gap-4">
      {availableDirectoryLevels.length > 0 ? (
        <div className="flex flex-wrap gap-2 border-b pb-3">
          {availableDirectoryLevels.map((level) => {
            const active = activeDirectoryLevels.has(level.id)
            return (
              <button
                key={level.id}
                type="button"
                className={`inline-flex items-baseline gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors ${
                  active
                    ? 'border-border bg-muted text-foreground'
                    : 'border-border bg-background text-muted-foreground hover:border-foreground/30 hover:text-foreground'
                }`}
                title={level.title}
                onClick={() =>
                  setActiveDirectoryLevels((current) => {
                    const next = new Set(current)
                    if (next.has(level.id)) {
                      next.delete(level.id)
                    } else {
                      next.add(level.id)
                    }
                    return next
                  })
                }
              >
                <span className="font-mono text-[11px] font-semibold uppercase tracking-wide text-primary">
                  {level.name}
                </span>
                <span className="font-medium">{level.label}</span>
              </button>
            )
          })}
        </div>
      ) : null}

      {directoryPreview.isLoading && availableDirectoryLevels.length === 0 ? (
        <div className="text-sm text-muted-foreground">
          {t('filePreview.loadingContent')}
        </div>
      ) : availableDirectoryLevels.length === 0 ? (
        <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
          {t('filePreview.noDirectoryContext')}
        </div>
      ) : visibleDirectoryLevels.length === 0 ? (
        <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
          {t('filePreview.selectDirectoryContext')}
        </div>
      ) : (
        <div className="grid gap-5">
          {visibleDirectoryLevels.map((level, index) => (
            <section key={level.id} className="grid gap-2">
              {index > 0 ? <div className="border-t" /> : null}
              <header className="flex items-center gap-2 text-xs">
                <span className="font-mono font-semibold uppercase tracking-wide text-primary">
                  {level.name}
                </span>
                <span className="font-medium">{level.label}</span>
                <span className="text-muted-foreground">{level.title}</span>
              </header>
              {level.document ? (
                <OkfMetadataPanel
                  metadata={level.document.metadata}
                  onNavigate={onNavigate}
                  rawFrontmatter={level.document.rawFrontmatter}
                />
              ) : null}
              {level.content.trim() ? (
                <article className="prose prose-sm max-w-none break-words rounded-md border bg-muted/20 p-3 dark:prose-invert dark:prose-pre:bg-muted-foreground/20">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    urlTransform={transformDirectoryMarkdownUrl}
                    components={{
                      ...markdownComponents,
                      a: ({ href, children }) => (
                        <DirectoryMarkdownLink
                          href={href}
                          fileUri={file.uri}
                          onNavigate={onNavigate}
                        >
                          {children}
                        </DirectoryMarkdownLink>
                      ),
                    }}
                  >
                    {level.content}
                  </ReactMarkdown>
                </article>
              ) : null}
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
