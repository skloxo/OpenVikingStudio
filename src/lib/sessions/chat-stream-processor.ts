import type { StreamToolCall } from './types/chat'
import type {
  MessagePart,
  ReasoningPart,
  TextPart,
  ToolPart,
} from './types/message'
import { parseSseStream, streamEventDataToText } from './sse'
import { createBrowserId } from '../browser-crypto'
import {
  clonePart,
  dedupeToolCalls,
  isToolErrorResult,
  waitForNextFrame,
} from './chat-utils'

export interface ChatStreamConsumerCallbacks {
  setStreamingContent: (content: string) => void
  setStreamingToolCalls: (calls: StreamToolCall[]) => void
  setStreamingReasoning: (reasoning: string) => void
  setStreamingParts: (parts: MessagePart[]) => void
  setIteration: (iter: number) => void
}

export class ChatStreamAccumulator {
  content = ''
  reasoning = ''
  toolCalls: StreamToolCall[] = []
  parts: MessagePart[] = []
  lastToolCall: StreamToolCall | null = null
  currentReasoningPart: ReasoningPart | null = null
  currentReasoningHasDelta = false
  currentTextPart: TextPart | null = null
  currentIteration = 0

  finishCurrentReasoning() {
    if (!this.currentReasoningPart) return
    this.currentReasoningPart.is_running = false
    this.currentReasoningPart = null
    this.currentReasoningHasDelta = false
  }

  appendReasoning(text: string, publish: () => void) {
    if (!text) return
    if (
      !this.currentReasoningPart ||
      this.parts.at(-1) !== this.currentReasoningPart
    ) {
      this.currentReasoningPart = {
        type: 'reasoning',
        reasoning: '',
        is_running: true,
      }
      this.parts.push(this.currentReasoningPart)
    }
    this.currentReasoningPart.reasoning += text
    publish()
  }

  appendText(text: string, publish: () => void) {
    if (!text) return
    this.finishCurrentReasoning()
    if (!this.currentTextPart || this.parts.at(-1) !== this.currentTextPart) {
      this.currentTextPart = { type: 'text', text: '' }
      this.parts.push(this.currentTextPart)
    }
    this.currentTextPart.text += text
    publish()
  }

  setFinalText(text: string, publishNow: () => void) {
    if (!text) return
    this.finishCurrentReasoning()
    if (this.currentTextPart) {
      this.currentTextPart.text = text
    } else {
      this.currentTextPart = { type: 'text', text }
      this.parts.push(this.currentTextPart)
    }
    publishNow()
  }
}

