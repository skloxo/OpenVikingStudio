import { SendIcon } from 'lucide-react'
import type { KeyboardEvent, RefObject } from 'react'

import { Button } from '#/components/ui/button'

export function RetrievalSearchBar({
  inputRef,
  onChange,
  onSubmit,
  placeholder,
  query,
  sendLabel = '检索',
}: {
  inputRef: RefObject<HTMLInputElement | null>
  onChange: (value: string) => void
  onSubmit: () => void
  placeholder: string
  query: string
  sendLabel?: string
}) {
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="flex items-center gap-2 rounded-sm border border-border/70 bg-card p-1.5 shadow-sm transition-colors focus-within:border-ring focus-within:ring-1 focus-within:ring-ring">
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="flex-1 bg-transparent px-2 text-sm font-mono outline-none placeholder:text-muted-foreground/60"
      />
      <div className="flex items-center gap-1.5 shrink-0">
        <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded-xs border border-border/60 bg-muted/40 px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
          Enter ⏎
        </kbd>
        <Button
          size="sm"
          className="h-7 rounded-xs px-3 text-xs font-medium gap-1.5 shrink-0 shadow-none"
          onClick={onSubmit}
          disabled={query.trim().length === 0}
        >
          <SendIcon className="size-3.5" />
          <span>{sendLabel}</span>
        </Button>
      </div>
    </div>
  )
}
