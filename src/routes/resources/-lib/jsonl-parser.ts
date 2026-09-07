/**
 * JSONL 纯解析层 — 无 React 依赖，可独立单测
 * 从 file-preview.tsx 拆解，保持全量 export 向后兼容
 */

// ─── 类型 ────────────────────────────────────────────────────────────────────

export type JsonlRecord = {
  error: Error | null
  index: number
  line: string
  parsed: unknown
}

/** One renderable unit of a JSONL message, classified by its structural type. */
export type JsonlPart =
  | { input: unknown; kind: 'tool-call'; toolName: string }
  | { kind: 'raw'; text: string }
  | { kind: 'text'; text: string }
  | { kind: 'tool-result'; text: string; toolName: string }

export type JsonlMessage = {
  id: string
  label: string
  lineNo: number
  parts: JsonlPart[]
  role: 'agent' | 'assistant' | 'invalid' | 'other' | 'user'
  roleId: string
  time: string
  toolShape: 'call' | 'none' | 'result'
}

// ─── 常量 ────────────────────────────────────────────────────────────────────

export const JSONL_MESSAGE_PREVIEW_LIMIT = 720
export const JSONL_TOOLCALL_STORAGE_KEY = 'openviking.playground.jsonlToolCall'
export const COLLAPSE_SYMBOL = '▾'
export const EXPAND_SYMBOL = '▸'

// ─── 内部工具 ─────────────────────────────────────────────────────────────────

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Flatten a tool_result `content` (string, or a list of text blocks) to text. */
function jsonlContentToText(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value
      .map((item) =>
        typeof item === 'string'
          ? item
          : isRecord(item) && typeof item.text === 'string'
            ? item.text
            : JSON.stringify(item, null, 2),
      )
      .join('\n')
  }
  if (value === undefined || value === null) return ''
  return JSON.stringify(value, null, 2)
}

/**
 * Classify one content entry by its structural `type` field, never by a
 * rendered string prefix. Covers the Anthropic transcript shape
 * (`text` / `tool_use` / `tool_result`) and the OpenViking parts shape
 * (`text` / `tool`, see openviking/message/part.py). An OpenViking `tool`
 * part carries both the call and its output, so it expands to two entries.
 */
function toJsonlParts(part: unknown): JsonlPart[] {
  if (typeof part === 'string') return [{ kind: 'text', text: part }]
  if (!isRecord(part)) return [{ kind: 'raw', text: JSON.stringify(part) }]

  const type = String(part.type ?? '')

  if (type === 'tool_use') {
    return [
      {
        input: part.input ?? part.arguments ?? {},
        kind: 'tool-call',
        toolName: typeof part.name === 'string' ? part.name : 'tool',
      },
    ]
  }

  if (type === 'tool_result') {
    return [
      {
        kind: 'tool-result',
        text: jsonlContentToText(part.content ?? part.result ?? ''),
        toolName: '',
      },
    ]
  }

  if (type === 'tool') {
    const toolName = typeof part.tool_name === 'string' ? part.tool_name : ''
    const output = typeof part.tool_output === 'string' ? part.tool_output : ''
    const hasInput =
      isRecord(part.tool_input) && Object.keys(part.tool_input).length > 0
    const parts: JsonlPart[] = []
    if (hasInput || !output) {
      parts.push({ input: part.tool_input ?? {}, kind: 'tool-call', toolName })
    }
    if (output) parts.push({ kind: 'tool-result', text: output, toolName })
    return parts
  }

  if (type === 'text' || typeof part.text === 'string') {
    return [
      { kind: 'text', text: typeof part.text === 'string' ? part.text : '' },
    ]
  }

  const payload = { ...part }
  delete payload.type
  const body = Object.keys(payload).length
    ? JSON.stringify(payload, null, 2)
    : ''
  const label = type || 'part'
  return [{ kind: 'raw', text: body ? `[${label}]\n${body}` : `[${label}]` }]
}

