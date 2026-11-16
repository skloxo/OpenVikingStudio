import i18n from '#/i18n'
import {
  getFsStat,
  getOvResult,
  isOvClientError,
  normalizeOvClientError,
  ovClient,
  postFsMkdir,
} from '#/lib/ov-client'
import { fileNameFromUri, normalizeFsEntries } from '#/routes/resources/-lib/normalize'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import { isLiveContextDocument, sha256Hex } from './doc'
import { invalidArrangerApiResponse } from './mcp-api'
import type {
  LiveMountIndex,
  LoadedDirectory,
  MutationKind,
  TextDocument,
} from './model'
import { assertMutationBoundary, normalizeVikingUri } from './uri'

export {
  batchMountLiveContexts,
  invokeMcpToolDirect,
  loadLiveMounts,
  loadMcpCatalog,
  mountLiveContext,
  parseMcpMounts,
  parseMcpServers,
  parseMcpTools,
  unmountLiveContext,
} from './mcp-api'

type Envelope<T> = { status: string; result: T; has_more?: boolean }

const SAVE_RETRY_DELAYS_MS = [100, 200, 400]
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function isRetryableWriteConflict(error: unknown): boolean {
  const normalized = normalizeOvClientError(error)
  const details = normalized.details as Record<string, unknown> | undefined
  return normalized.code === 'CONFLICT' && details?.reason === 'BASE_HEAD_MOVED'
}

export function isNotFoundError(error: unknown): boolean {
  if (isOvClientError(error)) {
    return error.code === 'NOT_FOUND' || error.statusCode === 404
  }
  const normalized = normalizeOvClientError(error)
  return normalized.code === 'NOT_FOUND' || normalized.statusCode === 404
}

export async function statResource(uri: string): Promise<VikingFsEntry> {
  const normalized = normalizeVikingUri(uri)
  const result = await getOvResult<Record<string, unknown>>(
    getFsStat({ query: { uri: normalized } }),
  )
  if (
    typeof result !== 'object' ||
    (!('isDir' in result) && !('is_dir' in result))
  ) {
    throw invalidArrangerApiResponse('filesystemStat', result)
  }
  return {
    abstract: String(result.abstract ?? ''),
    isDir: Boolean(result.isDir ?? result.is_dir),
    modTime: String(result.modTime ?? result.mod_time ?? ''),
    modTimestamp: null,
    name: fileNameFromUri(normalized),
    overview: String(result.overview ?? ''),
    size: String(result.size ?? ''),
    sizeBytes:
      typeof result.size === 'number'
        ? result.size
        : typeof result.size_bytes === 'number'
          ? result.size_bytes
          : null,
    uri: normalized,
  }
}

export async function listDirectory(
  uri: string,
  offset = 0,
  limit = 200,
  recursive = false,
): Promise<LoadedDirectory> {
  const normalized = normalizeVikingUri(uri)
  const response = await ovClient.instance.get<Envelope<unknown>>(
    '/api/v1/fs/ls',
    {
      params: {
        uri: normalized,
        output: 'agent',
        show_all_hidden: true,
        include_abstract: true,
        recursive,
        offset,
        limit,
        sort_by: 'name',
        sort_order: 'asc',
      },
    },
  )
  const entries = normalizeFsEntries(response.data.result, normalized)
  return {
    entries,
    hasMore: Boolean(response.data.has_more),
    nextOffset: offset + entries.length,
  }
}

export async function readTextDocument(uri: string): Promise<TextDocument> {
  const response = await ovClient.instance.get<ArrayBuffer>(
    '/api/v1/content/download',
    {
      params: { uri },
      responseType: 'arraybuffer',
    },
  )
  const bytes = new Uint8Array(response.data)
  return {
    bytes,
    content: new TextDecoder('utf-8', { fatal: true }).decode(bytes),
    sha256: await sha256Hex(bytes),
  }
}

export async function readLiveContext(uri: string): Promise<unknown> {
  return getOvResult<unknown>(
    ovClient.instance.get('/api/v1/content/read', {
      params: { uri: normalizeVikingUri(uri), offset: 0, limit: -1, raw: false },
    }),
  )
}

export async function createDirectory(
  uri: string,
  description?: string,
): Promise<void> {
  await getOvResult(
    postFsMkdir({ body: { uri: normalizeVikingUri(uri), description } }),
  )
}

