import { useCallback, useEffect, useRef, useState } from 'react'

import type { ChatStatus, StreamToolCall } from './types/chat'
import type { Message, MessagePart } from './types/message'
import { addMessage, sendChatStream, serializeParts } from './api'
import { setSessionTitle } from './use-session-titles'
import {
  createUserMessage,
  dedupeToolCalls,
  buildAssistantMessage,
  type SendOptions,
} from './chat-utils'
import {
  ChatStreamAccumulator,
  consumeChatStream,
} from './chat-stream-processor'

export { createUserMessage, dedupeToolCalls, buildAssistantMessage }
export type { SendOptions }

export interface UseChatOptions {
  identityScopeKey: string
  sessionId: string
  /** Initial messages to populate the chat. */
  initialMessages?: Message[]
  /** Whether to persist messages via the sessions API after each exchange. */
  persistMessages?: boolean
}

export interface UseChatReturn {
  messages: Message[]
  status: ChatStatus
  error: string | undefined
  streamingContent: string
  streamingToolCalls: StreamToolCall[]
  streamingReasoning: string
  streamingParts: MessagePart[]
  iteration: number
  send: (message: string, options?: SendOptions) => Promise<void>
  abort: () => void
  reset: () => void
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
}

export function useChat(options: UseChatOptions): UseChatReturn {
  const {
    identityScopeKey,
    sessionId,
    initialMessages,
    persistMessages = true,
  } = options

  const [messages, setMessages] = useState<Message[]>(initialMessages ?? [])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [error, setError] = useState<string>()
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingToolCalls, setStreamingToolCalls] = useState<
    StreamToolCall[]
  >([])
  const [streamingReasoning, setStreamingReasoning] = useState('')
  const [streamingParts, setStreamingParts] = useState<MessagePart[]>([])
  const [iteration, setIteration] = useState(0)

  const abortRef = useRef<AbortController | null>(null)
  const messagesRef = useRef<Message[]>(messages)
  const lastSyncedInitialMessagesRef = useRef<Message[] | undefined>(undefined)
  const pendingInitialMessagesRef = useRef<Message[] | undefined>(undefined)
  messagesRef.current = messages

  // Reset state when sessionId changes
  useEffect(() => {
    abortRef.current?.abort()
    abortRef.current = null
    lastSyncedInitialMessagesRef.current = undefined
    pendingInitialMessagesRef.current = undefined
    setMessages([])
    setStatus('idle')
    setError(undefined)
    setStreamingContent('')
    setStreamingToolCalls([])
    setStreamingReasoning('')
    setStreamingParts([])
    setIteration(0)
  }, [sessionId])

  // Sync initialMessages into state when they load or when switching sessions.
  useEffect(() => {
    if (!initialMessages) return

    if (status === 'streaming') {
      pendingInitialMessagesRef.current = initialMessages
      return
    }

    const nextInitialMessages =
      pendingInitialMessagesRef.current ?? initialMessages
    // Consume the deferred snapshot on every non-streaming run so it can never
    // permanently shadow later initialMessages updates.
    pendingInitialMessagesRef.current = undefined
    if (lastSyncedInitialMessagesRef.current === nextInitialMessages) return

    lastSyncedInitialMessagesRef.current = nextInitialMessages
    setMessages(nextInitialMessages)
  }, [initialMessages, sessionId, status])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  const reset = useCallback(() => {
    abort()
    setMessages(initialMessages ?? [])
    setStatus('idle')
    setError(undefined)
    setStreamingContent('')
    setStreamingToolCalls([])
    setStreamingReasoning('')
    setStreamingParts([])
    setIteration(0)
  }, [abort, initialMessages])

  const send = useCallback(
    async (message: string, sendOptions?: SendOptions) => {
      if (status === 'streaming') return

      const isFirstExchange = messagesRef.current.length === 0
      const displayMessage = sendOptions?.displayMessage ?? message

      const userMsg = createUserMessage(displayMessage)
      setMessages((prev) => [...prev, userMsg])
      setStatus('streaming')
      setError(undefined)
      setStreamingContent('')
      setStreamingToolCalls([])
      setStreamingReasoning('')
      setStreamingParts([])
      setIteration(0)

      const controller = new AbortController()
      abortRef.current = controller

      const accumulator = new ChatStreamAccumulator()

      try {
        const response = await sendChatStream(
          { message, session_id: sessionId },
          controller.signal,
        )

        await consumeChatStream(
          response,
          controller.signal,
          accumulator,
          {
            setStreamingContent,
            setStreamingToolCalls,
            setStreamingReasoning,
            setStreamingParts,
            setIteration,
          },
        )

        // Build assistant message and finalize
        accumulator.finishCurrentReasoning()
        const assistantMsg = buildAssistantMessage(
          accumulator.content,
          dedupeToolCalls(accumulator.toolCalls),
          accumulator.parts,
        )
        setStreamingContent('')
        setStreamingToolCalls([])
        setStreamingReasoning('')
        setStreamingParts([])
        setStatus('idle')
        setMessages((prev) => [...prev, assistantMsg])

        // Persist to openviking session
        if (persistMessages) {
          try {
            await addMessage(sessionId, 'user', displayMessage)
            await addMessage(
              sessionId,
              'assistant',
              undefined,
              serializeParts(assistantMsg.parts),
            )
          } catch {
            // Persistence failure is non-blocking
          }
        }

        // Generate session title on first exchange
        if (sessionId && isFirstExchange) {
          setSessionTitle(
            identityScopeKey,
            sessionId,
            displayMessage.slice(0, 20),
          )
        }
      } catch (err) {
        if (controller.signal.aborted) {
          // Aborted intentionally — still finalize any partial content
          if (accumulator.content || accumulator.parts.length > 0) {
            accumulator.finishCurrentReasoning()
            const partialMsg = buildAssistantMessage(
              accumulator.content,
              dedupeToolCalls(accumulator.toolCalls),
              accumulator.parts,
            )
            setStreamingContent('')
            setStreamingToolCalls([])
            setStreamingReasoning('')
            setStreamingParts([])
            setMessages((prev) => [...prev, partialMsg])
          } else {
            setStreamingContent('')
            setStreamingToolCalls([])
            setStreamingReasoning('')
            setStreamingParts([])
          }
          setStatus('idle')
        } else {
          const msg = err instanceof Error ? err.message : String(err)
          setError(msg)
          setStatus('error')
        }
      } finally {
        abortRef.current = null
      }
    },
    [identityScopeKey, persistMessages, sessionId, status],
  )

  return {
    messages,
    status,
    error,
    streamingContent,
    streamingToolCalls,
    streamingReasoning,
    streamingParts,
    iteration,
    send,
    abort,
    reset,
    setMessages,
  }
}