function toJsonlMessageParts(content: unknown): JsonlPart[] {
  if (typeof content === 'string') {
    return content ? [{ kind: 'text', text: content }] : []
  }
  if (Array.isArray(content)) return content.flatMap(toJsonlParts)
  if (content === undefined || content === null) return []
  return [{ kind: 'raw', text: JSON.stringify(content, null, 2) }]
}

/**
 * How the card should be styled. A message counts as tool-shaped only when it
 * carries no text of its own: an assistant turn holding both `text` and
 * `tool_use` is styled as a plain assistant message, because the text is the
 * readable content and the calls are an aside.
 */
function getJsonlToolShape(parts: JsonlPart[]): JsonlMessage['toolShape'] {
  if (parts.some((part) => part.kind === 'text')) return 'none'
  if (parts.some((part) => part.kind === 'tool-call')) return 'call'
  if (parts.some((part) => part.kind === 'tool-result')) return 'result'
  return 'none'
}

// ─── 公共 API ─────────────────────────────────────────────────────────────────

export function parseJsonlRecords(text: string): JsonlRecord[] {
  return text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line, index) => ({ line, index }))
    .filter((record) => record.line.trim().length > 0)
    .map((record) => {
      try {
        return {
          ...record,
          error: null,
          parsed: JSON.parse(record.line) as unknown,
        }
      } catch (error) {
        return {
          ...record,
          error: error instanceof Error ? error : new Error(String(error)),
          parsed: null,
        }
      }
    })
}

export function normalizeJsonlDisplayText(text: string): string {
  return text.replace(/↵|⏎|\r\n?/g, '\n')
}

export function hasJsonlToolPart(parts: JsonlPart[]): boolean {
  return parts.some(
    (part) => part.kind === 'tool-call' || part.kind === 'tool-result',
  )
}

export function getJsonlMessage(record: JsonlRecord): JsonlMessage {
  const { error, index, line, parsed } = record
  if (error || !isRecord(parsed)) {
    return {
      id: '',
      label: 'invalid',
      lineNo: index + 1,
      parts: [{ kind: 'raw', text: line }],
      role: 'invalid',
      roleId: '',
      time: '',
      toolShape: 'none',
    }
  }

  const nestedMessage = isRecord(parsed.message) ? parsed.message : null
  const source = nestedMessage ?? parsed
  const rawRole = String(source.role ?? parsed.role ?? parsed.type ?? 'message')
    .trim()
    .toLowerCase()
  const content =
    source.content ?? source.parts ?? parsed.parts ?? parsed.content ?? parsed
  const parts = toJsonlMessageParts(content)
  const toolShape = getJsonlToolShape(parts)

  return {
    id: String(parsed.uuid ?? parsed.id ?? source.id ?? ''),
    label: toolShape === 'result' ? 'tool-result' : rawRole,
    lineNo: index + 1,
    parts,
    role:
      rawRole === 'user'
        ? 'user'
        : rawRole === 'assistant' || rawRole === 'agent'
          ? rawRole
          : 'other',
    roleId: String(parsed.peer_id ?? source.peer_id ?? ''),
    time: String(
      parsed.timestamp ?? parsed.created_at ?? source.created_at ?? '',
    ),
    toolShape,
  }
}

export function isJsonlMarkdownMessage(role: JsonlMessage['role']): boolean {
  return role === 'assistant' || role === 'agent' || role === 'user'
}

/** Trim text parts against a shared character budget; tool parts pass through. */
export function collapseJsonlParts(
  parts: JsonlPart[],
  limit: number,
): JsonlPart[] {
  let budget = limit
  const collapsed: JsonlPart[] = []
  for (const part of parts) {
    if (part.kind !== 'text') {
      collapsed.push(part)
      continue
    }
    if (budget <= 0) continue
    if (part.text.length <= budget) {
      collapsed.push(part)
      budget -= part.text.length
      continue
    }
    collapsed.push({
      kind: 'text',
      text: `${part.text.slice(0, budget).trimEnd()}...`,
    })
    budget = 0
  }
  return collapsed
}

export function formatJsonlTime(value: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString([], {
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
  })
}
