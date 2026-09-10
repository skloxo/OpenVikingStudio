import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { CopyButton } from '#/components/common/copy-button'
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

  const beforeLabel = labels?.before || t('impact.before', '变更前')
  const afterLabel = labels?.after || t('impact.after', '变更后')
  const addedLabel = labels?.addedContent || t('impact.addedContent', '新增内容')
  const deletedLabel = labels?.deletedContent || t('impact.deletedContent', '删除内容')
  const emptyLabel = labels?.emptyContent || t('impact.emptyContent', '(空内容)')

  return (
    <details className="group border-b last:border-b-0" open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center gap-2.5 px-3.5 py-2.5 transition-colors hover:bg-muted/40 select-none">
        <Icon className={`size-4 shrink-0 ${conf.textColor}`} />
        <code className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
          {operation.uri}
        </code>
        <CopyButton value={operation.uri} size="xs" className="size-6 p-0" />
        <Badge
          className="max-w-32 shrink-0 text-[11px] font-normal"
          variant="outline"
        >
          <span className="truncate">{operation.memoryType}</span>
        </Badge>
        <span className="text-[11px] text-muted-foreground transition-transform duration-200 group-open:rotate-90">
          ›
        </span>
      </summary>

      <div className="border-t bg-muted/15 px-3.5 py-3">
        {operation.description ? (
          <p className="mb-2 text-xs text-muted-foreground">
            {operation.description}
          </p>
        ) : null}

        {operation.kind === 'update' ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <ContentBlock
              content={operation.before}
              label={beforeLabel}
              tone="delete"
              emptyText={emptyLabel}
            />
            <ContentBlock
              content={operation.after}
              label={afterLabel}
              tone="add"
              emptyText={emptyLabel}
            />
          </div>
        ) : (
          <ContentBlock
            content={operation.after || operation.before}
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
  const isAdd = tone === 'add'
  const textColor = isAdd
    ? 'text-cyan-600 dark:text-cyan-400'
    : 'text-rose-600 dark:text-rose-400'

  return (
    <div className="min-w-0 flex flex-col">
      <div className="mb-1.5 flex items-center justify-between">
        <span className={`text-[11px] font-medium ${textColor}`}>{label}</span>
        {content ? (
          <CopyButton value={content} size="xs" className="h-5 px-1.5 text-[11px]" />
        ) : null}
      </div>
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md border bg-background/80 p-2.5 font-mono text-[11px] leading-relaxed text-muted-foreground">
        {content || emptyText}
      </pre>
    </div>
  )
}