export async function consumeChatStream(
  response: Response,
  signal: AbortSignal,
  acc: ChatStreamAccumulator,
  callbacks: ChatStreamConsumerCallbacks,
): Promise<void> {
  const {
    setStreamingContent,
    setStreamingToolCalls,
    setStreamingReasoning,
    setStreamingParts,
    setIteration,
  } = callbacks

  let lastPaintAt = 0
  let publishScheduled = false
  let publishFrameId: number | null = null

  const publishStreamingPartsNow = () => {
    if (publishFrameId !== null && typeof window !== 'undefined') {
      window.cancelAnimationFrame(publishFrameId)
    }
    publishFrameId = null
    publishScheduled = false
    setStreamingParts(acc.parts.map(clonePart))
  }

  const publishStreamingParts = () => {
    if (publishScheduled) return
    publishScheduled = true
    if (typeof window === 'undefined') {
      queueMicrotask(publishStreamingPartsNow)
      return
    }
    publishFrameId = window.requestAnimationFrame(publishStreamingPartsNow)
  }

  const yieldToRenderer = async () => {
    const now =
      typeof performance !== 'undefined' ? performance.now() : Date.now()
    if (now - lastPaintAt < 16) return
    lastPaintAt = now
    await waitForNextFrame()
  }

  stream: for await (const event of parseSseStream(response)) {
    if (signal.aborted) break

    switch (event.event) {
      case 'iteration': {
        const data = streamEventDataToText(event.data)
        const match = data.match(/(\d+)/)
        if (match) {
          acc.currentIteration = Number(match[1])
          setIteration(acc.currentIteration)
          acc.finishCurrentReasoning()
          acc.currentTextPart = null
          const previousPart = acc.parts.at(-1)
          if (
            previousPart?.type !== 'iteration' ||
            previousPart.iteration !== acc.currentIteration
          ) {
            acc.parts.push({
              type: 'iteration',
              iteration: acc.currentIteration,
            })
            publishStreamingParts()
            await yieldToRenderer()
          }
        }
        break
      }

      case 'content_delta': {
        const delta = streamEventDataToText(event.data)
        acc.content += delta
        setStreamingContent(acc.content)
        acc.appendText(delta, publishStreamingParts)
        await yieldToRenderer()
        break
      }

      case 'reasoning_delta': {
        const delta = streamEventDataToText(event.data)
        acc.reasoning += delta
        setStreamingReasoning(acc.reasoning)
        acc.appendReasoning(delta, publishStreamingParts)
        acc.currentReasoningHasDelta = true
        await yieldToRenderer()
        break
      }

      case 'reasoning': {
        if (!acc.currentReasoningHasDelta) {
          const reasoning = streamEventDataToText(event.data)
          acc.reasoning += reasoning
          setStreamingReasoning(acc.reasoning)
          acc.appendReasoning(reasoning, publishStreamingParts)
          acc.finishCurrentReasoning()
          publishStreamingPartsNow()
          await yieldToRenderer()
        }
        break
      }

      case 'tool_call': {
        const raw = streamEventDataToText(event.data)
        const parenIdx = raw.indexOf('(')
        const name = parenIdx > 0 ? raw.slice(0, parenIdx) : raw
        const args = parenIdx > 0 ? raw.slice(parenIdx + 1, -1) : ''
        const duplicate = acc.toolCalls.find(
          (tc) =>
            tc.iteration === acc.currentIteration &&
            tc.name === name &&
            tc.arguments === args &&
            tc.result === undefined,
        )
        if (duplicate) {
          acc.lastToolCall = duplicate
          setStreamingToolCalls(dedupeToolCalls(acc.toolCalls))
          break
        }
        acc.lastToolCall = {
          name,
          arguments: args,
          iteration: acc.currentIteration,
        }
        acc.toolCalls.push(acc.lastToolCall)
        const toolPart: ToolPart = {
          type: 'tool',
          tool_id: createBrowserId('tool'),
          tool_name: name,
          tool_uri: '',
          skill_uri: '',
          tool_status: 'running',
        }
        try {
          toolPart.tool_input = JSON.parse(args) as Record<string, unknown>
        } catch {
          if (args) toolPart.tool_input = { raw: args }
        }
        acc.finishCurrentReasoning()
        acc.parts.push(toolPart)
        acc.currentTextPart = null
        setStreamingToolCalls(dedupeToolCalls(acc.toolCalls))
        publishStreamingParts()
        await yieldToRenderer()
        break
      }

      case 'tool_result': {
        acc.finishCurrentReasoning()
        const pendingToolCall = acc.toolCalls.find(
          (tc) => tc.result === undefined,
        )
        const pendingToolPart = acc.parts.find(
          (part): part is ToolPart =>
            part.type === 'tool' &&
            (part.tool_status === 'running' ||
              part.tool_status === 'pending'),
        )
        if (pendingToolCall) {
          const result = streamEventDataToText(event.data)
          const isError = isToolErrorResult(result)
          pendingToolCall.result = result
          if (pendingToolPart) {
            pendingToolPart.tool_output = result
            pendingToolPart.tool_status = isError ? 'error' : 'completed'
            acc.parts.push({
              type: 'tool_result',
              tool_id: pendingToolPart.tool_id,
              tool_name: pendingToolPart.tool_name,
              tool_output: result,
              is_error: isError,
            })
          }
          acc.currentTextPart = null
          setStreamingToolCalls(dedupeToolCalls(acc.toolCalls))
          publishStreamingParts()
          await yieldToRenderer()
        }
        break
      }

      case 'response': {
        acc.content = streamEventDataToText(event.data)
        setStreamingContent(acc.content)
        acc.setFinalText(acc.content, publishStreamingPartsNow)
        break stream
      }
    }
  }
}
