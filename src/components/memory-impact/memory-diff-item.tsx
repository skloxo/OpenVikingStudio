import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDownIcon, LoaderCircleIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { CopyButton } from '#/components/common/copy-button'
import { fetchFileContent } from '#/routes/resources/-lib/api'
import { KIND_CONFIG } from './impact-summary-cards'
import type { UniversalMemoryDiffOperation } from './types'

export interface MemoryDiffItemProps {
  operation: UniversalMemoryDiffOperation
  defaultOpen?: boolean
  labels?: {
    before?: string
    after?: string
    addedContent?: string
    deletedContent?: string
    emptyContent?: string
  }
}

export function MemoryDiffItem({
  operation,
  defaultOpen = true,
  labels,
}: MemoryDiffItemProps) {
  const { t } = useTranslation('sessions')
  const conf = KIND_CONFIG[operation.kind]
  const Icon = conf.icon

  const [isOpen, setIsOpen] = React.useState(defaultOpen)
  const [asyncContent, setAsyncContent] = React.useState<string | null>(null)
  const [isLoadingContent, setIsLoadingContent] = React.useState(false)
  const attemptedUrisRef = React.useRef<Set<string>>(new Set())

  const isPlaceholder = (text?: string) => {
    if (!text) return true
    const trimmed = text.trim()
    return (
      trimmed.includes('已成功存储落盘') ||
      trimmed.includes('状态正常') ||
      trimmed === '已就绪' ||
      trimmed.length <= 35
    )
  }

  // 当项展开且内容为简短占位符时，自动尝试从底层 VikingFS 异步拉取真实文件正文（单次防死循环守卫）
  React.useEffect(() => {
    if (!isOpen) return
    const uri = operation.uri
    if (!uri || !uri.startsWith('viking://')) return

    const currentAfter = operation.after
    if (currentAfter && !isPlaceholder(currentAfter)) return
    if (asyncContent !== null || attemptedUrisRef.current.has(uri)) return

    let isMounted = true
    setIsLoadingContent(true)
    attemptedUrisRef.current.add(uri)

    fetchFileContent(uri)
      .then((res) => {
        if (isMounted && res.content) {
          setAsyncContent(res.content)
        }
      })
      .catch(() => {
        // 优雅降级保持现有占位说明
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingContent(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [isOpen, operation.uri, operation.after, asyncContent])

  const beforeLabel = labels?.before || t('impact.before', '变更前')
  const afterLabel = labels?.after || t('impact.after', '变更后')
  const addedLabel = labels?.addedContent || t('impact.addedContent', '新增内容')
  const deletedLabel = labels?.deletedContent || t('impact.deletedContent', '删除内容')
  const emptyLabel = labels?.emptyContent || t('impact.emptyContent', '(空内容)')

  const resolvedAfter = asyncContent || operation.after
  const typeLabel = t(`impact.types.${operation.memoryType}`, {
    defaultValue: operation.memoryType,
  })

  return (
    <details
      className="group border-b last:border-b-0 min-w-0 w-full overflow-hidden"
      open={defaultOpen}
      onToggle={(e) => setIsOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary className="flex w-full cursor-pointer list-none items-center gap-2.5 px-3.5 py-2.5 transition-colors hover:bg-muted/40 select-none min-w-0 overflow-hidden">
        <Icon className={`size-4 shrink-0 ${conf.textColor}`} />
        <code className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
          {operation.uri}
        </code>
        <CopyButton value={operation.uri} size="xs" className="size-6 p-0 shrink-0" />
        <Badge
          className="shrink-0 text-[11px] font-normal max-w-36"
          variant="outline"
          title={typeLabel}
        >
          <span className="truncate">{typeLabel}</span>
        </Badge>
        {isLoadingContent && (
          <LoaderCircleIcon className="size-3 text-muted-foreground animate-spin shrink-0" />
        )}
        <span className="shrink-0 text-[11px] text-muted-foreground transition-transform duration-200 group-open:rotate-90">
          ›
        </span>
      </summary>

      <div className="border-t bg-muted/15 px-3.5 py-3 min-w-0 w-full overflow-hidden">
        {operation.description ? (
          <p className="mb-2 text-xs text-muted-foreground leading-relaxed">
            {operation.description}
          </p>
        ) : null}

        {operation.kind === 'update' ? (
          <div className="grid gap-3 sm:grid-cols-2 min-w-0 w-full">
            <ContentBlock
              content={operation.before}
              label={beforeLabel}
              tone="delete"
              emptyText={emptyLabel}
            />
            <ContentBlock
              content={resolvedAfter}
              label={afterLabel}
              tone="add"
              emptyText={emptyLabel}
            />
          </div>
        ) : (
          <ContentBlock
            content={resolvedAfter || operation.before}
            label={operation.kind === 'add' ? addedLabel : deletedLabel}
            tone={operation.kind === 'add' ? 'add' : 'delete'}
            emptyText={emptyLabel}
          />
        )}
      </div>
    </details>
  )
}

interface ContentBlockProps {
  content?: string
  label: string
  tone: 'add' | 'delete'
  emptyText?: string
}

function ContentBlock({
  content,
  label,
  tone,
  emptyText = '(空内容)',
}: ContentBlockProps) {
  const { t } = useTranslation('sessions')
  const [isExpanded, setIsExpanded] = React.useState(false)
  const isAdd = tone === 'add'
  const textColor = isAdd
    ? 'text-cyan-600 dark:text-cyan-400'
    : 'text-rose-600 dark:text-rose-400'

  const hasLongContent = Boolean(
    content && (content.length > 240 || content.split('\n').length > 7),
  )

  return (
    <div className="min-w-0 flex flex-col">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className={`text-[11px] font-medium ${textColor}`}>{label}</span>
        <div className="flex items-center gap-1.5 shrink-0">
          {hasLongContent && (
            <button
              type="button"
              onClick={() => setIsExpanded((prev) => !prev)}
              className="inline-flex items-center gap-0.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <span>{isExpanded ? t('impact.collapseShort', '收起') : t('impact.expandFull', '展开全文')}</span>
              <ChevronDownIcon
                className={`size-3 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
              />
            </button>
          )}
          {content ? (
            <CopyButton value={content} size="xs" className="h-5 px-1.5 text-[11px]" />
          ) : null}
        </div>
      </div>
      <pre
        className={`overflow-auto whitespace-pre-wrap break-all min-w-0 max-w-full rounded-md border bg-background/80 p-2.5 font-mono text-[11px] leading-relaxed text-muted-foreground transition-all ${
          isExpanded ? 'max-h-none' : 'max-h-64'
        }`}
      >
        {content || emptyText}
      </pre>
    </div>
  )
}
