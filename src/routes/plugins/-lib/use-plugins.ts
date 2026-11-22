/**
 * use-plugins.ts
 * 插件中心 React Query 数据钩子与状态聚合。
 * 核心契约：30s 轮询，切后台物理断流休眠 (refetchIntervalInBackground: false)。
 */

import * as React from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useAppConnection } from '#/hooks/use-app-connection'
import { getOvResult, ovClient } from '#/lib/ov-client'
import type {
  PluginsHealthSummary,
  QuadPluginItem,
} from './plugin-types'

export async function fetchPluginsList(): Promise<QuadPluginItem[]> {
  const res = await getOvResult<{ plugins: QuadPluginItem[] }>(
    ovClient.client.get({
      url: '/api/v1/plugins',
    }),
  )
  return res.plugins ?? []
}

async function fetchPluginsHealth(): Promise<PluginsHealthSummary | null> {
  try {
    const res = await getOvResult<PluginsHealthSummary>(
      ovClient.client.get({
        url: '/api/v1/plugins/health/summary',
      }),
    )
    return res
  } catch {
    try {
      const fallbackRes = await getOvResult<PluginsHealthSummary>(
        ovClient.client.get({
          url: '/api/v1/plugins/health',
        }),
      )
      return fallbackRes
    } catch {
      return null
    }
  }
}

export function usePluginsData() {
  const { identityScopeKey } = useAppConnection()
  const [selectedPlugin, setSelectedPlugin] = React.useState<QuadPluginItem | null>(null)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [categoryFilter, setCategoryFilter] = React.useState<'all' | 'platform' | 'user'>('all')

  const pluginsQuery = useQuery({
    placeholderData: keepPreviousData,
    queryFn: fetchPluginsList,
    queryKey: ['plugins', 'list', identityScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    retry: 1,
    staleTime: 15_000,
  })

  const healthQuery = useQuery({
    placeholderData: keepPreviousData,
    queryFn: fetchPluginsHealth,
    queryKey: ['plugins', 'health', identityScopeKey],
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    staleTime: 15_000,
  })

  const plugins = pluginsQuery.data ?? []
  const healthSummary = healthQuery.data

  const filteredPlugins = React.useMemo(() => {
    return plugins.filter((p) => {
      if (categoryFilter !== 'all' && p.category !== categoryFilter) {
        return false
      }
      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      return (
        p.name.toLowerCase().includes(q) ||
        p.plugin_id.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
      )
    })
  }, [plugins, categoryFilter, searchQuery])

  return {
    categoryFilter,
    error: pluginsQuery.error,
    filteredPlugins,
    healthQuery,
    healthSummary,
    isError: pluginsQuery.isError,
    isLoading: pluginsQuery.isLoading,
    plugins,
    pluginsQuery,
    refetch: pluginsQuery.refetch,
    searchQuery,
    selectedPlugin,
    setCategoryFilter,
    setSearchQuery,
    setSelectedPlugin,
  }
}
