/**
 * terminal-quick-start.tsx
 * 从 terminal-panel.tsx 接缝提取的快捷示例列表组件。
 */
import { ArrowRightIcon } from 'lucide-react'
import type { TerminalQuickStartExample } from './terminal-panel-types'

export function TerminalQuickStart({
  examples,
  title,
}: {
  examples: TerminalQuickStartExample[]
  title: string
}) {
  return (
    <section className="space-y-3 py-3">
      <div className="text-xs font-semibold text-muted-foreground">{title}</div>
      <div className="space-y-2">
        {examples.map((example) => {
          const content = (
            <>
              <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-background text-muted-foreground">
                <ArrowRightIcon className="size-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-foreground">
                    {example.title}
                  </span>
                  <span className="rounded-md border bg-background px-2 py-0.5 font-mono text-xs font-semibold">
                    {example.command}
                  </span>
                </span>
                <span className="mt-1 block truncate font-mono text-xs text-muted-foreground">
                  {example.code}
                </span>
              </span>
            </>
          )

          if (!example.action) {
            return (
              <div
                key={example.key}
                className="flex min-w-0 items-center gap-3 rounded-lg bg-muted/40 px-3 py-3"
              >
                {content}
              </div>
            )
          }

          return (
            <button
              key={example.key}
              type="button"
              className="flex w-full min-w-0 items-center gap-3 rounded-lg bg-muted/40 px-3 py-3 text-left transition-colors hover:bg-muted/70"
              onClick={example.action}
            >
              {content}
            </button>
          )
        })}
      </div>
    </section>
  )
}
