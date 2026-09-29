/**
 * terminal-panel-types.ts
 * 从 terminal-panel.tsx 接缝提取的本地类型、常量与配置数据。
 * 不含任何 React 组件或副作用逻辑，纯声明层。
 */
import type {
  TerminalCommandGroup,
  TerminalCommandParameterKey,
  TerminalCommandView,
} from '../-lib/types'

// ─── Storage Keys & Limits ──────────────────────────────────────────────────

export const TERMINAL_COMMAND_HISTORY_STORAGE_KEY =
  'openviking.playground.terminalCommandHistory'
export const TERMINAL_ENTRY_HISTORY_STORAGE_KEY =
  'openviking.playground.terminalEntryHistory'
export const TERMINAL_COMMAND_HISTORY_LIMIT = 50
export const TERMINAL_ENTRY_HISTORY_LIMIT = 100

// ─── URI-Argument Commands ───────────────────────────────────────────────────

export const URI_ARGUMENT_COMMANDS = new Set([
  '/abstract',
  '/ls',
  '/overview',
  '/read',
  '/stat',
  '/tree',
])

// ─── Session Subcommand Help ─────────────────────────────────────────────────

export type SessionSubcommandHelp = {
  examples: string[]
  insertText: string
  key: string
  parameters: TerminalCommandParameterKey[]
  usage: string
}

export const SESSION_SUBCOMMANDS: SessionSubcommandHelp[] = [
  {
    examples: ['session.current'],
    insertText: '/session current',
    key: 'current',
    parameters: [],
    usage: '/session current',
  },
  {
    examples: ['session.list'],
    insertText: '/session list',
    key: 'list',
    parameters: [],
    usage: '/session list',
  },
  {
    examples: ['session.create'],
    insertText: '/session create ',
    key: 'create',
    parameters: ['sessionId'],
    usage: '/session create [session_id]',
  },
  {
    examples: ['session.switch'],
    insertText: '/session switch ',
    key: 'switch',
    parameters: ['sessionId'],
    usage: '/session switch <session_id>',
  },
  {
    examples: ['session.get'],
    insertText: '/session get ',
    key: 'get',
    parameters: ['sessionId'],
    usage: '/session get [session_id]',
  },
  {
    examples: ['session.context'],
    insertText: '/session context ',
    key: 'context',
    parameters: ['sessionId', 'tokenBudget'],
    usage: '/session context [session_id] --token-budget 8000',
  },
  {
    examples: ['session.messages'],
    insertText: '/session messages ',
    key: 'messages',
    parameters: ['sessionId'],
    usage: '/session messages [session_id]',
  },
  {
    examples: ['session.archive'],
    insertText: '/session archive ',
    key: 'archive',
    parameters: ['sessionId', 'archiveId'],
    usage: '/session archive [session_id] <archive_id>',
  },
  {
    examples: ['session.commit'],
    insertText: '/session commit ',
    key: 'commit',
    parameters: ['sessionId', 'keepRecent'],
    usage: '/session commit [session_id] --keep-recent 10',
  },
  {
    examples: ['session.extract'],
    insertText: '/session extract ',
    key: 'extract',
    parameters: ['sessionId'],
    usage: '/session extract [session_id]',
  },
  {
    examples: ['session.message'],
    insertText: '/session message ',
    key: 'message',
    parameters: ['sessionId', 'messageRole', 'messageContent'],
    usage: '/session message [session_id] user hello',
  },
  {
    examples: ['session.used'],
    insertText: '/session used ',
    key: 'used',
    parameters: ['sessionId', 'contexts', 'skillJson'],
    usage: '/session used [session_id] --context viking://resources/...',
  },
  {
    examples: ['session.toolResults'],
    insertText: '/session tool-results ',
    key: 'tool-results',
    parameters: ['sessionId', 'toolName', 'limit'],
    usage: '/session tool-results [session_id] --limit 20',
  },
  {
    examples: ['session.toolResult'],
    insertText: '/session tool-result ',
    key: 'tool-result',
    parameters: ['sessionId', 'toolResultId', 'limit', 'offset'],
    usage: '/session tool-result [session_id] <tool_result_id>',
  },
  {
    examples: ['session.toolSearch'],
    insertText: '/session tool-search ',
    key: 'tool-search',
    parameters: ['sessionId', 'toolResultId', 'query', 'limit', 'contextChars'],
    usage: '/session tool-search [session_id] <tool_result_id> query',
  },
  {
    examples: ['session.delete'],
    insertText: '/session delete ',
    key: 'delete',
    parameters: ['sessionId'],
    usage: '/session delete <session_id>',
  },
]

export const SESSION_SUBCOMMANDS_BY_KEY = new Map(
  SESSION_SUBCOMMANDS.map((item) => [item.key, item]),
)

// ─── Local Suggestion Types ──────────────────────────────────────────────────

export type TerminalSuggestionGroup =
  | TerminalCommandGroup
  | 'history'
  | 'resource'
  | 'subcommand'

export type TerminalSuggestion = Omit<TerminalCommandView, 'group'> & {
  group: TerminalSuggestionGroup
  id: string
}

export type TerminalQuickStartExample = {
  action?: () => void
  command: string
  code: string
  key: string
  title: string
}

export type ScopedSearchInput = {
  query: string
  scopeUri?: string
}

export type ParsedOptions = {
  flags: Map<string, string[]>
  positional: string[]
}
