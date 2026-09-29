/**
 * terminal-panel.tsx
 * Playground 控制台终端交互面板。
 * 遵循 Agent 编码规范与黄金甜点区（<= 300 行）。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import {
  HistoryIcon,
  Loader2Icon,
  SendIcon,
} from 'lucide-react'

import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'

import type {
  ResourceOpenHandler,
  TerminalEntry,
} from '../-lib/types'
import {
  createIdentityStorageKey,
  getErrorMessage,
} from '../-lib/utils'
import {
  TERMINAL_COMMAND_HISTORY_LIMIT,
  TERMINAL_COMMAND_HISTORY_STORAGE_KEY,
  TERMINAL_ENTRY_HISTORY_LIMIT,
  TERMINAL_ENTRY_HISTORY_STORAGE_KEY,
} from './terminal-panel-types'
import type {
  TerminalQuickStartExample,
} from './terminal-panel-types'
import {
  clearPersistedTerminalHistory,
  loadCommandHistory,
  loadTerminalHistory,
  persistCommandHistory,
  persistTerminalHistory,
} from './terminal-panel-utils'
import { TerminalCommandAssist } from './terminal-command-assist'
import { executeTerminalCommand } from './terminal-command-executor'
import { TerminalHistoryDialog } from './terminal-history-dialog'
import { TerminalHistoryItem } from './terminal-history-item'
import { TerminalQuickStart } from './terminal-quick-start'
import { useTerminalSuggestions } from './terminal-suggestions-hook'

export function TerminalPanel({
  currentUri,
  entries,
  onOpenAddResource,
  onOpenResource,
  openingUri,
  onSessionChange,
  sessionId,
  toolbarContainer,
}: {
  currentUri: string
  entries: VikingFsEntry[]
  onOpenAddResource: () => void
  onOpenResource: ResourceOpenHandler
  openingUri: string | null
  onSessionChange: (sessionId: string) => void
  sessionId?: string
  toolbarContainer: HTMLDivElement | null
}) {
  const { t } = useTranslation('playground')
  const { connectionRole, identityScopeKey } = useAppConnection()
  const commandHistoryStorageKey = createIdentityStorageKey(
    TERMINAL_COMMAND_HISTORY_STORAGE_KEY,
    identityScopeKey,
  )
  const terminalHistoryStorageKey = createIdentityStorageKey(
    TERMINAL_ENTRY_HISTORY_STORAGE_KEY,
    identityScopeKey,
  )
  const [command, setCommand] = useState('')
  const [running, setRunning] = useState(false)
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0)
  const [commandHistory, setCommandHistory] = useState(() =>
    loadCommandHistory(commandHistoryStorageKey),
  )
  const [history, setHistory] = useState(() =>
    loadTerminalHistory(terminalHistoryStorageKey),
  )
  const [historyOpen, setHistoryOpen] = useState(false)
  const [inputFocused, setInputFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  const groupLabels = useMemo(
    () => ({
      memories: t('terminal.groupLabels.memories'),
      resources: t('terminal.groupLabels.resources'),
      skills: t('terminal.groupLabels.skills'),
    }),
    [t],
  )

  const {
    commandExamples,
    commandParameters,
    commands,
    helpCommand,
    helpDescription,
    helpTitle,
    helpUsage,
    sessionSubcommandRows,
    showCommandAssist,
    showSessionSubcommandList,
    suggestions,
  } = useTerminalSuggestions({
    command,
    commandHistory,
    connectionRole,
    currentUri,
    entries,
    history,
    inputFocused,
    suggestionsOpen,
    t,
  })

  useEffect(() => {
    setActiveSuggestionIndex(0)
  }, [suggestions.length])

  useEffect(() => {
    suggestionRefs.current = suggestionRefs.current.slice(0, suggestions.length)
  }, [suggestions.length])

  useEffect(() => {
    if (!suggestionsOpen) return
    suggestionRefs.current[activeSuggestionIndex]?.scrollIntoView({
      block: 'nearest',
    })
  }, [activeSuggestionIndex, suggestionsOpen])

  useEffect(() => {
    scrollRef.current?.scrollTo({
      behavior: 'smooth',
      top: scrollRef.current.scrollHeight,
    })
  }, [history.length, running])

  const append = useCallback(
    (entry: Omit<TerminalEntry, 'id'>) => {
      setHistory((prev) => {
        const next = [
          ...prev,
          {
            ...entry,
            id: `terminal-entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          },
        ].slice(-TERMINAL_ENTRY_HISTORY_LIMIT)
        persistTerminalHistory(terminalHistoryStorageKey, next)
        return next
      })
    },
    [terminalHistoryStorageKey],
  )

  const clearHistory = useCallback(() => {
    setHistory([])
    clearPersistedTerminalHistory(terminalHistoryStorageKey)
  }, [terminalHistoryStorageKey])

  const rememberCommand = useCallback(
    (raw: string) => {
      const trimmed = raw.trim()
      if (!trimmed) return
      setCommandHistory((prev) => {
        const next = [
          trimmed,
          ...prev.filter(
            (item) => item.toLowerCase() !== trimmed.toLowerCase(),
          ),
        ].slice(0, TERMINAL_COMMAND_HISTORY_LIMIT)
        persistCommandHistory(commandHistoryStorageKey, next)
        return next
      })
    },
    [commandHistoryStorageKey],
  )

  const runCommand = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim()
      if (!trimmed || running) return

      append({ kind: 'command', title: trimmed })
      rememberCommand(trimmed)
      setCommand('')
      setSuggestionsOpen(false)
      setRunning(true)

      try {
        const [name = '', ...args] = trimmed.split(/\s+/)
        const body = args.join(' ').trim()
        await executeTerminalCommand(name, body, trimmed, {
          append,
          currentUri,
          entries,
          groupLabels,
          identityScopeKey,
          onOpenAddResource,
          onOpenResource,
          onSessionChange,
          sessionId,
          t,
        })
      } catch (error) {
        append({
          body: getErrorMessage(error),
          kind: 'error',
          title: t('terminal.commandFailed'),
        })
      } finally {
        setRunning(false)
      }
    },
    [
      append,
      currentUri,
      entries,
      groupLabels,
      identityScopeKey,
      onOpenAddResource,
      onOpenResource,
      onSessionChange,
      running,
      rememberCommand,
      sessionId,
      t,
    ],
  )

  const acceptSuggestion = useCallback((suggestion: { insertText: string }) => {
    setCommand(suggestion.insertText)
    setSuggestionsOpen(false)
    window.requestAnimationFrame(() => {
      const input = inputRef.current
      input?.focus()
      input?.setSelectionRange(
        suggestion.insertText.length,
        suggestion.insertText.length,
      )
    })
  }, [])

  const insertCurrentScope = useCallback(() => {
    const trimmed = command.trimEnd()
    const hasScope = trimmed.match(/(?:^|\s)--scope(?:=|\s)/)
    const commandName = helpCommand?.command ?? trimmed.split(/\s+/)[0]
    const body = trimmed.slice(commandName.length).trim()
    const next = hasScope
      ? command
      : body
        ? `${trimmed} --scope ${currentUri}`
        : `${commandName}  --scope ${currentUri}`
    const cursorPosition =
      hasScope || body ? next.length : commandName.length + 1
    setCommand(next)
    setSuggestionsOpen(false)
    window.requestAnimationFrame(() => {
      const input = inputRef.current
      input?.focus()
      input?.setSelectionRange(cursorPosition, cursorPosition)
    })
  }, [command, currentUri, helpCommand])

  const quickCommands = commands.filter((item) =>
    ['/status', '/find', '/search', '/add-resource'].includes(item.command),
  )

  const quickStartExamples = useMemo<TerminalQuickStartExample[]>(
    () => [
      {
        action: () => void runCommand('/add-resource'),
        code: t('terminal.quickStart.addResource.code'),
        command: t('terminal.quickStart.addResource.command'),
        key: 'add-resource',
        title: t('terminal.quickStart.addResource.title'),
      },
      {
        code: t('terminal.quickStart.addMemory.code'),
        command: t('terminal.quickStart.addMemory.command'),
        key: 'add-memory',
        title: t('terminal.quickStart.addMemory.title'),
      },
      {
        action: () => void runCommand(t('terminal.quickStart.find.command')),
        code: t('terminal.quickStart.find.code'),
        command: t('terminal.quickStart.find.command'),
        key: 'find',
        title: t('terminal.quickStart.find.title'),
      },
    ],
    [runCommand, t],
  )

  return (
    <>
      {toolbarContainer
        ? createPortal(
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="size-7 shrink-0"
              title={t('terminal.history')}
              onClick={() => setHistoryOpen(true)}
            >
              <HistoryIcon className="size-3.5" />
            </Button>,
            toolbarContainer,
          )
        : null}
      <div className="flex min-h-0 flex-1 flex-col">
        <div
          ref={scrollRef}
          className="min-h-0 flex-1 overflow-y-auto px-4 py-4"
        >
          <div className="space-y-3">
            {history.length === 0 && !running ? (
              <TerminalQuickStart
                examples={quickStartExamples}
                title={t('terminal.quickStart.title')}
              />
            ) : null}
            {history.map((entry) => (
              <TerminalHistoryItem
                key={entry.id}
                entry={entry}
                onOpenResource={onOpenResource}
                openingUri={openingUri}
              />
            ))}
            {running ? (
              <div className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-xs text-muted-foreground">
                <Loader2Icon className="size-3.5 animate-spin" />
                {t('terminal.running')}
              </div>
            ) : null}
          </div>
        </div>
        <div className="border-t bg-background/80 p-3">
          <div className="mb-2 flex flex-wrap gap-1.5">
            {quickCommands.map((item) => (
              <button
                key={item.command}
                type="button"
                className="rounded-md border bg-muted/40 px-2 py-1 font-mono text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                onClick={() => acceptSuggestion(item)}
              >
                {item.command}
              </button>
            ))}
          </div>
          <form
            className="relative flex items-center gap-2 rounded-lg border bg-muted/30 px-2 py-2"
            onSubmit={(event) => {
              event.preventDefault()
              void runCommand(command)
            }}
          >
            <span
              className="max-w-[45%] shrink-0 truncate font-mono text-xs text-muted-foreground"
              title={t('terminal.scopeLabel', { uri: currentUri })}
            >
              {currentUri}
            </span>
            <input
              ref={inputRef}
              value={command}
              onBlur={() => {
                window.setTimeout(() => {
                  setInputFocused(false)
                  setSuggestionsOpen(false)
                }, 120)
              }}
              onChange={(event) => {
                setCommand(event.target.value)
                setSuggestionsOpen(true)
              }}
              onFocus={() => {
                setInputFocused(true)
                setSuggestionsOpen(true)
              }}
              onKeyDown={(event) => {
                if (!suggestionsOpen || suggestions.length === 0) return
                if (event.key === 'ArrowDown') {
                  event.preventDefault()
                  setActiveSuggestionIndex((current) =>
                    Math.min(current + 1, suggestions.length - 1),
                  )
                  return
                }
                if (event.key === 'ArrowUp') {
                  event.preventDefault()
                  setActiveSuggestionIndex((current) =>
                    Math.max(current - 1, 0),
                  )
                  return
                }
                if (event.key === 'Tab') {
                  event.preventDefault()
                  acceptSuggestion(suggestions[activeSuggestionIndex])
                  return
                }
                if (
                  event.key === 'ArrowRight' &&
                  event.currentTarget.selectionStart === command.length &&
                  event.currentTarget.selectionEnd === command.length
                ) {
                  event.preventDefault()
                  acceptSuggestion(suggestions[activeSuggestionIndex])
                  return
                }
                if (event.key === 'Enter') {
                  event.preventDefault()
                  acceptSuggestion(suggestions[activeSuggestionIndex])
                  return
                }
                if (event.key === 'Escape') {
                  setSuggestionsOpen(false)
                }
              }}
              placeholder={t('terminal.placeholder')}
              className="h-8 min-w-0 flex-1 bg-transparent font-mono text-sm outline-none placeholder:text-muted-foreground/60"
            />
            <TerminalCommandAssist
              activeSuggestionIndex={activeSuggestionIndex}
              canUseCurrentScope={Boolean(helpCommand?.command === '/find' || helpCommand?.command === '/search')}
              commandExamples={commandExamples}
              commandParameters={commandParameters}
              helpCommand={helpCommand}
              helpDescription={helpDescription}
              helpTitle={helpTitle}
              helpUsage={helpUsage}
              onAcceptSuggestion={acceptSuggestion}
              onInsertCurrentScope={insertCurrentScope}
              onSelectSuggestionIndex={setActiveSuggestionIndex}
              sessionSubcommandRows={sessionSubcommandRows}
              showCommandAssist={showCommandAssist}
              showSessionSubcommandList={showSessionSubcommandList}
              suggestionRefs={suggestionRefs}
              suggestions={suggestions}
              suggestionsOpen={suggestionsOpen}
              t={t}
            />
            <Button
              type="submit"
              size="icon-sm"
              disabled={running || !command.trim()}
            >
              <SendIcon className="size-4" />
            </Button>
          </form>
        </div>
      </div>
      <TerminalHistoryDialog
        history={history}
        open={historyOpen}
        onOpenChange={setHistoryOpen}
        onClearHistory={clearHistory}
        onOpenResource={onOpenResource}
        openingUri={openingUri}
      />
    </>
  )
}
