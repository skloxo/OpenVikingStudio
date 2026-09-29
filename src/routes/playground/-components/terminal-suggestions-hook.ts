/**
 * terminal-suggestions-hook.ts
 * 负责终端自动补全、命令列表过滤、Session 子命令匹配与 Command Assist 帮助信息计算。
 */
import { useMemo } from 'react'

import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import { ROOT_URI, TERMINAL_COMMANDS } from '../-lib/constants'
import type {
  TerminalCommandParameterKey,
  TerminalCommandView,
  TerminalEntry,
} from '../-lib/types'
import { entryToRef, visibleContextEntries } from '../-lib/utils'
import {
  SESSION_SUBCOMMANDS,
  SESSION_SUBCOMMANDS_BY_KEY,
  URI_ARGUMENT_COMMANDS,
} from './terminal-panel-types'
import type {
  SessionSubcommandHelp,
  TerminalSuggestion,
} from './terminal-panel-types'
import { extractVikingUris } from './terminal-panel-utils'

export type UseTerminalSuggestionsOptions = {
  command: string
  commandHistory: string[]
  connectionRole?: string
  currentUri: string
  entries: VikingFsEntry[]
  history: TerminalEntry[]
  inputFocused: boolean
  suggestionsOpen: boolean
  t: (key: string, options?: Record<string, unknown>) => string
}

export type TerminalCommandParameterView = {
  description: string
  key: TerminalCommandParameterKey
  name: string
}

export type TerminalCommandExampleView = {
  code: string
  description: string
  key: string
}

export type SessionSubcommandRow = SessionSubcommandHelp & {
  description: string
}

