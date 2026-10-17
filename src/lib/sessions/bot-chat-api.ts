import { postBotV1Chat } from '#/gen/ov-client/sdk.gen'
import { OvClientError, ovClient } from '#/lib/ov-client'
import { fetchSse } from '#/lib/sse'
import type { BotChatRequest, BotChatResponse } from '@ov-server/bot/v1/chat'

export function extractErrorMessage(text: string, fallback: string): string {
  if (!text.trim()) return fallback

  try {
    const parsed = JSON.parse(text) as unknown
    if (parsed && typeof parsed === 'object') {
      const record = parsed as Record<string, unknown>
      if (typeof record.detail === 'string') return record.detail
      const error = record.error
      if (error && typeof error === 'object') {
        const message = (error as Record<string, unknown>).message
        if (typeof message === 'string') return message
      }
    }
  } catch {
    // Fall through to raw text.
  }

  return text
}

export function buildFetchHeaders(): Record<string, string> {
  const conn = ovClient.getConnection()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const apiKey = conn.adminApiKey || conn.apiKey
  if (apiKey) headers['X-API-Key'] = apiKey
  if (conn.identityHeaders) {
    if (conn.accountId) headers['X-OpenViking-Account'] = conn.accountId
    if (conn.userId) headers['X-OpenViking-User'] = conn.userId
  }
  return headers
}

export async function fetchBotHealth(): Promise<unknown> {
  const baseUrl = ovClient.getOptions().baseUrl
  const response = await fetch(`${baseUrl}/bot/v1/health`, {
    method: 'GET',
    headers: buildFetchHeaders(),
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new OvClientError({
      code: response.status === 503 ? 'BOT_MODE_DISABLED' : 'BOT_HEALTH_FAILED',
      message: extractErrorMessage(
        text,
        `Bot health check failed (${response.status})`,
      ),
      responseBody: text,
      statusCode: response.status,
    })
  }

  return response.json().catch(() => ({ status: 'ok' }))
}

/**
 * Send a streaming chat request and return standards-compliant SSE messages.
 */
export async function sendChatStream(
  request: BotChatRequest,
  signal?: AbortSignal,
): Promise<ReturnType<typeof fetchSse>> {
  const baseUrl = ovClient.getOptions().baseUrl
  const conn = ovClient.getConnection()
  return fetchSse(`${baseUrl}/bot/v1/chat/stream`, {
    method: 'POST',
    headers: {
      ...buildFetchHeaders(),
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      ...request,
      user_id: request.user_id || conn.userId || undefined,
      stream: true,
    }),
    signal,
  })
}

/** Send a non-streaming chat request. */
export async function sendChat(
  request: BotChatRequest,
): Promise<BotChatResponse> {
  const conn = ovClient.getConnection()
  const response = await postBotV1Chat({
    body: {
      ...request,
      user_id: request.user_id || conn.userId || undefined,
    },
    throwOnError: true,
  } as unknown as NonNullable<Parameters<typeof postBotV1Chat<true>>[0]>)

  return response.data as BotChatResponse
}
