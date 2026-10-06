import { useQuery } from '@tanstack/react-query'
import { fetchServerHealth } from './use-server-mode'
import { useAppConnection } from './use-app-connection'

export interface ServerVersionDetails {
  version: string
  appVersion: string
  remoteVersion: string
  isDrifted: boolean
}

/**
 * 实时获取当前 OpenViking 服务的详细版本信息。
 * 包含 UI 编译版本、服务端运行版本与版本漂移/脱节状态。
 */
export function useServerVersionDetails(): ServerVersionDetails {
  const { connection } = useAppConnection()
  const baseUrl = connection.baseUrl

  const { data: remoteVersion = '' } = useQuery({
    queryKey: ['server-version', baseUrl],
    queryFn: async () => {
      try {
        const health = await fetchServerHealth(baseUrl)
        return typeof health.version === 'string' && health.version.trim()
          ? health.version.trim()
          : ''
      } catch {
        return ''
      }
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  const appVersion = __APP_VERSION__
  const isDrifted = Boolean(remoteVersion && remoteVersion !== appVersion)

  return {
    version: remoteVersion || appVersion,
    appVersion,
    remoteVersion,
    isDrifted,
  }
}

/**
 * 实时获取当前 OpenViking 服务的动态运行版本号。
 * 优先读取 /health 返回的真实运行时版本，离线或等待期间 fallback 至编译期 __APP_VERSION__。
 */
export function useServerVersion(): string {
  const details = useServerVersionDetails()
  return details.version
}
