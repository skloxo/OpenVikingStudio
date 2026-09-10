import {
  FilePenLineIcon,
  FilePlus2Icon,
  FileX2Icon,
} from 'lucide-react'
import type {
  UniversalMemoryDiffKind,
  UniversalMemoryDiffSummary,
} from './types'

export const KIND_CONFIG: Record<
  UniversalMemoryDiffKind,
  {
    icon: typeof FilePlus2Icon
    textColor: string
    badgeBg: string
    defaultLabel: string
  }
> = {
  add: {
    icon: FilePlus2Icon,
    textColor: 'text-cyan-600 dark:text-cyan-400',
    badgeBg: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
    defaultLabel: '新增写入',
  },
  update: {
    icon: FilePenLineIcon,
    textColor: 'text-amber-600 dark:text-amber-400',
    badgeBg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
    defaultLabel: '特例演化',
  },
  delete: {
    icon: FileX2Icon,
    textColor: 'text-rose-600 dark:text-rose-400',
    badgeBg: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
    defaultLabel: '失效清理',
  },
}

export interface ImpactCountsProps {
  totals: UniversalMemoryDiffSummary
  className?: string
}

export function ImpactCounts({ totals, className = '' }: ImpactCountsProps) {
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-[11px] tabular-nums ${className}`}>
      {totals.adds > 0 ? (
        <span className="text-cyan-600 dark:text-cyan-400 font-medium">
          +{totals.adds}
        </span>
      ) : null}
      {totals.updates > 0 ? (
        <span className="text-amber-600 dark:text-amber-400 font-medium">
          ~{totals.updates}
        </span>
      ) : null}
      {totals.deletes > 0 ? (
        <span className="text-rose-600 dark:text-rose-400 font-medium">
          −{totals.deletes}
        </span>
      ) : null}
    </span>
  )
}

export interface ImpactSummaryCardsProps {
  summary: UniversalMemoryDiffSummary
  labels?: Partial<Record<UniversalMemoryDiffKind, string>>
}

export function ImpactSummaryCards({ summary, labels }: ImpactSummaryCardsProps) {
  const kinds: UniversalMemoryDiffKind[] = ['add', 'update', 'delete']

  const getValue = (kind: UniversalMemoryDiffKind) => {
    if (kind === 'add') return summary.adds
    if (kind === 'update') return summary.updates
    return summary.deletes
  }

  return (
    <div className="grid grid-cols-3 gap-2 border-b bg-muted/20 px-6 py-3.5">
      {kinds.map((kind) => {
        const conf = KIND_CONFIG[kind]
        const Icon = conf.icon
        const label = labels?.[kind] || conf.defaultLabel
        const count = getValue(kind)

        return (
          <div
            key={kind}
            className="flex flex-col rounded-lg border bg-background/80 px-3 py-2 transition-colors"
          >
            <div className={`flex items-center gap-1.5 text-[11px] font-medium ${conf.textColor}`}>
              <Icon className="size-3.5 shrink-0" />
              <span className="truncate">{label}</span>
            </div>
            <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-foreground">
              {count}
            </div>
          </div>
        )
      })}
    </div>
  )
}
