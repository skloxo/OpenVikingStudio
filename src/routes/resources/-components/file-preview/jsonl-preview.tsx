import { useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'
import { useTranslation } from 'react-i18next'

import {
  type JsonlRecord,
  type JsonlPart,
  type JsonlMessage,
  parseJsonlRecords,
  hasJsonlToolPart,
  getJsonlMessage,
  isJsonlMarkdownMessage,
  collapseJsonlParts,
  formatJsonlTime,
  JSONL_MESSAGE_PREVIEW_LIMIT,
  JSONL_TOOLCALL_STORAGE_KEY,
  COLLAPSE_SYMBOL,
  EXPAND_SYMBOL,
} from '../../-lib/jsonl-parser'
import { markdownComponents } from './markdown-renderer'

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function JsonlRawRow({ record }: { record: JsonlRecord }) {
  const [open, setOpen] = useState(false)
  const parsed = record.parsed
  const keys = isRecord(parsed) ? Object.keys(parsed) : []
  const titleKey = keys.find((key) =>
    ['name', 'title', 'event', 'type', 'role', 'method'].includes(key),
  )

  return (
    <div
      className={`grid grid-cols-[3.5rem_1fr] border-b transition-colors hover:bg-muted/40 ${
        open ? 'bg-muted/30' : ''
      }`}
    >
      <button
        type="button"
        className="flex items-center justify-end gap-1 border-r px-2 py-2 font-mono text-[11px] text-muted-foreground hover:text-foreground"
        onClick={() => setOpen((current) => !current)}
      >
        <span>{record.index + 1}</span>
        <span aria-hidden="true">{open ? COLLAPSE_SYMBOL : EXPAND_SYMBOL}</span>
      </button>
      <div className="min-w-0 px-3 py-2">
        {open ? (
          <pre className="overflow-auto whitespace-pre-wrap break-words text-xs leading-5">
            {record.error
              ? record.line
              : JSON.stringify(record.parsed, null, 2)}
          </pre>
        ) : record.error ? (
          <div className="truncate text-xs text-destructive">{record.line}</div>
        ) : titleKey && isRecord(parsed) ? (
          <div className="flex min-w-0 items-center gap-2 text-xs">
            <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold uppercase text-primary">
              {titleKey}
            </span>
            <span className="truncate font-medium">
              {String(parsed[titleKey])}
            </span>
            <span className="shrink-0 text-muted-foreground">
              {keys
                .filter((key) => key !== titleKey)
                .slice(0, 3)
                .join(', ')}
            </span>
          </div>
        ) : (
          <div className="truncate text-xs text-muted-foreground">
            {keys.slice(0, 6).join(', ') || record.line}
          </div>
        )}
      </div>
    </div>
  )
}

export function JsonlToolBody({ input }: { input: unknown }) {
  const { t } = useTranslation('resources')
  const text =
    input === undefined ||
    input === null ||
    (isRecord(input) && Object.keys(input).length === 0)
      ? ''
      : typeof input === 'string'
        ? input
        : JSON.stringify(input, null, 2)

  return text ? (
    <pre className="max-h-96 overflow-auto rounded border bg-muted/30 p-2 text-xs leading-5">
      {text}
    </pre>
  ) : (
    <pre className="whitespace-pre-wrap break-words text-xs leading-5">
      {t('filePreview.jsonl.noArguments')}
    </pre>
  )
}

export function JsonlMarkdownBody({ content }: { content: string }) {
  const { t } = useTranslation('resources')
  return (
    <div className="prose prose-sm max-w-none break-words dark:prose-invert dark:prose-pre:bg-muted-foreground/20">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={markdownComponents}
      >
        {content || t('filePreview.jsonl.emptyMessage')}
      </ReactMarkdown>
    </div>
  )
}

export function JsonlPartBody({
  markdown,
  part,
}: {
  markdown: boolean
  part: JsonlPart
}) {
  const { t } = useTranslation('resources')
  if (part.kind === 'tool-call') return <JsonlToolBody input={part.input} />

  if (part.kind === 'tool-result') {
    return (
      <div className="rounded border border-dashed bg-muted/20 p-2">
        <div className="mb-1 text-[11px] font-medium text-muted-foreground">
          {t('filePreview.jsonl.resultLabel')}
        </div>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs leading-5">
          {part.text || t('filePreview.jsonl.emptyResult')}
        </pre>
      </div>
    )
  }

  if (part.kind === 'text') {
    return markdown ? (
      <JsonlMarkdownBody content={part.text} />
    ) : (
      <pre className="whitespace-pre-wrap break-words text-xs leading-5">
        {part.text}
      </pre>
    )
  }

  return (
    <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-muted-foreground">
      {part.text}
    </pre>
  )
}

export function JsonlMessageCard({ message }: { message: JsonlMessage }) {
  const { t } = useTranslation('resources')
  const [expanded, setExpanded] = useState(false)
  const textLength = message.parts.reduce(
    (total, part) => (part.kind === 'text' ? total + part.text.length : total),
    0,
  )
  const needsExpand = textLength > JSONL_MESSAGE_PREVIEW_LIMIT
  const displayParts =
    expanded || !needsExpand
      ? message.parts
      : collapseJsonlParts(message.parts, JSONL_MESSAGE_PREVIEW_LIMIT)
  const toolNames = [
    ...new Set(
      message.parts.flatMap((part) =>
        (part.kind === 'tool-call' || part.kind === 'tool-result') &&
        part.toolName
          ? [part.toolName]
          : [],
      ),
    ),
  ]
  const markdown = isJsonlMarkdownMessage(message.role)
  const alignClass =
    message.toolShape === 'result'
      ? 'border-dashed bg-muted/50'
      : message.role === 'user'
        ? 'bg-primary/10 border-primary/25'
        : message.role === 'invalid'
          ? 'border-destructive/30 bg-muted/40'
          : message.role === 'other'
            ? 'bg-muted/40'
            : message.toolShape === 'call'
              ? 'border-dashed bg-background'
              : 'border-l-2 border-l-primary/50 bg-background'

  return (
    <article
      className={`w-full min-w-0 max-w-full rounded-lg border p-3 text-sm shadow-sm ${alignClass}`}
    >
      <div className="mb-2 flex min-w-0 items-center gap-2">
        <span className="text-xs font-semibold">{message.label}</span>
        {message.roleId ? (
          <span className="truncate text-xs text-muted-foreground">
            {message.roleId}
          </span>
        ) : null}
        {toolNames.map((toolName) => (
          <span
            key={toolName}
            className="truncate rounded border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
          >
            {toolName}
          </span>
        ))}
        <span className="ml-auto shrink-0 font-mono text-[11px] text-muted-foreground">
          #{message.lineNo}
        </span>
      </div>

      {displayParts.length ? (
        <div className="grid gap-2">
          {displayParts.map((part, index) => (
            <JsonlPartBody
              key={`${part.kind}-${index}`}
              markdown={markdown}
              part={part}
            />
          ))}
        </div>
      ) : (
        <pre className="whitespace-pre-wrap break-words text-xs leading-5">
          {t('filePreview.jsonl.emptyMessage')}
        </pre>
      )}

      <div className="mt-2 flex items-center gap-2 border-t pt-2 text-[11px] text-muted-foreground">
        {message.time ? (
          <time dateTime={message.time}>{formatJsonlTime(message.time)}</time>
        ) : null}
        {message.id ? <span className="truncate">{message.id}</span> : null}
        {needsExpand ? (
          <button
            type="button"
            className="ml-auto rounded border px-2 py-0.5 font-medium text-primary hover:border-primary"
            onClick={() => setExpanded((current) => !current)}
          >
            {expanded
              ? t('filePreview.jsonl.collapse')
              : t('filePreview.jsonl.expand')}
          </button>
        ) : null}
      </div>
    </article>
  )
}

export function JsonlPreview({ content }: { content: string }) {
  const { t } = useTranslation('resources')
  const [dialogMode, setDialogMode] = useState(true)
  const [showTools, setShowTools] = useState(() => {
    if (typeof window === 'undefined') return true
    const stored = window.localStorage.getItem(JSONL_TOOLCALL_STORAGE_KEY)
    return stored === null ? true : stored === 'true'
  })
  const records = useMemo(() => parseJsonlRecords(content), [content])
  const messages = useMemo(() => records.map(getJsonlMessage), [records])
  const visibleMessages = useMemo(() => {
    if (showTools) return messages
    return messages
      .map((message) => ({
        ...message,
        parts: message.parts.filter(
          (part) => part.kind !== 'tool-call' && part.kind !== 'tool-result',
        ),
      }))
      .filter((message) => message.parts.length > 0)
  }, [messages, showTools])
  const visibleLineNos = useMemo(
    () => new Set(visibleMessages.map((message) => message.lineNo)),
    [visibleMessages],
  )
  const hasTools = useMemo(
    () => messages.some((message) => hasJsonlToolPart(message.parts)),
    [messages],
  )

  if (!records.length) {
    return (
      <div className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
        {t('filePreview.jsonl.emptyJsonl')}
      </div>
    )
  }

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
        <span className="font-medium text-primary">
          {t('filePreview.jsonl.recordCount', { count: records.length })}
        </span>
        <div className="flex items-center gap-2">
          {hasTools ? (
            <label className="inline-flex cursor-pointer items-center gap-2">
              <span className="font-medium">
                {t('filePreview.jsonl.toolcall')}
              </span>
              <input
                type="checkbox"
                className="peer sr-only"
                checked={showTools}
                onChange={(event) => {
                  setShowTools(event.target.checked)
                  window.localStorage.setItem(
                    JSONL_TOOLCALL_STORAGE_KEY,
                    String(event.target.checked),
                  )
                }}
              />
              <span className="h-5 w-9 rounded-full border bg-muted transition-colors after:block after:size-3.5 after:translate-x-0.5 after:translate-y-0.5 after:rounded-full after:bg-muted-foreground after:transition-transform peer-checked:border-primary peer-checked:bg-primary/15 peer-checked:after:translate-x-[18px] peer-checked:after:bg-primary" />
            </label>
          ) : null}
          <label className="inline-flex cursor-pointer items-center gap-2">
            <span className="font-medium">
              {t('filePreview.jsonl.dialogMode')}
            </span>
            <input
              type="checkbox"
              className="peer sr-only"
              checked={dialogMode}
              onChange={(event) => setDialogMode(event.target.checked)}
            />
            <span className="h-5 w-9 rounded-full border bg-muted transition-colors after:block after:size-3.5 after:translate-x-0.5 after:translate-y-0.5 after:rounded-full after:bg-muted-foreground after:transition-transform peer-checked:border-primary peer-checked:bg-primary/15 peer-checked:after:translate-x-[18px] peer-checked:after:bg-primary" />
          </label>
        </div>
      </div>

      {dialogMode ? (
        <div className="flex min-w-0 flex-col gap-3">
          {visibleMessages.map((message) => (
            <JsonlMessageCard key={message.lineNo} message={message} />
          ))}
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border">
          {records
            .filter((record) => visibleLineNos.has(record.index + 1))
            .map((record) => (
              <JsonlRawRow key={record.index} record={record} />
            ))}
        </div>
      )}
    </div>
  )
}