export function useTerminalSuggestions({
  command,
  commandHistory,
  connectionRole,
  currentUri,
  entries,
  history,
  inputFocused,
  suggestionsOpen,
  t,
}: UseTerminalSuggestionsOptions) {
  const commands = useMemo<TerminalCommandView[]>(
    () =>
      TERMINAL_COMMANDS.filter(
        (item) =>
          !item.adminOnly ||
          connectionRole === 'admin' ||
          connectionRole === 'root',
      ).map((item) => ({
        ...item,
        description: t(`terminal.commands.${item.key}.description`),
        usage: t(`terminal.commands.${item.key}.usage`),
      })),
    [connectionRole, t],
  )

  const resourceCandidates = useMemo(() => {
    const candidates = new Set<string>([currentUri, ROOT_URI])
    for (const entry of visibleContextEntries(entries)) {
      const ref = entryToRef(entry)
      candidates.add(ref.uri)
    }
    for (const item of history) {
      for (const ref of item.refs ?? []) {
        candidates.add(ref.uri)
      }
      if (item.body) {
        for (const uri of extractVikingUris(item.body)) candidates.add(uri)
      }
      for (const uri of extractVikingUris(item.title)) candidates.add(uri)
    }
    for (const item of commandHistory) {
      for (const uri of extractVikingUris(item)) candidates.add(uri)
    }
    return Array.from(candidates).filter(Boolean).sort()
  }, [commandHistory, currentUri, entries, history])

  const activeCommand = useMemo(() => {
    const rawQuery = command.trimStart()
    return [...commands]
      .sort((a, b) => b.command.length - a.command.length)
      .find(
        (item) =>
          rawQuery === item.command || rawQuery.startsWith(`${item.command} `),
      )
  }, [command, commands])

  const suggestions = useMemo<TerminalSuggestion[]>(() => {
    const rawQuery = command.trimStart()
    const query = rawQuery.toLowerCase()
    const commandMatches =
      !query || query === '/'
        ? commands.map((item) => ({
            ...item,
            id: `command:${item.command}`,
          }))
        : query.startsWith('/')
          ? commands
              .filter(
                (item) =>
                  item.command.toLowerCase().startsWith(query) ||
                  item.description.toLowerCase().includes(query.slice(1)),
              )
              .map((item) => ({
                ...item,
                id: `command:${item.command}`,
              }))
          : []

    const resourceMatches =
      activeCommand && URI_ARGUMENT_COMMANDS.has(activeCommand.command)
        ? resourceCandidates
            .filter((uri) => {
              const argQuery = rawQuery
                .slice(activeCommand.command.length)
                .trimStart()
                .toLowerCase()
              if (!argQuery) return true
              return (
                uri.toLowerCase().startsWith(argQuery) ||
                uri.toLowerCase().includes(argQuery)
              )
            })
            .slice(0, 12)
            .map((uri) => ({
              ...activeCommand,
              command: uri,
              description: t('terminal.resourceSuggestion'),
              group: 'resource' as const,
              id: `resource:${activeCommand.command}:${uri}`,
              insertText: `${activeCommand.command} ${uri}`,
              usage: `${activeCommand.command} ${uri}`,
            }))
        : []

    const sessionSubcommandMatches =
      activeCommand?.command === '/session'
        ? (() => {
            const rawBody = rawQuery.slice(activeCommand.command.length)
            const body = rawBody.trimStart()
            const [partial = ''] = body.split(/\s+/)
            const isChoosingSubcommand =
              body.length === 0 ||
              (!rawBody.endsWith(' ') && !body.slice(partial.length).trim())

            if (!isChoosingSubcommand) return []

            return SESSION_SUBCOMMANDS.filter((item) => {
              const description = t(
                `terminal.commandExamples.${item.examples[0]}.description`,
              )
              return (
                !partial ||
                item.key.toLowerCase().startsWith(partial.toLowerCase()) ||
                description.toLowerCase().includes(partial.toLowerCase())
              )
            }).map((item) => ({
              ...activeCommand,
              command: item.key,
              description: t(
                `terminal.commandExamples.${item.examples[0]}.description`,
              ),
              group: 'subcommand' as const,
              id: `subcommand:session:${item.key}`,
              insertText: item.insertText,
              key: `session:${item.key}`,
              usage: item.usage,
            }))
          })()
        : []

    const historyMatches = commandHistory
      .filter((item) => {
        const lower = item.toLowerCase()
        return lower !== query && lower.startsWith(query)
      })
      .slice(0, 8)
      .map((item) => ({
        adminOnly: false,
        command: item,
        description: t('terminal.historySuggestion'),
        executable: false,
        group: 'history' as const,
        id: `history:${item}`,
        insertText: item,
        key: 'history',
        usage: item,
      }))

    const seen = new Set<string>()
    return [
      ...commandMatches,
      ...resourceMatches,
      ...sessionSubcommandMatches,
      ...historyMatches,
    ].filter((item) => {
      if (seen.has(item.insertText)) return false
      seen.add(item.insertText)
      return true
    })
  }, [activeCommand, command, commandHistory, commands, resourceCandidates, t])

  const helpCommand = useMemo(() => {
    if (!activeCommand) return undefined
    return activeCommand
  }, [activeCommand])

  const selectedSessionSubcommand = useMemo(() => {
    if (helpCommand?.command !== '/session') return undefined
    const body = command
      .trimStart()
      .slice(helpCommand.command.length)
      .trimStart()
    const [subcommand = ''] = body.split(/\s+/)
    return SESSION_SUBCOMMANDS_BY_KEY.get(subcommand)
  }, [command, helpCommand])

  const sessionSubcommandRows = useMemo<SessionSubcommandRow[]>(
    () =>
      SESSION_SUBCOMMANDS.map((item) => {
        const exampleKey = item.examples[0]
        return {
          ...item,
          description: t(`terminal.commandExamples.${exampleKey}.description`),
        }
      }),
    [t],
  )

  const showSessionSubcommandList =
    helpCommand?.command === '/session' && !selectedSessionSubcommand

  const helpTitle = selectedSessionSubcommand
    ? `/session ${selectedSessionSubcommand.key}`
    : helpCommand?.command

  const helpDescription = selectedSessionSubcommand
    ? t(
        `terminal.commandExamples.${selectedSessionSubcommand.examples[0]}.description`,
      )
    : helpCommand?.description

  const helpUsage = selectedSessionSubcommand
    ? selectedSessionSubcommand.usage
    : helpCommand?.usage

  const commandParameters = useMemo<TerminalCommandParameterView[]>(
    () =>
      (
        selectedSessionSubcommand?.parameters ??
        (showSessionSubcommandList ? [] : (helpCommand?.parameters ?? []))
      ).map((key) => ({
        description: t(`terminal.commandParameters.${key}.description`),
        key,
        name: t(`terminal.commandParameters.${key}.name`),
      })),
    [helpCommand, selectedSessionSubcommand, showSessionSubcommandList, t],
  )

  const commandExamples = useMemo<TerminalCommandExampleView[]>(
    () =>
      (
        selectedSessionSubcommand?.examples ??
        (showSessionSubcommandList ? [] : (helpCommand?.examples ?? []))
      ).map((key) => ({
        code: t(`terminal.commandExamples.${key}.code`),
        description: t(`terminal.commandExamples.${key}.description`),
        key,
      })),
    [helpCommand, selectedSessionSubcommand, showSessionSubcommandList, t],
  )

  const canUseCurrentScope =
    helpCommand?.command === '/find' || helpCommand?.command === '/search'

  const showCommandAssist =
    inputFocused &&
    (Boolean(helpCommand) || (suggestionsOpen && suggestions.length > 0))

  return {
    activeCommand,
    canUseCurrentScope,
    commandExamples,
    commandParameters,
    commands,
    helpCommand,
    helpDescription,
    helpTitle,
    helpUsage,
    resourceCandidates,
    selectedSessionSubcommand,
    sessionSubcommandRows,
    showCommandAssist,
    showSessionSubcommandList,
    suggestions,
  }
}
