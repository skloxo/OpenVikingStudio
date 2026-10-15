import { ArrowRight, AlertTriangle, CheckCircle2, History } from 'lucide-react'
import { cn } from '#/lib/utils'

export type MemoryLifecycleStatus = 'active' | 'disputed' | 'superseded' | 'archived'

interface MemoryStatusBadgeProps {
  status?: string
  supersededBy?: string | null
  disputedReason?: string | null
  className?: string
  showActive?: boolean
}

export function MemoryStatusBadge({
  status,
  supersededBy,
  disputedReason,
  className,
  showActive = false,
}: MemoryStatusBadgeProps) {
  const normStatus = (status || 'active').toLowerCase() as MemoryLifecycleStatus

  if (normStatus === 'active' && !showActive) {
    return null
  }

  if (normStatus === 'disputed') {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-xs font-mono font-medium text-amber-400',
          className,
        )}
        title={disputedReason || 'Marked disputed pending consensus review'}
      >
        <AlertTriangle className="size-3 shrink-0" />
        <span>DISPUTED</span>
      </div>
    )
  }

  if (normStatus === 'superseded') {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1 rounded border border-border/60 bg-muted/40 px-1.5 py-0.5 text-xs font-mono font-medium text-muted-foreground line-through opacity-75',
          className,
        )}
        title={supersededBy ? `Superseded by: ${supersededBy}` : 'Superseded by newer knowledge'}
      >
        <History className="size-3 shrink-0 text-muted-foreground/60" />
        <span>SUPERSEDED</span>
        {supersededBy && (
          <span className="no-underline inline-flex items-center gap-0.5 ml-1 text-cyan-400 font-sans opacity-100">
            <ArrowRight className="size-2.5" />
            <span className="truncate max-w-24">{supersededBy.split('/').pop()}</span>
          </span>
        )}
      </div>
    )
  }

  if (normStatus === 'archived') {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 shrink-0 rounded border border-muted-foreground/30 bg-muted/40 px-1.5 py-0.5 text-xs font-mono font-medium text-muted-foreground',
          className,
        )}
      >
        <span>ARCHIVED</span>
      </span>
    )
  }

  // Active status (when showActive is true)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 shrink-0 rounded border border-border/40 bg-muted/20 px-1.5 py-0.5 text-xs font-mono font-medium text-muted-foreground',
        className,
      )}
    >
      <CheckCircle2 className="size-3 shrink-0 text-cyan-500" />
      <span>ACTIVE</span>
    </span>
  )
}
