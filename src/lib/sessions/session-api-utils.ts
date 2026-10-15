import { normalizeOvClientError } from '#/lib/ov-client'
import type { Message } from './types/message'

export function isMessage(value: unknown): value is Message {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'role' in value &&
    'parts' in value
  )
}

export function getMessages(value: unknown): Message[] {
  return Array.isArray(value) ? value.filter(isMessage) : []
}

export function deduplicateMessages(messages: Message[]): Message[] {
  const seen = new Set<string>()
  return messages.filter((message) => {
    if (seen.has(message.id)) return false
    seen.add(message.id)
    return true
  })
}

export const SESSION_ARCHIVE_CONCURRENCY = 4

export async function mapWithConcurrency<T, TResult>(
  items: T[],
  concurrency: number,
  mapper: (item: T, index: number) => Promise<TResult>,
): Promise<TResult[]> {
  const results = new Array<TResult>(items.length)
  let nextIndex = 0

  async function worker() {
    while (nextIndex < items.length) {
      const index = nextIndex
      nextIndex += 1
      results[index] = await mapper(items[index], index)
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, () => worker()),
  )
  return results
}

export function isMissingArchive(error: unknown): boolean {
  const normalized = normalizeOvClientError(error)
  return normalized.statusCode === 404 || normalized.code === 'NOT_FOUND'
}
