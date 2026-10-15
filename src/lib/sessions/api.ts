import {
  deleteSessionBySessionId,
  getContentRead,
  getSessionIdArchiveByArchiveId,
  getSessions,
  getSessionBySessionId,
  getSessionIdContext,
  postSessions,
  postSessionIdCommit,
  postSessionIdExtract,
  postSessionIdMessages,
  postSessionIdUsed,
} from '#/gen/ov-client/sdk.gen'
import { getOvResult, ovClient } from '#/lib/ov-client'

import { parseSessionMemoryDiff } from './memory-diff'
import type { SessionMemoryDiff } from './memory-diff'
import type { Message } from './types/message'
import type {
  AddMessageResult,
  CommitSessionResult,
  CreateSessionResult,
  DeleteSessionResult,
  SessionArchiveResult,
  SessionContextResult,
  SessionListItem,
  SessionMeta,
} from '@ov-server/api/v1/sessions'
import type { UsedRequest } from '#/gen/ov-client/types.gen'

import {
  deduplicateMessages,
  getMessages,
  isMissingArchive,
  mapWithConcurrency,
  SESSION_ARCHIVE_CONCURRENCY,
} from './session-api-utils'

export * from './bot-chat-api'
export * from './serialize-parts'
export * from './session-api-utils'

// ---------------------------------------------------------------------------
// Session CRUD
// ---------------------------------------------------------------------------

export async function fetchSessions(): Promise<SessionListItem[]> {
  const result = await getOvResult<SessionListItem[]>(getSessions())
  return Array.isArray(result) ? result : []
}

export async function fetchSession(sessionId: string): Promise<SessionMeta> {
  return getOvResult<SessionMeta>(
    getSessionBySessionId({
      path: { session_id: sessionId },
    }),
  )
}

export async function createSession(
  sessionId?: string,
): Promise<CreateSessionResult> {
  return getOvResult<CreateSessionResult>(
    postSessions({
      body: sessionId ? { session_id: sessionId } : undefined,
    }),
  )
}

export async function fetchSessionContext(
  sessionId: string,
  tokenBudget?: number,
): Promise<SessionContextResult> {
  return getOvResult<SessionContextResult>(
    getSessionIdContext({
      path: { session_id: sessionId },
      query:
        tokenBudget === undefined ? undefined : { token_budget: tokenBudget },
    }),
  )
}

export async function fetchSessionArchive(
  sessionId: string,
  archiveId: string,
): Promise<SessionArchiveResult> {
  return getOvResult<SessionArchiveResult>(
    getSessionIdArchiveByArchiveId({
      path: { archive_id: archiveId, session_id: sessionId },
    }),
  )
}

export async function deleteSession(
  sessionId: string,
): Promise<DeleteSessionResult> {
  return getOvResult<DeleteSessionResult>(
    deleteSessionBySessionId({
      path: { session_id: sessionId },
    }),
  )
}

// ---------------------------------------------------------------------------
// Session Messages
// ---------------------------------------------------------------------------

/**
 * Fetch the complete message history.
 *
 * `/context` only contains messages after the latest completed archive, so
 * archived messages must be loaded separately and prepended in archive order.
 */
export async function fetchSessionMessages(
  sessionId: string,
  sessionMeta?: SessionMeta,
): Promise<Message[]> {
  const context = await getOvResult<SessionContextResult>(
    getSessionIdContext({
      path: { session_id: sessionId },
    }),
  )

  let commitCount = 0
  try {
    const session = sessionMeta ?? (await fetchSession(sessionId))
    commitCount = Math.max(0, Math.floor(session.commit_count || 0))
  } catch {
    // Older servers may not expose session details. Current context is still
    // useful, so preserve the previous behavior as a fallback.
  }

  const archiveIds = Array.from(
    { length: commitCount },
    (_, index) => `archive_${String(index + 1).padStart(3, '0')}`,
  )
  const archives = await mapWithConcurrency(
    archiveIds,
    SESSION_ARCHIVE_CONCURRENCY,
    async (archiveId) => {
      try {
        return await fetchSessionArchive(sessionId, archiveId)
      } catch (error) {
        if (isMissingArchive(error)) return null
        throw error
      }
    },
  )
  const archivedMessages = archives.flatMap((archive) =>
    archive ? getMessages(archive.messages) : [],
  )

  return deduplicateMessages([
    ...archivedMessages,
    ...getMessages(context.messages),
  ])
}

