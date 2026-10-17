/**
 * terminal-command-assist.tsx
 * 终端命令辅助面板与自动补全浮层组件。
 * 展示当前命令的参数说明、子命令列表、示例用法以及补全选项。
 */
import type { MutableRefObject } from 'react'

import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import type { TerminalCommandView } from '../-lib/types'
import type { TerminalSuggestion } from './terminal-panel-types'
import type {
  SessionSubcommandRow,
  TerminalCommandExampleView,
  TerminalCommandParameterView,
} from './terminal-suggestions-hook'

export type TerminalCommandAssistProps = {
  activeSuggestionIndex: number
  canUseCurrentScope: boolean
  commandExamples: TerminalCommandExampleView[]
  commandParameters: TerminalCommandParameterView[]
  helpCommand?: TerminalCommandView
  helpDescription?: string
  helpTitle?: string
  helpUsage?: string
  onAcceptSuggestion: (suggestion: { insertText: string }) => void
  onInsertCurrentScope: () => void
  onSelectSuggestionIndex: (index: number) => void
  sessionSubcommandRows: SessionSubcommandRow[]
  showCommandAssist: boolean
  showSessionSubcommandList: boolean
  suggestionRefs: MutableRefObject<Array<HTMLButtonElement | null>>
  suggestions: TerminalSuggestion[]
  suggestionsOpen: boolean
  t: (key: string, options?: Record<string, unknown>) => string
}

export function TerminalCommandAssist({
  activeSuggestionIndex,
  canUseCurrentScope,
  commandExamples,
  commandParameters,
  helpCommand,
  helpDescription,
  helpTitle,
  helpUsage,
  onAcceptSuggestion,
  onInsertCurrentScope,
  onSelectSuggestionIndex,
  sessionSubcommandRows,
  showCommandAssist,
  showSessionSubcommandList,
  suggestionRefs,
  suggestions,
  suggestionsOpen,
  t,
}: TerminalCommandAssistProps) {
  if (!showCommandAssist) return null

  return (
    <div className="absolute bottom-[calc(100%+0.5rem)] left-0 right-0 z-20 max-h-[min(72vh,36rem)] overflow-y-auto rounded-xl border bg-popover shadow-xl">
      {helpCommand ? (
        <div className="border-b p-3">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-mono text-sm font-semibold text-primary">
                {helpTitle}
              </div>
              <div className="mt-0.5 text-xs leading-4 text-muted-foreground">
                {helpDescription}
              </div>
            </div>
            <div className="shrink-0 rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground">
              {helpUsage}
            </div>
          </div>
          <div className="mt-3 space-y-3">
            {showSessionSubcommandList ? (
              <div className="min-w-0">
                <div className="mb-1.5 text-xs font-medium text-muted-foreground">
                  {t('terminal.helpSubcommands')}
                </div>
                <div className="overflow-hidden rounded-md border">
                  <table className="w-full table-fixed border-collapse text-xs">
                    <tbody className="divide-y">
                      {sessionSubcommandRows.map((item) => (
                        <tr key={item.key}>
                          <td className="w-40 align-top bg-muted/30 px-2 py-1.5 font-mono text-foreground">
                            <button
                              type="button"
                              className="block max-w-full truncate text-left text-primary hover:underline"
                              title={item.usage}
                              onClick={() =>
                                onAcceptSuggestion({
                                  insertText: item.insertText,
                                })
                              }
                              onMouseDown={(event) => event.preventDefault()}
                            >
                              {item.key}
                            </button>
                          </td>
                          <td className="align-top px-2 py-1.5 leading-4 text-muted-foreground">
                            {item.description}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <>
                <div className="min-w-0">
                  <div className="mb-1.5 text-xs font-medium text-muted-foreground">
                    {t('terminal.helpParameters')}
                  </div>
                  {commandParameters.length > 0 ? (
                    <div className="overflow-hidden rounded-md border">
                      <table className="w-full table-fixed border-collapse text-xs">
                        <tbody className="divide-y">
                          {commandParameters.map((parameter) => (
                            <tr key={parameter.key}>
                              <td className="w-32 align-top bg-muted/30 px-2 py-1.5 font-mono text-foreground">
                                <span className="block truncate">
                                  {parameter.name}
                                </span>
                              </td>
                              <td className="align-top px-2 py-1.5 text-muted-foreground">
                                <div className="flex min-w-0 items-start justify-between gap-2">
                                  <span className="min-w-0 leading-4">
                                    {parameter.description}
                                  </span>
                                  {canUseCurrentScope &&
                                  parameter.key === 'scope' ? (
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="h-6 shrink-0 px-2 text-xs"
                                      onClick={onInsertCurrentScope}
                                      onMouseDown={(event) =>
                                        event.preventDefault()
                                      }
                                    >
                                      {t('terminal.currentScopeAction')}
                                    </Button>
                                  ) : null}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="rounded-md border px-2 py-1.5 text-xs text-muted-foreground">
                      {t('terminal.noParameters')}
                    </div>
                  )}
                </div>
                <div className="min-w-0">
                  <div className="mb-1.5 text-xs font-medium text-muted-foreground">
                    {t('terminal.helpExamples')}
                  </div>
                  <div className="overflow-hidden rounded-md border">
                    <table className="w-full table-fixed border-collapse text-xs">
                      <tbody className="divide-y">
                        {commandExamples.map((example) => (
                          <tr key={example.key}>
                            <td className="w-56 align-top bg-muted/30 px-2 py-1.5 font-mono text-foreground">
                              <span
                                className="block truncate"
                                title={example.code}
                              >
                                {example.code}
                              </span>
                            </td>
                            <td className="align-top px-2 py-1.5 leading-4 text-muted-foreground">
                              {example.description}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
      {suggestionsOpen && suggestions.length > 0 ? (
        <div className="max-h-56 overflow-y-auto p-1.5">
          {suggestions.map((suggestion, index) => (
            <button
              key={suggestion.id}
              ref={(node) => {
                suggestionRefs.current[index] = node
              }}
              type="button"
              title={`${suggestion.usage} · ${t('terminal.suggestionsHint')}`}
              className={cn(
                'min-h-8 w-full min-w-0 rounded-md px-2.5 py-1 text-left transition-colors',
                index === activeSuggestionIndex
                  ? 'bg-primary/10 text-foreground'
                  : 'hover:bg-muted/60',
              )}
              onClick={() => onAcceptSuggestion(suggestion)}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => onSelectSuggestionIndex(index)}
            >
              {suggestion.group === 'history' ||
              suggestion.group === 'resource' ||
              suggestion.group === 'subcommand' ? (
                <span className="flex min-w-0 items-center gap-3">
                  <span
                    className="min-w-0 flex-1 truncate font-mono text-xs font-semibold text-primary"
                    title={suggestion.command}
                  >
                    {suggestion.command}
                  </span>
                  <span className="shrink-0 text-xs leading-4 text-muted-foreground">
                    {suggestion.description}
                  </span>
                </span>
              ) : (
                <span className="grid min-w-0 grid-cols-[minmax(5.25rem,7.5rem)_minmax(0,1fr)] items-center gap-2.5">
                  <span
                    className="min-w-0 truncate font-mono text-xs font-semibold text-primary"
                    title={suggestion.command}
                  >
                    {suggestion.command}
                  </span>
                  <span className="min-w-0 text-xs leading-4 text-muted-foreground">
                    {suggestion.description}
                  </span>
                </span>
              )}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
