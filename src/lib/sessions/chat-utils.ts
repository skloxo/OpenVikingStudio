import type { StreamToolCall } from './types/chat'
import type {
  Message,
  MessagePart,
  ContextPart,
  IterationPart,
  ReasoningPart,
  TextPart,
  ToolPart,
  ToolResultPart,
} from './types/message'
import { createBrowserId } from '../browser-crypto'

export type SendOptions = {
  displayMessage?: string
}

export function createUserMessage(content: string): Message {
  return {
    id: createBrowserId('msg'),
    role: 'user',
    parts: [{ type: 'text', text: content }],
    created_at: new Date().toISOString(),
  }
}

export function toolCallKey(toolCall: StreamToolCall): string {
  return `${toolCall.iteration ?? 0}\u0000${toolCall.name}\u0000${toolCall.arguments}`
}

export function dedupeToolCalls(toolCalls: StreamToolCall[]): StreamToolCall[] {
  const result: StreamToolCall[] = []
  const byKey = new Map<string, StreamToolCall>()

  for (const toolCall of toolCalls) {
    const key = toolCallKey(toolCall)
    const existing = byKey.get(key)
    if (!existing) {
      const next = { ...toolCall }
      byKey.set(key, next)
      result.push(next)
      continue
    }
    if (!existing.result && toolCall.result) {
      existing.result = toolCall.result
    }
  }

  return result
}

export function isToolErrorResult(result?: string): boolean {
  return Boolean(result?.trimStart().toLowerCase().startsWith('error'))
}

export function clonePart(part: MessagePart): MessagePart {
  switch (part.type) {
    case 'text':
      return { ...part } satisfies TextPart
    case 'reasoning':
      return { ...part } satisfies ReasoningPart
    case 'iteration':
      return { ...part } satisfies IterationPart
    case 'tool':
      return {
        ...part,
        tool_input: part.tool_input ? { ...part.tool_input } : undefined,
      } satisfies ToolPart
    case 'tool_result':
      return { ...part } satisfies ToolResultPart
    case 'context':
      return { ...part } satisfies ContextPart
  }
}

export function waitForNextFrame(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve()
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve())
  })
}

export function buildAssistantMessage(
  content: string,
  toolCalls: StreamToolCall[],
  orderedParts?: MessagePart[],
): Message {
  const parts: MessagePart[] = orderedParts?.length ? [...orderedParts] : []

  if (parts.length > 0) {
    if (content && !parts.some((part) => part.type === 'text')) {
      parts.push({ type: 'text', text: content } satisfies TextPart)
    }
    return {
      id: createBrowserId('msg'),
      role: 'assistant',
      parts,
      created_at: new Date().toISOString(),
    }
  }

  // Tool parts first (matches backend ordering)
  for (const tc of toolCalls) {
    const toolPart: ToolPart = {
      type: 'tool',
      tool_id: '',
      tool_name: tc.name,
      tool_uri: '',
      skill_uri: '',
      tool_status: isToolErrorResult(tc.result) ? 'error' : 'completed',
      tool_output: tc.result,
    }
    try {
      toolPart.tool_input = JSON.parse(tc.arguments)
    } catch {
      toolPart.tool_input = { raw: tc.arguments }
    }
    parts.push(toolPart)
  }

  // Text part
  if (content) {
    parts.push({ type: 'text', text: content } satisfies TextPart)
  }

  return {
    id: createBrowserId('msg'),
    role: 'assistant',
    parts,
    created_at: new Date().toISOString(),
  }
}
