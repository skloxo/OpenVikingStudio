const PUBLIC_BASE_URL = import.meta.env.BASE_URL || '/'

function trimTrailingSlash(value: string): string {
  return value.length > 1 ? value.replace(/\/+$/, '') : value
}

export function getRouterBasePath(): string {
  return '/'
}

export function resolvePublicAsset(path: string): string {
  const normalizedPath = path.replace(/^\/+/, '')

  if (!PUBLIC_BASE_URL || PUBLIC_BASE_URL === '/' || PUBLIC_BASE_URL === './') {
    return `/${normalizedPath}`
  }

  return `${PUBLIC_BASE_URL.replace(/\/?$/, '/')}${normalizedPath}`
}
