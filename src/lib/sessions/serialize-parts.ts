import type { MessagePart } from './types/message'

/**
 * Part serialization helpers (Message → API request format)
 */
export function serializeParts(
  parts: MessagePart[],
): Array<Record<string, unknown>> {
  return parts.flatMap((part) => {
    if (part.type === 'text') {
      return [{ type: 'text', text: part.text }]
    }
    if (part.type === 'context') {
      return [
        {
          type: 'context',
          uri: part.uri,
          context_type: part.context_type,
          abstract: part.abstract,
        },
      ]
    }
    if (
      part.type === 'reasoning' ||
      part.type === 'iteration' ||
      part.type === 'tool_result'
    )
      return []

    // tool
    const d: Record<string, unknown> = {
      type: 'tool',
      tool_id: part.tool_id,
      tool_name: part.tool_name,
      tool_uri: part.tool_uri,
      skill_uri: part.skill_uri,
      tool_status: part.tool_status,
    }
    if (part.tool_input) d.tool_input = part.tool_input
    if (part.tool_output) d.tool_output = part.tool_output
    if (part.duration_ms != null) d.duration_ms = part.duration_ms
    if (part.prompt_tokens != null) d.prompt_tokens = part.prompt_tokens
    if (part.completion_tokens != null)
      d.completion_tokens = part.completion_tokens
    return [d]
  })
}
