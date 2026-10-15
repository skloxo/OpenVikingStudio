import {
  useEffect,
  useMemo,
  useState,
  type ComponentProps,
  type ReactNode,
} from 'react'
import hljs from 'highlight.js/lib/core'
import { defaultUrlTransform } from 'react-markdown'

import { client } from '#/gen/ov-client/client.gen'
import { getContentDownload, ovClient } from '#/lib/ov-client'
import { fileNameFromUri } from '#/lib/viking-uri'
import type { GetContentDownloadData } from '#/gen/ov-client/types.gen'
import type { ContentDownloadQuery } from '@ov-server/api/v1/content'

import {
  ensureLanguage,
  escapeHtml,
  normalizeMarkdownLanguage,
} from '../../-lib/syntax-highlight'

export const vikingPrefix = 'viking://'
export const contentDownloadUrl: GetContentDownloadData['url'] =
  '/api/v1/content/download'

export function toDownloadUrl(vikingUri: string): string {
  const query: ContentDownloadQuery = { uri: vikingUri }
  return client.buildUrl({
    baseURL: ovClient.getOptions().baseUrl,
    query,
    url: contentDownloadUrl,
  })
}

export function withCacheBust(url: string, cacheKey: string): string {
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}_t=${encodeURIComponent(cacheKey)}`
}

export function dirnameVikingUri(fileUri: string): string {
  if (fileUri === vikingPrefix) {
    return vikingPrefix
  }

  const trimmed = fileUri.endsWith('/') ? fileUri.slice(0, -1) : fileUri
  const idx = trimmed.lastIndexOf('/')
  if (idx < vikingPrefix.length) {
    return vikingPrefix
  }
  return `${trimmed.slice(0, idx + 1)}`
}

export function resolveRelativeVikingUri(
  baseFileUri: string,
  rawPath: string,
): string {
  const baseDir = dirnameVikingUri(baseFileUri)
  const baseBody = baseDir.slice(vikingPrefix.length, -1)

  const pathPart = rawPath.split('#')[0]?.split('?')[0] || ''
  const suffix = rawPath.slice(pathPart.length)

  const baseSegments = baseBody ? baseBody.split('/').filter(Boolean) : []
  const relativeSegments = pathPart.split('/').filter(Boolean)

  const merged = [...baseSegments]
  for (const segment of relativeSegments) {
    if (segment === '.') continue
    if (segment === '..') {
      merged.pop()
      continue
    }
    merged.push(segment)
  }

  const resolved = `${vikingPrefix}${merged.join('/')}`
  return `${resolved}${suffix}`
}

export type MarkdownAssetTarget =
  | { kind: 'external'; value: string }
  | { kind: 'raw'; value: string }
  | { kind: 'viking'; value: string }

export function safeDecodeUri(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export function resolveMarkdownAssetTarget(
  assetPath: string,
  fileUri: string,
): MarkdownAssetTarget {
  const trimmed = assetPath.trim()
  if (!trimmed || trimmed.startsWith('#')) {
    return { kind: 'raw', value: trimmed }
  }

  if (/^(https?:|data:|blob:|mailto:|tel:)/i.test(trimmed)) {
    return { kind: 'external', value: trimmed }
  }

  const decoded = safeDecodeUri(trimmed)
  const vikingUri = decoded.startsWith(vikingPrefix)
    ? decoded
    : resolveRelativeVikingUri(fileUri, decoded)
  return { kind: 'viking', value: vikingUri }
}

export function resolveMarkdownAssetUrl(
  assetPath: string,
  fileUri: string,
): string {
  const target = resolveMarkdownAssetTarget(assetPath, fileUri)
  if (target.kind === 'viking') {
    return toDownloadUrl(target.value)
  }
  return target.value
}

export function transformDirectoryMarkdownUrl(url: string): string {
  return url.startsWith(vikingPrefix) ? url : defaultUrlTransform(url)
}

export function MarkdownLink({
  children,
  fileUri,
  href,
  onNavigate,
}: {
  children?: ReactNode
  fileUri: string
  href?: string
  onNavigate?: (uri: string) => void
}) {
  const target = href ? resolveMarkdownAssetTarget(String(href), fileUri) : null
  const isInternal = target?.kind === 'viking' && Boolean(onNavigate)
  const resolvedHref = target
    ? isInternal
      ? target.value
      : resolveMarkdownAssetUrl(target.value, fileUri)
    : ''
  const isExternal = /^(https?:|mailto:|tel:)/i.test(resolvedHref)

  return (
    <a
      href={resolvedHref}
      onClick={(event) => {
        if (target?.kind === 'viking' && onNavigate) {
          event.preventDefault()
          onNavigate(target.value)
        }
      }}
      target={isExternal ? '_blank' : undefined}
      rel={isExternal ? 'noreferrer noopener' : undefined}
    >
      {children}
    </a>
  )
}

export function DirectoryMarkdownLink({
  children,
  fileUri,
  href,
  onNavigate,
}: {
  children?: ReactNode
  fileUri: string
  href?: string
  onNavigate?: (uri: string) => void
}) {
  const decodedHref = href ? safeDecodeUri(href.trim()) : ''
  if (!decodedHref.startsWith(vikingPrefix)) {
    return <a href={href}>{children}</a>
  }

  return (
    <MarkdownLink href={decodedHref} fileUri={fileUri} onNavigate={onNavigate}>
      {children}
    </MarkdownLink>
  )
}

export function MarkdownImage({
  src,
  alt,
  fileUri,
}: {
  src?: string
  alt?: string
  fileUri: string
}) {
  const target = useMemo(
    () => (src ? resolveMarkdownAssetTarget(String(src), fileUri) : null),
    [src, fileUri],
  )
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!target || target.kind !== 'viking') return

    let alive = true
    let created: string | null = null
    setObjectUrl(null)
    setFailed(false)

    const run = async () => {
      try {
        const response = await getContentDownload({
          query: { uri: target.value },
          responseType: 'blob',
          throwOnError: true,
        })
        if (!alive) return
        const blob = response.data as Blob
        if (blob.size === 0) throw new Error('empty blob')
        created = URL.createObjectURL(blob)
        setObjectUrl(created)
      } catch {
        if (alive) setFailed(true)
      }
    }

    void run()
    return () => {
      alive = false
      if (created) URL.revokeObjectURL(created)
    }
  }, [target])

  const resolvedSrc =
    target?.kind === 'viking'
      ? objectUrl || ''
      : target
        ? target.value
        : String(src || '')

  if (target?.kind === 'viking' && !resolvedSrc) {
    if (failed) {
      return (
        <span className="text-xs text-muted-foreground">
          [{alt || fileNameFromUri(target.value)}]
        </span>
      )
    }
    return null
  }

  return (
    <img
      src={resolvedSrc}
      alt={alt || ''}
      loading="lazy"
      className="max-w-full rounded-md outline outline-1 -outline-offset-1 outline-black/10 dark:outline-white/10"
    />
  )
}

export function textFromReactNode(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textFromReactNode).join('')
  return ''
}

export function MarkdownCode({
  className,
  children,
}: ComponentProps<'code'> & { inline?: boolean }) {
  const rawText = textFromReactNode(children).replace(/\n$/, '')
  const language = normalizeMarkdownLanguage(className)
  const isBlock = Boolean(language || rawText.includes('\n'))
  const [html, setHtml] = useState(() => escapeHtml(rawText))

  useEffect(() => {
    if (!isBlock) {
      setHtml(escapeHtml(rawText))
      return
    }

    let cancelled = false
    const run = async () => {
      try {
        if (language) await ensureLanguage(language)
        if (cancelled) return
        const highlighted =
          language && hljs.getLanguage(language)
            ? hljs.highlight(rawText, { ignoreIllegals: true, language }).value
            : escapeHtml(rawText)
        setHtml(highlighted)
      } catch {
        if (!cancelled) setHtml(escapeHtml(rawText))
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [isBlock, language, rawText])

  if (!isBlock) {
    return (
      <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.92em] text-foreground">
        {children}
      </code>
    )
  }

  return (
    <code
      className={`hljs block overflow-x-auto whitespace-pre font-mono text-xs leading-6 ${className || ''}`}
      dangerouslySetInnerHTML={{ __html: html || escapeHtml(rawText) }}
    />
  )
}

export function MarkdownPre({ children }: ComponentProps<'pre'>) {
  return (
    <pre className="overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs leading-6 text-foreground dark:bg-muted-foreground/20">
      {children}
    </pre>
  )
}

export const markdownComponents = {
  code: MarkdownCode,
  pre: MarkdownPre,
  table: ({ children }: ComponentProps<'table'>) => (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  td: ({ children, colSpan, rowSpan }: ComponentProps<'td'>) => (
    <td
      className="border px-3 py-2 text-center align-middle"
      colSpan={colSpan}
      rowSpan={rowSpan}
    >
      {children}
    </td>
  ),
  th: ({ children, colSpan, rowSpan }: ComponentProps<'th'>) => (
    <th
      className="border bg-muted/50 px-3 py-2 text-center align-middle font-medium"
      colSpan={colSpan}
      rowSpan={rowSpan}
    >
      {children}
    </th>
  ),
}
