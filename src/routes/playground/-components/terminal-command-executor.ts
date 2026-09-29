/**
 * terminal-command-executor.ts
 * 从 terminal-panel.tsx 接缝提取的命令执行引擎。
 * executeTerminalCommand 是一个纯异步函数，不依赖任何 React hook。
 * TerminalPanel 中的 runCommand useCallback 调用此函数，只剩 ~20 行胶水代码。
 */
import {
  addMessage,
  commitSession,
  createSession,
  deleteSession,
  extractSession,
  fetchSession,
  fetchSessionArchive,
  fetchSessionContext,
  fetchSessionMessages,
  fetchSessions,
  fetchSessionToolResult,
  fetchSessionToolResults,
  recordSessionUsed,
  searchSessionToolResult,
} from '#/lib/sessions/api'
import {
  getHealth,
  getOvResult,
  getSystemStatus,
  postSystemWait,
} from '#/lib/ov-client'
import {
  fetchDirectoryLevelContent,
  fetchFileContent,
  fetchFsList,
  fetchFsStat,
  fetchFsTree,
  fetchSearch,
} from '#/routes/resources/-lib/api'
import { normalizeDirUri } from '#/routes/resources/-lib/normalize'
import type { ResourceOpenHandler, TerminalEntry, ResourceRef } from '../-lib/types'
import {
  cleanVikingUri,
  entryToRef,
  registerPlaygroundAgentSessionId,
  searchResultToRefs,
  visibleContextEntries,
} from '../-lib/utils'
import { ROOT_URI } from '../-lib/constants'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import {
  formatJson,
  getBooleanFlag,
  getLastFlag,
  getNumberFlag,
  joinBodyLines,
  parseOptions,
  parseScopedSearchInput,
  parseWaitTimeout,
} from './terminal-panel-utils'

// ─── Types ───────────────────────────────────────────────────────────────────

type FindGroup = 'memories' | 'resources' | 'skills'

// ─── Context Object ───────────────────────────────────────────────────────────

export type CommandExecutorContext = {
  currentUri: string
  entries: VikingFsEntry[]
  groupLabels: Record<FindGroup, string>
  identityScopeKey: string | undefined
  onOpenAddResource: () => void
  onOpenResource: ResourceOpenHandler
  onSessionChange: (sessionId: string) => void
  sessionId: string | undefined
  t: (key: string, options?: Record<string, unknown>) => string
  append: (entry: Omit<TerminalEntry, 'id'>) => void
}

// ─── Session Ref Helper ───────────────────────────────────────────────────────

function sessionRef(id: string): ResourceRef {
  return {
    label: id,
    meta: 'session',
    uri: `viking://session/${id}`,
  }
}

// ─── Main Command Executor ────────────────────────────────────────────────────

/**
 * Executes a single terminal command given its parsed name, body, and context.
 * Throws on unknown commands or validation errors (caller handles try/catch).
 */
