// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { ovClient } from '#/lib/ov-client'
import {
  buildFetchHeaders,
  fetchBotHealth,
  interruptSession,
  sendChatStream,
  steerSession,
} from './bot-chat-api'

describe('Bot fetch credentials and headers', () => {
  afterEach(() => {
    ovClient.clearConnection()
    vi.unstubAllGlobals()
  })

  it.each([
    { apiKey: '', expectedKey: 'root-key' },
    { apiKey: 'data-key', expectedKey: 'data-key' },
  ])('uses $expectedKey for Bot requests (prioritizing user apiKey over adminApiKey)', async ({ apiKey, expectedKey }) => {
    ovClient.setOptions({ baseUrl: 'http://localhost:1933' })
    ovClient.setConnection({
      accountId: 'account-1',
      adminApiKey: 'root-key',
      apiKey,
      identityHeaders: true,
      userId: 'user-1',
    })

    const headers = buildFetchHeaders()
    expect(headers['X-API-Key']).toBe(expectedKey)
    expect(headers['X-OpenViking-Account']).toBe('account-1')
    expect(headers['X-OpenViking-User']).toBe('user-1')

    const fetchMock = vi.fn().mockImplementation(async (url: string) =>
      url.endsWith('/stream')
        ? new Response('data: hello\n\n', {
            headers: { 'Content-Type': 'text/event-stream' },
          })
        : new Response(JSON.stringify({ status: 'ok' })),
    )
    vi.stubGlobal('fetch', fetchMock)

    await fetchBotHealth()
    const messages = []
    for await (const event of await sendChatStream({ message: 'hello' } as any)) {
      messages.push(event.data)
    }
    expect(messages).toEqual(['hello'])
    await steerSession('session 1', 'next input')
    await interruptSession('session 1')

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:1933/bot/v1/health',
      'http://localhost:1933/bot/v1/chat/stream',
      'http://localhost:1933/bot/v1/sessions/session%201/steer',
      'http://localhost:1933/bot/v1/sessions/session%201/interrupt',
    ])
    for (const [, options] of fetchMock.mock.calls) {
      expect(options.headers).toMatchObject({
        'X-API-Key': expectedKey,
        'X-OpenViking-Account': 'account-1',
        'X-OpenViking-User': 'user-1',
      })
    }
  })
})