export async function createText(uri: string, content = ''): Promise<void> {
  await ovClient.instance.post('/api/v1/content/batch-write', {
    root_uri: normalizeVikingUri(uri).split('/').slice(0, -1).join('/'),
    wait: false,
    operations: [
      {
        uri: normalizeVikingUri(uri),
        content,
        mode: 'create',
        if_absent: true,
      },
    ],
  })
}

export async function saveText(
  uri: string,
  content: string,
  expectedSha256: string,
): Promise<void> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      await ovClient.instance.post('/api/v1/content/batch-write', {
        root_uri: normalizeVikingUri(uri).split('/').slice(0, -1).join('/'),
        wait: false,
        operations: [
          {
            uri: normalizeVikingUri(uri),
            content,
            mode: 'replace',
            expected_sha256: expectedSha256,
          },
        ],
      })
      return
    } catch (error) {
      if (
        attempt >= SAVE_RETRY_DELAYS_MS.length ||
        !isRetryableWriteConflict(error)
      ) {
        throw error
      }
      await delay(SAVE_RETRY_DELAYS_MS[attempt])
    }
  }
}

export async function copyResource(
  source: string,
  target: string,
  recursive: boolean,
): Promise<void> {
  await ovClient.instance.post('/api/v1/fs/cp', {
    from_uri: normalizeVikingUri(source),
    to_uri: normalizeVikingUri(target),
    recursive,
  })
}

export async function removeResource(
  uri: string,
  recursive: boolean,
): Promise<void> {
  await ovClient.instance.delete('/api/v1/fs', {
    params: { uri: normalizeVikingUri(uri), recursive, wait: false },
  })
}

async function assertOrdinaryFile(uri: string): Promise<void> {
  if (!uri.toLowerCase().endsWith('.md')) return
  const doc = await readTextDocument(uri)
  if (isLiveContextDocument(doc.content)) {
    throw new Error(
      i18n.t('arranger:errors.liveContextMutationRequired', { uri }),
    )
  }
}

export async function preflightOrdinaryMutation(options: {
  kind: MutationKind
  rootUri: string
  source: VikingFsEntry
  target?: string
  liveIndex: LiveMountIndex
}): Promise<void> {
  const { liveIndex, rootUri, source, target } = options
  assertMutationBoundary(source.uri, target, rootUri)
  if (!liveIndex.complete) {
    throw new Error(i18n.t('arranger:errors.mountInventoryIncomplete'))
  }
  if (liveIndex.mounts.has(normalizeVikingUri(source.uri))) {
    throw new Error(i18n.t('arranger:errors.liveContextMutationOnly'))
  }
  if (target && liveIndex.mounts.has(normalizeVikingUri(target))) {
    throw new Error(i18n.t('arranger:errors.destinationLiveContext'))
  }
  if (!source.isDir) {
    await assertOrdinaryFile(source.uri)
    return
  }
  const prefix = `${normalizeVikingUri(source.uri)}/`
  if ([...liveIndex.mounts.keys()].some((uri) => uri.startsWith(prefix))) {
    throw new Error(i18n.t('arranger:errors.directoryContainsLiveContext'))
  }
  let offset = 0
  for (;;) {
    let page: LoadedDirectory
    try {
      page = await listDirectory(source.uri, offset, 500, true)
      await Promise.all(
        page.entries
          .filter((entry) => !entry.isDir)
          .map((entry) => assertOrdinaryFile(entry.uri)),
      )
    } catch (error) {
      throw new Error(
        i18n.t('arranger:errors.preflightFailedWithDetail', {
          detail: normalizeOvClientError(error).message,
        }),
      )
    }
    if (!page.hasMore) return
    if (page.nextOffset <= offset) {
      throw new Error(i18n.t('arranger:errors.preflightFailed'))
    }
    offset = page.nextOffset
  }
}

export async function mutateOrdinaryResource(options: {
  kind: MutationKind
  rootUri: string
  source: VikingFsEntry
  target?: string
  liveIndex: LiveMountIndex
}): Promise<void> {
  await preflightOrdinaryMutation(options)
  if (options.kind === 'delete') {
    await removeResource(options.source.uri, options.source.isDir)
  } else if (options.target) {
    await copyResource(options.source.uri, options.target, options.source.isDir)
  }
}
