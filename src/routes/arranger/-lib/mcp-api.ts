import i18n from '#/i18n'
import { getOvResult, normalizeOvClientError, ovClient } from '#/lib/ov-client'
import type {
  BatchLiveContextResult,
  JsonSchema,
  LiveContextMount,
  LiveMountIndex,
  McpCatalog,
  McpCatalogTool,
  McpServerInfo,
  MountInput,
} from './model'
import { isWithinRoot, normalizeVikingUri } from './uri'

type Envelope<T> = { status: string; result: T; has_more?: boolean }

export function invalidArrangerApiResponse(
  resource:
    | 'filesystemStat'
    | 'mcpMountList'
    | 'mcpServerList'
    | 'mcpToolCatalog',
  value: unknown,
): Error {
  const details =
    typeof value === 'string' && value.toLowerCase().includes('<html')
      ? ` — ${i18n.t('arranger:errors.studioHtmlResponse')}`
      : ''
  return new Error(
    `${i18n.t('arranger:errors.invalidApiResponse', {
      resource: i18n.t(`arranger:apiResources.${resource}`),
    })}${details}`,
  )
}

export function parseMcpServers(value: unknown): McpServerInfo[] {
  const servers = Array.isArray(value)
    ? value
    : value &&
        typeof value === 'object' &&
        'servers' in value &&
        Array.isArray((value as { servers?: unknown }).servers)
      ? (value as { servers: unknown[] }).servers
      : null
  if (
    !servers ||
    servers.some(
      (server) =>
        !server ||
        typeof server !== 'object' ||
        !('name' in server) ||
        typeof server.name !== 'string' ||
        !server.name,
    )
  ) {
    throw invalidArrangerApiResponse('mcpServerList', value)
  }
  return servers.map((server) => {
    const parsed = server as { name: string; root_uri?: unknown }
    return {
      name: parsed.name,
      root_uri:
        typeof parsed.root_uri === 'string' && parsed.root_uri
          ? normalizeVikingUri(parsed.root_uri)
          : 'viking://agent/tools',
    }
  })
}

export function parseMcpMounts(value: unknown): LiveContextMount[] {
  const mounts = Array.isArray(value)
    ? value
    : value &&
        typeof value === 'object' &&
        'mounts' in value &&
        Array.isArray((value as { mounts?: unknown }).mounts)
      ? (value as { mounts: unknown[] }).mounts
      : null
  if (!mounts) throw invalidArrangerApiResponse('mcpMountList', value)
  return mounts as LiveContextMount[]
}

export function parseMcpTools(
  server: string,
  value: unknown,
  rootUri = 'viking://agent/tools',
): McpCatalogTool[] {
  const tools =
    value &&
    typeof value === 'object' &&
    'tools' in value &&
    Array.isArray((value as { tools?: unknown }).tools)
      ? (value as { tools: unknown[] }).tools
      : null
  if (!tools) throw invalidArrangerApiResponse('mcpToolCatalog', value)
  return tools.map((document) => {
    if (
      !document ||
      typeof document !== 'object' ||
      !('tool' in document) ||
      !document.tool ||
      typeof document.tool !== 'object' ||
      !('name' in document.tool) ||
      typeof document.tool.name !== 'string'
    ) {
      throw invalidArrangerApiResponse('mcpToolCatalog', value)
    }
    const tool = document.tool as Record<string, unknown>
    const doc = document as Record<string, unknown>
    const name = tool.name as string
    return {
      input_revision:
        typeof doc.input_revision === 'string' ? doc.input_revision : '',
      revision: typeof doc.revision === 'string' ? doc.revision : '',
      server,
      tool: {
        annotations:
          tool.annotations && typeof tool.annotations === 'object'
            ? (tool.annotations as Record<string, unknown>)
            : undefined,
        description:
          typeof tool.description === 'string' ? tool.description : undefined,
        inputSchema:
          tool.inputSchema && typeof tool.inputSchema === 'object'
            ? (tool.inputSchema as JsonSchema)
            : { type: 'object' },
        name,
        title: typeof tool.title === 'string' ? tool.title : undefined,
      },
      uri:
        typeof doc.uri === 'string'
          ? normalizeVikingUri(doc.uri)
          : `${normalizeVikingUri(rootUri)}/${server}/${name}.json`,
    }
  })
}

