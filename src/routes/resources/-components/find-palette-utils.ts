import { fileNameFromUri, parentUri as getParentUri } from '../-lib/normalize'

/**
 * Parses a URI into human-readable name and immediate parent directory display.
 */
export function displayName(uri: string): { name: string; parent: string } {
  const name = fileNameFromUri(uri)
  const dir = getParentUri(uri)
  const segments = dir.replace(/\/$/, '').split('/').filter(Boolean)
  const parent = segments.length > 1 ? segments.slice(-1)[0] : dir
  return { name, parent }
}

/**
 * Extracts a human-readable error description from an unknown error payload.
 */
export function errorDescription(error: unknown): string {
  if (!error) return ''
  if (error instanceof Error) return error.message
  if (typeof error === 'object') {
    const data = error as {
      code?: unknown
      message?: unknown
      statusCode?: unknown
    }
    const code = typeof data.code === 'string' ? data.code : ''
    const message = typeof data.message === 'string' ? data.message : ''
    const status =
      typeof data.statusCode === 'number' ? `HTTP ${data.statusCode}` : ''
    const readable = [status, code, message].filter(Boolean).join(' · ')
    if (readable) return readable
  }
  return String(error)
}
