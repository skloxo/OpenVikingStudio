import type { PointerEvent as ReactPointerEvent } from 'react'
import type { FolderIcon } from 'lucide-react'

import { cn } from '#/lib/utils'

export function PlaygroundResizeHandle({
  active,
  label,
  onPointerDown,
}: {
  active: boolean
  label: string
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void
}) {
  return (
    <div
      role="separator"
      aria-label={label}
      aria-orientation="vertical"
      data-active={active}
      className="group hidden w-2 shrink-0 cursor-col-resize touch-none items-center justify-center border-x border-transparent transition-colors hover:bg-primary/10 active:bg-primary/15 data-[active=true]:bg-primary/15 lg:flex"
      onPointerDown={onPointerDown}
    >
      <span className="h-full w-px bg-border transition-colors group-hover:bg-primary/60 group-data-[active=true]:bg-primary" />
    </div>
  )
}

export function PanelTab({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean
  icon: typeof FolderIcon
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-medium transition-colors',
        active
          ? 'bg-foreground text-background shadow-sm'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
      )}
      onClick={onClick}
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  )
}
