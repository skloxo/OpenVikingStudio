import { useQuery } from '@tanstack/react-query'
import { fetchServerHealth } from './use-server-mode'
import { useAppConnection } from './use-app-connection'

/**
 * 实时获取当前 OpenViking 服务的动态运行版本号。
 * 优先读取 /health 返回的真实运行时版本，离线或等待期间 fallback 至编译期 __APP_VERSION__。
 */
export function useServerVersion(): string {
  const { connection } = useAppConnection()
  const baseUrl = connection.baseUrl

  const { data: remoteVersion } = useQuery({
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

  return remoteVersion || __APP_VERSION__
}