export async function executeTerminalCommand(
  name: string,
  body: string,
  trimmed: string,
  ctx: CommandExecutorContext,
): Promise<void> {
  const {
    append,
    currentUri,
    entries,
    groupLabels,
    identityScopeKey,
    onOpenAddResource,
    onOpenResource,
    onSessionChange,
    sessionId,
    t,
  } = ctx

  // Viking URI shorthand: open resource directly
  if (trimmed.startsWith('viking://')) {
    await onOpenResource(trimmed)
    append({
      kind: 'success',
      refs: [{ uri: trimmed }],
      title: t('terminal.opened'),
    })
    return
  }

  switch (name) {
    case '/status': {
      const root = await fetchFsList(ROOT_URI, { nodeLimit: 12 })
      const status =
        await getOvResult<Record<string, unknown>>(getSystemStatus())
      append({
        body: `${t('terminal.onlineBody', { count: root.entries.length })}\n\n${formatJson(status)}`,
        kind: 'success',
        refs: root.entries.slice(0, 6).map(entryToRef),
        title: t('terminal.onlineTitle'),
      })
      return
    }
    case '/health': {
      const health =
        await getOvResult<Record<string, unknown>>(getHealth())
      append({
        body: formatJson(health),
        kind: 'success',
        title: 'health',
      })
      return
    }
    case '/wait': {
      const timeout = parseWaitTimeout(body)
      const result = await getOvResult<unknown>(
        postSystemWait({ body: { timeout } }),
      )
      append({
        body: formatJson(result),
        kind: 'success',
        title: 'wait',
      })
      return
    }
    case '/ls': {
      const target = body ? normalizeDirUri(body) : currentUri
      const result = body
        ? await fetchFsList(target, {
            nodeLimit: 60,
            output: 'agent',
            showAllHidden: true,
          })
        : { entries, uri: currentUri }
      const visibleEntries = visibleContextEntries(result.entries)
      append({
        body: t('terminal.lsBody', { count: visibleEntries.length, uri: target }),
        kind: 'success',
        refs: visibleEntries.map(entryToRef),
        title: `ls ${target}`,
      })
      return
    }
    case '/tree': {
      const target = body ? normalizeDirUri(body) : currentUri
      const result = await fetchFsTree(target, {
        nodeLimit: 80,
        output: 'agent',
        showAllHidden: true,
      })
      const visibleEntries = visibleContextEntries(result.nodes)
      append({
        body: t('terminal.lsBody', { count: visibleEntries.length, uri: target }),
        kind: 'success',
        refs: visibleEntries.map(entryToRef),
        title: `tree ${target}`,
      })
      return
    }
    case '/stat': {
      if (!body) throw new Error(t('terminal.enterUri'))
      const uri = cleanVikingUri(body)
      if (!uri) throw new Error(t('terminal.enterUri'))
      const entry = await fetchFsStat(uri, { throwOnError: true })
      append({
        body: formatJson(entry),
        kind: 'success',
        refs: [entryToRef(entry)],
        title: `stat ${uri}`,
      })
      return
    }
    case '/read': {
      if (!body) throw new Error(t('terminal.readUsage'))
      const uri = cleanVikingUri(body)
      if (!uri) throw new Error(t('terminal.enterUri'))
      const content = await fetchFileContent(uri, { limit: 1200, raw: true })
      await onOpenResource(uri)
      append({
        body: content.content.slice(0, 1200) || t('terminal.fileEmpty'),
        kind: 'success',
        refs: [{ uri }],
        title: `read ${uri}`,
      })
      return
    }
    case '/abstract':
    case '/overview': {
      if (!body) throw new Error(t('terminal.enterUri'))
      const uri = cleanVikingUri(body)
      if (!uri) throw new Error(t('terminal.enterUri'))
      const level = name === '/abstract' ? 'abstract' : 'overview'
      const content = await fetchDirectoryLevelContent(uri, level)
      await onOpenResource(uri)
      append({
        body: content || t('terminal.fileEmpty'),
        kind: 'success',
        refs: [{ uri }],
        title: `${name.slice(1)} ${uri}`,
      })
      return
    }
    case '/find':
    case '/search': {
      const { query, scopeUri } = parseScopedSearchInput(
        body,
        currentUri,
        t('terminal.searchUsage', { name }),
      )
      if (!query) throw new Error(t('terminal.searchUsage', { name }))
      const result = await fetchSearch(query, { limit: 8, targetUri: scopeUri })
      const scopeText = scopeUri ?? t('terminal.globalScope')
      const summary = t('terminal.hits', {
        memories: result.memories.length,
        resources: result.resources.length,
        skills: result.skills.length,
      })
      append({
        body: joinBodyLines([
          t('terminal.searchScopeLine', { scope: scopeText }),
          result.query_plan?.reasoning || summary,
          result.query_plan?.reasoning ? summary : undefined,
        ]),
        kind: 'success',
        refs: searchResultToRefs(result, groupLabels),
        title: `${name} ${body}`,
      })
      return
    }
    case '/add-resource': {
      onOpenAddResource()
      append({
        body: t('terminal.addResourceBody'),
        kind: 'info',
        title: t('terminal.addResourceTitle'),
      })
      return
    }
    case '/session': {
      await executeSessionCommand(body, ctx, sessionId, identityScopeKey, onSessionChange, sessionRef)
      return
    }
    default:
      throw new Error(t('terminal.unknownCommand'))
  }
}

// ─── Session Sub-Command Handler ──────────────────────────────────────────────

