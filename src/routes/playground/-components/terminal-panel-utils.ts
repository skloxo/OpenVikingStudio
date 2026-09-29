/**
 * terminal-panel-utils.ts
 * 从 terminal-panel.tsx 接缝提取的纯函数工具集。
 * 全部为无副作用纯函数，不依赖任何 React hook。
 */
import type { ResourceRef, TerminalEntry } from '../-lib/types'
import { normalizeDirUri } from '#/routes/resources/-lib/normalize'
import {
  readStoredJsonArray,
  removeStoredValue,
  writeStoredJson,
} from '../-lib/utils'
import {
  TERMINAL_COMMAND_HISTORY_LIMIT,
  TERMINAL_ENTRY_HISTORY_LIMIT,
} from './terminal-panel-types'
import type {
  ParsedOptions,
  ScopedSearchInput,
} from './terminal-panel-types'

// ─── Command History Persistence ─────────────────────────────────────────────

export function loadCommandHistory(storageKey: string): string[] {
  return readStoredJsonArray(
    storageKey,
    (item) => {
      if (typeof item !== 'string') return undefined
      const trimmed = item.trim()
      return trimmed || undefined
    },
    TERMINAL_COMMAND_HISTORY_LIMIT,
  )
}

export function persistCommandHistory(
  storageKey: string,
  history: string[],
): void {
  writeStoredJson(storageKey, history.slice(0, TERMINAL_COMMAND_HISTORY_LIMIT))
}

// ─── Resource Ref Normalization ───────────────────────────────────────────────

export function normalizeRefs(value: unknown): ResourceRef[] | undefined {
  if (!Array.isArray(value)) return undefined
  const refs = value
    .filter(
      (item): item is ResourceRef =>
        typeof item === 'object' &&
        item !== null &&
        typeof (item as ResourceRef).uri === 'string',
    )
    .map((item) => ({
      label: typeof item.label === 'string' ? item.label : undefined,
      meta: typeof item.meta === 'string' ? item.meta : undefined,
      uri: item.uri,
    }))
  return refs.length > 0 ? refs : undefined
}

// ─── Terminal History Persistence ────────────────────────────────────────────

export function loadTerminalHistory(storageKey: string): TerminalEntry[] {
  return readStoredJsonArray(
    storageKey,
    (item): TerminalEntry | undefined => {
      if (typeof item !== 'object' || item === null) return undefined
      const record = item as Record<string, unknown>
      if (
        typeof record.id !== 'string' ||
        typeof record.title !== 'string' ||
        !['command', 'error', 'info', 'success'].includes(
          String(record.kind),
        ) ||
        (record.body !== undefined && typeof record.body !== 'string')
      ) {
        return undefined
      }
      return {
        body: typeof record.body === 'string' ? record.body : undefined,
        id: record.id,
        kind: record.kind as TerminalEntry['kind'],
        refs: normalizeRefs(record.refs),
        title: record.title,
      }
    },
    TERMINAL_ENTRY_HISTORY_LIMIT,
    true,
  )
}

export function persistTerminalHistory(
  storageKey: string,
  history: TerminalEntry[],
): void {
  writeStoredJson(storageKey, history.slice(-TERMINAL_ENTRY_HISTORY_LIMIT))
}

export function clearPersistedTerminalHistory(storageKey: string): void {
  removeStoredValue(storageKey)
}

// ─── URI & JSON Helpers ───────────────────────────────────────────────────────

export function extractVikingUris(text: string): string[] {
  return text.match(/viking:\/\/[^\s,，)）\]}】'"`]+/g) ?? []
}

export function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

// ─── CLI Option Parsing ───────────────────────────────────────────────────────

export function parseWaitTimeout(body: string): number | undefined {
  const trimmed = body.trim()
  if (!trimmed) return undefined
  const match = trimmed.match(/^(?:--timeout\s+)?(\d+(?:\.\d+)?)$/)
  if (!match) {
    throw new Error('Usage: /wait [--timeout seconds]')
  }
  return Number(match[1])
}

export function joinBodyLines(lines: Array<string | undefined>): string {
  return lines.filter((line): line is string => Boolean(line)).join('\n')
}

export function parseOptions(body: string): ParsedOptions {
  const tokens = body.trim().split(/\s+/).filter(Boolean)
  const flags = new Map<string, string[]>()
  const positional: string[] = []

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]
    if (!token.startsWith('--')) {
      positional.push(token)
      continue
    }

    const eqIndex = token.indexOf('=')
    const key = token.slice(2, eqIndex > -1 ? eqIndex : undefined)
    const inlineValue = eqIndex > -1 ? token.slice(eqIndex + 1) : undefined
    let value = inlineValue ?? 'true'

    if (
      inlineValue === undefined &&
      tokens[index + 1] &&
      !tokens[index + 1].startsWith('--')
    ) {
      value = tokens[index + 1]
      index += 1
    }

    flags.set(key, [...(flags.get(key) ?? []), value])
  }

  return { flags, positional }
}

export function getLastFlag(
  flags: Map<string, string[]>,
  key: string,
): string | undefined {
  return flags.get(key)?.at(-1)
}

export function getNumberFlag(
  flags: Map<string, string[]>,
  key: string,
): number | undefined {
  const value = getLastFlag(flags, key)
  if (value === undefined || value === 'true') return undefined
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    throw new Error(`Invalid --${key}: ${value}`)
  }
  return parsed
}

export function getBooleanFlag(
  flags: Map<string, string[]>,
  key: string,
): boolean {
  return flags.has(key) && getLastFlag(flags, key) !== 'false'
}

export function parseScopedSearchInput(
  body: string,
  currentUri: string,
  missingScopeMessage: string,
): ScopedSearchInput {
  const tokens = body.trim().split(/\s+/).filter(Boolean)
  const queryParts: string[] = []
  let scopeUri: string | undefined

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]
    if (token === '--scope') {
      const value = tokens[index + 1]
      if (!value) throw new Error(missingScopeMessage)
      scopeUri = value === '.' ? currentUri : normalizeDirUri(value)
      index += 1
      continue
    }
    if (token.startsWith('--scope=')) {
      const value = token.slice('--scope='.length)
      if (!value) throw new Error(missingScopeMessage)
      scopeUri = value === '.' ? currentUri : normalizeDirUri(value)
      continue
    }
    queryParts.push(token)
  }

  return {
    query: queryParts.join(' ').trim(),
    scopeUri,
  }
}