export async function fetchSessionMemoryDiffs(
  session: SessionMeta,
): Promise<SessionMemoryDiff[]> {
  const commitCount = Math.max(0, Math.floor(session.commit_count || 0))
  if (commitCount === 0) return []

  const sessionUri =
    session.uri?.replace(/\/+$/, '') ||
    `viking://user/${session.user.user_id}/sessions/${session.session_id}`
  const archiveIds = Array.from(
    { length: commitCount },
    (_, index) => `archive_${String(index + 1).padStart(3, '0')}`,
  )
  const results = await mapWithConcurrency(
    archiveIds,
    SESSION_ARCHIVE_CONCURRENCY,
    async (archiveId) => {
      try {
        const result = await getOvResult<unknown>(
          getContentRead({
            query: {
              limit: -1,
              offset: 0,
              raw: true,
              uri: `${sessionUri}/history/${archiveId}/memory_diff.json`,
            } as Parameters<typeof getContentRead>[0]['query'] & {
              raw?: boolean
            },
          }),
        )
        return parseSessionMemoryDiff(result, archiveId)
      } catch (error) {
        if (isMissingArchive(error)) return null
        throw error
      }
    },
  )

  return results
    .flatMap((result) => (result ? [result] : []))
    .sort((left, right) => right.archiveId.localeCompare(left.archiveId))
}

export async function addMessage(
  sessionId: string,
  role: 'user' | 'assistant',
  content?: string,
  parts?: Array<Record<string, unknown>>,
): Promise<AddMessageResult> {
  return getOvResult<AddMessageResult>(
    postSessionIdMessages({
      path: { session_id: sessionId },
      body: {
        role,
        content: parts ? undefined : content,
        parts: parts ?? undefined,
      },
    }),
  )
}

export async function commitSession(
  sessionId: string,
  keepRecentCount?: number,
): Promise<CommitSessionResult> {
  return getOvResult<CommitSessionResult>(
    postSessionIdCommit({
      body:
        keepRecentCount === undefined
          ? undefined
          : { keep_recent_count: keepRecentCount },
      path: { session_id: sessionId },
    }),
  )
}

export async function extractSession(sessionId: string): Promise<unknown> {
  return getOvResult<unknown>(
    postSessionIdExtract({
      path: { session_id: sessionId },
    }),
  )
}

export async function recordSessionUsed(
  sessionId: string,
  body: UsedRequest,
): Promise<unknown> {
  return getOvResult<unknown>(
    postSessionIdUsed({
      body,
      path: { session_id: sessionId },
    }),
  )
}

export async function fetchSessionToolResults(
  sessionId: string,
  options: { limit?: number; toolName?: string } = {},
): Promise<unknown> {
  const response = await ovClient.instance.get(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/tool-results`,
    {
      params: {
        limit: options.limit,
        tool_name: options.toolName || undefined,
      },
    },
  )
  return getOvResult<unknown>(Promise.resolve(response))
}

export async function fetchSessionToolResult(
  sessionId: string,
  toolResultId: string,
  options: { includeMetadata?: boolean; limit?: number; offset?: number } = {},
): Promise<unknown> {
  const response = await ovClient.instance.get(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/tool-results/${encodeURIComponent(
      toolResultId,
    )}`,
    {
      params: {
        include_metadata: options.includeMetadata,
        limit: options.limit,
        offset: options.offset,
      },
    },
  )
  return getOvResult<unknown>(Promise.resolve(response))
}

export async function searchSessionToolResult(
  sessionId: string,
  toolResultId: string,
  query: string,
  options: { contextChars?: number; limit?: number } = {},
): Promise<unknown> {
  const response = await ovClient.instance.get(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/tool-results/${encodeURIComponent(
      toolResultId,
    )}/search`,
    {
      params: {
        context_chars: options.contextChars,
        limit: options.limit,
        q: query,
      },
    },
  )
  return getOvResult<unknown>(Promise.resolve(response))
}