async function executeSessionCommand(
  body: string,
  ctx: CommandExecutorContext,
  sessionId: string | undefined,
  identityScopeKey: string | undefined,
  onSessionChange: (id: string) => void,
  makeSessionRef: (id: string) => ResourceRef,
): Promise<void> {
  const { append, t } = ctx
  const { flags, positional } = parseOptions(body)
  const subcommand = positional.shift() ?? 'current'

  const requireCurrentSession = () => {
    if (!sessionId) throw new Error(t('terminal.sessionMissing'))
    return sessionId
  }
  const resolveSessionId = () =>
    positional.shift() ?? requireCurrentSession()

  switch (subcommand) {
    case 'current': {
      const id = requireCurrentSession()
      append({
        body: t('terminal.sessionCurrentBody', { id }),
        kind: 'success',
        refs: [makeSessionRef(id)],
        title: '/session current',
      })
      return
    }
    case 'list': {
      const sessions = await fetchSessions()
      append({
        body: t('terminal.sessionListBody', { count: sessions.length }),
        kind: 'success',
        refs: sessions.map((s) => makeSessionRef(s.session_id)),
        title: '/session list',
      })
      return
    }
    case 'create': {
      const requestedId = positional.shift()
      const result = await createSession(requestedId)
      if (identityScopeKey !== undefined) {
        registerPlaygroundAgentSessionId(result.session_id, identityScopeKey)
      }
      onSessionChange(result.session_id)
      append({
        body: joinBodyLines([
          t('terminal.sessionCreatedBody', { id: result.session_id }),
          formatJson(result),
        ]),
        kind: 'success',
        refs: [makeSessionRef(result.session_id)],
        title: '/session create',
      })
      return
    }
    case 'switch': {
      const id = positional.shift()
      if (!id) throw new Error(t('terminal.sessionUsage'))
      if (identityScopeKey !== undefined) {
        registerPlaygroundAgentSessionId(id, identityScopeKey)
      }
      onSessionChange(id)
      append({
        body: t('terminal.sessionSwitchedBody', { id }),
        kind: 'success',
        refs: [makeSessionRef(id)],
        title: `/session switch ${id}`,
      })
      return
    }
    case 'get': {
      const id = resolveSessionId()
      const result = await fetchSession(id)
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session get ${id}` })
      return
    }
    case 'context': {
      const id = resolveSessionId()
      const result = await fetchSessionContext(id, getNumberFlag(flags, 'token-budget'))
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session context ${id}` })
      return
    }
    case 'messages': {
      const id = resolveSessionId()
      const result = await fetchSessionMessages(id)
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session messages ${id}` })
      return
    }
    case 'archive': {
      const id = positional.length > 1 ? positional.shift()! : requireCurrentSession()
      const archiveId = positional.shift()
      if (!archiveId) throw new Error(t('terminal.sessionUsage'))
      const result = await fetchSessionArchive(id, archiveId)
      append({
        body: formatJson(result),
        kind: 'success',
        refs: [{ label: archiveId, meta: 'archive', uri: `viking://session/${id}/history/${archiveId}` }],
        title: `/session archive ${id} ${archiveId}`,
      })
      return
    }
    case 'commit': {
      const id = resolveSessionId()
      const result = await commitSession(id, getNumberFlag(flags, 'keep-recent'))
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session commit ${id}` })
      return
    }
    case 'extract': {
      const id = resolveSessionId()
      const result = await extractSession(id)
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session extract ${id}` })
      return
    }
    case 'message': {
      const roleIndex = positional.findIndex(
        (item) => item === 'user' || item === 'assistant',
      )
      if (roleIndex < 0) throw new Error(t('terminal.sessionUsage'))
      const id = roleIndex > 0 ? positional.slice(0, roleIndex).join(' ') : requireCurrentSession()
      const role = positional[roleIndex] as 'user' | 'assistant'
      const content = positional.slice(roleIndex + 1).join(' ').trim()
      if (!content) throw new Error(t('terminal.sessionUsage'))
      const result = await addMessage(id, role, content)
      append({
        body: joinBodyLines([t('terminal.sessionMessageAddedBody', { id }), formatJson(result)]),
        kind: 'success',
        refs: [makeSessionRef(id)],
        title: `/session message ${id}`,
      })
      return
    }
    case 'used': {
      const id = resolveSessionId()
      const contexts = flags.get('context')
      const skillJson = getLastFlag(flags, 'skill-json')
      const result = await recordSessionUsed(id, {
        contexts,
        skill: skillJson ? JSON.parse(skillJson) : undefined,
      })
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session used ${id}` })
      return
    }
    case 'tool-results': {
      const id = resolveSessionId()
      const result = await fetchSessionToolResults(id, {
        limit: getNumberFlag(flags, 'limit'),
        toolName: getLastFlag(flags, 'tool-name'),
      })
      append({ body: formatJson(result), kind: 'success', refs: [makeSessionRef(id)], title: `/session tool-results ${id}` })
      return
    }
    case 'tool-result': {
      const id = positional.length > 1 ? positional.shift()! : requireCurrentSession()
      const toolResultId = positional.shift()
      if (!toolResultId) throw new Error(t('terminal.sessionUsage'))
      const result = await fetchSessionToolResult(id, toolResultId, {
        includeMetadata: !getBooleanFlag(flags, 'no-metadata'),
        limit: getNumberFlag(flags, 'limit'),
        offset: getNumberFlag(flags, 'offset'),
      })
      append({
        body: formatJson(result),
        kind: 'success',
        refs: [{ label: toolResultId, meta: 'tool result', uri: `viking://session/${id}/tool-results/${toolResultId}` }],
        title: `/session tool-result ${id} ${toolResultId}`,
      })
      return
    }
    case 'tool-search': {
      const id = positional.length > 2 ? positional.shift()! : requireCurrentSession()
      const toolResultId = positional.shift()
      const query = positional.join(' ').trim()
      if (!toolResultId || !query) throw new Error(t('terminal.sessionUsage'))
      const result = await searchSessionToolResult(id, toolResultId, query, {
        contextChars: getNumberFlag(flags, 'context-chars'),
        limit: getNumberFlag(flags, 'limit'),
      })
      append({
        body: formatJson(result),
        kind: 'success',
        refs: [{ label: toolResultId, meta: 'tool search', uri: `viking://session/${id}/tool-results/${toolResultId}` }],
        title: `/session tool-search ${id} ${toolResultId}`,
      })
      return
    }
    case 'delete': {
      const id = positional.shift()
      if (!id) throw new Error(t('terminal.sessionDeleteUsage'))
      const result = await deleteSession(id)
      append({
        body: joinBodyLines([t('terminal.sessionDeletedBody', { id }), formatJson(result)]),
        kind: 'success',
        title: `/session delete ${id}`,
      })
      return
    }
    default:
      throw new Error(t('terminal.sessionUsage'))
  }
}
