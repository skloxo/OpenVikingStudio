import { getOvResult, ovClient } from '#/lib/ov-client'

export type ResourceTransferOperation = 'copy' | 'move'

export function isSharedResourceUri(uri: string): boolean {
  const normalized = uri.replace(/\/$/, '')
  return (
    normalized.startsWith('viking://resources/') &&
    normalized.length > 'viking://resources/'.length
  )
}

export function isValidTransferTarget(source: string, target: string): boolean {
  const normalizedTarget = target.replace(/\/$/, '')
  if (
    !normalizedTarget.startsWith('viking://resources/') ||
    normalizedTarget === source
  ) {
    return false
  }
  try {
    return !decodeURIComponent(normalizedTarget)
      .replace(/\\/g, '/')
      .split('/')
      .some((segment) => segment === '.' || segment === '..')
  } catch {
    return false
  }
}

export async function transferSharedResource(
  operation: ResourceTransferOperation,
  fromUri: string,
  toUri: string,
  _isDirectory?: boolean,
): Promise<{ from_uri?: string; to_uri?: string }> {
  const endpoint =
    operation === 'copy' ? '/api/v1/resources/cp' : '/api/v1/resources/mv'
  return getOvResult<{ from_uri?: string; to_uri?: string }>(
    ovClient.instance.post(endpoint, {
      from_uri: fromUri,
      to_uri: toUri,
    }),
  )
}

export async function deleteSharedResource(
  uri: string,
  recursive: boolean,
): Promise<{ uri?: string; semantic_status?: string; semanticStatus?: string }> {
  const res = await getOvResult<{
    uri?: string
    semantic_status?: string
    semanticStatus?: string
  }>(
    ovClient.instance.delete('/api/v1/resources', {
      params: { uri, recursive },
    }),
  )
  return {
    ...res,
    semanticStatus: res?.semanticStatus ?? res?.semantic_status,
  }
}