export async function loadMcpCatalog(): Promise<McpCatalog> {
  const serverResult = await getOvResult<unknown>(
    ovClient.instance.get('/api/v1/mcps'),
  )
  const servers = parseMcpServers(serverResult)
  const settled = await Promise.allSettled(
    servers.map(async ({ name, root_uri }) => {
      const result = await getOvResult<unknown>(
        ovClient.instance.get(`/api/v1/mcps/${encodeURIComponent(name)}`, {
          params: { target_uri: root_uri },
        }),
      )
      return {
        name,
        root_uri,
        tools: parseMcpTools(name, result, root_uri),
      }
    }),
  )
  const loaded = settled.flatMap((item) =>
    item.status === 'fulfilled' ? [item.value] : [],
  )
  const failed = settled.find(
    (item): item is PromiseRejectedResult => item.status === 'rejected',
  )
  return {
    complete: !failed,
    error: failed ? normalizeOvClientError(failed.reason).message : undefined,
    servers: loaded,
    tools: loaded.flatMap((server) => server.tools),
  }
}

export async function invokeMcpToolDirect(
  toolUri: string,
  args: Record<string, unknown>,
): Promise<unknown> {
  return getOvResult<unknown>(
    ovClient.instance.post('/api/v1/mcps/invoke', {
      uri: normalizeVikingUri(toolUri),
      arguments: args,
    }),
  )
}

export async function loadLiveMounts(rootUri: string): Promise<LiveMountIndex> {
  try {
    const serverResult = await getOvResult<unknown>(
      ovClient.instance.get('/api/v1/mcps'),
    )
    const servers = parseMcpServers(serverResult)
    const settled = await Promise.allSettled(
      servers.map(async ({ name, root_uri }) => {
        const mountResult = await getOvResult<unknown>(
          ovClient.instance.get('/api/v1/mcps/mounts', {
            params: { mcp: name, target_uri: root_uri },
          }),
        )
        return parseMcpMounts(mountResult)
      }),
    )
    const mounts = new Map<string, LiveContextMount>()
    for (const item of settled) {
      if (item.status !== 'fulfilled') continue
      for (const mount of item.value) {
        if (isWithinRoot(mount.node_uri, rootUri)) {
          mounts.set(normalizeVikingUri(mount.node_uri), mount)
        }
      }
    }
    const failed = settled.find(
      (item): item is PromiseRejectedResult => item.status === 'rejected',
    )
    return {
      complete: !failed,
      error: failed ? normalizeOvClientError(failed.reason).message : undefined,
      mounts,
    }
  } catch (error) {
    return {
      complete: false,
      error: normalizeOvClientError(error).message,
      mounts: new Map(),
    }
  }
}

export async function mountLiveContext(input: MountInput): Promise<void> {
  await ovClient.instance.post('/api/v1/mcps/mount', {
    ...input,
    node_uri: normalizeVikingUri(input.node_uri),
    wait: false,
  })
}

export async function batchMountLiveContexts(
  mounts: MountInput[],
): Promise<BatchLiveContextResult> {
  const response = await ovClient.instance.post<
    Envelope<BatchLiveContextResult>
  >('/api/v1/mcps/batch-mount', {
    mounts: mounts.map((mount) => ({
      ...mount,
      node_uri: normalizeVikingUri(mount.node_uri),
    })),
    wait: false,
  })
  return response.data.result
}

export async function unmountLiveContext(nodeUri: string): Promise<void> {
  await ovClient.instance.delete('/api/v1/mcps/mount', {
    params: { node_uri: normalizeVikingUri(nodeUri), wait: false },
  })
}
